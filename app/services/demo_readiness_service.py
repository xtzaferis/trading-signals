from datetime import datetime

from app.config.settings import MAX_DRAWDOWN_PCT
from app.storage.exchange_order_repository import ExchangeOrderRepository
from app.storage.exchange_position_repository import ExchangePositionRepository
from app.storage.execution_risk_repository import ExecutionRiskRepository


class DemoReadinessService:
    MIN_CLOSED_TRADES = 30
    MIN_DAYS = 30
    MIN_PROFIT_FACTOR = 1.20

    def __init__(
        self,
        positions=None,
        orders=None,
        risk_repository=None,
    ):
        self.positions = positions or ExchangePositionRepository()
        self.orders = orders or ExchangeOrderRepository()
        self.risk_repository = risk_repository or ExecutionRiskRepository()

    def report(self) -> dict:
        performance = self.positions.operational_summary()
        pending_orders = self.orders.pending()
        risk = self.risk_repository.load("okx_demo")
        observed_days = self._observed_days(performance)
        checks = {
            "minimum_trades": (
                performance["closed_trades"] >= self.MIN_CLOSED_TRADES
            ),
            "minimum_observation_days": observed_days >= self.MIN_DAYS,
            "positive_net_profit": performance["net_profit"] > 0,
            "minimum_profit_factor": (
                performance["profit_factor"] >= self.MIN_PROFIT_FACTOR
            ),
            "drawdown_within_limit": (
                performance.get("max_drawdown_pct", 0.0)
                <= MAX_DRAWDOWN_PCT * 100
            ),
            "no_pending_orders": not pending_orders,
            "no_pending_positions": performance["pending_positions"] == 0,
            "all_open_positions_protected": (
                performance["unprotected_positions"] == 0
            ),
            "circuit_breaker_clear": not (
                risk and risk.get("halted_reason")
            ),
        }
        return {
            "ready": all(checks.values()),
            "checks": checks,
            "performance": performance,
            "observed_days": observed_days,
            "pending_order_ids": [
                order["client_order_id"] for order in pending_orders
            ],
            "risk": risk,
        }

    @staticmethod
    def _observed_days(performance: dict) -> int:
        start = performance["first_opened_at"]
        end = performance["last_closed_at"]
        if not start or not end:
            return 0
        return max(0, (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days)
