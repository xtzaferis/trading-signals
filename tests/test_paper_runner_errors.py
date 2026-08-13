from unittest.mock import Mock

import ccxt

from app.paper.paper_runner import (
    PaperRunner,
)


def test_paper_runner_handles_market_error():

    health = Mock()
    runner = PaperRunner(health_repository=health)

    runner.market = Mock()

    runner.scanner = Mock()

    runner.scanner.get_top_spot_pairs.return_value = ["BTC/USDC"]

    runner.market.get_snapshot.side_effect = (
        ccxt.NetworkError(
            "OKX connection failed"
        )
    )

    runner.run_once()

    health.record_failure.assert_called_once()
    health.complete_cycle.assert_called_once()


def test_paper_runner_records_scanner_failure():
    health = Mock()
    runner = PaperRunner(health_repository=health)
    runner.scanner = Mock()
    runner.scanner.get_top_spot_pairs.side_effect = ccxt.NetworkError(
        "scanner offline"
    )

    runner.run_once()

    health.record_scan_failure.assert_called_once_with("scanner offline")
