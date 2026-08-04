def ema_filter(data):
    if (
        data["ema20"] > data["ema50"]
        and data["ema50"] > data["ema200"]
    ):
        return 30, "EMA Trend"

    return 0, None


def rsi_filter(data):
    if 50 <= data["rsi"] <= 65:
        return 15, "Healthy RSI"

    return 0, None


def macd_filter(data):
    if data["macd"] > data["macd_signal"]:
        return 20, "Bullish MACD"

    return 0, None


def adx_filter(data):
    if data["adx"] > 25:
        return 15, "Strong Trend"

    return 0, None