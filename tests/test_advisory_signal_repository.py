from datetime import datetime, timezone

from app.advisory.derivatives_context import DerivativesContext
from app.advisory.planner import AdvisoryLevels
from app.advisory.service import AdvisoryCandidate, AdvisoryReport
from app.storage.advisory_signal_repository import AdvisorySignalRepository
from app.storage.database import Database


def test_advisory_repository_persists_and_resolves_shortlisted_signal(tmp_path):
    repository = AdvisorySignalRepository(Database(tmp_path / "advisory.db"))
    candidate = AdvisoryCandidate(
        symbol="AVAX/USDT",
        status="SHORT",
        score=91,
        price=6.32,
        trade=AdvisoryLevels("SHORT", 6.32, 6.37, 6.18, 2.16),
        reasons=("Confirmed",),
        derivatives=DerivativesContext(funding_rate=0.0001),
        risk="MEDIUM",
    )
    generated_at = datetime(2026, 8, 19, 15, tzinfo=timezone.utc)
    report = AdvisoryReport(
        generated_at=generated_at,
        window_open=True,
        candidates=(candidate,),
        shortlist=(candidate,),
    )

    repository.save_report(report)
    open_signal = repository.list_open()[0]
    repository.resolve(open_signal["id"], generated_at, 6.18, "TARGET", 2.0)

    assert repository.list_open() == []
    assert repository.statistics() == {
        "resolved": 1,
        "targets": 1,
        "stops": 0,
        "timeouts": 0,
        "average_return_pct": 2.0,
        "total_return_pct": 2.0,
    }


def test_wait_observation_is_not_opened_for_outcome_tracking(tmp_path):
    repository = AdvisorySignalRepository(Database(tmp_path / "advisory.db"))
    candidate = AdvisoryCandidate("BTC/USDT", "WAIT", 80, 60_000)
    report = AdvisoryReport(
        generated_at=datetime(2026, 8, 19, 15, tzinfo=timezone.utc),
        window_open=True,
        candidates=(candidate,),
    )

    repository.save_report(report)

    assert repository.list_open() == []
    count = repository.database.execute(
        "SELECT COUNT(*) FROM advisory_signals"
    ).fetchone()[0]
    assert count == 1


def test_public_history_round_trip_preserves_forward_statistics(tmp_path):
    first = AdvisorySignalRepository(Database(tmp_path / "first.db"))
    candidate = AdvisoryCandidate(
        "BTC/USDT",
        "LONG",
        90,
        100,
        AdvisoryLevels("LONG", 100, 98, 104, 1.8),
    )
    generated_at = datetime(2026, 8, 19, 14, tzinfo=timezone.utc)
    report = AdvisoryReport(
        generated_at,
        True,
        candidates=(candidate,),
        shortlist=(candidate,),
    )
    first.save_report(report)
    open_signal = first.list_open()[0]
    first.resolve(open_signal["id"], generated_at, 104, "TARGET", 3.8)
    history_path = tmp_path / "history.json"
    first.export_public_history(history_path)

    restored = AdvisorySignalRepository(Database(tmp_path / "restored.db"))
    assert restored.import_public_history(history_path) == 1

    assert restored.statistics()["targets"] == 1
    assert restored.statistics()["total_return_pct"] == 3.8


def test_calibration_groups_resolved_results_without_claiming_reliability(tmp_path):
    repository = AdvisorySignalRepository(Database(tmp_path / "calibration.db"))
    candidate = AdvisoryCandidate(
        "BTC/USDT",
        "SHORT",
        85,
        100,
        AdvisoryLevels("SHORT", 100, 102, 94, 1.8),
        market_regime="BEAR",
    )
    generated_at = datetime(2026, 8, 19, 14, tzinfo=timezone.utc)
    repository.save_report(
        AdvisoryReport(
            generated_at, True, candidates=(candidate,), shortlist=(candidate,)
        )
    )
    signal = repository.list_open()[0]
    repository.resolve(signal["id"], generated_at, 94, "TARGET", 5.8)

    calibration = repository.calibration()

    assert calibration["overall"]["sample"] == 1
    assert calibration["overall"]["target_rate_pct"] == 100
    assert calibration["overall"]["reliable"] is False
    assert calibration["by_direction"]["SHORT"]["average_net_return_pct"] == 5.8
    assert calibration["by_regime"]["BEAR"]["sample"] == 1
    assert calibration["by_score_band"]["80-89"]["sample"] == 1
