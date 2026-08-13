from datetime import datetime, timezone
from typing import Any

from app.config.settings import (
    ACCOUNT_SIZE,
    MAX_OPEN_POSITIONS,
)
from app.core.logger import logger
from app.models.position import Position
from app.models.trade_record import TradeRecord


class Portfolio:

    def __init__(self) -> None:

        self.initial_balance: float = float(ACCOUNT_SIZE)

        self.cash: float = float(ACCOUNT_SIZE)

        self.open_positions: list[Position] = []

        self.closed_positions: list[Position] = []

        self.trade_history: list[TradeRecord] = []

        self.trade_repository: Any = None

        self.peak_equity: float = float(ACCOUNT_SIZE)

        self.max_drawdown: float = 0.0


    @property
    def equity(self) -> float:

        positions_value = float(
            sum(
                position.market_value
                for position in self.open_positions
            )
        )

        return (
            self.cash
            + positions_value
        )


    @property
    def realized_pnl(self) -> float:

        return float(
            sum(
                position.realized_pnl
                for position in self.closed_positions
            )
        )


    @property
    def open_positions_count(self) -> int:

        return len(
            self.open_positions
        )


    @property
    def available_cash(self) -> float:

        return self.cash


    def update_peak_equity(self) -> None:
        self.peak_equity = max(
            self.peak_equity,
            self.equity,
        )

        current_drawdown = (
            (self.peak_equity - self.equity)
            / self.peak_equity
        )
        self.max_drawdown = max(
            self.max_drawdown,
            current_drawdown,
        )


    def get_drawdown_percent(self) -> float:
        if self.peak_equity <= 0:
            return 0.0
        return (
            (self.peak_equity - self.equity)
            / self.peak_equity
        ) * 100


    def is_max_drawdown_exceeded(
        self,
        max_drawdown_pct: float,
    ) -> bool:
        return (
            self.get_drawdown_percent()
            > max_drawdown_pct * 100
        )


    def has_open_position(
        self,
        symbol: str,
    ) -> bool:

        return any(
            position.symbol == symbol
            for position in self.open_positions
        )


    def can_open_position(
        self,
        position: Position,
    ) -> bool:

        if (
            self.open_positions_count
            >= MAX_OPEN_POSITIONS
        ):
            return False


        required_cash = (
            position.entry_price
            *
            position.quantity
        )


        return bool(
            required_cash
            <= self.cash
        )


    def add_position(
        self,
        position: Position,
    ):

        if not self.can_open_position(
            position
        ):
            return False


        cost = (
            position.entry_price
            *
            position.quantity
        )


        self.cash -= cost


        self.open_positions.append(
            position
        )


        return True



    def close_position(
        self,
        position: Position,
        exit_price: float,
        exit_reason: str = "UNKNOWN",
        closed_at: datetime | None = None,
    ):


        position.current_price = exit_price


        position.closed_at = (
            closed_at
            or datetime.now(timezone.utc)
        )


        position.status = "CLOSED"


        position.exit_reason = (
            exit_reason
        )


        # ==================================
        # PNL FIX
        # ==================================
        #
        # Αν ο Broker έχει ήδη υπολογίσει
        # net pnl με fees/slippage,
        # το κρατάμε.
        #
        # Αν όχι, υπολόγισε απλό pnl
        # για Portfolio tests.
        #

        if position.realized_pnl == 0.0:

            position.realized_pnl = (
                exit_price
                -
                position.entry_price
            ) * position.quantity



        proceeds = (
            exit_price
            *
            position.quantity
        )


        self.cash += proceeds

        if self.cash < -0.01:
            logger.warning(
                f"WARNING: Cash close to negative! "
                f"cash={self.cash}, proceeds={proceeds}"
            )


        self.open_positions.remove(
            position
        )


        self.closed_positions.append(
            position
        )



        record = TradeRecord(

            symbol=position.symbol,

            entry_price=position.entry_price,

            exit_price=exit_price,

            quantity=position.quantity,

            opened_at=position.opened_at,

            closed_at=position.closed_at,

            exit_reason=exit_reason,

            pnl=position.realized_pnl,
        )



        self.trade_history.append(
            record
        )



        if self.trade_repository:

            self.trade_repository.save(
                record
            )
