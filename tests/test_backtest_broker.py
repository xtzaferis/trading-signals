from datetime import datetime, timezone
from unittest.mock import Mock

from app.backtesting.backtest_broker import (
    BacktestBroker,
)
from app.models.trade_plan import (
    TradePlan,
)
from app.trading.portfolio import (
    Portfolio,
)


def create_trade_plan():

    return TradePlan(
        symbol="BTC/USDC",
        action="BUY",
        entry=100.0,
        stop_loss=90.0,
        take_profit=120.0,
        position_size=100.0,
        risk_reward=2.0,
    )


def test_open_position():

    portfolio = Portfolio()

    broker = BacktestBroker(
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


def test_quantity():

    portfolio = Portfolio()

    broker = BacktestBroker(
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
        == 0.9995
    )


def test_take_profit():

    portfolio = Portfolio()

    broker = BacktestBroker(
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
            portfolio.closed_positions
        )
        == 1
    )


def test_stop_loss():

    portfolio = Portfolio()

    broker = BacktestBroker(
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

    position = broker.open(
        create_trade_plan(),
        datetime.now(
            timezone.utc
        ),
    )

    closed = broker.update(
        position,
        high=105.0,
        low=99.0,
        close=103.0,
        timestamp=Mock(),
    )

    assert closed is False


def test_trade_journal_records_take_profit():

    portfolio = Portfolio()

    broker = BacktestBroker(
        portfolio
    )

    position = broker.open(
        create_trade_plan(),
        datetime.now(
            timezone.utc
        ),
    )

    assert position is not None

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


def test_break_even_moves_stop():

    portfolio = Portfolio()

    broker = BacktestBroker(
        portfolio
    )

    position = broker.open(
        create_trade_plan(),
        datetime.now(
            timezone.utc
        ),
    )

    assert position is not None

    broker.update(
        position,
        high=111.0,
        low=105.0,
        close=108.0,
        timestamp=Mock(),
    )

    assert (
        position.break_even
        is True
    )

    assert (
        position.stop_loss
        >= position.entry_price
    )


def test_trailing_stop_moves_stop():

    portfolio = Portfolio()

    broker = BacktestBroker(
        portfolio
    )

    position = broker.open(
        create_trade_plan(),
        datetime.now(
            timezone.utc
        ),
    )

    assert position is not None

    closed = broker.update(
        position,
        high=116.0,
        low=110.0,
        close=112.0,
        timestamp=Mock(),
    )

    assert (
        position.trailing_stop
        > 0
    )

    assert (
        position.stop_loss
        > 90.0
    )

    # The stop derived from this candle's high must not be applied
    # retroactively to this same candle's low.
    assert closed is False


def test_trailing_stop_becomes_active_on_next_candle():

    portfolio = Portfolio()
    broker = BacktestBroker(portfolio)
    position = broker.open(
        create_trade_plan(),
        datetime.now(timezone.utc),
    )

    assert position is not None
    assert broker.update(
        position,
        high=116.0,
        low=99.0,
        close=112.0,
        timestamp=datetime.now(timezone.utc),
    ) is False

    assert broker.update(
        position,
        high=107.0,
        low=105.0,
        close=106.0,
        timestamp=datetime.now(timezone.utc),
    ) is True
    assert position.exit_reason == "STOP_LOSS"


def test_break_even_stop_covers_fees_and_slippage():

    portfolio = Portfolio()
    broker = BacktestBroker(portfolio)
    position = broker.open(
        create_trade_plan(),
        datetime.now(timezone.utc),
    )

    assert position is not None
    assert broker.update(
        position,
        high=111.0,
        low=105.0,
        close=108.0,
        timestamp=datetime.now(timezone.utc),
    ) is False
    assert position.stop_loss > position.entry_price

    assert broker.update(
        position,
        high=position.stop_loss + 1.0,
        low=position.stop_loss - 1.0,
        close=position.stop_loss,
        timestamp=datetime.now(timezone.utc),
    ) is True
    assert position.realized_pnl >= -1e-9
