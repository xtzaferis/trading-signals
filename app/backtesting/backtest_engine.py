from app.backtesting.historical_feed import (
    HistoricalFeed,
)
from app.core.logger import logger
from app.indicators.indicator_engine import (
    IndicatorEngine,
)
from app.services.historical_data_service import (
    HistoricalDataService,
)
from app.strategy.signal_engine import (
    SignalEngine,
)


class BacktestEngine:

    def __init__(self):

        self.history = (
            HistoricalDataService()
        )

        self.feed = (
            HistoricalFeed()
        )

        self.indicators = (
            IndicatorEngine()
        )

        self.signal_engine = (
            SignalEngine()
        )

    def run(self):

        logger.info("")
        logger.info("=" * 50)
        logger.info(
            "BACKTEST ENGINE"
        )
        logger.info("=" * 50)

        data = (
            self.history.load_multiple(
                symbol="BTC/USDC",
                timeframes=[
                    "4h",
                    "1h",
                    "15m",
                ],
                limit=300,
            )
        )

        self.feed.load(
            data
        )

        logger.info(
            "Historical feed loaded."
        )

        while self.feed.has_next():

            self.feed.next()

            #
            # TODO
            #
            # IndicatorEngine
            # SignalEngine
            # RiskManager
            # Broker
            #


        logger.info("")
        logger.info(
            "Backtest finished."
        )