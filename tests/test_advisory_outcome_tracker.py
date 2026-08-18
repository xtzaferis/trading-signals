from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from app.advisory.outcome_tracker import AdvisoryOutcomeTracker


def signal(direction="LONG"):
    return {
        "id": 1,
        "generated_at": datetime(2026, 8, 19, 15, tzinfo=timezone.utc).isoformat(),
        "symbol": "BTC/USDT",
        "direction": direction,
        "reference_price": 100.0,
        "stop_loss": 98.0 if direction == "LONG" else 102.0,
        "take_profit": 104.0 if direction == "LONG" else 96.0,
        "funding_rate": 0.0001,
    }


def test_outcome_tracker_uses_stop_when_same_candle_hits_both_levels():
    repository = Mock()
    repository.list_open.return_value = [signal()]
    client = Mock()
    client.get_ohlcv_since.return_value = [[1_776_783_600_000, 100, 105, 97, 101, 10]]
    tracker = AdvisoryOutcomeTracker(client, repository)

    assert tracker.resolve_open(datetime(2026, 8, 19, 16, tzinfo=timezone.utc)) == 1

    args = repository.resolve.call_args.args
    assert args[2] == 98.0
    assert args[3] == "STOP"
    assert args[4] < -2.0


def test_outcome_tracker_resolves_short_target():
    repository = Mock()
    repository.list_open.return_value = [signal("SHORT")]
    client = Mock()
    client.get_ohlcv_since.return_value = [[1_776_783_600_000, 100, 101, 95, 96, 10]]

    resolved = AdvisoryOutcomeTracker(client, repository).resolve_open(
        datetime(2026, 8, 19, 16, tzinfo=timezone.utc)
    )

    assert resolved == 1
    assert repository.resolve.call_args.args[3] == "TARGET"
    assert repository.resolve.call_args.args[4] > 3.0


def test_outcome_tracker_closes_at_timeout():
    repository = Mock()
    open_signal = signal()
    repository.list_open.return_value = [open_signal]
    opened = datetime.fromisoformat(open_signal["generated_at"])
    client = Mock()
    client.get_ohlcv_since.return_value = [
        [
            int((opened + timedelta(hours=23)).timestamp() * 1000),
            100,
            101,
            99,
            100.5,
            10,
        ]
    ]

    resolved = AdvisoryOutcomeTracker(client, repository).resolve_open(
        opened + timedelta(hours=25)
    )

    assert resolved == 1
    assert repository.resolve.call_args.args[3] == "TIMEOUT"
