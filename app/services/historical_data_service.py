
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

        logger.info(
            f"Loaded {len(candles)} candles."
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