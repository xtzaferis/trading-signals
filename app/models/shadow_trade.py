from dataclasses import dataclass
from datetime import datetime


@dataclass
class ShadowTrade:
    symbol: str
    regime: str
    entry_price: float
    stop_loss: float
    take_profit: float
    quantity: float
    opened_at: datetime
    id: int | None = None
    status: str = "OPEN"
    closed_at: datetime | None = None
    exit_price: float | None = None
    exit_reason: str | None = None
    pnl: float | None = None
