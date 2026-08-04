from app.strategy.scoring import SignalResult
from app.strategy.filters import (
    ema_filter,
    rsi_filter,
    macd_filter,
    adx_filter,
)


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

        if result.score >= 90:
            result.action = "BUY"

        return result