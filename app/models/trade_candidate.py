from dataclasses import dataclass

from app.models.trade_plan import TradePlan
from app.strategy.scoring import SignalResult


@dataclass
class TradeCandidate:

    signal: SignalResult

    trade: TradePlan