from datetime import datetime

from app.config.settings import (
    BREAK_EVEN_ENABLED,
    BREAK_EVEN_R,
    SLIPPAGE,
    TRADING_FEE,
    TRAILING_STOP_ENABLED,
)
from app.execution.broker import Broker
from app.models.position import Position
from app.models.trade_plan import TradePlan
from app.trading.portfolio import Portfolio


class BacktestBroker(Broker):

    def __init__(
        self,
        portfolio: Portfolio,
    ):

        self.portfolio = portfolio


    def open(
        self,
        trade_plan: TradePlan,
        opened_at: datetime,
    ) -> Position | None:

        if self.portfolio.has_open_position(
            trade_plan.symbol,
        ):
            return None


        execution_price = (
            trade_plan.entry
            *
            (1 + SLIPPAGE)
        )


        quantity = (
            trade_plan.position_size
            /
            execution_price
        )


        position = Position(
            symbol=trade_plan.symbol,
            entry_price=execution_price,
            quantity=quantity,
            stop_loss=trade_plan.stop_loss,
            take_profit=trade_plan.take_profit,
            opened_at=opened_at,
        )


        position.initial_risk = abs(
            execution_price
            -
            trade_plan.stop_loss
        )


        position.update_price(
            execution_price
        )


        position.entry_fee = (
            trade_plan.position_size
            *
            TRADING_FEE
        )


        self.portfolio.add_position(
            position
        )


        self.portfolio.cash -= (
            position.entry_fee
        )


        return position



    def update(
        self,
        position: Position,
        high: float,
        low: float,
        close: float,
        timestamp: datetime,
    ) -> bool:


        # -------------------------------
        # Exit checks
        # -------------------------------

        if low <= position.stop_loss:

            self.close(
                position,
                position.stop_loss,
                "STOP_LOSS",
            )

            return True


        if high >= position.take_profit:

            self.close(
                position,
                position.take_profit,
                "TAKE_PROFIT",
            )

            return True



        # -------------------------------
        # Position management
        # -------------------------------

        position.update_price(
            high
        )


        self.manage_position(
            position
        )


        position.update_price(
            close
        )


        return False



    def manage_position(
        self,
        position: Position,
    ):


        if position.initial_risk <= 0:
            return


        profit = (
            position.highest_price
            -
            position.entry_price
        )


        r_multiple = (
            profit
            /
            position.initial_risk
        )


        if (
            BREAK_EVEN_ENABLED
            and not position.break_even
            and r_multiple >= BREAK_EVEN_R
        ):

            position.move_to_break_even()



        if TRAILING_STOP_ENABLED:

            trailing_distance = (
                position.initial_risk
            )


            new_stop = (
                position.highest_price
                -
                trailing_distance
            )


            position.update_trailing_stop(
                new_stop
            )



    def close(
        self,
        position: Position,
        price: float,
        reason: str = "MANUAL",
    ):


        execution_price = (
            price
            *
            (1 - SLIPPAGE)
        )


        exit_value = (
            execution_price
            *
            position.quantity
        )


        exit_fee = (
            exit_value
            *
            TRADING_FEE
        )


        entry_fee = getattr(
            position,
            "entry_fee",
            0.0,
        )


        gross_pnl = (
            execution_price
            -
            position.entry_price
        ) * position.quantity


        net_pnl = (
            gross_pnl
            -
            entry_fee
            -
            exit_fee
        )


        # IMPORTANT:
        # Set pnl BEFORE portfolio persistence

        position.realized_pnl = net_pnl

        position.exit_reason = reason


        self.portfolio.close_position(
            position,
            execution_price,
            reason,
        )


        self.portfolio.cash -= (
            exit_fee
        )