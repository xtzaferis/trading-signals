from app.storage.exchange_order_repository import ExchangeOrderRepository


def prepare(repository, client_order_id="botBTC123"):
    return repository.prepare(
        client_order_id=client_order_id,
        symbol="BTC/USDC",
        side="buy",
        order_type="market",
        amount=0.001,
        reference_price=100_000.0,
    )


def test_prepare_is_idempotent():
    repository = ExchangeOrderRepository()

    assert prepare(repository) is True
    assert prepare(repository) is False

    intent = repository.get("botBTC123")
    assert intent["status"] == "PREPARED"
    assert intent["requested_amount"] == 0.001


def test_record_order_preserves_exchange_fill_state():
    repository = ExchangeOrderRepository()
    prepare(repository)

    repository.record_order(
        "botBTC123",
        {
            "id": "exchange-1",
            "status": "closed",
            "filled": 0.001,
            "remaining": 0,
            "average": 99_900.0,
            "fee": {"cost": 0.12},
        },
    )

    intent = repository.get("botBTC123")
    assert intent["exchange_order_id"] == "exchange-1"
    assert intent["status"] == "FILLED"
    assert intent["filled_amount"] == 0.001
    assert intent["average_price"] == 99_900.0
    assert intent["fee_cost"] == 0.12
    assert repository.pending() == []


def test_partial_fill_remains_pending_for_reconciliation():
    repository = ExchangeOrderRepository()
    prepare(repository)

    repository.record_order(
        "botBTC123",
        {
            "id": "exchange-1",
            "status": "open",
            "filled": 0.0005,
            "remaining": 0.0005,
        },
    )

    assert repository.get("botBTC123")["status"] == "PARTIALLY_FILLED"
    assert len(repository.pending()) == 1


def test_ambiguous_submission_is_marked_unknown():
    repository = ExchangeOrderRepository()
    prepare(repository)

    repository.mark_unknown("botBTC123", "request timed out")

    intent = repository.get("botBTC123")
    assert intent["status"] == "UNKNOWN"
    assert intent["last_error"] == "request timed out"


def test_explicit_exchange_rejection_is_terminal():
    repository = ExchangeOrderRepository()
    prepare(repository)

    repository.mark_rejected("botBTC123", "trading permission denied")

    intent = repository.get("botBTC123")
    assert intent["status"] == "REJECTED"
    assert intent["last_error"] == "trading permission denied"
    assert repository.pending() == []
