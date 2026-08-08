from datetime import datetime

from app.config.settings import (
    SLIPPAGE,
    TRADING_FEE,
)
from app.execution.broker import Broker
from app.models.position import Position
from app.models.trade_plan import TradePlan
from app.trading.portfolio import Portfolio


class PaperBroker(Broker):

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
            * (1 + SLIPPAGE)
        )

        quantity = (
            trade_plan.position_size
            / execution_price
        )

        position = Position(
            symbol=trade_plan.symbol,
            entry_price=execution_price,
            quantity=quantity,
            stop_loss=trade_plan.stop_loss,
            take_profit=trade_plan.take_profit,
            opened_at=opened_at,
        )

        position.update_price(
            execution_price
        )

        position.entry_fee = (
            trade_plan.position_size
            * TRADING_FEE
        )

        added = self.portfolio.add_position(
            position
        )

        if not added:
            return None

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

        position.update_price(
            close
        )

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

        return False

    def close(
        self,
        position: Position,
        price: float,
        reason: str = "MANUAL",
    ):

        execution_price = (
            price
            * (1 - SLIPPAGE)
        )

        exit_value = (
            execution_price
            * position.quantity
        )

        exit_fee = (
            exit_value
            * TRADING_FEE
        )

        entry_fee = getattr(
            position,
            "entry_fee",
            0.0,
        )

        gross_pnl = (
            execution_price
            - position.entry_price
        ) * position.quantity

        net_pnl = (
            gross_pnl
            - entry_fee
            - exit_fee
        )

        self.portfolio.close_position(
            position,
            execution_price,
            reason,
        )

        position.realized_pnl = (
            net_pnl
        )

        self.portfolio.cash -= (
            exit_fee
        )