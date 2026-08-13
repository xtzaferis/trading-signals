from app.config.settings import ALLOW_RECOVERY_TRADES
from app.config.weights import (
    ADX_WEIGHT,
    EMA_WEIGHT,
    MACD_WEIGHT,
    RSI_WEIGHT,
)

# =====================================
# Gates
# =====================================

def classify_regime(regime):
    """Classify the daily market without allowing bearish long entries."""

    bullish = (
        regime["close"] > regime["ema200"]
        and regime["ema50"] > regime["ema200"]
        and regime["ema20_slope_pct"] > 0
    )
    if bullish:
        return "BULL"

    recovery = (
        regime["close"] > regime["ema50"]
        and regime["ema20"] > regime["ema50"]
        and regime["ema20_slope_pct"] > 0
        and regime["close"] >= regime["ema200"] * 0.90
    )
    if recovery:
        return "RECOVERY"

    return "BEAR"


def regime_filter(regime):
    """Permit proven regimes; recovery stays experimental by default."""

    classification = classify_regime(regime)
    return (
        classification == "BULL"
        or (
            ALLOW_RECOVERY_TRADES
            and classification == "RECOVERY"
        )
    )


def trend_filter(trend):
    """
    4H Trend Gate
    """

    return (
        trend["close"] > trend["ema200"]
        and trend["ema20_slope_pct"] > 0
        and
        trend["ema20"] > trend["ema50"]
        and trend["ema50"] > trend["ema200"]
    )


def confirmation_filter(confirm):
    """
    1H Confirmation Gate
    """

    return (
        confirm["close"] > confirm["ema20"]
        and confirm["ema20"] > confirm["ema50"]
        and confirm["macd_histogram"] > 0
        and 50 <= confirm["rsi"] <= 72
    )


def entry_filter(entry):
    """
    15m Entry Gate
    """

    momentum_cross = (
        entry["macd_histogram_prev"] <= 0
        and entry["macd_histogram"] > 0
    )

    ema_reclaim = (
        entry["close_prev"] <= entry["ema20_prev"]
        and entry["close"] > entry["ema20"]
    )

    return (
        entry["adx"] >= 18
        and entry["atr_pct"] >= 0.0005
        and 50 <= entry["rsi"] <= 65
        and entry["close"] > entry["ema20"]
        and entry["macd_histogram"] > 0
        and (momentum_cross or ema_reclaim)
    )


# =====================================
# Scoring Filters
# =====================================

def ema_filter(
    trend,
    confirm,
    entry,
):

    if trend_filter(trend):

        return (
            EMA_WEIGHT,
            "4H EMA Trend"
        )

    return 0, None


def rsi_filter(
    trend,
    confirm,
    entry,
):

    if 50 <= entry["rsi"] <= 70:

        return (
            RSI_WEIGHT,
            "15m Healthy RSI"
        )

    return 0, None


def macd_filter(
    trend,
    confirm,
    entry,
):

    if confirmation_filter(confirm):

        return (
            MACD_WEIGHT,
            "1H Bullish MACD"
        )

    return 0, None


def adx_filter(
    trend,
    confirm,
    entry,
):

    if entry["adx"] >= 18:

        return (
            ADX_WEIGHT,
            "15m Strong Trend"
        )

    return 0, None
