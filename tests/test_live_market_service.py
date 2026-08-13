from unittest.mock import Mock

from app.market.live_market_service import (
    LiveMarketService,
)


def test_live_market_service_returns_snapshot():

    service = LiveMarketService()

    service.client = Mock()

    service.client.get_ohlcv.side_effect = [
        [
            [0, 99, 100, 98, 99, 9],
        ],
        [
            [1, 100, 101, 99, 100, 10],
        ],
        [
            [2, 101, 102, 100, 101, 11],
        ],
        [
            [3, 102, 103, 101, 102, 12],
        ],
    ]

    snapshot = service.get_snapshot(
        symbol="BTC/USDC",
        regime_timeframe="1d",
        trend_timeframe="4h",
        confirm_timeframe="1h",
        entry_timeframe="15m",
        limit=200,
    )

    assert (
        "regime"
        in snapshot
    )

    assert (
        "trend"
        in snapshot
    )

    assert (
        "confirm"
        in snapshot
    )

    assert (
        "entry"
        in snapshot
    )

    assert (
        snapshot["regime"]["candles"][0][0]
        == 0
    )

    assert (
        snapshot["trend"]["candles"][0][0]
        == 1
    )

    assert (
        snapshot["confirm"]["candles"][0][0]
        == 2
    )

    assert (
        snapshot["entry"]["candles"][0][0]
        == 3
    )
