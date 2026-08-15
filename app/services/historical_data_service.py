import json
import math
import time
from pathlib import Path
from typing import Any

from app.config.settings import (
    BACKTEST_CACHE_TTL_SECONDS,
    BACKTEST_USE_CACHE,
)
from app.core.logger import logger
from app.exchange.kraken_client import KrakenClient


class HistoricalDataService:

    def __init__(self, client=None, use_cache: bool | None = None):

        self.client = client or KrakenClient()

        self.exchange = (
            self.client.exchange
        )

        self.use_cache = (
            BACKTEST_USE_CACHE
            if use_cache is None and client is None
            else bool(use_cache)
        )
        self.cache_dir = Path("data") / "backtest_cache"

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

        cached = self._load_cache(
            symbol,
            timeframe,
            limit,
        )
        if cached is not None:
            logger.info(
                f"Loaded {len(cached)} candles from cache."
            )
            return cached

        timeframe_ms = int(
            self.exchange.parse_timeframe(timeframe)
            * 1000
        )
        now = int(self.exchange.milliseconds())
        since = now - (limit + 1) * timeframe_ms

        # CCXT's deterministic pagination is required for larger,
        # statistically useful backtests.
        pagination_calls = max(1, math.ceil(limit / 200) + 1)
        logger.info(
            f"Requesting approximately {pagination_calls} exchange pages."
        )
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

        # The most recent candle may still be forming. Using it would leak
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

        self._save_cache(
            symbol,
            timeframe,
            limit,
            candles,
        )

        return candles

    def _cache_path(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> Path:

        safe_symbol = symbol.replace("/", "-")
        return self.cache_dir / (
            f"{safe_symbol}_{timeframe}_{limit}.json"
        )

    def _load_cache(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> list[Any] | None:

        if not self.use_cache:
            return None

        path = self._cache_path(
            symbol,
            timeframe,
            limit,
        )

        try:
            payload = json.loads(
                path.read_text(encoding="utf-8")
            )
        except (
            FileNotFoundError,
            json.JSONDecodeError,
            OSError,
        ):
            return None

        age = time.time() - float(
            payload.get("saved_at", 0)
        )
        if age > BACKTEST_CACHE_TTL_SECONDS:
            return None

        candles = payload.get("candles")
        return candles if isinstance(candles, list) else None

    def _save_cache(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        candles: list[Any],
    ) -> None:

        if not self.use_cache:
            return

        self.cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        path = self._cache_path(
            symbol,
            timeframe,
            limit,
        )
        path.write_text(
            json.dumps({
                "saved_at": time.time(),
                "candles": candles,
            }),
            encoding="utf-8",
        )

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
