from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from app.advisory.directional_signal import DirectionalSignal
from app.advisory.planner import AdvisoryLevels
from app.advisory.service import EntryAdvisoryService


def test_advisory_does_not_call_exchange_outside_session():
    scanner = Mock()
    service = EntryAdvisoryService(scanner=scanner)

    report = service.scan(datetime(2026, 8, 18, 13, 59, tzinfo=timezone.utc))

    assert report.window_open is False
    assert report.candidates == ()
    scanner.get_top_spot_pairs.assert_not_called()


def test_advisory_session_is_athens_1700_until_1900():
    service = EntryAdvisoryService(scanner=Mock())

    assert service.is_window_open(datetime(2026, 8, 18, 14, 0, tzinfo=timezone.utc))
    assert not service.is_window_open(datetime(2026, 8, 18, 16, 0, tzinfo=timezone.utc))


def test_directional_entry_ranks_before_higher_scoring_wait():
    scanner = Mock()
    scanner.get_top_futures_pairs.return_value = ["BTC/EUR", "ETH/EUR"]
    indicators = Mock()
    indicators.calculate_multi_timeframe.side_effect = [
        {"entry": {"close": 100.0}},
        {"entry": {"close": 50.0}},
    ]
    signal_engine = Mock()
    signal_engine.evaluate.side_effect = [
        DirectionalSignal("BTC/EUR", "WAIT", 95, ("Entry filter failed",)),
        DirectionalSignal("ETH/EUR", "LONG", 80, ("Bullish setup",)),
    ]
    planner = Mock()
    planner.create.return_value = AdvisoryLevels(
        direction="LONG",
        entry=50.0,
        stop_loss=48.0,
        take_profit=56.0,
        net_risk_reward=1.8,
    )
    service = EntryAdvisoryService(
        scanner=scanner,
        indicators=indicators,
        signal_engine=signal_engine,
        planner=planner,
    )

    report = service.scan(datetime(2026, 8, 18, 15, 0, tzinfo=timezone.utc))

    assert [item.symbol for item in report.candidates] == [
        "ETH/EUR",
        "BTC/EUR",
    ]
    assert report.candidates[0].status == "LONG"
    assert report.candidates[1].status == "WAIT"
    assert report.shortlist == (report.candidates[0],)
    planner.create.assert_called_once_with("LONG", {"close": 50.0})


def test_naive_timestamp_is_rejected():
    naive_time = datetime.now(timezone.utc).replace(tzinfo=None)
    with pytest.raises(ValueError, match="timezone-aware"):
        EntryAdvisoryService(scanner=Mock()).scan(naive_time)


def test_force_scans_outside_session_without_changing_actual_window():
    scanner = Mock()
    scanner.get_top_futures_pairs.return_value = []
    journal = Mock()
    outcome_tracker = Mock()
    report = EntryAdvisoryService(
        scanner=scanner,
        journal=journal,
        outcome_tracker=outcome_tracker,
    ).scan(
        datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc),
        force=True,
    )

    assert report.window_open is False
    assert report.forced is True
    scanner.get_top_futures_pairs.assert_called_once()
    journal.save_report.assert_not_called()
    outcome_tracker.resolve_open.assert_not_called()


def test_scan_reports_when_no_futures_markets_are_eligible():
    scanner = Mock()
    scanner.get_top_futures_pairs.return_value = []
    report = EntryAdvisoryService(
        scanner=scanner,
        journal=Mock(),
        outcome_tracker=Mock(),
    ).scan(datetime(2026, 8, 18, 15, 0, tzinfo=timezone.utc))

    assert report.candidates == ()
    assert report.errors == (
        "Market scan returned no eligible Kraken futures markets.",
    )


def test_scan_reports_progress_for_each_coin():
    scanner = Mock()
    scanner.get_top_futures_pairs.return_value = ["BTC/EUR"]
    indicators = Mock()
    indicators.calculate_multi_timeframe.return_value = {"entry": {"close": 100.0}}
    signal_engine = Mock()
    signal_engine.evaluate.return_value = DirectionalSignal(
        "BTC/EUR", "WAIT", 50, ("No setup",)
    )
    messages = []
    service = EntryAdvisoryService(
        scanner=scanner,
        indicators=indicators,
        signal_engine=signal_engine,
        progress=messages.append,
    )

    service.scan(datetime(2026, 8, 18, 15, 0, tzinfo=timezone.utc))

    assert messages[0].startswith("Loading Kraken")
    assert "[1/1] Loading BTC/EUR" in messages[1]
    assert messages[2] == "[1/1] BTC/EUR: WAIT score=50"


@pytest.mark.parametrize(
    ("atr_pct", "expected"),
    [(0.002, "LOW"), (0.004, "MEDIUM"), (0.008, "HIGH"), (None, "UNKNOWN")],
)
def test_advisory_classifies_short_term_volatility_risk(atr_pct, expected):
    assert EntryAdvisoryService._risk_label(atr_pct) == expected


def test_entry_is_rejected_after_large_move_from_completed_setup_candle():
    assert EntryAdvisoryService._entry_deviation_failure(100, 102, 2) is not None
    assert EntryAdvisoryService._entry_deviation_failure(100, 100.5, 2) is None


def test_order_book_vetoes_opposing_imbalance_and_wide_spread():
    assert EntryAdvisoryService._order_book_failure(
        "LONG",
        {"spread_bps": 2, "total_depth_usdt": 200_000, "imbalance": -0.6},
    ) == "Current order-book imbalance opposes the setup"
    assert EntryAdvisoryService._order_book_failure(
        "SHORT",
        {"spread_bps": 20, "total_depth_usdt": 200_000, "imbalance": 0},
    ) == "Current futures spread is too wide"
