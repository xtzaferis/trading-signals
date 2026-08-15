import pytest

from app.exceptions import OrderValidationError
from app.execution.fee_normalizer import fee_cost_in_quote


def test_quote_fee_is_returned_unchanged():
    order = {"fee": {"cost": 0.08, "currency": "EUR"}}
    assert fee_cost_in_quote(order, "BTC/EUR", 100_000) == pytest.approx(0.08)


def test_base_fee_is_converted_and_multiple_fees_are_summed():
    order = {
        "fees": [
            {"cost": 0.000001, "currency": "BTC"},
            {"cost": 0.02, "currency": "EUR"},
        ]
    }
    assert fee_cost_in_quote(order, "BTC/EUR", 100_000) == pytest.approx(0.12)


def test_unknown_fee_currency_fails_closed():
    with pytest.raises(OrderValidationError, match="Cannot normalize"):
        fee_cost_in_quote(
            {"fee": {"cost": 1, "currency": "USD"}},
            "BTC/EUR",
            100_000,
        )
