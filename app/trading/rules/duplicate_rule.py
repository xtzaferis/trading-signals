from app.models.trade_candidate import TradeCandidate
from app.trading.portfolio import Portfolio
from app.trading.rules.base_rule import BaseTradingRule


class DuplicateRule(BaseTradingRule):

    def validate(
        self,
        portfolio: Portfolio,
        candidate: TradeCandidate,
    ) -> tuple[bool, str | None]:

        symbol = candidate.signal.symbol

        if portfolio.has_open_position(
            symbol
        ):

            message = (
                f"Skipping {symbol}: "
                "position already open."
            )

            return False, message

        return True, None