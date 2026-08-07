from app.config.settings import (
    MAX_OPEN_POSITIONS,
)
from app.models.trade_candidate import TradeCandidate
from app.trading.portfolio import Portfolio
from app.trading.rules.base_rule import BaseTradingRule


class MaxPositionsRule(BaseTradingRule):

    def validate(
        self,
        portfolio: Portfolio,
        candidate: TradeCandidate,
    ) -> tuple[bool, str | None]:

        if (
            portfolio.open_positions_count
            >= MAX_OPEN_POSITIONS
        ):

            message = (
                f"Maximum open positions reached "
                f"({MAX_OPEN_POSITIONS})."
            )

            return False, message

        return True, None