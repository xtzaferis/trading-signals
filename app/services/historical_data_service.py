
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
    ) -> list:

        logger.info(
            f"Loading {symbol} "
            f"{timeframe} candles..."
        )

        candles = (
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
    ) -> dict:

        data = {}

        for timeframe in timeframes:

            data[timeframe] = self.load(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
            )

        return data