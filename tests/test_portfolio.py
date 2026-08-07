from app.config.settings import ACCOUNT_SIZE
from app.models.position import Position
from app.trading.portfolio import Portfolio


def create_position():

    return Position(
        symbol="BTC/USDC",
        entry_price=100.0,
        quantity=2.0,
        stop_loss=95.0,
        take_profit=110.0,
    )


def test_new_portfolio_has_initial_balance():

    portfolio = Portfolio()

    assert portfolio.cash == ACCOUNT_SIZE
    assert portfolio.available_cash == ACCOUNT_SIZE
    assert portfolio.equity == ACCOUNT_SIZE
    assert portfolio.open_positions_count == 0
    assert portfolio.realized_pnl == 0


def test_add_position_reduces_cash():

    portfolio = Portfolio()

    position = create_position()

    portfolio.add_position(position)

    assert portfolio.cash == ACCOUNT_SIZE - 200
    assert portfolio.open_positions_count == 1


def test_has_open_position():

    portfolio = Portfolio()

    position = create_position()

    portfolio.add_position(position)

    assert portfolio.has_open_position("BTC/USDC")
    assert not portfolio.has_open_position("ETH/USDC")


def test_close_position_moves_position():

    portfolio = Portfolio()

    position = create_position()

    portfolio.add_position(position)

    portfolio.close_position(
        position,
        exit_price=110.0,
    )

    assert portfolio.open_positions_count == 0
    assert len(portfolio.closed_positions) == 1


def test_realized_profit():

    portfolio = Portfolio()

    position = create_position()

    portfolio.add_position(position)

    portfolio.close_position(
        position,
        exit_price=110.0,
    )

    assert position.realized_pnl == 20.0
    assert portfolio.realized_pnl == 20.0


def test_cash_after_profitable_trade():

    portfolio = Portfolio()

    position = create_position()

    portfolio.add_position(position)

    portfolio.close_position(
        position,
        exit_price=110.0,
    )

    assert portfolio.cash == ACCOUNT_SIZE + 20


def test_equity_with_open_position():

    portfolio = Portfolio()

    position = create_position()

    portfolio.add_position(position)

    position.update_price(105.0)

    assert portfolio.equity == ACCOUNT_SIZE + 10