from dataclasses import dataclass

from app.config.settings import (
    BACKTEST_ENTRY_FEE,
    BACKTEST_ENTRY_SLIPPAGE,
    BACKTEST_EXIT_FEE,
    BACKTEST_EXIT_SLIPPAGE,
    MAKER_FEE,
    MAKER_SLIPPAGE,
    TAKER_FEE,
    TAKER_SLIPPAGE,
)


@dataclass(frozen=True)
class ExecutionCostModel:
    entry_fee: float
    exit_fee: float
    entry_slippage: float
    exit_slippage: float

    def buy_price(self, reference_price: float) -> float:
        return reference_price * (1 + self.entry_slippage)

    def sell_price(self, reference_price: float) -> float:
        return reference_price * (1 - self.exit_slippage)

    def entry_fee_cost(self, price: float, quantity: float) -> float:
        return price * quantity * self.entry_fee

    def exit_fee_cost(self, price: float, quantity: float) -> float:
        return price * quantity * self.exit_fee

    def net_outcome(
        self,
        entry_reference: float,
        exit_reference: float,
        quantity: float = 1.0,
    ) -> float:
        entry = self.buy_price(entry_reference)
        exit_price = self.sell_price(exit_reference)
        return (
            (exit_price - entry) * quantity
            - self.entry_fee_cost(entry, quantity)
            - self.exit_fee_cost(exit_price, quantity)
        )


BACKTEST_COSTS = ExecutionCostModel(
    entry_fee=BACKTEST_ENTRY_FEE,
    exit_fee=BACKTEST_EXIT_FEE,
    entry_slippage=BACKTEST_ENTRY_SLIPPAGE,
    exit_slippage=BACKTEST_EXIT_SLIPPAGE,
)

POST_ONLY_LIVE_COSTS = ExecutionCostModel(
    entry_fee=MAKER_FEE,
    exit_fee=TAKER_FEE,
    entry_slippage=MAKER_SLIPPAGE,
    exit_slippage=TAKER_SLIPPAGE,
)
