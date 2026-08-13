from datetime import datetime, timezone
from unittest.mock import Mock, patch

from app.models.position import Position
from app.paper.paper_engine import PaperEngine


def create_snapshot():

    return {
        "regime": {
            "candles": [],
        },
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


def test_paper_engine_monitors_position_during_hold_signal():
    engine = PaperEngine()
    engine.shadow_tracker = Mock()
    position = Position(
        symbol="BTC/USDC",
        entry_price=100,
        quantity=1,
        stop_loss=95,
        take_profit=110,
    )
    engine.portfolio.open_positions.append(position)
    engine.broker.update = Mock(return_value=False)
    hold_signal = Mock(action="HOLD", score=0)
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
        return_value=hold_signal,
    ), patch.object(
        engine.market_provider,
        "next",
        return_value=(market, create_snapshot()),
    ):
        engine.process_snapshot(create_snapshot())

    engine.broker.update.assert_called_once()


def test_paper_engine_ignores_repeated_completed_candle():
    engine = PaperEngine()
    engine.shadow_tracker = Mock()
    entry_timestamp = datetime.now(timezone.utc)
    market = {
        "entry": {
            "timestamp": entry_timestamp,
            "close": 100.0,
            "high": 101.0,
            "low": 99.0,
            "atr": 5.0,
        }
    }
    engine.signal_engine.evaluate = Mock(
        return_value=Mock(action="HOLD", score=0)
    )
    engine.market_provider.next = Mock(
        return_value=(market, create_snapshot())
    )

    engine.process_snapshot(create_snapshot())
    engine.process_snapshot(create_snapshot())

    engine.signal_engine.evaluate.assert_called_once()
