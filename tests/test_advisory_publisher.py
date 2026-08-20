import json
from datetime import datetime, timezone
from unittest.mock import Mock

from app.advisory.publisher import publish
from app.advisory.service import AdvisoryCandidate, AdvisoryReport
from app.storage.advisory_signal_repository import AdvisorySignalRepository
from app.storage.database import Database


def test_publisher_creates_static_dashboard_and_signal_payload(tmp_path):
    repository = AdvisorySignalRepository(Database(tmp_path / "publisher.db"))
    service = Mock()
    candidate = AdvisoryCandidate("BTC/USDT", "WAIT", 70, 60_000)
    service.scan.return_value = AdvisoryReport(
        datetime(2026, 8, 19, 14, tzinfo=timezone.utc),
        True,
        candidates=(candidate,),
    )
    site = tmp_path / "site"

    assert publish(site, repository, service) is True

    payload = json.loads((site / "signals.json").read_text(encoding="utf-8"))
    assert payload["candidates"][0]["symbol"] == "BTC/USDT"
    assert (site / "index.html").exists()
    assert (site / "advisory-history.json").exists()


def test_publisher_preserves_previous_signals_outside_session(tmp_path):
    repository = AdvisorySignalRepository(Database(tmp_path / "publisher.db"))
    service = Mock()
    service.scan.return_value = AdvisoryReport(
        datetime(2026, 8, 19, 12, tzinfo=timezone.utc),
        False,
    )
    site = tmp_path / "site"
    site.mkdir()
    signal_path = site / "signals.json"
    signal_path.write_text('{"previous": true}', encoding="utf-8")

    assert publish(site, repository, service) is False

    assert json.loads(signal_path.read_text(encoding="utf-8")) == {"previous": True}


def test_publisher_exposes_in_session_scan_failure(tmp_path):
    repository = AdvisorySignalRepository(Database(tmp_path / "publisher.db"))
    service = Mock()
    service.scan.return_value = AdvisoryReport(
        datetime(2026, 8, 19, 14, tzinfo=timezone.utc),
        True,
        errors=("Market scan failed: unavailable",),
    )
    site = tmp_path / "site"

    assert publish(site, repository, service) is True

    payload = json.loads((site / "signals.json").read_text(encoding="utf-8"))
    assert payload["candidates"] == []
    assert payload["errors"] == ["Market scan failed: unavailable"]
    assert payload["summary"] == {
        "long": 0,
        "short": 0,
        "wait": 0,
        "shortlisted": 0,
    }
