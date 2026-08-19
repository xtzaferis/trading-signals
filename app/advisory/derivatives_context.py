from dataclasses import dataclass


@dataclass(frozen=True)
class DerivativesContext:
    """Public futures positioning data used as confirmation, never as a trigger."""

    funding_rate: float | None = None
    open_interest_change_pct: float | None = None
    open_interest_change_15m_pct: float | None = None
    open_interest_change_1h_pct: float | None = None
    long_short_ratio: float | None = None
    taker_buy_sell_ratio: float | None = None
    taker_buy_sell_ratio_15m: float | None = None
    taker_buy_sell_ratio_1h: float | None = None
    mark_price: float | None = None

    @property
    def pressure(self) -> int:
        votes: list[int] = []
        horizons = (
            (self.open_interest_change_pct, self.taker_buy_sell_ratio),
            (self.open_interest_change_15m_pct, self.taker_buy_sell_ratio_15m),
            (self.open_interest_change_1h_pct, self.taker_buy_sell_ratio_1h),
        )
        for interest_change, taker_ratio in horizons:
            if taker_ratio is None:
                continue
            if taker_ratio >= 1.05:
                vote = 1
            elif taker_ratio <= 0.95:
                vote = -1
            else:
                continue
            # New positioning gives directional taker flow more weight than
            # flow caused mostly by traders closing existing positions.
            votes.extend((vote, vote) if (interest_change or 0) > 0 else (vote,))
        if self.funding_rate is not None:
            if self.funding_rate > 0.0005:
                votes.append(-1)
            elif self.funding_rate < -0.0005:
                votes.append(1)
        if self.long_short_ratio is not None:
            if self.long_short_ratio >= 2.0:
                votes.append(-1)
            elif self.long_short_ratio <= 0.7:
                votes.append(1)
        total = sum(votes)
        return 1 if total > 0 else -1 if total < 0 else 0

    @property
    def label(self) -> str:
        return {1: "BULLISH", -1: "BEARISH", 0: "NEUTRAL"}[self.pressure]
