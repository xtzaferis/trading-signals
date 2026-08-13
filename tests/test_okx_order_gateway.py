from unittest.mock import Mock

import pytest

from app.exceptions import OrderValidationError
from app.execution.okx_order_gateway import OKXOrderGateway


def create_gateway(free_usdc=1000.0, max_order_value=500.0):
    client = Mock()
    client.amount_to_precision.side_effect = lambda symbol, amount: amount
    client.load_markets.return_value = {
        "BTC/USDC": {
            "limits": {
                "amount": {"min": 0.00001, "max": 10.0},
                "cost": {"min": 5.0, "max": None},
            }
        }
    }
    client.get_balance.return_value = {
        "free": {"BTC": 1.0, "USDC": free_usdc}
    }
    client.create_order.return_value = {"id": "order-1"}
    return OKXOrderGateway(client, max_order_value), client


def test_validated_market_buy_reaches_client():
    gateway, client = create_gateway()

    result = gateway.submit_market_order(
        "BTC/USDC",
        "buy",
        amount=0.002,
        reference_price=100_000.0,
        client_order_id="botBTC123",
    )

    assert result == {"id": "order-1"}
    client.create_order.assert_called_once_with(
        symbol="BTC/USDC",
        order_type="market",
        side="buy",
        amount=0.002,
        client_order_id="botBTC123",
    )


def test_order_above_safety_ceiling_is_rejected():
    gateway, client = create_gateway(max_order_value=100.0)

    with pytest.raises(OrderValidationError, match="safety ceiling"):
        gateway.submit_market_order(
            "BTC/USDC",
            "buy",
            amount=0.002,
            reference_price=100_000.0,
            client_order_id="botBTC123",
        )

    client.create_order.assert_not_called()


def test_order_with_insufficient_balance_is_rejected():
    gateway, client = create_gateway(free_usdc=50.0)

    with pytest.raises(OrderValidationError, match="Insufficient"):
        gateway.submit_market_order(
            "BTC/USDC",
            "buy",
            amount=0.002,
            reference_price=100_000.0,
            client_order_id="botBTC123",
        )

    client.create_order.assert_not_called()


def test_order_below_exchange_minimum_is_rejected():
    gateway, client = create_gateway()

    with pytest.raises(OrderValidationError, match="below the OKX minimum"):
        gateway.submit_market_order(
            "BTC/USDC",
            "buy",
            amount=0.000001,
            reference_price=100_000.0,
            client_order_id="botBTC123",
        )

    client.create_order.assert_not_called()


def test_exchange_amount_precision_is_used_for_order():
    gateway, client = create_gateway()
    client.amount_to_precision.return_value = 0.00123
    client.amount_to_precision.side_effect = None

    gateway.submit_market_order(
        "BTC/USDC",
        "buy",
        amount=0.00123456,
        reference_price=100_000.0,
        client_order_id="botBTC123",
    )

    client.create_order.assert_called_once_with(
        symbol="BTC/USDC",
        order_type="market",
        side="buy",
        amount=0.00123,
        client_order_id="botBTC123",
    )


def test_reconciliation_detects_duplicate_client_order_ids():
    gateway, client = create_gateway()
    client.fetch_open_orders.return_value = [
        {"id": "1", "clientOrderId": "duplicate1"},
        {"id": "2", "info": {"clOrdId": "duplicate1"}},
    ]

    snapshot = gateway.reconciliation_snapshot("BTC/USDC")

    assert snapshot["safe"] is False
    assert snapshot["open_order_count"] == 2
    assert snapshot["duplicate_client_order_ids"] == ["duplicate1"]
