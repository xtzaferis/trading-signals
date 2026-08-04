from dataclasses import dataclass

from app.indicators.indicator_engine import IndicatorEngine


@dataclass
class MarketState:

    bullish: bool
    score: int
    reasons: list[str]


class MarketAnalyzer:

    def __init__(self):

        self.engine = IndicatorEngine()

    def analyze(self):

        data = self.engine.calculate("BTC/USDC")

        score = 0

        reasons = []

        if data["ema20"] > data["ema50"]:
            score += 25
            reasons.append("EMA Trend")

        if data["ema50"] > data["ema200"]:
            score += 25
            reasons.append("Long Trend")

        if data["macd"] > data["macd_signal"]:
            score += 25
            reasons.append("MACD Bullish")

        if data["rsi"] > 50:
            score += 25
            reasons.append("RSI Bullish")

        return MarketState(bullish=score >= 75, score=score, reasons=reasons)
