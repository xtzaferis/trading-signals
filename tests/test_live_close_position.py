from unittest.mock import Mock

import pytest

from app.exceptions import TradingModeError
from app.live.close_position import CONFIRMATION, close_canary
from app.models.position import Position


def _broker():
    position = Position(
        symbol="BTC/EUR",
        entry_price=100.0,
        quantity=0.1,
        stop_loss=98.0,
        take_profit=104.0,
    )
    broker = Mock()
    broker.reconcile.return_value = {"safe": True}
    broker.portfolio.open_positions = [position]
    broker.gateway.client.get_ticker.return_value = {
        "last": 101.0,
        "datetime": "2026-08-15T12:00:00+00:00",
    }
    broker.gateway.client.fetch_open_orders.return_value = []
    broker.gateway.client.get_balance.return_value = {
        "free": {"EUR": 20.1},
        "total": {"BTC": 0.0},
    }

    def close_effect(target, price, reason, timestamp):
        target.current_price = price
        target.realized_pnl = 0.09
        return True

    broker.close.side_effect = close_effect
    return broker


def test_preview_does_not_close_position():
    broker = _broker()

    result = close_canary(broker, symbol="BTC/EUR")

    assert result["executed"] is False
    assert result["estimated_quote_value"] == pytest.approx(10.1)
    broker.close.assert_not_called()


def test_execute_requires_exact_confirmation():
    broker = _broker()

    with pytest.raises(TradingModeError, match="confirmation"):
        close_canary(broker, execute=True, confirmation="wrong")

    broker.reconcile.assert_not_called()


def test_execute_closes_and_reports_exchange_state():
    broker = _broker()

    result = close_canary(
        broker,
        execute=True,
        confirmation=CONFIRMATION,
        symbol="BTC/EUR",
    )

    assert result["executed"] is True
    assert result["exit_price"] == 101.0
    assert result["realized_pnl"] == 0.09
    assert result["open_orders"] == 0
    assert result["free_quote"] == 20.1
    assert result["remaining_base"] == 0.0
    broker.close.assert_called_once()


def test_unsafe_reconciliation_aborts_before_ticker_or_close():
    broker = _broker()
    broker.reconcile.return_value = {"safe": False}

    with pytest.raises(TradingModeError, match="unsafe"):
        close_canary(broker, symbol="BTC/EUR")

    broker.gateway.client.get_ticker.assert_not_called()
    broker.close.assert_not_called()
