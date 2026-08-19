from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from app.advisory.directional_signal import DirectionalSignal
from app.advisory.planner import AdvisoryLevels
from app.advisory.replay import AdvisoryReplayEngine

MINUTES = {"1d": 1440, "4h": 240, "1h": 60, "15m": 15, "5m": 5}


def candles(timeframe, start, count):
    step = timedelta(minutes=MINUTES[timeframe])
    values = []
    for index in range(count):
        timestamp = start + step * index
        high = 105 if timeframe == "5m" and timestamp.hour == 14 else 101
        values.append([int(timestamp.timestamp() * 1000), 100, high, 99, 100, 1000])
    return values


def test_replay_uses_athens_decision_time_and_resolves_target():
    signal_engine = Mock()
    signal_engine.evaluate.return_value = DirectionalSignal(
        "BTC/USDT", "LONG", 90, ("Confirmed",)
    )
    planner = Mock()
    planner.create.return_value = AdvisoryLevels("LONG", 100, 98, 104, 1.8)
    engine = AdvisoryReplayEngine(signal_engine, planner)
    evaluation_start = datetime(2026, 8, 19, tzinfo=timezone.utc)
    data = {
        timeframe: candles(
            timeframe,
            evaluation_start - timedelta(minutes=minutes * 250),
            250 + int(timedelta(days=2) / timedelta(minutes=minutes)),
        )
        for timeframe, minutes in MINUTES.items()
    }

    result = engine.run(
        "BTC/USDT",
        data,
        evaluation_start,
        evaluation_start + timedelta(hours=23),
    )

    assert len(result.trades) == 1
    assert result.trades[0].opened_at.hour == 17
    assert result.trades[0].opened_at.utcoffset() == timedelta(hours=3)
    assert result.trades[0].outcome == "TARGET"
    assert result.trades[0].net_return_pct > 3


def test_replay_result_compounds_trade_returns():
    assert AdvisoryReplayEngine._net_return("SHORT", 100, 96, 0) > 0.038


def test_replay_evaluates_every_fifteen_minutes_in_full_session():
    engine = AdvisoryReplayEngine()
    start = datetime(2026, 8, 19, 14, tzinfo=timezone.utc)

    decisions = list(engine._decision_times(start, start + timedelta(hours=2)))

    assert len(decisions) == 8
    assert decisions[0].hour == 17
    assert decisions[-1].hour == 18
    assert decisions[-1].minute == 45
