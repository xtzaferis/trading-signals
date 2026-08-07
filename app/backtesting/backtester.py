from app.backtesting.historical_data_provider import (
    HistoricalDataProvider,
)
from app.core.logger import logger
from app.services.historical_data_service import (
    HistoricalDataService,
)


class Backtester:

    def __init__(self):

        self.data = HistoricalDataService()

        self.provider = (
            HistoricalDataProvider()
        )

    def run(self):

        logger.info("")
        logger.info("=" * 50)
        logger.info("BACKTEST ENGINE")
        logger.info("=" * 50)

        candles = self.data.load(
            symbol="BTC/USDC",
            timeframe="15m",
            limit=300,
        )

        self.provider.load(
            candles
        )

        logger.info(
            f"Candles loaded: {len(candles)}"
        )

        self.execute()

        logger.info("")
        logger.info(
            "Backtest finished."
        )

    def execute(self):

        while self.provider.has_next():

            self.provider.step()

            if self.provider.index % 100 == 0:

                logger.info(
                    f"Processed "
                    f"{self.provider.index} candles."
                )

        logger.info("")
        logger.info(
            f"Finished "
            f"{self.provider.index} candles."
        )