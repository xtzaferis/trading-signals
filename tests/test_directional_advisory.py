from app.advisory.directional_signal import DirectionalSignalEngine
from app.advisory.planner import FuturesAdvisoryPlanner


def bullish_data():
    data = {
        "regime": {
            "close": 130, "ema20": 120, "ema50": 110, "ema200": 100,
            "ema20_slope_pct": 0.01,
        },
        "trend": {
            "close": 125, "ema20": 120, "ema50": 110, "ema200": 100,
            "ema20_slope_pct": 0.01,
        },
        "confirm": {
            "close": 120, "ema20": 110, "ema50": 100, "macd": 5,
            "macd_signal": 3, "macd_histogram": 2,
            "macd_histogram_prev": 1, "rsi": 60, "adx": 30,
        },
        "entry": {
            "close": 110, "ema20": 105, "rsi": 55, "adx": 30,
            "macd_histogram": 1, "macd_histogram_prev": -1,
            "close_prev": 100, "ema20_prev": 105, "atr_pct": 0.01,
            "atr": 2,
        },
    }
    data["trigger"] = dict(data["entry"])
    return data


def bearish_data():
    data = {
        "regime": {
            "close": 80, "ema20": 85, "ema50": 90, "ema200": 100,
            "ema20_slope_pct": -0.01,
        },
        "trend": {
            "close": 80, "ema20": 85, "ema50": 90, "ema200": 100,
            "ema20_slope_pct": -0.01,
        },
        "confirm": {
            "close": 80, "ema20": 85, "ema50": 90, "macd": -5,
            "macd_signal": -3, "macd_histogram": -2,
            "macd_histogram_prev": -1, "rsi": 40, "adx": 30,
        },
        "entry": {
            "close": 80, "ema20": 85, "rsi": 45, "adx": 30,
            "macd_histogram": -1, "macd_histogram_prev": 1,
            "close_prev": 90, "ema20_prev": 85, "atr_pct": 0.01,
            "atr": 2,
        },
    }
    data["trigger"] = dict(data["entry"])
    return data


def test_bullish_setup_is_labeled_long():
    signal = DirectionalSignalEngine().evaluate("BTC/EUR", bullish_data())

    assert signal.direction == "LONG"
    assert signal.score == 100


def test_bearish_setup_is_labeled_short():
    signal = DirectionalSignalEngine().evaluate("BTC/EUR", bearish_data())

    assert signal.direction == "SHORT"
    assert signal.score == 100


def test_strong_short_term_setup_can_be_counter_trend():
    data = bullish_data()
    data["regime"].update(close=80, ema200=100, ema20_slope_pct=-0.01)
    data["trend"].update(
        close=80, ema20=85, ema50=90, ema200=100, ema20_slope_pct=-0.01
    )

    signal = DirectionalSignalEngine().evaluate("BTC/EUR", data)

    assert signal.direction == "LONG"
    assert signal.score == 75
    assert "Counter-trend" in signal.reasons[0]


def test_missing_five_minute_confirmation_waits():
    data = bullish_data()
    data["trigger"].update(close=100, ema20=105, macd_histogram=-1)

    signal = DirectionalSignalEngine().evaluate("BTC/EUR", data)

    assert signal.direction == "WAIT"
    assert signal.reasons[0] == "5m long timing is not confirmed"


def test_short_levels_place_stop_above_and_target_below_entry():
    levels = FuturesAdvisoryPlanner().create("SHORT", bearish_data()["entry"])

    assert levels is not None
    assert levels.stop_loss > levels.entry > levels.take_profit
    assert levels.net_risk_reward >= 1.5


def test_long_levels_place_stop_below_and_target_above_entry():
    levels = FuturesAdvisoryPlanner().create("LONG", bullish_data()["entry"])

    assert levels is not None
    assert levels.stop_loss < levels.entry < levels.take_profit
    assert levels.net_risk_reward >= 1.5
