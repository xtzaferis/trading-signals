from unittest.mock import Mock

import pytest

from app.exceptions import DuplicateOrderIntentError, OrderValidationError
from app.execution.kraken_order_gateway import KrakenOrderGateway


def create_gateway(max_order_value=10.0, eur=20.0):
    client = Mock()
    client.amount_to_precision.side_effect = lambda symbol, amount: amount
    client.price_to_precision.side_effect = lambda symbol, price: price
    client.load_markets.return_value = {
        "BTC/EUR": {
            "spot": True,
            "active": True,
            "limits": {
                "amount": {"min": 0.00001, "max": 1.0},
                "cost": {"min": 5.0, "max": None},
            },
        }
    }
    client.get_balance.return_value = {
        "free": {"BTC": 1.0, "EUR": eur}
    }
    client.create_market_order.return_value = {
        "id": "entry-order",
        "status": "closed",
        "filled": 0.0001,
        "remaining": 0,
        "average": 100_000.0,
    }
    return KrakenOrderGateway(client, max_order_value), client


def test_quote_buy_carries_attached_native_stop():
    gateway, client = create_gateway()

    order = gateway.submit_market_order(
        "BTC/EUR",
        "buy",
        amount=0.0001,
        reference_price=100_000.0,
        client_order_id="kentry-1",
        quote_cost=10.0,
        stop_loss=98_000.0,
    )

    assert order["status"] == "closed"
    client.create_market_order.assert_called_once_with(
        symbol="BTC/EUR",
        side="buy",
        amount=0.0001,
        client_order_id="kentry-1",
        quote_cost=10.0,
        stop_loss=98_000.0,
    )


def test_gateway_rejects_order_above_ten_euro_cap():
    gateway, client = create_gateway()

    with pytest.raises(OrderValidationError, match="safety ceiling"):
        gateway.submit_market_order(
            "BTC/EUR", "buy", 0.00011, 100_000, "kentry-1", quote_cost=11
        )

    client.create_market_order.assert_not_called()


def test_duplicate_intent_never_reaches_kraken_twice():
    gateway, client = create_gateway()
    arguments = {
        "symbol": "BTC/EUR",
        "side": "buy",
        "amount": 0.0001,
        "reference_price": 100_000.0,
        "client_order_id": "kentry-1",
        "quote_cost": 10.0,
        "stop_loss": 98_000.0,
    }

    gateway.submit_market_order(**arguments)
    with pytest.raises(DuplicateOrderIntentError):
        gateway.submit_market_order(**arguments)

    assert client.create_market_order.call_count == 1


def test_ambiguous_submission_is_persisted_for_reconciliation():
    gateway, client = create_gateway()
    client.create_market_order.side_effect = TimeoutError("timed out")

    with pytest.raises(TimeoutError):
        gateway.submit_market_order(
            "BTC/EUR", "buy", 0.0001, 100_000, "kentry-1", quote_cost=10
        )

    assert gateway.order_repository.get("kentry-1")["status"] == "UNKNOWN"


def test_generic_kraken_validation_error_is_terminal_rejection():
    import ccxt

    gateway, client = create_gateway()
    client.create_market_order.side_effect = ccxt.ExchangeError(
        'kraken {"error":["EOrder:Invalid price"]}'
    )

    with pytest.raises(OrderValidationError, match="Kraken rejected"):
        gateway.submit_market_order(
            "BTC/EUR", "buy", 0.0001, 100_000, "kentry-1", quote_cost=10
        )

    assert gateway.order_repository.get("kentry-1")["status"] == "REJECTED"


def test_pending_order_is_refreshed_by_exchange_id():
    gateway, client = create_gateway()
    client.create_market_order.return_value = {
        "id": "entry-order",
        "status": "open",
        "filled": 0,
    }
    client.fetch_order.return_value = {
        "id": "entry-order",
        "status": "closed",
        "filled": 0.0001,
        "average": 100_000.0,
    }

    result = gateway.submit_market_order(
        "BTC/EUR", "buy", 0.0001, 100_000, "kentry-1", quote_cost=10
    )

    assert result["status"] == "closed"
    assert gateway.order_repository.get("kentry-1")["status"] == "FILLED"
