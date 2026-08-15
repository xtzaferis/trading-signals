from datetime import datetime, timezone
from uuid import uuid4

import ccxt

from app.config.settings import QUOTE_CURRENCY
from app.core.logger import logger
from app.exceptions import OrderValidationError
from app.execution.broker import Broker
from app.execution.kraken_order_gateway import KrakenOrderGateway
from app.models.position import Position
from app.models.trade_plan import TradePlan
from app.risk.execution_circuit_breaker import ExecutionCircuitBreaker
from app.storage.database import Database, mode_database_path
from app.storage.exchange_position_repository import ExchangePositionRepository
from app.storage.execution_risk_repository import ExecutionRiskRepository
from app.trading.portfolio import Portfolio


class KrakenLiveBroker(Broker):
    """Crash-safe Kraken Spot execution with native stop protection."""

    def __init__(
        self,
        portfolio: Portfolio,
        gateway: KrakenOrderGateway,
        position_repository=None,
        id_factory=None,
        circuit_breaker=None,
    ):
        self.portfolio = portfolio
        self.gateway = gateway
        live_database = Database(mode_database_path("kraken-live"))
        self.positions = position_repository or ExchangePositionRepository(
            live_database
        )
        self.id_factory = id_factory or self._new_client_order_id
        self.circuit_breaker = circuit_breaker or ExecutionCircuitBreaker(
            "kraken_live",
            ExecutionRiskRepository(live_database),
        )
        self._restore_positions()

    def entries_allowed(self) -> tuple[bool, str | None]:
        return self.circuit_breaker.can_open(
            self.portfolio.equity,
            self.portfolio.get_drawdown_percent(),
            projected_orders=2,
        )

    def sync_balance(self) -> float:
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
        if trade_plan.action.upper() != "BUY":
            raise OrderValidationError("Kraken Spot broker opens BUY trades only.")
        if self.positions.find_active(trade_plan.symbol) is not None:
            return None
        if self.portfolio.has_open_position(trade_plan.symbol):
            return None
        allowed, _ = self.entries_allowed()
        if not allowed:
            return None

        amount = trade_plan.position_size / trade_plan.entry
        client_order_id = self.id_factory("entry")
        if not self.positions.prepare_entry(
            client_order_id,
            trade_plan.symbol,
            amount,
            trade_plan.entry,
            trade_plan.stop_loss,
            trade_plan.take_profit,
        ):
            return None

        try:
            order = self.gateway.submit_market_order(
                symbol=trade_plan.symbol,
                side="buy",
                amount=amount,
                reference_price=trade_plan.entry,
                client_order_id=client_order_id,
                quote_cost=trade_plan.position_size,
                stop_loss=trade_plan.stop_loss,
            )
            self.circuit_breaker.record_order(self.portfolio.equity)
        except OrderValidationError as error:
            self.positions.record_entry_status(
                client_order_id, "ENTRY_REJECTED", str(error)
            )
            raise
        except (
            ccxt.NetworkError,
            ccxt.ExchangeError,
            ConnectionError,
            TimeoutError,
        ) as error:
            self.positions.record_entry_status(
                client_order_id, "ENTRY_UNKNOWN", str(error)
            )
            raise

        position = self._activate_confirmed_entry(
            client_order_id,
            trade_plan,
            order,
            opened_at,
        )
        if position is None:
            self.positions.record_entry_status(client_order_id, "PENDING_ENTRY")
        return position

    def update(
        self,
        position: Position,
        high: float,
        low: float,
        close: float,
        timestamp: datetime,
    ) -> bool:
        del high, low
        stored = self.positions.find_active(position.symbol)
        if stored is None:
            return False
        if stored["status"] in {"PENDING_EXIT", "EXIT_UNKNOWN"}:
            return self._resume_pending_exit(position, stored, timestamp)

        position.update_price(close)
        if close >= position.take_profit:
            if stored["protection_status"] != "ACTIVE":
                logger.warning(
                    "Take-profit exit deferred until Kraken stop protection "
                    "is reconciled."
                )
                return False
            return self.close(position, close, "TAKE_PROFIT", timestamp)
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
        exit_client_order_id = self.id_factory("exit")
        if not self.positions.prepare_exit(
            stored["entry_client_order_id"],
            exit_client_order_id,
            reason,
        ):
            return False
        stored = self.positions.find_active(position.symbol)
        try:
            if not self._cancel_protection_or_close(position, stored):
                return False
            order = self.gateway.submit_market_order(
                symbol=position.symbol,
                side="sell",
                amount=position.quantity,
                reference_price=price,
                client_order_id=exit_client_order_id,
            )
            self.circuit_breaker.record_order(self.portfolio.equity)
        except OrderValidationError as error:
            # The native stop may already have been canceled. Keep the exit
            # pending for reconciliation rather than pretending the position
            # is safely OPEN again.
            self.positions.record_entry_status(
                stored["entry_client_order_id"], "EXIT_UNKNOWN", str(error)
            )
            raise
        except (
            ccxt.NetworkError,
            ccxt.ExchangeError,
            ConnectionError,
            TimeoutError,
        ) as error:
            self.positions.record_entry_status(
                stored["entry_client_order_id"], "EXIT_UNKNOWN", str(error)
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
            position = self._activate_confirmed_entry(
                stored["entry_client_order_id"],
                self._plan_from_stored(stored),
                self._order_from_intent(intent),
                datetime.now(timezone.utc),
            )
            restored_entries += position is not None

        unprotected = []
        for stored in self.positions.open_positions():
            position = self._portfolio_position(stored["symbol"])
            if position is None:
                continue
            if stored["status"] in {"PENDING_EXIT", "EXIT_UNKNOWN"}:
                closed_exits += self._resume_pending_exit(
                    position,
                    stored,
                    datetime.now(timezone.utc),
                )
                continue
            if not self._reconcile_protection(position, stored):
                unprotected.append(stored["symbol"])

        balance_mismatches = self._balance_mismatches()
        unexpected_open_orders = self._unexpected_open_orders()
        return {
            **order_result,
            "restored_entries": restored_entries,
            "closed_exits": closed_exits,
            "unprotected_symbols": sorted(set(unprotected)),
            "balance_mismatches": balance_mismatches,
            "unexpected_open_order_ids": unexpected_open_orders,
            "safe": (
                bool(order_result.get("safe"))
                and not unprotected
                and not balance_mismatches
                and not unexpected_open_orders
            ),
        }

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

        stop_fraction = max(0.0, (plan.entry - plan.stop_loss) / plan.entry)
        target_fraction = max(0.0, (plan.take_profit - plan.entry) / plan.entry)
        stop_loss = entry_price * (1.0 - stop_fraction)
        take_profit = entry_price * (1.0 + target_fraction)
        entry_fee = self._fee_cost(order)
        position = Position(
            symbol=plan.symbol,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            opened_at=self._as_datetime(opened_at),
        )
        position.initial_risk = entry_price - stop_loss
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
                    "Confirmed Kraken fill could not be added to portfolio."
                )
            self.portfolio.cash = max(0.0, self.portfolio.cash - entry_fee)
        logger.info(
            f"KRAKEN LIVE ENTRY FILLED | {position.symbol} | "
            f"qty={quantity:.8f} | price={entry_price:.8f}"
        )
        self._prepare_attached_protection(position)
        return position

    def _prepare_attached_protection(self, position: Position) -> None:
        stored = self.positions.find_active(position.symbol)
        if stored is None or stored["protection_client_order_id"]:
            return
        logical_id = self.id_factory("protect")
        self.positions.prepare_protection(
            stored["entry_client_order_id"], logical_id
        )
        stored = self.positions.find_active(position.symbol)
        self._reconcile_protection(position, stored)

    def _reconcile_protection(self, position: Position, stored: dict) -> bool:
        try:
            order = self._find_protection(stored)
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
                error="Attached Kraken stop-loss order was not found.",
            )
            return False

        status = self._order_status(order)
        order_id = self._string_value(order.get("id"))
        if status in {"OPEN", "SUBMITTED", "PENDING"}:
            self.positions.record_protection(
                stored["entry_client_order_id"], "ACTIVE", order_id=order_id
            )
            return True
        if status == "FILLED":
            self._close_native_stop(position, stored, order)
            return True
        if status in {"CANCELED", "CANCELLED", "EXPIRED", "REJECTED"}:
            self.positions.record_protection(
                stored["entry_client_order_id"], status, order_id=order_id
            )
            return False
        self.positions.record_protection(
            stored["entry_client_order_id"],
            "UNKNOWN",
            order_id=order_id,
            error=status,
        )
        return False

    def _find_protection(self, stored: dict) -> dict | None:
        if stored["protection_order_id"]:
            return self.gateway.client.fetch_order(
                stored["protection_order_id"], stored["symbol"]
            )
        if not stored["entry_exchange_order_id"]:
            return None
        return self.gateway.client.find_attached_stop(
            stored["symbol"], stored["entry_exchange_order_id"]
        )

    def _cancel_protection_or_close(
        self,
        position: Position,
        stored: dict,
    ) -> bool:
        order = self._find_protection(stored)
        if order is None:
            raise OrderValidationError(
                "Cannot sell while Kraken stop protection is unresolved."
            )
        status = self._order_status(order)
        if status == "FILLED":
            self._close_native_stop(position, stored, order)
            return False
        if status in {"CANCELED", "CANCELLED"}:
            return True
        if status not in {"OPEN", "SUBMITTED", "PENDING"}:
            raise OrderValidationError(
                f"Cannot cancel Kraken protection in status {status}."
            )
        order_id = self._string_value(order.get("id"))
        if not order_id:
            raise OrderValidationError("Kraken stop order has no order ID.")
        self.gateway.client.cancel_order(order_id, position.symbol)
        confirmed = self.gateway.client.fetch_order(order_id, position.symbol)
        confirmed_status = self._order_status(confirmed)
        if confirmed_status == "FILLED":
            self._close_native_stop(position, stored, confirmed)
            return False
        if confirmed_status not in {"CANCELED", "CANCELLED"}:
            raise OrderValidationError(
                "Kraken stop cancellation is not yet confirmed."
            )
        self.positions.record_protection(
            stored["entry_client_order_id"],
            "CANCELED",
            order_id=order_id,
        )
        return True

    def _resume_pending_exit(
        self,
        position: Position,
        stored: dict,
        timestamp: datetime,
    ) -> bool:
        if not stored["exit_client_order_id"]:
            return False
        try:
            if not self._cancel_protection_or_close(position, stored):
                return position.status == "CLOSED"
        except OrderValidationError:
            return False

        intent = self.gateway.order_repository.get(
            stored["exit_client_order_id"]
        )
        if intent is None:
            ticker = self.gateway.client.get_ticker(position.symbol)
            price = float(ticker.get("last") or 0.0)
            if price <= 0:
                return False
            try:
                order = self.gateway.submit_market_order(
                    symbol=position.symbol,
                    side="sell",
                    amount=position.quantity,
                    reference_price=price,
                    client_order_id=stored["exit_client_order_id"],
                )
                self.circuit_breaker.record_order(self.portfolio.equity)
            except (
                OrderValidationError,
                ccxt.NetworkError,
                ccxt.ExchangeError,
                ConnectionError,
                TimeoutError,
            ):
                return False
        else:
            self.gateway.reconcile_intents()
            intent = self.gateway.order_repository.get(
                stored["exit_client_order_id"]
            )
            if intent is None or intent["status"] != "FILLED":
                return False
            order = self._order_from_intent(intent)
        return self._close_from_fill(position, stored, order, timestamp)

    def _close_native_stop(
        self,
        position: Position,
        stored: dict,
        order: dict,
    ) -> None:
        exit_price = self._fill_price(order)
        filled = float(order.get("filled") or 0.0)
        if exit_price is None or filled + 1e-12 < position.quantity:
            raise OrderValidationError(
                "Kraken stop-loss fill data is incomplete."
            )
        self._finalize_close(
            position,
            stored,
            order,
            exit_price,
            "STOP_LOSS",
            datetime.now(timezone.utc),
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
        exit_price = self._fill_price(order)
        if filled + 1e-12 < position.quantity or exit_price is None:
            return False
        self._finalize_close(
            position,
            stored,
            order,
            exit_price,
            stored["exit_reason"] or "UNKNOWN",
            timestamp,
        )
        return True

    def _finalize_close(
        self,
        position: Position,
        stored: dict,
        order: dict,
        exit_price: float,
        reason: str,
        timestamp: datetime,
    ) -> None:
        exit_fee = self._fee_cost(order)
        pnl = (
            (exit_price - position.entry_price) * position.quantity
            - position.entry_fee
            - exit_fee
        )
        position.realized_pnl = pnl
        closed_at = self._as_datetime(timestamp)
        self.portfolio.close_position(
            position, exit_price, reason, closed_at=closed_at
        )
        self.portfolio.cash = max(0.0, self.portfolio.cash - exit_fee)
        self.positions.close(
            stored["entry_client_order_id"],
            self._string_value(order.get("id")),
            exit_price,
            exit_fee,
            pnl,
            closed_at,
            exit_reason=reason,
        )
        self.circuit_breaker.record_trade(pnl, self.portfolio.equity)
        logger.info(
            f"KRAKEN LIVE EXIT FILLED | {position.symbol} | "
            f"reason={reason} | price={exit_price:.8f} | pnl={pnl:.8f}"
        )

    def _balance_mismatches(self) -> list[str]:
        if not self.portfolio.open_positions:
            return []
        balance = self.gateway.client.get_balance()
        totals = balance.get("total") or {}
        mismatches = []
        for position in self.portfolio.open_positions:
            base = position.symbol.split("/", maxsplit=1)[0]
            total = totals.get(base)
            if total is None:
                total = (balance.get(base) or {}).get("total", 0.0)
            if float(total or 0.0) + 1e-12 < position.quantity:
                mismatches.append(position.symbol)
        return sorted(set(mismatches))

    def _unexpected_open_orders(self) -> list[str]:
        orders = self.gateway.client.fetch_open_orders(None)
        expected_ids = {
            stored["protection_order_id"]
            for stored in self.positions.open_positions()
            if stored["protection_order_id"]
        }
        return sorted(
            str(order.get("id") or "unknown")
            for order in orders
            if str(order.get("id") or "") not in expected_ids
        )

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
            position.initial_risk = position.entry_price - position.stop_loss
            position.update_price(position.entry_price)
            self.portfolio.open_positions.append(position)

    def _portfolio_position(self, symbol: str) -> Position | None:
        return next(
            (p for p in self.portfolio.open_positions if p.symbol == symbol),
            None,
        )

    @staticmethod
    def _plan_from_stored(stored: dict) -> TradePlan:
        risk = stored["planned_entry"] - stored["stop_loss"]
        reward = stored["take_profit"] - stored["planned_entry"]
        return TradePlan(
            symbol=stored["symbol"],
            action="BUY",
            entry=stored["planned_entry"],
            stop_loss=stored["stop_loss"],
            take_profit=stored["take_profit"],
            position_size=stored["requested_amount"] * stored["planned_entry"],
            risk_reward=reward / risk if risk > 0 else 0.0,
        )

    @staticmethod
    def _order_status(order: dict) -> str:
        status = str(order.get("status") or "").lower()
        if status == "closed":
            return "FILLED"
        if status in {"canceled", "cancelled"}:
            return "CANCELED"
        return status.upper() or "SUBMITTED"

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
    def _new_client_order_id(prefix: str) -> str:
        return f"k{prefix}-{uuid4().hex}"[:18]

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
