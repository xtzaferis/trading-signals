from app.models.statistics_report import StatisticsReport
from app.trading.portfolio import Portfolio


class StatisticsService:

    PNL_EPSILON = 1e-9

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
            if position.realized_pnl > self.PNL_EPSILON
        )

        report.losses = sum(
            1
            for position in closed
            if position.realized_pnl < -self.PNL_EPSILON
        )

        report.breakevens = (
            report.trades
            - report.wins
            - report.losses
        )

        if report.trades > 0:

            report.win_rate = (
                report.wins
                / report.trades
            ) * 100

        winners = [
            position.realized_pnl
            for position in closed
            if position.realized_pnl > self.PNL_EPSILON
        ]

        losers = [
            position.realized_pnl
            for position in closed
            if position.realized_pnl < -self.PNL_EPSILON
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
                sum(
                    position.realized_pnl
                    for position in closed
                )
                / report.trades
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

        monthly_pnl: dict[str, float] = {}

        period_start = portfolio.backtest_started_at
        period_end = portfolio.backtest_ended_at

        if period_start is not None and period_end is not None:
            cursor = period_start.replace(
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
            final_month = period_end.replace(
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
            while cursor <= final_month:
                monthly_pnl[cursor.strftime("%Y-%m")] = 0.0
                if cursor.month == 12:
                    cursor = cursor.replace(
                        year=cursor.year + 1,
                        month=1,
                    )
                else:
                    cursor = cursor.replace(
                        month=cursor.month + 1,
                    )

        for position in closed:
            if position.closed_at is None:
                continue

            month = position.closed_at.strftime(
                "%Y-%m"
            )
            pnl = position.realized_pnl
            if abs(pnl) <= self.PNL_EPSILON:
                pnl = 0.0
            monthly_pnl[month] = (
                monthly_pnl.get(month, 0.0)
                + pnl
            )

        month_start_equity = report.initial_equity

        for month, pnl in sorted(
            monthly_pnl.items()
        ):
            report.monthly_returns[month] = (
                pnl / month_start_equity * 100
                if month_start_equity > 0
                else 0.0
            )
            month_start_equity += pnl

        report.evaluated_months = len(
            report.monthly_returns
        )
        report.profitable_months = sum(
            monthly_return > self.PNL_EPSILON
            for monthly_return in report.monthly_returns.values()
        )

        return report
