from app.config.weights import BUY_THRESHOLD
from app.strategy.filters import (
    adx_filter,
    ema_filter,
    macd_filter,
    rsi_filter,
)
from app.strategy.scoring import SignalResult


class SignalEngine:

    def evaluate(self, symbol, data):

        result = SignalResult(symbol=symbol)

        filters = [
            ema_filter,
            rsi_filter,
            macd_filter,
            adx_filter,
        ]

        for check in filters:

            points, reason = check(data)

            result.score += points

            if reason:
                result.reasons.append(reason)

        result.confidence = result.score / 100

        if result.score >= BUY_THRESHOLD:
            result.action = "BUY"

        return result