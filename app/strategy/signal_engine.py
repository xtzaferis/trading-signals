from app.config.settings import MIN_SCORE
from app.strategy.filters import (
    adx_filter,
    confirmation_filter,
    ema_filter,
    entry_filter,
    macd_filter,
    rsi_filter,
    trend_filter,
)
from app.strategy.scoring import SignalResult


class SignalEngine:

    def evaluate(self, symbol, data):

        result = SignalResult(symbol=symbol)

        # ---------------------------------
        # Multi-Timeframe Data
        # ---------------------------------

        trend = data["trend"]
        confirm = data["confirm"]
        entry = data["entry"]

        # ---------------------------------
        # Gate Strategy
        # ---------------------------------

        if not trend_filter(trend):
            result.action = "HOLD"
            result.reasons.append("Trend filter failed")
            return result

        if not confirmation_filter(confirm):
            result.action = "HOLD"
            result.reasons.append("Confirmation filter failed")
            return result

        if not entry_filter(entry):
            result.action = "HOLD"
            result.reasons.append("Entry filter failed")
            return result

        # ---------------------------------
        # Scoring
        # ---------------------------------

        filters = [
            ema_filter,
            rsi_filter,
            macd_filter,
            adx_filter,
        ]

        for check in filters:

            points, reason = check(
                trend,
                confirm,
                entry,
            )

            result.score += points

            if reason:
                result.reasons.append(reason)

        result.confidence = result.score / 100

        if result.score < MIN_SCORE:

            result.action = "HOLD"

            result.reasons.append(
                "Score below minimum"
            )

            return result

        result.action = "BUY"

        return result