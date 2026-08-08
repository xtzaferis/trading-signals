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

    initial_risk: float = 0.0

    trailing_stop: float = 0.0

    entry_fee: float = 0.0

    exit_reason: str | None = None


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


    @property
    def risk(self) -> float:

        return abs(
            self.entry_price
            - self.stop_loss
        )


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


    def move_to_break_even(
        self,
    ):

        self.stop_loss = (
            self.entry_price
        )

        self.break_even = True


    def update_trailing_stop(
        self,
        stop_price: float,
    ):

        if stop_price > self.stop_loss:

            self.stop_loss = stop_price

            self.trailing_stop = stop_price


    def close(
        self,
        price: float,
        closed_at: datetime | None = None,
    ):

        self.current_price = price


        # Μην αντικαθιστάς PNL που έχει ήδη
        # υπολογιστεί από Broker με fees/slippage

        if self.realized_pnl == 0.0:

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