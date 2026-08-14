from app.market.market_feed import MarketFeed
from app.paper.live_feed import LiveFeed


def test_market_feed_updates_live_feed():

    live_feed = LiveFeed()

    market_feed = MarketFeed(
        live_feed
    )

    market_feed.update_candles(
        regime_candles=[0],
        trend_candles=[1, 2, 3],
        confirm_candles=[4, 5, 6],
        entry_candles=[7, 8, 9],
    )

    assert live_feed.has_next()

    snapshot = live_feed.next()

    assert (
        snapshot["regime"]["candles"]
        == [0]
    )

    assert (
        snapshot["trend"]["candles"]
        == [1, 2, 3]
    )

    assert (
        snapshot["entry"]["candles"]
        == [7, 8, 9]
    )
