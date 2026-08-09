from app.config.weights import (
    ADX_WEIGHT,
    EMA_WEIGHT,
    MACD_WEIGHT,
    RSI_WEIGHT,
)

# =====================================
# Gates
# =====================================

def trend_filter(trend):
    """
    4H Trend Gate
    """

    return (
        trend["ema20"] > trend["ema50"]
        and trend["ema50"] > trend["ema200"]
    )


def confirmation_filter(confirm):
    """
    1H Confirmation Gate

    Accept bullish momentum:
    - MACD above signal
    - OR MACD close to signal with positive momentum
    """

    macd = confirm["macd"]
    signal = confirm["macd_signal"]

    return (
        macd >= signal * 0.995
    )


def entry_filter(entry):
    """
    15m Entry Gate
    """

    return (
        50 <= entry["rsi"] <= 70
        and entry["adx"] > 20
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

    if 50 <= entry["rsi"] <= 65:

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

    if entry["adx"] > 25:

        return (
            ADX_WEIGHT,
            "15m Strong Trend"
        )

    return 0, None