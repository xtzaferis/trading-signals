from app.config.settings import ACCOUNT_SIZE
from app.models.position import Position


class Portfolio:

    def __init__(self):

        self.initial_balance = ACCOUNT_SIZE

        self.cash = ACCOUNT_SIZE

        self.open_positions: list[Position] = []

        self.closed_positions: list[Position] = []

    @property
    def equity(self) -> float:

        positions_value = sum(
            position.market_value
            for position in self.open_positions
        )

        return self.cash + positions_value

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

    def add_position(
        self,
        position: Position,
    ):

        cost = (
            position.entry_price
            * position.quantity
        )

        self.cash -= cost

        self.open_positions.append(
            position
        )

    def close_position(
        self,
        position: Position,
        exit_price: float,
    ):

        position.close(exit_price)

        proceeds = (
            exit_price
            * position.quantity
        )

        self.cash += proceeds

        self.open_positions.remove(
            position
        )

        self.closed_positions.append(
            position
        )