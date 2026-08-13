from app.config.weights import (
    ADX_WEIGHT,
    EMA_WEIGHT,
    MACD_WEIGHT,
    RSI_WEIGHT,
)
from app.strategy.filters import (
    adx_filter,
    classify_regime,
    confirmation_filter,
    ema_filter,
    entry_filter,
    macd_filter,
    regime_filter,
    rsi_filter,
    trend_filter,
)


def bullish_trend():

    return {
        "close": 125,
        "ema20": 120,
        "ema50": 110,
        "ema200": 100,
        "ema20_slope_pct": 0.01,
    }


def test_regime_filter():

    assert regime_filter(bullish_trend())
    assert not regime_filter(bearish_trend())


def test_regime_classifier_allows_conservative_recovery():
    recovery = {
        "close": 96,
        "ema20": 95,
        "ema50": 94,
        "ema200": 100,
        "ema20_slope_pct": 0.01,
    }

    assert classify_regime(bullish_trend()) == "BULL"
    assert classify_regime(recovery) == "RECOVERY"
    assert not regime_filter(recovery)


def test_regime_classifier_blocks_weak_recovery():
    recovery = {
        "close": 89,
        "ema20": 88,
        "ema50": 87,
        "ema200": 100,
        "ema20_slope_pct": 0.01,
    }

    assert classify_regime(recovery) == "BEAR"
    assert not regime_filter(recovery)


def bearish_trend():

    return {
        "close": 85,
        "ema20": 90,
        "ema50": 100,
        "ema200": 110,
        "ema20_slope_pct": -0.01,
    }


def bullish_confirm():

    return {
        "close": 120,
        "ema20": 110,
        "ema50": 100,
        "macd": 5,
        "macd_signal": 3,
        "macd_histogram": 2,
        "macd_histogram_prev": 1,
        "rsi": 60,
    }


def bearish_confirm():

    return {
        "close": 90,
        "ema20": 100,
        "ema50": 110,
        "macd": 2,
        "macd_signal": 4,
        "macd_histogram": -2,
        "macd_histogram_prev": -1,
        "rsi": 40,
    }


def healthy_entry():

    return {
        "close": 110,
        "ema20": 105,
        "rsi": 55,
        "rsi_prev": 49,
        "adx": 30,
        "macd_histogram": 1,
        "macd_histogram_prev": -1,
        "close_prev": 100,
        "ema20_prev": 105,
        "atr_pct": 0.001,
        "breakout_high_20": 120,
        "volume_ratio": 1.0,
    }


def weak_entry():

    return {
        "close": 90,
        "ema20": 100,
        "rsi": 40,
        "rsi_prev": 45,
        "adx": 15,
        "macd_histogram": -1,
        "macd_histogram_prev": -2,
        "close_prev": 95,
        "ema20_prev": 100,
        "atr_pct": 0.0001,
        "breakout_high_20": 120,
        "volume_ratio": 0.5,
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


def test_entry_requires_positive_momentum():

    entry = healthy_entry()
    entry["macd_histogram"] = -1

    assert not entry_filter(entry)


def test_entry_requires_fresh_trigger():

    entry = healthy_entry()
    entry["macd_histogram_prev"] = 0.5
    entry["close_prev"] = 106

    assert not entry_filter(entry)


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
