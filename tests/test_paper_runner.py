from unittest.mock import Mock

from app.paper.paper_runner import (
    PaperRunner,
)


def create_snapshot():

    return {
        "regime": {
            "candles": [
                [0, 100, 101, 99, 100, 10],
            ],
        },
        "trend": {
            "candles": [
                [1, 100, 101, 99, 100, 10],
            ],
        },
        "confirm": {
            "candles": [
                [2, 100, 101, 99, 100, 10],
            ],
        },
        "entry": {
            "candles": [
                [3, 100, 101, 99, 100, 10],
            ],
        },
    }


def test_paper_runner_run_once():

    health = Mock()
    runner = PaperRunner(health_repository=health)

    snapshot = create_snapshot()

    runner.market = Mock()

    runner.scanner = Mock()

    runner.scanner.get_top_spot_pairs.return_value = [
        "BTC/USDC",
        "ETH/USDC",
    ]

    runner.market.get_snapshot.return_value = (
        snapshot
    )

    runner.engine.process_snapshot = Mock()

    runner.run_once()

    assert runner.market.get_snapshot.call_count == 2

    assert runner.engine.process_snapshot.call_count == 2
    health.start_cycle.assert_called_once_with(2)
    assert health.record_success.call_count == 2
    health.complete_cycle.assert_called_once_with(2, 0, None)
