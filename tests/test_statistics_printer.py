from unittest.mock import patch

from app.models.statistics_report import (
    StatisticsReport,
)
from app.services.statistics_printer import (
    StatisticsPrinter,
)


def test_statistics_printer_outputs_report():

    report = StatisticsReport(
        trades=10,
        wins=6,
        losses=4,
        win_rate=60.0,
        gross_profit=300.0,
        gross_loss=120.0,
        net_profit=180.0,
        profit_factor=2.5,
        average_winner=50.0,
        average_loser=-30.0,
        best_trade=100.0,
        worst_trade=-50.0,
        initial_equity=1000.0,
        current_equity=1180.0,
        total_return=18.0,
        peak_equity=1200.0,
        max_drawdown=5.0,
        current_drawdown=1.5,
        expectancy=18.0,
        average_r=1.8,
    )

    printer = StatisticsPrinter()

    with patch(
        "app.services.statistics_printer.logger"
    ) as logger:

        printer.print(
            report
        )

        logger.info.assert_any_call(
            "TRADING STATISTICS"
        )

        logger.info.assert_any_call(
            "Trades:            10"
        )

        logger.info.assert_any_call(
            "Wins:              6"
        )

        logger.info.assert_any_call(
            "Losses:            4"
        )

        logger.info.assert_any_call(
            "Profit Factor:     2.50"
        )

        logger.info.assert_any_call(
            "Expectancy:        18.00 USDC"
        )