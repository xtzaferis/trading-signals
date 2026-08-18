from dataclasses import dataclass


@dataclass(frozen=True)
class DerivativesContext:
    """Public futures positioning data used as confirmation, never as a trigger."""

    funding_rate: float | None = None
    open_interest_change_pct: float | None = None
    long_short_ratio: float | None = None
    taker_buy_sell_ratio: float | None = None
    mark_price: float | None = None

    @property
    def pressure(self) -> int:
        votes = []
        if (
            self.open_interest_change_pct is not None
            and self.open_interest_change_pct > 0
            and self.taker_buy_sell_ratio is not None
        ):
            votes.append(1 if self.taker_buy_sell_ratio > 1 else -1)
        if self.taker_buy_sell_ratio is not None:
            votes.append(1 if self.taker_buy_sell_ratio > 1 else -1)
        if self.funding_rate is not None:
            if self.funding_rate > 0.0005:
                votes.append(-1)
            elif self.funding_rate < -0.0005:
                votes.append(1)
        total = sum(votes)
        return 1 if total > 0 else -1 if total < 0 else 0

    @property
    def label(self) -> str:
        return {1: "BULLISH", -1: "BEARISH", 0: "NEUTRAL"}[self.pressure]
