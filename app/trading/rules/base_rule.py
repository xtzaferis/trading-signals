from abc import ABC, abstractmethod

from app.models.trade_candidate import TradeCandidate
from app.trading.portfolio import Portfolio


class BaseTradingRule(ABC):

    @abstractmethod
    def validate(
        self,
        portfolio: Portfolio,
        candidate: TradeCandidate,
    ) -> tuple[bool, str | None]:
        pass