from app.models.statistics_report import StatisticsReport
from app.trading.portfolio import Portfolio


class StatisticsService:

    def generate(
        self,
        portfolio: Portfolio,
    ) -> StatisticsReport:

        report = StatisticsReport()

        closed = (
            portfolio.closed_positions
        )

        report.trades = len(
            closed
        )

        report.wins = sum(
            1
            for position in closed
            if position.realized_pnl > 0
        )

        report.losses = sum(
            1
            for position in closed
            if position.realized_pnl <= 0
        )

        if report.trades > 0:

            report.win_rate = (
                report.wins
                / report.trades
            ) * 100

        winners = [
            position.realized_pnl
            for position in closed
            if position.realized_pnl > 0
        ]

        losers = [
            position.realized_pnl
            for position in closed
            if position.realized_pnl < 0
        ]

        report.gross_profit = sum(
            winners
        )

        report.gross_loss = abs(
            sum(losers)
        )

        report.net_profit = (
            report.gross_profit
            - report.gross_loss
        )

        if report.gross_loss > 0:

            report.profit_factor = (
                report.gross_profit
                / report.gross_loss
            )

        elif report.gross_profit > 0:

            report.profit_factor = float(
                "inf"
            )

        if winners:

            report.average_winner = (
                sum(winners)
                / len(winners)
            )

            report.best_trade = max(
                winners
            )

        if losers:

            report.average_loser = (
                sum(losers)
                / len(losers)
            )

            report.worst_trade = min(
                losers
            )

        report.current_equity = (
            portfolio.equity
        )

        return report