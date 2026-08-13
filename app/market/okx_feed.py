from datetime import datetime, timezone

from app.paper.live_feed import LiveFeed


class OKXFeed:

    def __init__(
        self,
        live_feed: LiveFeed,
    ):

        self.live_feed = live_feed

    def update_candles(
        self,
        regime_candles: list,
        trend_candles: list,
        confirm_candles: list,
        entry_candles: list,
    ):

        snapshot = {

            "regime": {
                "candles": regime_candles,
            },

            "trend": {
                "candles": trend_candles,
            },

            "confirm": {
                "candles": confirm_candles,
            },

            "entry": {
                "candles": entry_candles,
            },

            "timestamp": datetime.now(
                timezone.utc
            ),
        }

        self.live_feed.update(
            snapshot
        )
