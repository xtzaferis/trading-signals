from unittest.mock import Mock

import ccxt

from app.paper.paper_runner import (
    PaperRunner,
)


def test_paper_runner_handles_market_error():

    runner = PaperRunner()

    runner.market = Mock()

    runner.scanner = Mock()

    runner.scanner.get_top_spot_pairs.return_value = ["BTC/USDC"]

    runner.market.get_snapshot.side_effect = (
        ccxt.NetworkError(
            "OKX connection failed"
        )
    )

    runner.run_once()
