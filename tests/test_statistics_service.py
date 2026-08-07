from app.models.position import Position
from app.services.statistics_service import (
    StatisticsService,
)
from app.trading.portfolio import Portfolio


def create_position(
    entry: float,
    exit: float,
):

    position = Position(
        symbol="BTC/USDC",
        entry_price=entry,
        quantity=1,
        stop_loss=entry - 5,
        take_profit=entry + 10,
    )

    position.close(exit)

    return position


def test_empty_portfolio():

    portfolio = Portfolio()

    service = StatisticsService()

    report = service.generate(
        portfolio
    )

    assert report.trades == 0
    assert report.wins == 0
    assert report.losses == 0
    assert report.win_rate == 0
    assert report.net_profit == 0


def test_single_winning_trade():

    portfolio = Portfolio()

    portfolio.closed_positions.append(
        create_position(100, 110)
    )

    report = (
        StatisticsService().generate(
            portfolio
        )
    )

    assert report.trades == 1
    assert report.wins == 1
    assert report.losses == 0
    assert report.win_rate == 100
    assert report.gross_profit == 10
    assert report.net_profit == 10


def test_single_losing_trade():

    portfolio = Portfolio()

    portfolio.closed_positions.append(
        create_position(100, 90)
    )

    report = (
        StatisticsService().generate(
            portfolio
        )
    )

    assert report.trades == 1
    assert report.wins == 0
    assert report.losses == 1
    assert report.gross_loss == 10
    assert report.net_profit == -10


def test_mixed_trades():

    portfolio = Portfolio()

    portfolio.closed_positions.extend(
        [
            create_position(100, 110),
            create_position(100, 90),
            create_position(100, 120),
        ]
    )

    report = (
        StatisticsService().generate(
            portfolio
        )
    )

    assert report.trades == 3
    assert report.wins == 2
    assert report.losses == 1
    assert report.win_rate == (
        2 / 3
    ) * 100
    assert report.gross_profit == 30
    assert report.gross_loss == 10
    assert report.net_profit == 20
    assert report.best_trade == 20
    assert report.worst_trade == -10
    assert report.average_winner == 15
    assert report.average_loser == -10


def test_profit_factor():

    portfolio = Portfolio()

    portfolio.closed_positions.extend(
        [
            create_position(100, 110),
            create_position(100, 90),
        ]
    )

    report = (
        StatisticsService().generate(
            portfolio
        )
    )

    assert report.profit_factor == 1.0