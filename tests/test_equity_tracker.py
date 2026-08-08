from app.services.equity_tracker import (
    EquityTracker,
)


def test_equity_tracker():

    tracker = EquityTracker(
        1000.0
    )

    tracker.update(
        100.0
    )

    tracker.update(
        -50.0
    )

    assert (
        tracker.current_equity
        == 1050.0
    )

    assert (
        tracker.peak_equity
        == 1100.0
    )

    assert (
        tracker.max_drawdown
        > 0
    )

    assert (
        tracker.total_return()
        == 5.0
    )