from app.config.weights import (
    ADX_WEIGHT,
    EMA_WEIGHT,
    MACD_WEIGHT,
    RSI_WEIGHT,
)


def ema_filter(data):
    if (
        data["ema20"] > data["ema50"]
        and data["ema50"] > data["ema200"]
    ):
        return EMA_WEIGHT, "EMA Trend"

    return 0, None


def rsi_filter(data):
    if 50 <= data["rsi"] <= 65:
        return RSI_WEIGHT, "Healthy RSI"

    return 0, None


def macd_filter(data):
    if data["macd"] > data["macd_signal"]:
        return MACD_WEIGHT, "Bullish MACD"

    return 0, None


def adx_filter(data):
    if data["adx"] > 25:
        return ADX_WEIGHT, "Strong Trend"

    return 0, None