from dataclasses import dataclass

from app.models.market_snapshot import (
    MarketSnapshot,
)


@dataclass
class MarketContext:

    market: dict

    snapshot: MarketSnapshot