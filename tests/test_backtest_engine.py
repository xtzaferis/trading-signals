from unittest.mock import Mock, patch

from app.backtesting.backtest_engine import (
    BacktestEngine,
)
from app.models.trade_plan import (
    TradePlan,
)

EMPTY_DATA = {
    "1d": [],
    "4h": [],
    "1h": [],
    "15m": [],
}


def test_engine_opens_position_on_buy_signal():

    engine = BacktestEngine()

    market = {
        "regime": {},
        "trend": {},
        "confirm": {},
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

        engine.run(
            data=EMPTY_DATA,
            close_open_positions=False,
        )


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
            position_size=100.0,
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
        round(position.realized_pnl, 6)
        == 9.730065
    )



def test_engine_closes_position_on_stop_loss():

    engine = BacktestEngine()


    position = engine.broker.open(
        trade_plan=TradePlan(
            symbol="BTC/USDC",
            action="BUY",
            entry=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            position_size=100.0,
            risk_reward=2.0,
        ),
        opened_at=Mock(),
    )


    assert position is not None


    closed = engine.broker.update(
        position,
        high=101.0,
        low=94.0,
        close=95.0,
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
        round(position.realized_pnl, 6)
        == -5.239957
    )



def test_engine_full_trade_lifecycle_take_profit():

    engine = BacktestEngine()


    first_market = {
        "regime": {},
        "trend": {},
        "confirm": {},
        "entry": {
            "close": 100.0,
            "atr": 5.0,
        },
    }


    second_market = {
        "regime": {},
        "trend": {},
        "confirm": {},
        "entry": {
            "close": 135.0,
            "high": 135.10,
            "low": 129.0,
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
        True,
        False,
    ]


    mock_provider.next.side_effect = [
        (
            first_market,
            {
                "timestamp": Mock(),
            },
        ),
        (
            second_market,
            {
                "timestamp": Mock(),
            },
        ),
    ]


    with patch.object(
        engine.signal_engine,
        "evaluate",
        return_value=mock_signal,
    ), patch(
        "app.backtesting.backtest_engine.MarketProvider",
        return_value=mock_provider,
    ):

        engine.run(data=EMPTY_DATA)


    assert (
        len(
            engine.portfolio.closed_positions
        )
        == 1
    )


    assert (
        engine.portfolio.closed_positions[0]
        .realized_pnl
        > 0
    )
