from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Position:

    symbol: str

    entry_price: float

    quantity: float

    stop_loss: float

    take_profit: float

    opened_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    closed_at: datetime | None = None

    current_price: float = 0.0

    highest_price: float = 0.0

    status: str = "OPEN"

    break_even: bool = False

    realized_pnl: float = 0.0

    @property
    def market_value(self) -> float:

        if self.current_price == 0:

            return (
                self.entry_price
                * self.quantity
            )

        return (
            self.current_price
            * self.quantity
        )

    @property
    def unrealized_pnl(self) -> float:

        if self.current_price == 0:

            return 0.0

        return (
            self.current_price
            - self.entry_price
        ) * self.quantity

    def update_price(
        self,
        price: float,
    ):

        self.current_price = price

        if (
            self.highest_price == 0
            or price > self.highest_price
        ):

            self.highest_price = price

    def close(
        self,
        price: float,
        closed_at: datetime | None = None,
    ):

        self.current_price = price

        self.realized_pnl = (
            price
            - self.entry_price
        ) * self.quantity

        self.closed_at = (
            closed_at
            or datetime.now(
                timezone.utc
            )
        )

        self.status = "CLOSED"