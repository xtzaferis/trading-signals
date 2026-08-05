from dataclasses import dataclass

from app.config.settings import (
    MARKET_MIN_SCORE,
    MARKET_SYMBOL,
    TREND_TIMEFRAME,
)
from app.indicators.indicator_engine import IndicatorEngine


@dataclass
class MarketState:
    bullish: bool
    score: int
    reasons: list[str]


class MarketAnalyzer:

    def __init__(self):
        self.engine = IndicatorEngine()

    def analyze(self) -> MarketState:

        data = self.engine.calculate(
            symbol=MARKET_SYMBOL,
            timeframe=TREND_TIMEFRAME,
        )

        score = 0
        reasons = []

        if data["ema20"] > data["ema50"]:
            score += 25
            reasons.append("EMA20 > EMA50")

        if data["ema50"] > data["ema200"]:
            score += 25
            reasons.append("EMA50 > EMA200")

        if data["macd"] > data["macd_signal"]:
            score += 25
            reasons.append("Bullish MACD")

        if data["rsi"] > 50:
            score += 25
            reasons.append("RSI > 50")

        return MarketState(
            bullish=score >= MARKET_MIN_SCORE,
            score=score,
            reasons=reasons,
        )