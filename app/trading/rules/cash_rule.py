from app.models.trade_candidate import TradeCandidate
from app.trading.portfolio import Portfolio
from app.trading.rules.base_rule import BaseTradingRule


class CashRule(BaseTradingRule):

    def validate(
        self,
        portfolio: Portfolio,
        candidate: TradeCandidate,
    ) -> tuple[bool, str | None]:

        required_cash = (
            candidate.trade.position_size
        )

        if (
            portfolio.available_cash
            < required_cash
        ):

            return (
                False,
                f"Insufficient cash "
                f"({portfolio.available_cash:.2f} USDC)."
            )

        return True, None