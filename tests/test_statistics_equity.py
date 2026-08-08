from app.services.statistics_service import (
    StatisticsService,
)
from app.trading.portfolio import (
    Portfolio,
)


def test_statistics_equity_metrics():

    portfolio = Portfolio()

    service = StatisticsService()

    report = service.generate(
        portfolio
    )

    assert (
        report.initial_equity
        == 1000.0
    )

    assert (
        report.current_equity
        == 1000.0
    )

    assert (
        report.total_return
        == 0.0
    )