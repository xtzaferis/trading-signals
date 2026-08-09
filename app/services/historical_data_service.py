from typing import Any

from app.core.logger import logger
from app.exchange.okx_client import OKXClient


class HistoricalDataService:

    def __init__(self):

        self.client = OKXClient()

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

        candles: list[Any] = list(
            self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
            )
        )

        #
        # Indicators require chronological order:
        # oldest candle -> newest candle
        #
        candles.sort(
            key=lambda candle: candle[0]
        )

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