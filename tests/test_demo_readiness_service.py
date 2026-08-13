from unittest.mock import Mock

from app.services.demo_readiness_service import DemoReadinessService


def test_empty_demo_history_is_not_ready():
    report = DemoReadinessService().report()

    assert report["ready"] is False
    assert report["checks"]["minimum_trades"] is False


def test_complete_profitable_demo_sample_is_ready():
    positions = Mock()
    positions.operational_summary.return_value = {
        "closed_trades": 35,
        "wins": 20,
        "losses": 15,
        "net_profit": 50.0,
        "profit_factor": 1.5,
        "max_drawdown_pct": 2.0,
        "pending_positions": 0,
        "unprotected_positions": 0,
        "open_positions": 0,
        "first_opened_at": "2026-01-01T00:00:00+00:00",
        "last_closed_at": "2026-02-15T00:00:00+00:00",
    }
    orders = Mock()
    orders.pending.return_value = []
    risk = Mock()
    risk.load.return_value = None

    report = DemoReadinessService(positions, orders, risk).report()

    assert report["ready"] is True
