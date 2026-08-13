from datetime import datetime, timezone

from app.config.settings import (
    ACCOUNT_SIZE,
    SHADOW_MIN_CLOSED_TRADES,
    SHADOW_MIN_PROFIT_FACTOR,
    SHADOW_RECOVERY_ENABLED,
    SLIPPAGE,
    TRADING_FEE,
)
from app.core.logger import logger
from app.models.shadow_trade import ShadowTrade
from app.risk.risk_manager import RiskManager
from app.storage.shadow_trade_repository import ShadowTradeRepository
from app.strategy.filters import classify_regime
from app.strategy.signal_engine import SignalEngine


class RecoveryShadowTracker:
    """Persist hypothetical recovery trades without touching a portfolio."""

    def __init__(self, repository=None):
        self.repository = repository or ShadowTradeRepository()
        self.signal_engine = SignalEngine()
        self.risk_manager = RiskManager()

    def observe(
        self,
        symbol: str,
        market: dict,
        timestamp,
    ) -> None:
        if not SHADOW_RECOVERY_ENABLED:
            return
        if any(
            market.get(label) is None
            for label in ("regime", "trend", "confirm", "entry")
        ):
            return

        observed_at = self._as_datetime(timestamp)
        entry = market["entry"]
        open_trade = self.repository.get_open(symbol)
        if open_trade is not None:
            if self._update_open(open_trade, entry, observed_at):
                return
            return

        if classify_regime(market["regime"]) != "RECOVERY":
            return

        signal = self.signal_engine.evaluate(
            symbol,
            market,
            allow_recovery=True,
        )
        if signal.action != "BUY":
            return

        plan = self.risk_manager.create_trade_plan(
            signal,
            entry,
            available_cash=ACCOUNT_SIZE,
        )
        if plan is None:
            return

        execution_entry = plan.entry * (1 + SLIPPAGE)
        original_risk = plan.entry - plan.stop_loss
        quantity = plan.position_size / execution_entry
        shadow = ShadowTrade(
            symbol=symbol,
            regime="RECOVERY",
            entry_price=execution_entry,
            stop_loss=execution_entry - original_risk,
            take_profit=(
                execution_entry + original_risk * plan.risk_reward
            ),
            quantity=quantity,
            opened_at=observed_at,
        )
        shadow.id = self.repository.save_open(shadow)
        logger.info(
            f"SHADOW OPEN: {symbol} recovery "
            f"@ {shadow.entry_price:.6f}"
        )

    def _update_open(
        self,
        trade: ShadowTrade,
        entry,
        timestamp: datetime,
    ) -> bool:
        low = float(entry.get("low", entry["close"]))
        high = float(entry.get("high", entry["close"]))
        hit_stop = low <= trade.stop_loss
        hit_target = high >= trade.take_profit
        if not hit_stop and not hit_target:
            return False

        level = trade.stop_loss if hit_stop else trade.take_profit
        reason = "STOP_LOSS" if hit_stop else "TAKE_PROFIT"
        execution_exit = level * (1 - SLIPPAGE)
        entry_fee = trade.entry_price * trade.quantity * TRADING_FEE
        exit_fee = execution_exit * trade.quantity * TRADING_FEE
        trade.pnl = (
            (execution_exit - trade.entry_price) * trade.quantity
            - entry_fee
            - exit_fee
        )
        trade.status = "CLOSED"
        trade.closed_at = timestamp
        trade.exit_price = execution_exit
        trade.exit_reason = reason
        self.repository.close(trade)
        logger.info(
            f"SHADOW CLOSE: {trade.symbol} {reason} "
            f"pnl={trade.pnl:+.2f} USDC"
        )
        return True

    def summary(self) -> dict[str, float | int]:
        closed = self.repository.get_closed()
        wins = sum((trade.pnl or 0) > 0 for trade in closed)
        losses = sum((trade.pnl or 0) < 0 for trade in closed)
        net_profit = sum(trade.pnl or 0 for trade in closed)
        gross_profit = sum(
            trade.pnl or 0
            for trade in closed
            if (trade.pnl or 0) > 0
        )
        gross_loss = abs(sum(
            trade.pnl or 0
            for trade in closed
            if (trade.pnl or 0) < 0
        ))
        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else (float("inf") if gross_profit > 0 else 0.0)
        )
        expectancy = net_profit / len(closed) if closed else 0.0
        ready = (
            len(closed) >= SHADOW_MIN_CLOSED_TRADES
            and profit_factor >= SHADOW_MIN_PROFIT_FACTOR
            and expectancy > 0
        )
        return {
            "open": self.repository.count_open(),
            "trades": len(closed),
            "wins": wins,
            "losses": losses,
            "net_profit": net_profit,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "ready": int(ready),
        }

    @staticmethod
    def _as_datetime(value) -> datetime:
        if isinstance(value, datetime):
            return value
        if value is None:
            return datetime.now(timezone.utc)
        numeric = float(value)
        if numeric > 10_000_000_000:
            numeric /= 1000
        return datetime.fromtimestamp(numeric, tz=timezone.utc)
