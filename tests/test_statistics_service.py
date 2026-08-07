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