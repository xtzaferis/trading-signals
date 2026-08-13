from unittest.mock import Mock

from app.backtesting.market_provider import MarketProvider


def create_candles(close: float):
    return [
        [index * 60_000, close, close, close, close, 1.0]
        for index in range(200)
    ]


def test_indicator_cache_is_separate_for_each_timeframe():
    provider = MarketProvider(Mock())

    trend = provider.calculate(
        create_candles(100.0),
        "trend",
    )
    entry = provider.calculate(
        create_candles(200.0),
        "entry",
    )

    assert trend["close"] == 100.0
    assert entry["close"] == 200.0
    assert len(provider.cache) == 2


def test_accepts_precomputed_indicator_rows():
    precomputed = {
        ("entry", 123): {
            "close": 99.0,
        },
    }
    provider = MarketProvider(
        Mock(data={}),
        precomputed=precomputed,
    )

    assert provider.calculate(
        [
            [index, 1, 1, 1, 1, 1]
            for index in range(-76, 124)
        ],
        "entry",
    )["close"] == 99.0
