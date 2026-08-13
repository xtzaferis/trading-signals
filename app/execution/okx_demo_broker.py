from datetime import datetime, timezone
from uuid import uuid4

import ccxt

from app.config.settings import QUOTE_CURRENCY
from app.core.logger import logger
from app.exceptions import OrderValidationError
from app.execution.broker import Broker
from app.execution.okx_order_gateway import OKXOrderGateway
from app.models.position import Position
from app.models.trade_plan import TradePlan
from app.storage.exchange_position_repository import (
    ExchangePositionRepository,
)
from app.trading.portfolio import Portfolio


class OKXDemoBroker(Broker):
    """Execute spot orders in OKX demo mode from confirmed fills only."""

    def __init__(
        self,
        portfolio: Portfolio,
        gateway: OKXOrderGateway,
        position_repository=None,
        id_factory=None,
    ):
        self.portfolio = portfolio
        self.gateway = gateway
        self.positions = (
            position_repository or ExchangePositionRepository()
        )
        self.id_factory = id_factory or self._new_client_order_id
        self._restore_positions()

    def sync_balance(self) -> float:
        """Use free demo quote balance as the next trade's cash ceiling."""
        balance = self.gateway.client.get_balance()
        free = (balance.get("free") or {}).get(QUOTE_CURRENCY)
        if free is None:
            free = (balance.get(QUOTE_CURRENCY) or {}).get("free", 0.0)
        self.portfolio.cash = max(0.0, float(free or 0.0))
        return self.portfolio.cash

    def open(
        self,
        trade_plan: TradePlan,
        opened_at: datetime,
    ) -> Position | None:
        if self.positions.find_active(trade_plan.symbol) is not None:
            return None
        if self.portfolio.has_open_position(trade_plan.symbol):
            return None

        amount = trade_plan.position_size / trade_plan.entry
        client_order_id = self.id_factory("entry")
        prepared = self.positions.prepare_entry(
            client_order_id,
            trade_plan.symbol,
            amount,
            trade_plan.entry,
            trade_plan.stop_loss,
            trade_plan.take_profit,
        )
        if not prepared:
            return None

        try:
            order = self.gateway.submit_market_order(
                symbol=trade_plan.symbol,
                side="buy",
                amount=amount,
                reference_price=trade_plan.entry,
                client_order_id=client_order_id,
            )
        except OrderValidationError as error:
            self.positions.record_entry_status(
                client_order_id,
                "ENTRY_REJECTED",
                str(error),
            )
            raise
        except (
            ccxt.NetworkError,
            ccxt.ExchangeError,
            ConnectionError,
            TimeoutError,
        ) as error:
            self.positions.record_entry_status(
                client_order_id,
                "ENTRY_UNKNOWN",
                str(error),
            )
            raise

        position = self._activate_confirmed_entry(
            client_order_id,
            trade_plan,
            order,
            opened_at,
        )
        if position is None:
            self.positions.record_entry_status(
                client_order_id,
                "PENDING_ENTRY",
            )
        return position

    def update(
        self,
        position: Position,
        high: float,
        low: float,
        close: float,
        timestamp: datetime,
    ) -> bool:
        stored = self.positions.find_active(position.symbol)
        if stored is None:
            return False
        if stored["protection_status"] in {
            "ACTIVE", "PENDING", "UNKNOWN", "TRIGGERED"
        }:
            # OKX owns the exit while an OCO may exist. Sending another sell
            # here could double-close a spot position.
            position.update_price(close)
            return False
        if stored["status"] in {"PENDING_EXIT", "EXIT_UNKNOWN"}:
            return self._sync_pending_exit(position, stored, timestamp)

        if low <= position.stop_loss:
            return self.close(
                position,
                position.stop_loss,
                "STOP_LOSS",
                timestamp,
            )
        if high >= position.take_profit:
            return self.close(
                position,
                position.take_profit,
                "TAKE_PROFIT",
                timestamp,
            )

        position.update_price(close)
        return False

    def close(
        self,
        position: Position,
        price: float,
        reason: str = "MANUAL",
        timestamp: datetime | None = None,
    ) -> bool:
        stored = self.positions.find_active(position.symbol)
        if stored is None or stored["status"] != "OPEN":
            return False

        client_order_id = self.id_factory("exit")
        if not self.positions.prepare_exit(
            stored["entry_client_order_id"],
            client_order_id,
            reason,
        ):
            return False
        stored = self.positions.find_active(position.symbol)

        try:
            order = self.gateway.submit_market_order(
                symbol=position.symbol,
                side="sell",
                amount=position.quantity,
                reference_price=price,
                client_order_id=client_order_id,
            )
        except OrderValidationError as error:
            self.positions.reset_exit(
                stored["entry_client_order_id"],
                str(error),
            )
            raise
        except (
            ccxt.NetworkError,
            ccxt.ExchangeError,
            ConnectionError,
            TimeoutError,
        ) as error:
            self.positions.record_entry_status(
                stored["entry_client_order_id"],
                "EXIT_UNKNOWN",
                str(error),
            )
            raise

        return self._close_from_fill(
            position,
            stored,
            order,
            timestamp or datetime.now(timezone.utc),
        )

    def reconcile(self) -> dict:
        order_result = self.gateway.reconcile_intents()
        restored_entries = 0
        closed_exits = 0

        for stored in self.positions.pending_entries():
            intent = self.gateway.order_repository.get(
                stored["entry_client_order_id"]
            )
            if intent is None or intent["status"] != "FILLED":
                continue
            order = self._order_from_intent(intent)
            plan = TradePlan(
                symbol=stored["symbol"],
                action="BUY",
                entry=stored["planned_entry"],
                stop_loss=stored["stop_loss"],
                take_profit=stored["take_profit"],
                position_size=(
                    stored["requested_amount"] * stored["planned_entry"]
                ),
                risk_reward=self._risk_reward(stored),
            )
            position = self._activate_confirmed_entry(
                stored["entry_client_order_id"],
                plan,
                order,
                datetime.now(timezone.utc),
            )
            restored_entries += position is not None

        for stored in self.positions.open_positions():
            if stored["status"] not in {"PENDING_EXIT", "EXIT_UNKNOWN"}:
                continue
            position = self._portfolio_position(stored["symbol"])
            if position is None or not stored["exit_client_order_id"]:
                continue
            intent = self.gateway.order_repository.get(
                stored["exit_client_order_id"]
            )
            if intent is None or intent["status"] != "FILLED":
                continue
            closed_exits += self._close_from_fill(
                position,
                stored,
                self._order_from_intent(intent),
                datetime.now(timezone.utc),
            )

        unprotected = []
        for stored in self.positions.open_positions():
            if stored["status"] != "OPEN":
                continue
            position = self._portfolio_position(stored["symbol"])
            if position is None:
                continue
            if not self._reconcile_native_protection(position, stored):
                unprotected.append(stored["symbol"])

        return {
            **order_result,
            "restored_entries": restored_entries,
            "closed_exits": closed_exits,
            "unprotected_symbols": unprotected,
            "safe": bool(order_result.get("safe")) and not unprotected,
        }

    def _ensure_native_protection(self, position: Position) -> bool:
        stored = self.positions.find_active(position.symbol)
        if stored is None:
            return False
        client_order_id = stored["protection_client_order_id"]
        if client_order_id is None:
            client_order_id = self.id_factory("protect")
            if not self.positions.prepare_protection(
                stored["entry_client_order_id"], client_order_id
            ):
                return False
        try:
            order = self.gateway.client.create_protective_oco(
                position.symbol,
                position.quantity,
                position.take_profit,
                position.stop_loss,
                client_order_id,
            )
        except OrderValidationError as error:
            self.positions.record_protection(
                stored["entry_client_order_id"], "FAILED", error=str(error)
            )
            raise
        except (
            ccxt.NetworkError,
            ccxt.ExchangeError,
            ConnectionError,
            TimeoutError,
        ) as error:
            self.positions.record_protection(
                stored["entry_client_order_id"], "UNKNOWN", error=str(error)
            )
            raise
        self.positions.record_protection(
            stored["entry_client_order_id"],
            "ACTIVE",
            order_id=self._string_value(order.get("id")),
        )
        return True

    def _reconcile_native_protection(
        self,
        position: Position,
        stored: dict,
    ) -> bool:
        client_order_id = stored["protection_client_order_id"]
        if client_order_id is None:
            return self._ensure_native_protection(position)
        try:
            order = self.gateway.client.find_protective_oco(
                position.symbol, client_order_id
            )
        except (
            ccxt.NetworkError,
            ccxt.ExchangeError,
            ConnectionError,
            TimeoutError,
        ) as error:
            self.positions.record_protection(
                stored["entry_client_order_id"], "UNKNOWN", error=str(error)
            )
            return False
        if order is None:
            self.positions.record_protection(
                stored["entry_client_order_id"],
                "UNKNOWN",
                error="Protective OCO not found on OKX.",
            )
            return False
        info = order.get("info") or {}
        state = str(info.get("state") or order.get("status") or "").lower()
        if state in {"live", "open"}:
            self.positions.record_protection(
                stored["entry_client_order_id"],
                "ACTIVE",
                order_id=self._string_value(
                    info.get("algoId") or order.get("id")
                ),
            )
            return True
        if state in {"order_failed", "canceled", "cancelled"}:
            self.positions.record_protection(
                stored["entry_client_order_id"],
                "FAILED",
                error=str(info.get("failCode") or state),
            )
            return False
        # A completed OCO may already have sold the asset. Never submit a
        # second exit until its fill has been reconciled.
        self.positions.record_protection(
            stored["entry_client_order_id"], "TRIGGERED"
        )
        return False

    def _activate_confirmed_entry(
        self,
        client_order_id: str,
        plan: TradePlan,
        order: dict,
        opened_at: datetime,
    ) -> Position | None:
        if self._order_status(order) != "FILLED":
            return None
        quantity = float(order.get("filled") or 0.0)
        entry_price = self._fill_price(order)
        if quantity <= 0 or entry_price is None:
            return None

        original_risk = plan.entry - plan.stop_loss
        stop_loss = entry_price - original_risk
        take_profit = entry_price + original_risk * plan.risk_reward
        entry_fee = self._fee_cost(order)
        position = Position(
            symbol=plan.symbol,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            opened_at=self._as_datetime(opened_at),
        )
        position.initial_risk = original_risk
        position.entry_fee = entry_fee
        position.update_price(entry_price)

        self.positions.activate(
            client_order_id,
            self._string_value(order.get("id")),
            quantity,
            entry_price,
            entry_fee,
            stop_loss,
            take_profit,
            position.opened_at,
        )
        if not self.portfolio.has_open_position(position.symbol):
            if not self.portfolio.add_position(position):
                raise OrderValidationError(
                    "Confirmed OKX fill could not be added to portfolio."
                )
            self.portfolio.cash = max(0.0, self.portfolio.cash - entry_fee)
        logger.info(
            f"OKX DEMO ENTRY FILLED | {position.symbol} | "
            f"qty={quantity:.8f} | price={entry_price:.8f}"
        )
        self._ensure_native_protection(position)
        return position

    def _sync_pending_exit(
        self,
        position: Position,
        stored: dict,
        timestamp: datetime,
    ) -> bool:
        self.gateway.reconcile_intents()
        intent = self.gateway.order_repository.get(
            stored["exit_client_order_id"]
        )
        if intent is None or intent["status"] != "FILLED":
            return False
        return self._close_from_fill(
            position,
            stored,
            self._order_from_intent(intent),
            timestamp,
        )

    def _close_from_fill(
        self,
        position: Position,
        stored: dict,
        order: dict,
        timestamp: datetime,
    ) -> bool:
        if self._order_status(order) != "FILLED":
            return False
        filled = float(order.get("filled") or 0.0)
        if filled + 1e-12 < position.quantity:
            return False
        exit_price = self._fill_price(order)
        if exit_price is None:
            return False
        exit_fee = self._fee_cost(order)
        pnl = (
            (exit_price - position.entry_price) * position.quantity
            - position.entry_fee
            - exit_fee
        )
        position.realized_pnl = pnl
        self.portfolio.close_position(
            position,
            exit_price,
            stored["exit_reason"] or "UNKNOWN",
            closed_at=self._as_datetime(timestamp),
        )
        self.portfolio.cash = max(0.0, self.portfolio.cash - exit_fee)
        self.positions.close(
            stored["entry_client_order_id"],
            self._string_value(order.get("id")),
            exit_price,
            exit_fee,
            pnl,
            self._as_datetime(timestamp),
        )
        logger.info(
            f"OKX DEMO EXIT FILLED | {position.symbol} | "
            f"price={exit_price:.8f} | pnl={pnl:.8f}"
        )
        return True

    def _restore_positions(self) -> None:
        for stored in self.positions.open_positions():
            if self.portfolio.has_open_position(stored["symbol"]):
                continue
            if stored["entry_price"] is None or stored["quantity"] <= 0:
                continue
            position = Position(
                symbol=stored["symbol"],
                entry_price=stored["entry_price"],
                quantity=stored["quantity"],
                stop_loss=stored["stop_loss"],
                take_profit=stored["take_profit"],
                opened_at=self._as_datetime(stored["opened_at"]),
            )
            position.entry_fee = stored["entry_fee"]
            position.initial_risk = abs(
                position.entry_price - position.stop_loss
            )
            position.update_price(position.entry_price)
            self.portfolio.open_positions.append(position)

    def _portfolio_position(self, symbol: str) -> Position | None:
        return next(
            (p for p in self.portfolio.open_positions if p.symbol == symbol),
            None,
        )

    @staticmethod
    def _order_status(order: dict) -> str:
        status = str(order.get("status") or "").lower()
        return "FILLED" if status == "closed" else status.upper()

    @staticmethod
    def _fill_price(order: dict) -> float | None:
        average = order.get("average")
        if average is not None:
            return float(average)
        filled = float(order.get("filled") or 0.0)
        cost = order.get("cost")
        if cost is not None and filled > 0:
            return float(cost) / filled
        return None

    @staticmethod
    def _fee_cost(order: dict) -> float:
        fee = order.get("fee") or {}
        return abs(float(fee.get("cost") or 0.0))

    @staticmethod
    def _order_from_intent(intent: dict) -> dict:
        return {
            "id": intent["exchange_order_id"],
            "status": "closed" if intent["status"] == "FILLED" else "open",
            "filled": intent["filled_amount"],
            "average": intent["average_price"],
            "fee": {"cost": intent["fee_cost"]},
        }

    @staticmethod
    def _risk_reward(stored: dict) -> float:
        risk = stored["planned_entry"] - stored["stop_loss"]
        return (
            (stored["take_profit"] - stored["planned_entry"]) / risk
            if risk > 0
            else 0.0
        )

    @staticmethod
    def _new_client_order_id(prefix: str) -> str:
        return f"bot{prefix}{uuid4().hex}"[:32]

    @staticmethod
    def _string_value(value) -> str | None:
        return str(value) if value is not None else None

    @staticmethod
    def _as_datetime(value) -> datetime:
        if isinstance(value, datetime):
            return (
                value.replace(tzinfo=timezone.utc)
                if value.tzinfo is None
                else value.astimezone(timezone.utc)
            )
        if isinstance(value, str):
            return datetime.fromisoformat(value).astimezone(timezone.utc)
        return datetime.now(timezone.utc)
