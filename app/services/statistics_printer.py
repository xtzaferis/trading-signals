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
            f"Breakeven:         {report.breakevens}"
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
            f"Initial Equity:    {report.initial_equity:.2f} USDC"
        )

        logger.info(
            f"Current Equity:    {report.current_equity:.2f} USDC"
        )

        logger.info(
            f"Total Return:      {report.total_return:.2f}%"
        )

        logger.info(
            f"Peak Equity:       {report.peak_equity:.2f} USDC"
        )

        logger.info(
            f"Max Drawdown:      {report.max_drawdown:.2f}%"
        )

        logger.info(
            f"Current Drawdown:  {report.current_drawdown:.2f}%"
        )

        logger.info("")

        logger.info(
            f"Expectancy:        {report.expectancy:.2f} USDC"
        )

        logger.info(
            f"Average R:         {report.average_r:.2f}"
        )

        if report.monthly_returns:
            logger.info("")
            logger.info("Monthly Returns:")
            for month, monthly_return in (
                report.monthly_returns.items()
            ):
                logger.info(
                    f"  {month}:          {monthly_return:.2f}%"
                )
            logger.info(
                "Profitable Months: "
                f"{report.profitable_months}/"
                f"{report.evaluated_months}"
            )

        logger.info("=" * 50)
