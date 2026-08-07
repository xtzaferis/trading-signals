from datetime import datetime

from app.models.position import Position
from app.models.trade_plan import TradePlan
from app.trading.portfolio import Portfolio


class BacktestBroker:

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

        quantity = (
            trade_plan.position_size
            / trade_plan.entry
        )

        position = Position(
            symbol=trade_plan.symbol,
            entry_price=trade_plan.entry,
            quantity=quantity,
            stop_loss=trade_plan.stop_loss,
            take_profit=trade_plan.take_profit,
            opened_at=opened_at,
        )

        position.update_price(
            trade_plan.entry
        )

        self.portfolio.add_position(
            position
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
            )

            return True

        if high >= position.take_profit:

            self.close(
                position,
                position.take_profit,
            )

            return True

        return False

    def close(
        self,
        position: Position,
        price: float,
    ):

        self.portfolio.close_position(
            position,
            price,
        )