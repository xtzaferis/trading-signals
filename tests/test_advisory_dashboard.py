from datetime import datetime, timezone
from unittest.mock import Mock

from app.advisory.dashboard import HTML_PATH, DashboardApplication, report_to_dict
from app.advisory.derivatives_context import DerivativesContext
from app.advisory.planner import AdvisoryLevels
from app.advisory.service import AdvisoryCandidate, AdvisoryReport


def sample_report():
    candidate = AdvisoryCandidate(
        symbol="AVAX/USDT",
        status="SHORT",
        score=91,
        price=6.32,
        trade=AdvisoryLevels("SHORT", 6.32, 6.37, 6.18, 2.16),
        reasons=("Trend-aligned short",),
        derivatives=DerivativesContext(
            funding_rate=0.0001,
            open_interest_change_pct=-0.2,
            long_short_ratio=1.2,
            taker_buy_sell_ratio=0.8,
        ),
        risk="MEDIUM",
    )
    return AdvisoryReport(
        generated_at=datetime(2026, 8, 19, 15, tzinfo=timezone.utc),
        window_open=True,
        candidates=(candidate,),
        shortlist=(candidate,),
        calibration={"overall": {"sample": 4, "target_rate_pct": 50}},
    )


def test_dashboard_serializes_signal_report_for_browser():
    payload = report_to_dict(sample_report(), 12.34)

    assert payload["summary"] == {
        "long": 0,
        "short": 1,
        "wait": 0,
        "shortlisted": 1,
    }
    assert payload["duration_seconds"] == 12.3
    assert payload["candidates"][0]["shortlisted"] is True
    assert payload["candidates"][0]["trade"]["stop_loss"] == 6.37
    assert payload["candidates"][0]["derivatives"]["label"] == "BEARISH"
    assert payload["calibration"]["overall"]["sample"] == 4
    assert "expires_at" in payload["candidates"][0]


def test_dashboard_serializes_scan_errors_for_browser():
    report = AdvisoryReport(
        generated_at=datetime(2026, 8, 19, 15, tzinfo=timezone.utc),
        window_open=True,
        errors=("Market scan failed",),
    )

    payload = report_to_dict(report, 1.0)

    assert payload["errors"] == ["Market scan failed"]
    assert payload["summary"]["shortlisted"] == 0


def test_dashboard_has_visible_scan_error_container():
    html = HTML_PATH.read_text(encoding="utf-8")

    assert 'id="errors"' in html
    assert "Market scan warning" in html


def test_hosted_dashboard_refreshes_publication_and_excludes_expired_counts():
    html = HTML_PATH.read_text(encoding="utf-8")

    assert "data.candidates.filter(c=>!expired(c))" in html
    assert "['Expired',expiredCount]" in html
    assert "data.generated_at!==latestSnapshot?.generated_at" in html


def test_dashboard_application_passes_force_to_read_only_service():
    service = Mock()
    service.scan.return_value = sample_report()
    application = DashboardApplication(service_factory=lambda: service)

    payload = application.scan(force=True)

    service.scan.assert_called_once_with(force=True)
    assert payload["candidates"][0]["symbol"] == "AVAX/USDT"
