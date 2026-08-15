from unittest.mock import Mock

import pytest

from app.exceptions import LiveTradingDisabledError, TradingModeError
from app.exchange.kraken_client import KrakenClient


def create_client(mode="live", live_enabled=False):
    exchange = Mock()
    client = KrakenClient(
        trading_mode=mode,
        live_trading_enabled=live_enabled,
        api_key="api-key",
        secret="private-secret",
        exchange=exchange,
    )
    return client, exchange


def test_key_info_uses_authenticated_spot_endpoint():
    client, exchange = create_client()
    exchange.privatePostGetApiKeyInfo.return_value = {
        "error": [],
        "result": {"apiKeyName": "trading-bot"},
    }

    assert client.get_key_info() == {"apiKeyName": "trading-bot"}
    exchange.privatePostGetApiKeyInfo.assert_called_once_with()


def test_preview_validates_quote_sized_order_without_live_opt_in():
    client, exchange = create_client(live_enabled=False)
    exchange.create_order.return_value = {"id": None}

    result = client.preview_market_buy("BTC/EUR", 5.0, "preview-1")

    assert result == {"id": None}
    exchange.create_order.assert_called_once_with(
        symbol="BTC/EUR",
        type="market",
        side="buy",
        amount=5.0,
        price=None,
        params={
            "cost": 5.0,
            "clientOrderId": "preview-1",
            "validate": True,
        },
    )


def test_live_order_requires_separate_opt_in():
    client, exchange = create_client(live_enabled=False)

    with pytest.raises(LiveTradingDisabledError):
        client.create_market_order("BTC/EUR", "buy", 5.0, "order-1", 5.0)

    exchange.create_order.assert_not_called()


def test_client_rejects_unsupported_demo_mode():
    with pytest.raises(TradingModeError, match="no Spot execution sandbox"):
        KrakenClient(
            trading_mode="demo",
            api_key="key",
            secret="secret",
            exchange=Mock(),
        )
