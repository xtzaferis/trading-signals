from unittest.mock import Mock, patch

from app.backtesting.backtest_engine import (
    BacktestEngine,
)
from app.models.trade_plan import (
    TradePlan,
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


def test_engine_closes_position_on_take_profit():

    engine = BacktestEngine()

    position = engine.broker.open(
        trade_plan=TradePlan(
            symbol="BTC/USDC",
            action="BUY",
            entry=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            position_size=1000.0,
            risk_reward=2.0,
        ),
        opened_at=Mock(),
    )

    assert position is not None

    closed = engine.broker.update(
        position,
        high=111.0,
        low=99.0,
        close=110.0,
        timestamp=Mock(),
    )

    assert closed is True

    assert (
        engine.portfolio.open_positions_count
        == 0
    )

    assert (
        len(
            engine.portfolio.closed_positions
        )
        == 1
    )

    assert (
        position.realized_pnl
        == 100.0
    )