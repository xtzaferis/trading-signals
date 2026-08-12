import math
from typing import Any

from app.core.logger import logger
from app.exchange.okx_client import OKXClient


class HistoricalDataService:

    def __init__(self, client=None):

        self.client = client or OKXClient()

        self.exchange = (
            self.client.exchange
        )

    def load(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 1000,
    ) -> list[Any]:

        logger.info(
            f"Loading {symbol} "
            f"{timeframe} candles..."
        )

        timeframe_ms = int(
            self.exchange.parse_timeframe(timeframe)
            * 1000
        )
        now = int(self.exchange.milliseconds())
        since = now - (limit + 1) * timeframe_ms

        # OKX returns at most 300 candles in one response. CCXT's deterministic
        # pagination is required for larger, statistically useful backtests.
        pagination_calls = max(1, math.ceil(limit / 200) + 1)
        candles: list[Any] = list(
            self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=since,
                limit=limit,
                params={
                    "paginate": True,
                    "paginationCalls": pagination_calls,
                },
            )
        )

        #
        # Indicators require chronological order:
        # oldest candle -> newest candle
        #
        candles.sort(
            key=lambda candle: candle[0]
        )

        # The most recent OKX candle may still be forming. Using it would leak
        # information that was not available at the candle's open time.
        candles = [
            candle
            for candle in candles
            if candle[0] + timeframe_ms <= now
        ][-limit:]

        logger.info(
            f"Loaded {len(candles)} candles."
        )

        if candles:

            logger.info(
                f"First candle timestamp: {candles[0][0]}"
            )

            logger.info(
                f"Last candle timestamp: {candles[-1][0]}"
            )

        return candles

    def load_multiple(
        self,
        symbol: str,
        timeframes: list[str],
        limit: int = 1000,
    ) -> dict[str, list[Any]]:

        data: dict[str, list[Any]] = {}

        for timeframe in timeframes:

            data[timeframe] = self.load(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
            )

        return data
