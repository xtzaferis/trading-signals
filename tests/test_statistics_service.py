from datetime import datetime, timezone

from app.models.position import (
    Position,
)
from app.services.statistics_service import (
    StatisticsService,
)
from app.trading.portfolio import (
    Portfolio,
)


def create_closed_position(
    pnl: float,
) -> Position:

    position = Position(
        symbol="BTC/USDC",
        entry_price=100.0,
        quantity=1.0,
        stop_loss=95.0,
        take_profit=110.0,
        opened_at=datetime.now(
            timezone.utc
        ),
    )

    position.realized_pnl = pnl

    position.status = "CLOSED"

    return position


def test_statistics_service_generates_report():

    portfolio = Portfolio()

    portfolio.closed_positions = [
        create_closed_position(100.0),
        create_closed_position(-50.0),
        create_closed_position(25.0),
    ]

    service = StatisticsService()

    report = service.generate(
        portfolio
    )

    assert (
        report.trades
        == 3
    )

    assert (
        report.wins
        == 2
    )

    assert (
        report.losses
        == 1
    )

    assert (
        report.win_rate
        == 66.66666666666666
    )

    assert (
        report.gross_profit
        == 125.0
    )

    assert (
        report.gross_loss
        == 50.0
    )

    assert (
        report.net_profit
        == 75.0
    )

    assert (
        report.profit_factor
        == 2.5
    )

    assert report.expectancy == 25.0


def test_statistics_treats_floating_point_dust_as_breakeven():
    portfolio = Portfolio()
    portfolio.closed_positions = [
        create_closed_position(1e-14),
    ]

    report = StatisticsService().generate(portfolio)

    assert report.wins == 0
    assert report.losses == 0
    assert report.breakevens == 1


def test_expectancy_includes_breakeven_probability():
    portfolio = Portfolio()
    portfolio.closed_positions = [
        create_closed_position(10.0),
        create_closed_position(-5.0),
        create_closed_position(0.0),
    ]

    report = StatisticsService().generate(portfolio)

    assert report.expectancy == 5.0 / 3.0


def test_statistics_includes_months_without_trades():
    portfolio = Portfolio()
    portfolio.backtest_started_at = datetime(
        2026, 1, 15, tzinfo=timezone.utc
    )
    portfolio.backtest_ended_at = datetime(
        2026, 3, 15, tzinfo=timezone.utc
    )

    report = StatisticsService().generate(portfolio)

    assert report.monthly_returns == {
        "2026-01": 0.0,
        "2026-02": 0.0,
        "2026-03": 0.0,
    }
    assert report.profitable_months == 0
    assert report.evaluated_months == 3
