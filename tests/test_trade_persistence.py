from unittest.mock import Mock

from app.models.position import (
    Position,
)
from app.trading.portfolio import (
    Portfolio,
)


def create_position():

    return Position(
        symbol="BTC/USDC",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0,
    )


def test_close_position_saves_trade():

    portfolio = Portfolio()

    portfolio.trade_repository = Mock()

    position = create_position()

    portfolio.add_position(
        position
    )

    portfolio.close_position(
        position,
        exit_price=110.0,
        exit_reason="TAKE_PROFIT",
    )

    portfolio.trade_repository.save.assert_called_once()

    record = (
        portfolio.trade_repository.save
        .call_args.args[0]
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
        == 20.0
    )