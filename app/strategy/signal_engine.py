from app.config.settings import MIN_SCORE
from app.core.logger import logger
from app.strategy.filters import (
    adx_filter,
    confirmation_filter,
    ema_filter,
    entry_filter,
    macd_filter,
    regime_filter,
    rsi_filter,
    trend_filter,
)
from app.strategy.scoring import SignalResult


class SignalEngine:

    def evaluate(
        self,
        symbol,
        data,
        allow_recovery: bool | None = None,
    ):

        result = SignalResult(
            symbol=symbol
        )


        # ---------------------------------
        # Multi-Timeframe Data
        # ---------------------------------

        regime = data["regime"]

        trend = data["trend"]

        confirm = data["confirm"]

        entry = data["entry"]


        logger.debug(
            f"SIGNAL INPUT | "
            f"symbol={symbol} | "
            f"EMA20={trend['ema20']} | "
            f"EMA50={trend['ema50']} | "
            f"EMA200={trend['ema200']} | "
            f"MACD={confirm['macd']} | "
            f"MACD_SIGNAL={confirm['macd_signal']} | "
            f"RSI={entry['rsi']} | "
            f"ADX={entry['adx']}"
        )


        # ---------------------------------
        # Hard Market Structure Gates
        # ---------------------------------

        if not regime_filter(
            regime,
            allow_recovery=allow_recovery,
        ):

            result.action = "HOLD"
            result.reasons.append(
                "Daily regime filter failed"
            )
            logger.debug(
                f"SIGNAL BLOCKED: REGIME | symbol={symbol}"
            )
            return result

        if not trend_filter(trend):

            result.action = "HOLD"

            result.reasons.append(
                "Trend filter failed"
            )

            logger.debug(
                f"SIGNAL BLOCKED: TREND | symbol={symbol}"
            )

            return result



        if not confirmation_filter(confirm):

            result.action = "HOLD"

            result.reasons.append(
                "Confirmation filter failed"
            )

            logger.debug(
                f"SIGNAL BLOCKED: CONFIRMATION | "
                f"symbol={symbol} | "
                f"MACD={confirm['macd']} | "
                f"SIGNAL={confirm['macd_signal']}"
            )

            return result



        # ---------------------------------
        # Entry Timing Gate
        # ---------------------------------

        if not entry_filter(entry):

            result.action = "HOLD"

            result.reasons.append(
                "Entry filter failed"
            )

            logger.debug(
                f"SIGNAL BLOCKED: ENTRY | "
                f"symbol={symbol} | "
                f"RSI={entry['rsi']} | "
                f"ADX={entry['adx']}"
            )

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

                result.reasons.append(
                    reason
                )


        result.confidence = (
            result.score / 100
        )


        logger.debug(
            f"SCORE DEBUG | "
            f"symbol={symbol} | "
            f"score={result.score}/100 | "
            f"confidence={result.confidence:.2f} | "
            f"reasons={result.reasons}"
        )


        # ---------------------------------
        # Final Decision
        # ---------------------------------

        if result.score < MIN_SCORE:

            result.action = "HOLD"

            result.reasons.append(
                "Score below minimum"
            )

            logger.debug(
                f"SIGNAL REJECTED: SCORE | "
                f"symbol={symbol} | "
                f"score={result.score}"
            )

            return result



        result.action = "BUY"


        logger.debug(
            f"SIGNAL APPROVED: BUY | "
            f"symbol={symbol} | "
            f"score={result.score}"
        )


        return result
