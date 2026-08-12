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

        report.initial_equity = (
            portfolio.initial_balance
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

        if report.initial_equity > 0:

            report.total_return = (
                (
                    report.current_equity
                    - report.initial_equity
                )
                / report.initial_equity
            ) * 100

        equity = (
            report.initial_equity
        )

        peak = equity

        max_drawdown = 0.0

        for position in closed:

            equity += (
                position.realized_pnl
            )

            peak = max(peak, equity)

            drawdown = (
                (peak - equity)
                / peak
            ) * 100

            max_drawdown = max(max_drawdown, drawdown)

        report.peak_equity = peak

        report.max_drawdown = (
            max_drawdown
        )

        if peak > 0:

            report.current_drawdown = (
                (
                    peak
                    - report.current_equity
                )
                / peak
            ) * 100

        if report.trades > 0:

            report.expectancy = (
                (
                    report.win_rate / 100
                )
                * report.average_winner
                +
                (
                    1
                    - report.win_rate / 100
                )
                * report.average_loser
            )

        if closed:

            r_values = [
                (
                    position.realized_pnl
                    /
                    (
                        position.initial_risk
                        * position.quantity
                    )
                )
                for position in closed
                if (
                    position.initial_risk > 0
                    and position.quantity > 0
                )
            ]

            if r_values:

                report.average_r = (
                    sum(r_values)
                    /
                    len(r_values)
                )

        return report
