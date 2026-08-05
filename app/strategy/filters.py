from app.config.weights import (
    ADX_WEIGHT,
    EMA_WEIGHT,
    MACD_WEIGHT,
    RSI_WEIGHT,
)


def ema_filter(
    trend,
    confirm,
    entry,
):
    """
    Trend (4H)
    """

    if (
        trend["ema20"] > trend["ema50"]
        and trend["ema50"] > trend["ema200"]
    ):
        return EMA_WEIGHT, "4H EMA Trend"

    return 0, None


def rsi_filter(
    trend,
    confirm,
    entry,
):
    """
    Entry (15m)
    """

    if 50 <= entry["rsi"] <= 65:
        return RSI_WEIGHT, "15m Healthy RSI"

    return 0, None


def macd_filter(
    trend,
    confirm,
    entry,
):
    """
    Confirmation (1H)
    """

    if confirm["macd"] > confirm["macd_signal"]:
        return MACD_WEIGHT, "1H Bullish MACD"

    return 0, None


def adx_filter(
    trend,
    confirm,
    entry,
):
    """
    Entry (15m)
    """

    if entry["adx"] > 25:
        return ADX_WEIGHT, "15m Strong Trend"

    return 0, None