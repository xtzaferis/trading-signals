from unittest.mock import Mock, patch

from app.backtesting.backtest_engine import (
    BacktestEngine,
)


def test_engine_opens_position_on_buy_signal():

    engine = BacktestEngine()

    market = {
        "entry": {
            "close": 100.0,
            "atr": 5.0,
        },
    }

    mock_signal = Mock()

    mock_signal.symbol = (
        "BTC/USDC"
    )

    mock_signal.action = (
        "BUY"
    )

    mock_signal.score = 80

    mock_provider = Mock()

    mock_provider.has_next.side_effect = [
        True,
        False,
    ]

    mock_provider.next.return_value = (
        market,
        {},
    )

    with patch.object(
        engine.signal_engine,
        "evaluate",
        return_value=mock_signal,
    ), patch(
        "app.backtesting.backtest_engine.MarketProvider",
        return_value=mock_provider,
    ):

        engine.run()

    assert (
        engine.portfolio.open_positions_count
        == 1
    )

    assert (
        engine.portfolio.has_open_position(
            "BTC/USDC"
        )
    )