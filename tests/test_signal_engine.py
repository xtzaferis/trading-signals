from app.config.settings import MIN_SCORE
from app.config.weights import (
    ADX_WEIGHT,
    EMA_WEIGHT,
    MACD_WEIGHT,
    RSI_WEIGHT,
)
from app.strategy.signal_engine import SignalEngine


def bullish_data():

    return {
        "regime": {
            "close": 130,
            "ema20": 120,
            "ema50": 110,
            "ema200": 100,
            "ema20_slope_pct": 0.01,
        },
        "trend": {
            "close": 125,
            "ema20": 120,
            "ema50": 110,
            "ema200": 100,
            "ema20_slope_pct": 0.01,
        },
        "confirm": {
            "close": 120,
            "ema20": 110,
            "ema50": 100,
            "macd": 5,
            "macd_signal": 3,
            "macd_histogram": 2,
            "macd_histogram_prev": 1,
            "rsi": 60,
        },
        "entry": {
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
        },
    }


def test_buy_signal():

    engine = SignalEngine()

    result = engine.evaluate(
        "BTC/USDC",
        bullish_data(),
    )

    expected_score = (
        EMA_WEIGHT
        + RSI_WEIGHT
        + MACD_WEIGHT
        + ADX_WEIGHT
    )

    assert result.score >= MIN_SCORE
    assert result.action == "BUY"
    assert result.score == expected_score
    assert result.confidence == (
        expected_score / 100
    )
    assert len(result.reasons) == 4



def test_hold_when_trend_fails():

    data = bullish_data()

    data["trend"]["ema20"] = 90

    engine = SignalEngine()

    result = engine.evaluate(
        "BTC/USDC",
        data,
    )

    assert result.action == "HOLD"
    assert result.score == 0
    assert "Trend filter failed" in result.reasons


def test_hold_when_daily_regime_fails():

    data = bullish_data()
    data["regime"]["close"] = 90

    result = SignalEngine().evaluate(
        "BTC/USDC",
        data,
    )

    assert result.action == "HOLD"
    assert "Daily regime filter failed" in result.reasons



def test_hold_when_confirmation_fails():

    data = bullish_data()

    data["confirm"]["macd"] = 2
    data["confirm"]["macd_signal"] = 4
    data["confirm"]["macd_histogram"] = -2

    engine = SignalEngine()

    result = engine.evaluate(
        "BTC/USDC",
        data,
    )

    assert result.action == "HOLD"
    assert result.score == 0
    assert "Confirmation filter failed" in result.reasons



def test_hold_when_entry_fails():

    data = bullish_data()

    data["entry"]["rsi"] = 45

    engine = SignalEngine()

    result = engine.evaluate(
        "BTC/USDC",
        data,
    )

    assert result.action == "HOLD"
    assert result.score == 0
    assert "Entry filter failed" in result.reasons



def test_reasons_are_recorded():

    engine = SignalEngine()

    result = engine.evaluate(
        "BTC/USDC",
        bullish_data(),
    )

    assert "4H EMA Trend" in result.reasons
    assert "15m Healthy RSI" in result.reasons
    assert "1H Bullish MACD" in result.reasons
    assert "15m Strong Trend" in result.reasons


def test_positive_histogram_can_confirm_below_zero_macd():

    data = bullish_data()
    data["confirm"]["macd"] = -100.4
    data["confirm"]["macd_signal"] = -101.0
    data["confirm"]["macd_histogram"] = 0.6
    data["confirm"]["macd_histogram_prev"] = 0.5

    result = SignalEngine().evaluate(
        "BTC/USDC",
        data,
    )

    assert result.action == "BUY"
