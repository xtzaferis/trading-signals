from unittest.mock import Mock

import pytest

from app.exceptions import OrderValidationError, TradingModeError
from app.live import order_preview


def create_client(balance=20.0):
    client = Mock()
    client.load_markets.return_value = {
        "BTC/EUR": {"spot": True, "active": True}
    }
    client.get_balance.return_value = {"free": {"EUR": balance}}
    client.get_ticker.return_value = {"ask": 100.0, "last": 99.9}
    client.price_to_precision.side_effect = lambda symbol, price: price
    client.preview_market_buy.return_value = {
        "id": None,
        "status": None,
    }
    return client


def configure_eur_preview(monkeypatch):
    monkeypatch.setattr(order_preview, "LIVE_TRADING_ENABLED", False)
    monkeypatch.setattr(order_preview, "LIVE_ACCOUNT_SIZE", 20.0)
    monkeypatch.setattr(order_preview, "MAX_EXCHANGE_ORDER_VALUE", 10.0)
    monkeypatch.setattr(order_preview, "QUOTE_CURRENCY", "EUR")


def test_preview_uses_kraken_validation_without_submitting(monkeypatch):
    configure_eur_preview(monkeypatch)
    client = create_client()

    result = order_preview.preview(
        client,
        symbol="BTC/EUR",
        quote_cost=10.0,
        client_order_id="preview-1",
    )

    assert result["submitted"] is False
    assert result["quote_cost"] == 10.0
    client.preview_market_buy.assert_called_once_with(
        "BTC/EUR",
        10.0,
        "preview-1",
        stop_loss=98.0,
    )
    assert result["stop_loss"] == 98.0
    client.create_market_order.assert_not_called()


def test_preview_rejects_when_live_execution_is_enabled(monkeypatch):
    configure_eur_preview(monkeypatch)
    monkeypatch.setattr(order_preview, "LIVE_TRADING_ENABLED", True)
    client = create_client()

    with pytest.raises(TradingModeError, match="requires.*false"):
        order_preview.preview(client, "BTC/EUR", 10.0, "preview-1")

    client.load_markets.assert_not_called()
    client.preview_market_buy.assert_not_called()


def test_preview_rejects_value_above_order_limit(monkeypatch):
    configure_eur_preview(monkeypatch)
    client = create_client()

    with pytest.raises(OrderValidationError, match="safety limit"):
        order_preview.preview(client, "BTC/EUR", 10.01, "preview-1")

    client.load_markets.assert_not_called()
    client.preview_market_buy.assert_not_called()


def test_preview_rejects_insufficient_balance(monkeypatch):
    configure_eur_preview(monkeypatch)
    client = create_client(balance=9.99)

    with pytest.raises(OrderValidationError, match="Available balance"):
        order_preview.preview(client, "BTC/EUR", 10.0, "preview-1")

    client.preview_market_buy.assert_not_called()
