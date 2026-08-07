from app.core.logger import logger
from app.services.historical_data_service import (
    HistoricalDataService,
)
from app.backtesting.candle_player import (
    CandlePlayer,
)


class Backtester:

    def __init__(self):

        self.data = (
            HistoricalDataService()
        )

        self.player = (
            CandlePlayer()
        )

    def run(self):

        logger.info("")
        logger.info("=" * 50)
        logger.info("BACKTEST ENGINE")
        logger.info("=" * 50)

        candles = self.data.load(
            symbol="BTC/USDC",
            timeframe="15m",
            limit=500,
        )

        self.player.load(
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

        while self.player.has_next():

            candle = self.player.next()

            timestamp = candle[0]

            close = candle[4]

            if (
                self.player.index
                % 100
                == 0
            ):

                logger.info(
                    f"{self.player.index} | "
                    f"Close: {close}"
                )

        logger.info(
            f"Processed "
            f"{self.player.index} candles."
        )