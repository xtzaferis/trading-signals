from unittest.mock import Mock

import pytest

from app.exceptions import LiveTradingDisabledError, TradingModeError
from app.exchange.coinbase_client import CoinbaseClient


def create_client(mode="live", live_enabled=False):
    exchange = Mock()
    client = CoinbaseClient(
        trading_mode=mode,
        live_trading_enabled=live_enabled,
        api_key="organizations/test/apiKeys/key",
        secret="-----BEGIN EC PRIVATE KEY-----\\nsecret\\n-----END EC PRIVATE KEY-----",
        exchange=exchange,
    )
    return client, exchange


def test_client_normalizes_dotenv_private_key():
    client, _ = create_client()

    assert "\\n" not in client.secret
    assert "\nsecret\n" in client.secret


def test_key_permissions_use_authenticated_advanced_trade_endpoint():
    client, exchange = create_client()
    exchange.v3_private_get_brokerage_key_permissions.return_value = {
        "can_view": True
    }

    assert client.get_key_permissions() == {"can_view": True}
    exchange.v3_private_get_brokerage_key_permissions.assert_called_once_with()


def test_preview_uses_preview_endpoint_flag_without_live_opt_in():
    client, exchange = create_client(live_enabled=False)
    exchange.create_order.return_value = {"preview_id": "preview-1"}

    result = client.preview_market_buy("BTC/EUR", 5.0, "preview-1")

    assert result == {"preview_id": "preview-1"}
    exchange.create_order.assert_called_once_with(
        symbol="BTC/EUR",
        type="market",
        side="buy",
        amount=5.0,
        price=None,
        params={
            "cost": 5.0,
            "client_order_id": "preview-1",
            "preview": True,
        },
    )


def test_live_order_requires_separate_opt_in():
    client, exchange = create_client(live_enabled=False)

    with pytest.raises(LiveTradingDisabledError):
        client.create_market_order("BTC/EUR", "buy", 5.0, "order-1", 5.0)

    exchange.create_order.assert_not_called()


def test_coinbase_rejects_unsupported_demo_mode():
    with pytest.raises(TradingModeError, match="static responses"):
        CoinbaseClient(
            trading_mode="demo",
            api_key="key",
            secret="secret",
            exchange=Mock(),
        )
