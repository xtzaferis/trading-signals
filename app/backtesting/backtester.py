from app.backtesting.historical_data_provider import (
    HistoricalDataProvider,
)
from app.core.logger import logger
from app.indicators.indicator_engine import (
    IndicatorEngine,
)
from app.services.historical_data_service import (
    HistoricalDataService,
)


class Backtester:

    def __init__(self):

        self.history = (
            HistoricalDataService()
        )

        self.provider = (
            HistoricalDataProvider()
        )

        self.indicators = (
            IndicatorEngine(
                data_service=self.provider
            )
        )

    def run(self):

        logger.info("")
        logger.info("=" * 50)
        logger.info("BACKTEST ENGINE")
        logger.info("=" * 50)

        candles = self.history.load(
            symbol="BTC/USDC",
            timeframe="15m",
            limit=300,
        )

        self.provider.load(
            candles
        )

        logger.info(
            f"Loaded {len(candles)} candles."
        )

        self.execute()

        logger.info("")
        logger.info("Backtest finished.")

    def execute(self):

        while self.provider.has_next():

            indicators = (
                self.indicators.calculate(
                    symbol="BTC/USDC",
                    timeframe="15m",
                )
            )

            if (
                self.provider.index
                % 10
                == 0
            ):

                logger.info(
                    f"{self.provider.index:>3} | "
                    f"Close={indicators['close']:.2f} | "
                    f"EMA20={indicators['ema20']:.2f} | "
                    f"EMA50={indicators['ema50']:.2f} | "
                    f"RSI={indicators['rsi']:.2f}"
                )

            self.provider.step()

        logger.info("")
        logger.info(
            f"Processed "
            f"{self.provider.total} candles."
        )