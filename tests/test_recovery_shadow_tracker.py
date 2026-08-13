from datetime import datetime, timezone
from unittest.mock import Mock

from app.models.shadow_trade import ShadowTrade
from app.services.recovery_shadow_tracker import RecoveryShadowTracker


def recovery_market():
    return {
        "regime": {
            "close": 96,
            "ema20": 95,
            "ema50": 94,
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
            "close": 100,
            "high": 101,
            "low": 99,
            "ema20": 95,
            "rsi": 55,
            "rsi_prev": 49,
            "adx": 30,
            "atr": 2,
            "atr_pct": 0.02,
            "macd_histogram": 1,
            "macd_histogram_prev": -1,
            "close_prev": 94,
            "ema20_prev": 95,
        },
    }


def test_recovery_signal_is_recorded_without_opening_a_position():
    repository = Mock()
    repository.get_open.return_value = None
    repository.save_open.return_value = 7
    tracker = RecoveryShadowTracker(repository)

    tracker.observe(
        "BTC/USDC",
        recovery_market(),
        datetime.now(timezone.utc),
    )

    repository.save_open.assert_called_once()
    trade = repository.save_open.call_args.args[0]
    assert trade.id == 7
    assert trade.regime == "RECOVERY"


def test_open_shadow_trade_closes_at_stop():
    repository = Mock()
    repository.get_open.return_value = ShadowTrade(
        id=1,
        symbol="BTC/USDC",
        regime="RECOVERY",
        entry_price=100,
        stop_loss=95,
        take_profit=110,
        quantity=1,
        opened_at=datetime.now(timezone.utc),
    )
    tracker = RecoveryShadowTracker(repository)
    market = recovery_market()
    market["entry"]["low"] = 94

    tracker.observe(
        "BTC/USDC",
        market,
        datetime.now(timezone.utc),
    )

    repository.close.assert_called_once()
    trade = repository.close.call_args.args[0]
    assert trade.status == "CLOSED"
    assert trade.exit_reason == "STOP_LOSS"
    assert trade.pnl < 0


def test_shadow_summary_requires_an_independent_sample():
    repository = Mock()
    repository.count_open.return_value = 1
    repository.get_closed.return_value = [
        Mock(pnl=5.0),
        Mock(pnl=-2.0),
    ]
    tracker = RecoveryShadowTracker(repository)

    summary = tracker.summary()

    assert summary["open"] == 1
    assert summary["profit_factor"] == 2.5
    assert summary["expectancy"] == 1.5
    assert summary["ready"] == 0
