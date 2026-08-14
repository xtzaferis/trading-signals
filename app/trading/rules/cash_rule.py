from app.config.settings import QUOTE_CURRENCY
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

            message = (
                "Insufficient cash "
                f"({portfolio.available_cash:.2f} {QUOTE_CURRENCY})."
            )

            return False, message

        return True, None
