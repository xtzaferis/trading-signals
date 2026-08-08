from datetime import datetime, timezone
from unittest.mock import Mock, patch

from app.paper.paper_engine import PaperEngine


def create_snapshot():

    return {
        "trend": {
            "candles": [],
        },
        "confirm": {
            "candles": [],
        },
        "entry": {
            "candles": [],
        },
        "timestamp": datetime.now(
            timezone.utc
        ),
    }


def test_paper_engine_opens_position():

    engine = PaperEngine()

    mock_signal = Mock()

    mock_signal.action = "BUY"
    mock_signal.score = 95
    mock_signal.symbol = "BTC/USDC"

    market = {
        "entry": {
            "close": 100.0,
            "high": 101.0,
            "low": 99.0,
            "atr": 5.0,
        }
    }

    with patch.object(
        engine.signal_engine,
        "evaluate",
        return_value=mock_signal,
    ), patch.object(
        engine.market_provider,
        "next",
        return_value=(
            market,
            create_snapshot(),
        ),
    ):

        engine.process_snapshot(
            create_snapshot()
        )

    assert (
        engine.portfolio.open_positions_count
        == 1
    )