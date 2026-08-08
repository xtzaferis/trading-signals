from dataclasses import dataclass
from datetime import datetime


@dataclass
class TradeRecord:

    symbol: str

    entry_price: float

    exit_price: float

    quantity: float

    opened_at: datetime

    closed_at: datetime

    exit_reason: str

    pnl: float