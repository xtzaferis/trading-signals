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

    runner = PaperRunner()

    snapshot = create_snapshot()

    runner.market = Mock()

    runner.market.get_snapshot.return_value = (
        snapshot
    )

    runner.engine.process_snapshot = Mock()

    runner.run_once()

    runner.market.get_snapshot.assert_called_once()

    runner.engine.process_snapshot.assert_called_once()
