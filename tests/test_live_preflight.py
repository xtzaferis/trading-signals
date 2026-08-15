from unittest.mock import Mock

import pytest

from app.exceptions import TradingModeError
from app.live.preflight import REQUIRED_PERMISSIONS, check


def create_client(permissions=None):
    client = Mock()
    client.get_key_info.return_value = {
        "apiKeyName": "trading-bot",
        "permissions": sorted(permissions or REQUIRED_PERMISSIONS),
        "ipAllowlist": ["203.0.113.10/32"],
    }
    client.load_markets.return_value = {
        "BTC/USDC": {"spot": True, "active": True}
    }
    client.get_balance.return_value = {"free": {"USDC": 100.0}}
    client.fetch_open_orders.return_value = []
    return client


def test_preflight_is_read_only_and_reports_key_identity():
    client = create_client()

    result = check(client)

    assert result == {
        "exchange": "kraken",
        "permissions": sorted(REQUIRED_PERMISSIONS),
        "key_name": "trading-bot",
        "ip_allowlist": ["203.0.113.10/32"],
        "free_quote": 100.0,
        "quote_currency": "USDC",
        "market_symbol": "BTC/USDC",
        "open_order_count": 0,
    }
    client.create_market_order.assert_not_called()
    client.preview_market_buy.assert_not_called()


def test_preflight_rejects_missing_order_permission():
    permissions = REQUIRED_PERMISSIONS - {"modify-trades"}
    client = create_client(permissions)

    with pytest.raises(TradingModeError, match="modify-trades"):
        check(client)

    client.get_balance.assert_not_called()


@pytest.mark.parametrize(
    "permission",
    [
        "add-funds",
        "withdraw-funds",
        "earn-funds",
        "add-withdraw-address",
        "update-withdraw-address",
    ],
)
def test_preflight_rejects_funding_permissions(permission):
    client = create_client(REQUIRED_PERMISSIONS | {permission})

    with pytest.raises(TradingModeError, match="forbidden funding"):
        check(client)

    client.get_balance.assert_not_called()


def test_preflight_rejects_unavailable_market():
    client = create_client()
    client.load_markets.return_value = {}

    with pytest.raises(TradingModeError, match="spot market"):
        check(client)

    client.get_balance.assert_not_called()
