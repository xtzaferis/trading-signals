from datetime import datetime, timezone

from app.storage.exchange_position_repository import ExchangePositionRepository


def test_position_lifecycle_round_trip():
    repository = ExchangePositionRepository()
    opened_at = datetime(2026, 8, 13, tzinfo=timezone.utc)

    assert repository.prepare_entry(
        "entry1",
        "BTC/USDC",
        0.001,
        100_000.0,
        98_000.0,
        106_000.0,
    )
    repository.activate(
        "entry1",
        "exchange-entry",
        0.001,
        100_100.0,
        0.1,
        98_100.0,
        106_100.0,
        opened_at,
    )

    active = repository.find_active("BTC/USDC")
    assert active["status"] == "OPEN"
    assert active["entry_fee"] == 0.1
    assert repository.prepare_exit("entry1", "exit1", "TAKE_PROFIT")

    repository.close(
        "entry1",
        "exchange-exit",
        106_200.0,
        0.1,
        5.9,
        opened_at,
    )

    assert repository.find_active("BTC/USDC") is None


def test_second_active_position_for_symbol_is_detectable():
    repository = ExchangePositionRepository()
    assert repository.prepare_entry(
        "entry1", "BTC/USDC", 0.001, 100, 90, 120
    )

    active = repository.find_active("BTC/USDC")

    assert active["entry_client_order_id"] == "entry1"
    assert active["status"] == "PENDING_ENTRY"


def test_rejected_exit_returns_position_to_open_for_retry():
    repository = ExchangePositionRepository()
    repository.prepare_entry("entry1", "BTC/USDC", 1, 100, 90, 120)
    repository.activate(
        "entry1", "exchange-entry", 1, 100, 0, 90, 120,
        datetime.now(timezone.utc),
    )
    repository.prepare_exit("entry1", "exit1", "STOP_LOSS")

    repository.reset_exit("entry1", "insufficient balance")

    active = repository.find_active("BTC/USDC")
    assert active["status"] == "OPEN"
    assert active["exit_client_order_id"] is None
