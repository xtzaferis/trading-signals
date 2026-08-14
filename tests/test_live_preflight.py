from unittest.mock import Mock

import pytest

from app.exceptions import TradingModeError
from app.live.preflight import check


def create_client(**permission_overrides):
    client = Mock()
    permissions = {
        "can_view": True,
        "can_trade": True,
        "can_transfer": False,
        "can_receive": False,
        "portfolio_uuid": "portfolio-1",
        "portfolio_type": "DEFAULT",
    }
    permissions.update(permission_overrides)
    client.get_key_permissions.return_value = permissions
    client.load_markets.return_value = {
        "BTC/USDC": {"spot": True, "active": True}
    }
    client.get_balance.return_value = {"free": {"USDC": 100.0}}
    client.fetch_open_orders.return_value = []
    return client


def test_preflight_is_read_only_and_reports_portfolio():
    client = create_client()

    result = check(client)

    assert result == {
        "exchange": "coinbase",
        "permissions": ["trade", "view"],
        "portfolio_id": "portfolio-1",
        "free_quote": 100.0,
        "quote_currency": "USDC",
        "market_symbol": "BTC/USDC",
        "open_order_count": 0,
    }
    client.create_market_order.assert_not_called()
    client.preview_market_buy.assert_not_called()


def test_preflight_rejects_missing_trade_permission():
    client = create_client(can_trade=False)

    with pytest.raises(TradingModeError, match="Trade permission"):
        check(client)

    client.get_balance.assert_not_called()


def test_preflight_rejects_transfer_permission():
    client = create_client(can_transfer=True)

    with pytest.raises(TradingModeError, match="must not have Transfer"):
        check(client)

    client.get_balance.assert_not_called()


def test_preflight_rejects_unavailable_market():
    client = create_client()
    client.load_markets.return_value = {}

    with pytest.raises(TradingModeError, match="spot market"):
        check(client)

    client.get_balance.assert_not_called()
