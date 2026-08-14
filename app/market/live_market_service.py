import time
from typing import ClassVar

from app.exchange.coinbase_client import CoinbaseClient


class LiveMarketService:

    TIMEFRAME_SECONDS: ClassVar[dict[str, int]] = {
        "15m": 15 * 60,
        "1h": 60 * 60,
        "4h": 4 * 60 * 60,
        "1d": 24 * 60 * 60,
    }

    def __init__(self, client=None):

        self.client = client or CoinbaseClient()

    def get_snapshot(
        self,
        symbol: str,
        regime_timeframe: str,
        trend_timeframe: str,
        confirm_timeframe: str,
        entry_timeframe: str,
        limit: int = 200,
    ) -> dict:

        return {

            "regime": {
                "candles": (
                    self._load_closed(
                        symbol, regime_timeframe, limit
                    )
                ),
            },

            "trend": {
                "candles": (
                    self._load_closed(
                        symbol, trend_timeframe, limit
                    )
                ),
            },

            "confirm": {
                "candles": (
                    self._load_closed(
                        symbol, confirm_timeframe, limit
                    )
                ),
            },

            "entry": {
                "candles": (
                    self._load_closed(
                        symbol, entry_timeframe, limit
                    )
                ),
            },
        }

    def _load_closed(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> list:
        candles = self.client.get_ohlcv(
            symbol,
            timeframe=timeframe,
            limit=limit + 1,
        )
        duration_ms = self.TIMEFRAME_SECONDS[timeframe] * 1000
        now_ms = int(time.time() * 1000)
        return [
            candle
            for candle in candles
            if candle[0] + duration_ms <= now_ms
        ][-limit:]
