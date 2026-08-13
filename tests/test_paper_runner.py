from unittest.mock import Mock

import pytest

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


def test_paper_runner_clean_shutdown_persists_state():
    health = Mock()
    stop_event = Mock()
    stop_event.wait.return_value = True
    runner = PaperRunner(
        health_repository=health,
        stop_event=stop_event,
    )
    runner.run_once = Mock()
    runner.engine.save_state = Mock()

    runner.run()

    runner.run_once.assert_called_once()
    stop_event.wait.assert_called_once()
    runner.engine.save_state.assert_called_once()
    health.mark_stopped.assert_called_once()


def test_paper_runner_records_unexpected_failure_and_saves_state():
    health = Mock()
    runner = PaperRunner(health_repository=health)
    runner.run_once = Mock(side_effect=RuntimeError("unexpected failure"))
    runner.engine.save_state = Mock()

    with pytest.raises(RuntimeError, match="unexpected failure"):
        runner.run()

    health.record_runner_failure.assert_called_once_with(
        "unexpected failure"
    )
    runner.engine.save_state.assert_called_once()
    health.mark_stopped.assert_not_called()


def test_stop_interrupts_runner_wait():
    stop_event = Mock()
    runner = PaperRunner(
        health_repository=Mock(),
        stop_event=stop_event,
    )

    runner.stop()

    assert runner.running is False
    stop_event.set.assert_called_once()


def test_runner_reconciles_before_scanning():
    health = Mock()
    engine = Mock()
    engine.reconcile_execution.return_value = {"safe": True}
    runner = PaperRunner(health_repository=health, engine=engine)
    runner.scanner = Mock()
    runner.scanner.get_top_spot_pairs.return_value = []

    runner.run_once()

    engine.reconcile_execution.assert_called_once()
    runner.scanner.get_top_spot_pairs.assert_called_once()


def test_runner_keeps_monitoring_when_new_entries_are_blocked():
    health = Mock()
    engine = Mock()
    engine.reconcile_execution.return_value = {"safe": False}
    runner = PaperRunner(health_repository=health, engine=engine)
    runner.scanner = Mock()
    runner.scanner.get_top_spot_pairs.return_value = ["BTC/USDC"]
    runner._process_symbol = Mock()

    runner.run_once()

    runner._process_symbol.assert_called_once_with("BTC/USDC")


def test_runner_stops_cycle_when_reconciliation_request_fails():
    health = Mock()
    engine = Mock()
    engine.reconcile_execution.side_effect = TimeoutError(
        "reconciliation timed out"
    )
    runner = PaperRunner(health_repository=health, engine=engine)
    runner.scanner = Mock()

    runner.run_once()

    runner.scanner.get_top_spot_pairs.assert_not_called()
    health.record_scan_failure.assert_called_once_with(
        "reconciliation timed out"
    )
