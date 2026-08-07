from app.core.logger import logger
from app.models.statistics_report import StatisticsReport


class StatisticsPrinter:

    def print(
        self,
        report: StatisticsReport,
    ):

        logger.info("")
        logger.info("=" * 50)
        logger.info("TRADING STATISTICS")
        logger.info("=" * 50)

        logger.info(
            f"Trades:            {report.trades}"
        )

        logger.info(
            f"Wins:              {report.wins}"
        )

        logger.info(
            f"Losses:            {report.losses}"
        )

        logger.info(
            f"Win Rate:          {report.win_rate:.2f}%"
        )

        logger.info("")

        logger.info(
            f"Gross Profit:      {report.gross_profit:.2f} USDC"
        )

        logger.info(
            f"Gross Loss:        {report.gross_loss:.2f} USDC"
        )

        logger.info(
            f"Net Profit:        {report.net_profit:.2f} USDC"
        )

        logger.info(
            f"Profit Factor:     {report.profit_factor:.2f}"
        )

        logger.info("")

        logger.info(
            f"Average Winner:    {report.average_winner:.2f} USDC"
        )

        logger.info(
            f"Average Loser:     {report.average_loser:.2f} USDC"
        )

        logger.info(
            f"Best Trade:        {report.best_trade:.2f} USDC"
        )

        logger.info(
            f"Worst Trade:       {report.worst_trade:.2f} USDC"
        )

        logger.info("")

        logger.info(
            f"Current Equity:    {report.current_equity:.2f} USDC"
        )

        logger.info("=" * 50)