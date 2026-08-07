from datetime import datetime, timezone

from app.backtesting.backtest_broker import (
    BacktestBroker,
)
from app.models.trade_plan import TradePlan
from app.trading.portfolio import Portfolio


def create_trade_plan():

    return TradePlan(
        symbol="BTC/USDC",
        action="BUY",
        entry=100.0,
        stop_loss=90.0,
        take_profit=120.0,
        position_size=1000.0,
        risk_reward=2.0,
    )


def test_open_position():

    portfolio = Portfolio()

    broker = BacktestBroker(
        portfolio
    )

    trade_plan = (
        create_trade_plan()
    )

    broker.open(
        trade_plan,
        datetime.now(
            timezone.utc
        ),
    )

    assert (
        portfolio.open_positions_count
        == 1
    )


def test_quantity():

    portfolio = Portfolio()

    broker = BacktestBroker(
        portfolio
    )

    trade_plan = (
        create_trade_plan()
    )

    position = broker.open(
        trade_plan,
        datetime.now(
            timezone.utc
        ),
    )

    assert (
        position.quantity
        == 10.0
    )


def test_take_profit():

    portfolio = Portfolio()

    broker = BacktestBroker(
        portfolio
    )

    trade_plan = (
        create_trade_plan()
    )

    position = broker.open(
        trade_plan,
        datetime.now(
            timezone.utc
        ),
    )

    closed = broker.update(
        position,
        high=125.0,
        low=99.0,
        close=123.0,
        timestamp=datetime.now(
            timezone.utc
        ),
    )

    assert closed

    assert (
        portfolio.open_positions_count
        == 0
    )

    assert (
        len(
            portfolio.closed_positions
        )
        == 1
    )


def test_stop_loss():

    portfolio = Portfolio()

    broker = BacktestBroker(
        portfolio
    )

    trade_plan = (
        create_trade_plan()
    )

    position = broker.open(
        trade_plan,
        datetime.now(
            timezone.utc
        ),
    )

    closed = broker.update(
        position,
        high=101.0,
        low=85.0,
        close=86.0,
        timestamp=datetime.now(
            timezone.utc
        ),
    )

    assert closed

    assert (
        portfolio.open_positions_count
        == 0
    )

    assert (
        len(
            portfolio.closed_positions
        )
        == 1
    )


def test_no_exit():

    portfolio = Portfolio()

    broker = BacktestBroker(
        portfolio
    )

    trade_plan = (
        create_trade_plan()
    )

    position = broker.open(
        trade_plan,
        datetime.now(
            timezone.utc
        ),
    )

    closed = broker.update(
        position,
        high=110.0,
        low=95.0,
        close=108.0,
        timestamp=datetime.now(
            timezone.utc
        ),
    )

    assert not closed

    assert (
        portfolio.open_positions_count
        == 1
    )