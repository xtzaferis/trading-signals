from datetime import datetime, timezone
from unittest.mock import Mock

from app.execution.paper_broker import PaperBroker
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


def test_paper_open_position():

    portfolio = Portfolio()

    broker = PaperBroker(
        portfolio
    )

    position = broker.open(
        create_trade_plan(),
        datetime.now(
            timezone.utc
        ),
    )

    assert position is not None

    assert (
        portfolio.open_positions_count
        == 1
    )


def test_paper_quantity():

    portfolio = Portfolio()

    broker = PaperBroker(
        portfolio
    )

    position = broker.open(
        create_trade_plan(),
        datetime.now(
            timezone.utc
        ),
    )

    assert (
        round(position.quantity, 6)
        == 9.995002
    )


def test_paper_take_profit():

    portfolio = Portfolio()

    broker = PaperBroker(
        portfolio
    )

    position = broker.open(
        create_trade_plan(),
        datetime.now(
            timezone.utc
        ),
    )

    closed = broker.update(
        position,
        high=121.0,
        low=99.0,
        close=120.0,
        timestamp=Mock(),
    )

    assert closed is True

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


def test_paper_stop_loss():

    portfolio = Portfolio()

    broker = PaperBroker(
        portfolio
    )

    position = broker.open(
        create_trade_plan(),
        datetime.now(
            timezone.utc
        ),
    )

    closed = broker.update(
        position,
        high=101.0,
        low=89.0,
        close=90.0,
        timestamp=Mock(),
    )

    assert closed is True

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


def test_paper_trade_journal():

    portfolio = Portfolio()

    broker = PaperBroker(
        portfolio
    )

    position = broker.open(
        create_trade_plan(),
        datetime.now(
            timezone.utc
        ),
    )

    closed = broker.update(
        position,
        high=121.0,
        low=99.0,
        close=120.0,
        timestamp=Mock(),
    )

    assert closed is True

    assert (
        len(
            portfolio.trade_history
        )
        == 1
    )

    record = (
        portfolio.trade_history[0]
    )

    assert (
        record.symbol
        == "BTC/USDC"
    )

    assert (
        record.exit_reason
        == "TAKE_PROFIT"
    )

    assert (
        record.pnl
        > 0
    )