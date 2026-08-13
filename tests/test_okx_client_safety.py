from unittest.mock import Mock

import pytest

from app.exceptions import (
    LiveTradingDisabledError,
    OrderValidationError,
    TradingModeError,
)
from app.exchange.okx_client import OKXClient


def create_client(mode="okx_demo", live_enabled=False):
    exchange = Mock()
    exchange.create_order.return_value = {"id": "order-1"}
    client = OKXClient(
        trading_mode=mode,
        live_trading_enabled=live_enabled,
        api_key="key",
        secret="secret",
        passphrase="passphrase",
        exchange=exchange,
    )
    return client, exchange


def test_demo_mode_enables_okx_sandbox():
    _, exchange = create_client()

    exchange.set_sandbox_mode.assert_called_once_with(True)


def test_paper_mode_rejects_exchange_order():
    client, exchange = create_client(mode="paper")

    with pytest.raises(TradingModeError, match="paper mode"):
        client.create_order("BTC/USDC", "market", "buy", 0.001)

    exchange.create_order.assert_not_called()


def test_live_mode_requires_separate_opt_in():
    client, exchange = create_client(mode="live", live_enabled=False)

    with pytest.raises(LiveTradingDisabledError):
        client.create_order("BTC/USDC", "market", "buy", 0.001)

    exchange.create_order.assert_not_called()


def test_demo_order_uses_cash_mode_and_client_order_id():
    client, exchange = create_client()

    client.create_order(
        "BTC/USDC",
        "market",
        "buy",
        0.001,
        client_order_id="botBTC123",
    )

    exchange.create_order.assert_called_once_with(
        symbol="BTC/USDC",
        type="market",
        side="buy",
        amount=0.001,
        price=None,
        params={"tdMode": "cash", "clOrdId": "botBTC123"},
    )


def test_invalid_client_order_id_is_rejected():
    client, exchange = create_client()

    with pytest.raises(OrderValidationError, match="alphanumeric"):
        client.create_order(
            "BTC/USDC",
            "market",
            "buy",
            0.001,
            client_order_id="contains-hyphens",
        )

    exchange.create_order.assert_not_called()
