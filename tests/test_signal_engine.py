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
        "trend": {
            "ema20": 120,
            "ema50": 110,
            "ema200": 100,
        },
        "confirm": {
            "macd": 5,
            "macd_signal": 3,
        },
        "entry": {
            "rsi": 55,
            "adx": 30,
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


def test_hold_when_confirmation_fails():

    data = bullish_data()

    data["confirm"]["macd"] = 2
    data["confirm"]["macd_signal"] = 4

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