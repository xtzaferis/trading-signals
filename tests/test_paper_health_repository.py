from datetime import datetime, timedelta, timezone

from app.storage.paper_health_repository import PaperHealthRepository


def create_repository():
    return PaperHealthRepository()


def test_successful_cycle_is_healthy():
    repository = create_repository()
    repository.start_cycle(2)
    repository.record_success("BTC/USDC")
    repository.record_success("ETH/USDC")
    repository.complete_cycle(2, 0)

    status = repository.status()

    assert status["health"] == "HEALTHY"
    assert status["successful_symbols"] == 2
    assert status["failed_symbols"] == 0


def test_symbol_failure_degrades_cycle():
    repository = create_repository()
    repository.start_cycle(2)
    repository.record_success("BTC/USDC")
    repository.record_failure("ETH/USDC", "timeout")
    repository.complete_cycle(1, 1, "timeout")

    status = repository.status()

    assert status["health"] == "DEGRADED"
    assert status["symbol_failures"]["ETH/USDC"]["count"] == 1


def test_old_cycle_is_stale():
    repository = create_repository()
    repository.start_cycle(1)
    repository.complete_cycle(1, 0)
    old = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    repository.database.execute(
        "UPDATE paper_health SET cycle_completed_at = ? WHERE id = 1",
        (old,),
    )

    assert repository.status()["health"] == "STALE"


def test_clean_shutdown_is_reported_as_stopped():
    repository = create_repository()
    repository.start_cycle(1)
    repository.complete_cycle(1, 0)

    repository.mark_stopped()

    assert repository.status()["health"] == "STOPPED"


def test_runner_failure_is_reported_as_degraded():
    repository = create_repository()

    repository.record_runner_failure("unexpected failure")

    status = repository.status()
    assert status["health"] == "DEGRADED"
    assert status["last_error"] == "unexpected failure"
