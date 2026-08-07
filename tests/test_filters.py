from app.config.weights import (
    ADX_WEIGHT,
    EMA_WEIGHT,
    MACD_WEIGHT,
    RSI_WEIGHT,
)
from app.strategy.filters import (
    adx_filter,
    confirmation_filter,
    ema_filter,
    entry_filter,
    macd_filter,
    rsi_filter,
    trend_filter,
)


def bullish_trend():

    return {
        "ema20": 120,
        "ema50": 110,
        "ema200": 100,
    }


def bearish_trend():

    return {
        "ema20": 90,
        "ema50": 100,
        "ema200": 110,
    }


def bullish_confirm():

    return {
        "macd": 5,
        "macd_signal": 3,
    }


def bearish_confirm():

    return {
        "macd": 2,
        "macd_signal": 4,
    }


def healthy_entry():

    return {
        "rsi": 55,
        "adx": 30,
    }


def weak_entry():

    return {
        "rsi": 40,
        "adx": 15,
    }


def test_trend_filter():

    assert trend_filter(
        bullish_trend()
    )

    assert not trend_filter(
        bearish_trend()
    )


def test_confirmation_filter():

    assert confirmation_filter(
        bullish_confirm()
    )

    assert not confirmation_filter(
        bearish_confirm()
    )


def test_entry_filter():

    assert entry_filter(
        healthy_entry()
    )

    assert not entry_filter(
        weak_entry()
    )


def test_ema_filter():

    points, reason = ema_filter(
        bullish_trend(),
        bullish_confirm(),
        healthy_entry(),
    )

    assert points == EMA_WEIGHT
    assert reason is not None


def test_rsi_filter():

    points, reason = rsi_filter(
        bullish_trend(),
        bullish_confirm(),
        healthy_entry(),
    )

    assert points == RSI_WEIGHT
    assert reason is not None


def test_macd_filter():

    points, reason = macd_filter(
        bullish_trend(),
        bullish_confirm(),
        healthy_entry(),
    )

    assert points == MACD_WEIGHT
    assert reason is not None


def test_adx_filter():

    points, reason = adx_filter(
        bullish_trend(),
        bullish_confirm(),
        healthy_entry(),
    )

    assert points == ADX_WEIGHT
    assert reason is not None