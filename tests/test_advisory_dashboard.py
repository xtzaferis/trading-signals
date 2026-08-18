from datetime import datetime, timezone
from unittest.mock import Mock

from app.advisory.dashboard import DashboardApplication, report_to_dict
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


def test_dashboard_application_passes_force_to_read_only_service():
    service = Mock()
    service.scan.return_value = sample_report()
    application = DashboardApplication(service_factory=lambda: service)

    payload = application.scan(force=True)

    service.scan.assert_called_once_with(force=True)
    assert payload["candidates"][0]["symbol"] == "AVAX/USDT"
