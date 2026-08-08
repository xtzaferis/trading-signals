from app.config.settings import (
    ACCOUNT_SIZE,
    MAX_OPEN_POSITIONS,
)
from app.models.position import (
    Position,
)
from app.models.trade_record import (
    TradeRecord,
)


class Portfolio:

    def __init__(self):

        self.initial_balance = (
            ACCOUNT_SIZE
        )

        self.cash = (
            ACCOUNT_SIZE
        )

        self.open_positions: list[Position] = []

        self.closed_positions: list[Position] = []

        self.trade_history: list[TradeRecord] = []

        self.trade_repository = None


    @property
    def equity(self) -> float:

        positions_value = sum(
            position.market_value
            for position in self.open_positions
        )

        return (
            self.cash
            + positions_value
        )


    @property
    def realized_pnl(self) -> float:

        return sum(
            position.realized_pnl
            for position in self.closed_positions
        )


    @property
    def open_positions_count(self) -> int:

        return len(
            self.open_positions
        )


    @property
    def available_cash(self) -> float:

        return self.cash


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

        return (
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
    ):

        position.close(
            exit_price
        )

        proceeds = (
            exit_price
            *
            position.quantity
        )

        self.cash += proceeds


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