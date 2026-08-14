from unittest.mock import Mock, patch

import pytest

from app.backtesting.multi_symbol_backtest_engine import (
    MultiSymbolBacktestEngine,
)
from app.backtesting.trade_cooldown import (
    cooldown_bars_for_exit,
)
from app.strategy.scoring import SignalResult


def test_empty_multi_symbol_backtest():
    engine = MultiSymbolBacktestEngine()

    report = engine.run(
        symbols=[],
        data={},
    )

    assert report.trades == 0
    assert engine.portfolio.equity == 1000.0


def test_history_validation_accepts_small_exchange_gaps():
    assert MultiSymbolBacktestEngine._minimum_history(580) == 522


def test_backtest_uses_deeper_quote_history_proxy():
    assert MultiSymbolBacktestEngine._data_symbol(
        "BTC/USDC"
    ) == "BTC/USDC"


def test_benchmark_return_includes_round_trip_costs():
    result = MultiSymbolBacktestEngine._benchmark_return({
        "BTC/USDC": [100.0, 110.0],
    })

    assert 9.6 < result < 9.8


def test_invalid_evaluation_period_is_rejected():
    engine = MultiSymbolBacktestEngine()

    with pytest.raises(ValueError):
        engine.run(
            symbols=[],
            data={},
            start_at=2_000_000_000_000,
            end_at=1_000_000_000_000,
        )


def test_stop_loss_uses_longer_cooldown():
    assert cooldown_bars_for_exit("STOP_LOSS") == 96
    assert cooldown_bars_for_exit("TAKE_PROFIT") == 4


def test_rejections_are_recorded_per_symbol():
    engine = MultiSymbolBacktestEngine()
    provider = Mock()
    provider.has_next.side_effect = [True, False]
    provider.next.return_value = (
        {
            "regime": {},
            "trend": {},
            "confirm": {},
            "entry": {
                "close": 100.0,
                "high": 101.0,
                "low": 99.0,
                "atr": 5.0,
            },
        },
        {"timestamp": 1_000_000},
    )
    engine.signal_engine.evaluate = Mock(
        return_value=SignalResult(
            symbol="BTC/USDC",
            action="HOLD",
            reasons=["Daily regime filter failed"],
        )
    )
    candle = [0, 1, 1, 1, 1, 1]
    data = {
        "BTC/USDC": {
            timeframe: [candle]
            for timeframe in ("1d", "4h", "1h", "15m")
        }
    }

    with patch(
        "app.backtesting.multi_symbol_backtest_engine.MarketProvider",
        return_value=provider,
    ):
        engine.run(data=data)

    assert engine.rejections_by_symbol["BTC/USDC"] == {
        "Daily regime filter failed": 1
    }


def test_two_symbols_share_one_portfolio():
    engine = MultiSymbolBacktestEngine()
    timestamp = 1_000_000
    market = {
        "regime": {},
        "trend": {},
        "confirm": {},
        "entry": {
            "close": 100.0,
            "high": 101.0,
            "low": 99.0,
            "atr": 5.0,
        },
    }

    providers = []
    for _ in range(2):
        provider = Mock()
        provider.has_next.side_effect = [
            True,
            False,
        ]
        provider.next.return_value = (
            market,
            {"timestamp": timestamp},
        )
        providers.append(provider)

    engine.signal_engine.evaluate = Mock(
        side_effect=lambda symbol, _: SignalResult(
            symbol=symbol,
            score=100,
            action="BUY",
        )
    )
    candle = [0, 1, 1, 1, 1, 1]
    data = {
        symbol: {
            timeframe: [candle]
            for timeframe in (
                "1d",
                "4h",
                "1h",
                "15m",
            )
        }
        for symbol in (
            "BTC/USDC",
            "ETH/USDC",
        )
    }

    with patch(
        "app.backtesting.multi_symbol_backtest_engine.MarketProvider",
        side_effect=providers,
    ):
        report = engine.run(data=data)

    assert report.trades == 2
    assert {
        position.symbol
        for position in engine.portfolio.closed_positions
    } == {
        "BTC/USDC",
        "ETH/USDC",
    }
