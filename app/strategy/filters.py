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


def regime_filter(
    regime,
    allow_recovery: bool | None = None,
):
    """Permit proven regimes; recovery stays experimental by default."""

    classification = classify_regime(regime)
    recovery_enabled = (
        ALLOW_RECOVERY_TRADES
        if allow_recovery is None
        else allow_recovery
    )
    return (
        classification == "BULL"
        or (
            recovery_enabled
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
        and trend["ema20"] > trend["ema50"]
        and trend["ema50"] > trend["ema200"]
    )


def confirmation_filter(confirm):
    """
    1H Confirmation Gate
    """

    return (
        confirm["close"] > confirm["ema50"]
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

    points = 0
    points += EMA_WEIGHT // 3 if trend["close"] > trend["ema20"] else 0
    points += EMA_WEIGHT // 3 if trend["ema20"] > trend["ema50"] else 0
    points += EMA_WEIGHT - 2 * (EMA_WEIGHT // 3) if (
        trend["ema50"] > trend["ema200"]
    ) else 0
    return points, "4H EMA Trend" if points else None


def rsi_filter(
    trend,
    confirm,
    entry,
):

    rsi = float(entry["rsi"])
    if 52 <= rsi <= 60:
        points = RSI_WEIGHT
    elif 48 <= rsi <= 65:
        points = round(RSI_WEIGHT * 0.75)
    elif 42 <= rsi <= 72:
        points = round(RSI_WEIGHT * 0.25)
    else:
        points = 0
    return points, "15m Healthy RSI" if points else None


def macd_filter(
    trend,
    confirm,
    entry,
):

    histogram = float(confirm["macd_histogram"])
    previous = float(
        confirm.get("macd_histogram_prev", entry["macd_histogram_prev"])
    )
    points = 0
    if histogram > 0:
        points += MACD_WEIGHT // 2
    if histogram > previous:
        points += MACD_WEIGHT - MACD_WEIGHT // 2
    return points, "1H Bullish MACD" if points else None


def adx_filter(
    trend,
    confirm,
    entry,
):

    adx = float(entry["adx"])
    # ADX is strength, not direction. Award it gradually rather than making
    # the old threshold both a hard gate and an automatic full score.
    points = round(ADX_WEIGHT * min(1.0, max(0.0, (adx - 18) / 12)))
    return points, "15m Strong Trend" if points else None
