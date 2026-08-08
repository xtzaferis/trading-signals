from app.models.statistics_report import (
    StatisticsReport,
)
from app.services.equity_tracker import (
    EquityTracker,
)
from app.storage.trade_repository import (
    TradeRepository,
)


class TradeStatisticsService:

    def __init__(self):

        self.repository = (
            TradeRepository()
        )

    def generate(self):

        trades = (
            self.repository.get_all()
        )

        pnl_values = [
            trade[7]
            for trade in trades
        ]

        tracker = EquityTracker(
            1000.0
        )

        for pnl in pnl_values:

            tracker.update(
                pnl
            )

        winners = [
            pnl
            for pnl in pnl_values
            if pnl > 0
        ]

        losers = [
            pnl
            for pnl in pnl_values
            if pnl < 0
        ]

        gross_profit = sum(
            winners
        )

        gross_loss = abs(
            sum(losers)
        )

        net_profit = sum(
            pnl_values
        )

        profit_factor = 0.0

        if gross_loss:

            profit_factor = (
                gross_profit
                /
                gross_loss
            )

        win_rate = 0.0

        if trades:

            win_rate = (
                len(winners)
                /
                len(trades)
            ) * 100

        average_winner = 0.0

        if winners:

            average_winner = (
                gross_profit
                /
                len(winners)
            )

        average_loser = 0.0

        if losers:

            average_loser = (
                sum(losers)
                /
                len(losers)
            )

        expectancy = 0.0

        if trades:

            expectancy = (
                (
                    len(winners)
                    /
                    len(trades)
                )
                *
                average_winner
            ) + (
                (
                    len(losers)
                    /
                    len(trades)
                )
                *
                average_loser
            )

        return StatisticsReport(

            trades=len(trades),

            wins=len(winners),

            losses=len(losers),

            win_rate=win_rate,

            gross_profit=gross_profit,

            gross_loss=gross_loss,

            net_profit=net_profit,

            profit_factor=profit_factor,

            average_winner=average_winner,

            average_loser=average_loser,

            best_trade=max(
                pnl_values,
                default=0.0,
            ),

            worst_trade=min(
                pnl_values,
                default=0.0,
            ),

            expectancy=expectancy,

            initial_equity=(
                tracker.initial_equity
            ),

            current_equity=(
                tracker.current_equity
            ),

            total_return=(
                tracker.total_return()
            ),

            peak_equity=(
                tracker.peak_equity
            ),

            max_drawdown=(
                tracker.max_drawdown
            ),

            current_drawdown=(
                tracker.current_drawdown
            ),

        )