from unittest.mock import Mock

import pytest

from app.exceptions import TradingModeError
from app.live import canary


def enable_gates(monkeypatch):
    monkeypatch.setattr(canary, "TRADING_MODE", "live")
    monkeypatch.setattr(canary, "LIVE_TRADING_ENABLED", True)
    monkeypatch.setattr(canary, "EMERGENCY_STOP", False)
    monkeypatch.setattr(canary, "LIVE_CANARY_ENABLED", True)
    monkeypatch.setattr(
        canary, "LIVE_CANARY_CONFIRMATION", canary.REQUIRED_CONFIRMATION
    )
    monkeypatch.setattr(canary, "LIVE_CANARY_ORDER_VALUE", 10.0)
    monkeypatch.setattr(canary, "LIVE_ACCOUNT_SIZE", 20.0)
    monkeypatch.setattr(canary, "MAX_EXCHANGE_ORDER_VALUE", 10.0)


def test_canary_is_blocked_by_default():
    with pytest.raises(TradingModeError):
        canary.open_canary(client=Mock(), broker=Mock())


def test_canary_builds_ten_euro_protected_plan(monkeypatch):
    enable_gates(monkeypatch)
    monkeypatch.setattr(
        canary,
        "preflight_check",
        lambda client: {"open_order_count": 0},
    )
    client = Mock()
    client.get_ticker.return_value = {"ask": 100.0}
    client.price_to_precision.side_effect = lambda symbol, price: price
    broker = Mock()
    broker.sync_balance.return_value = 20.0
    broker.positions.find_active.side_effect = [None, {
        "status": "OPEN",
        "protection_status": "ACTIVE",
    }]
    broker.reconcile.return_value = {"safe": True}

    result = canary.open_canary(client=client, broker=broker)

    submitted_plan = broker.open.call_args.args[0]
    assert submitted_plan.position_size == 10.0
    assert submitted_plan.stop_loss == 98.0
    assert submitted_plan.take_profit == 104.0
    assert result["protection_status"] == "ACTIVE"
