from datetime import datetime, timezone

from app.config.settings import (
    EMERGENCY_STOP,
    MAX_CONSECUTIVE_LOSSES,
    MAX_DAILY_LOSS_PCT,
    MAX_DRAWDOWN_PCT,
    MAX_EXCHANGE_ORDERS_PER_DAY,
)
from app.storage.execution_risk_repository import ExecutionRiskRepository


class ExecutionCircuitBreaker:
    """Persistent entry gate for demo and eventual live execution."""

    def __init__(self, mode: str, repository=None):
        self.mode = mode
        self.repository = repository or ExecutionRiskRepository()

    def can_open(
        self,
        equity: float,
        drawdown_percent: float,
        projected_orders: int = 2,
    ) -> tuple[bool, str | None]:
        state = self._state(equity)
        reason = None
        if EMERGENCY_STOP:
            reason = "EMERGENCY_STOP"
        elif drawdown_percent >= MAX_DRAWDOWN_PCT * 100:
            reason = "MAX_DRAWDOWN"
        elif state["daily_pnl"] <= -(
            state["day_start_equity"] * MAX_DAILY_LOSS_PCT
        ):
            reason = "MAX_DAILY_LOSS"
        elif state["consecutive_losses"] >= MAX_CONSECUTIVE_LOSSES:
            reason = "MAX_CONSECUTIVE_LOSSES"
        elif (
            state["orders_today"] + projected_orders
            > MAX_EXCHANGE_ORDERS_PER_DAY
        ):
            reason = "MAX_DAILY_ORDERS"
        state["halted_reason"] = reason
        self._save(state)
        return reason is None, reason

    def record_order(self, equity: float) -> None:
        state = self._state(equity)
        state["orders_today"] += 1
        self._save(state)

    def record_trade(self, pnl: float, equity: float) -> None:
        state = self._state(equity)
        state["daily_pnl"] += pnl
        state["consecutive_losses"] = (
            state["consecutive_losses"] + 1 if pnl < 0 else 0
        )
        self._save(state)

    def status(self, equity: float) -> dict:
        state = self._state(equity)
        allowed, reason = self.can_open(equity, 0.0)
        return {**state, "entries_allowed": allowed, "halted_reason": reason}

    def _state(self, equity: float) -> dict:
        today = datetime.now(timezone.utc).date().isoformat()
        state = self.repository.load(self.mode)
        if state is None or state["trading_day"] != today:
            state = {
                "trading_day": today,
                "day_start_equity": max(0.0, float(equity)),
                "daily_pnl": 0.0,
                "consecutive_losses": 0,
                "orders_today": 0,
                "halted_reason": None,
                "updated_at": self._now(),
            }
            self.repository.save(self.mode, state)
        return state

    def _save(self, state: dict) -> None:
        state["updated_at"] = self._now()
        self.repository.save(self.mode, state)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
