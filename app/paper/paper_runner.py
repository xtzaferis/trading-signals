import time

import ccxt

from app.config.settings import (
    CANDLE_LIMIT,
    CONFIRM_TIMEFRAME,
    ENTRY_TIMEFRAME,
    MARKET_SYMBOL,
    SCAN_INTERVAL,
    TREND_TIMEFRAME,
)
from app.core.logger import logger
from app.market.live_market_service import (
    LiveMarketService,
)
from app.market.okx_feed import (
    OKXFeed,
)
from app.paper.live_feed import (
    LiveFeed,
)
from app.paper.paper_engine import (
    PaperEngine,
)


class PaperRunner:

    def __init__(self):

        self.live_feed = LiveFeed()

        self.okx_feed = OKXFeed(
            self.live_feed
        )

        self.market = (
            LiveMarketService()
        )

        self.engine = (
            PaperEngine()
        )

        self.running = True

    def run_once(self):

        try:

            snapshot = (
                self.market.get_snapshot(
                    symbol=MARKET_SYMBOL,
                    trend_timeframe=TREND_TIMEFRAME,
                    confirm_timeframe=CONFIRM_TIMEFRAME,
                    entry_timeframe=ENTRY_TIMEFRAME,
                    limit=CANDLE_LIMIT,
                )
            )

            self.okx_feed.update_candles(
                trend_candles=snapshot["trend"]["candles"],
                confirm_candles=snapshot["confirm"]["candles"],
                entry_candles=snapshot["entry"]["candles"],
            )

            if not self.live_feed.has_next():

                logger.warning(
                    "No market snapshot available."
                )

                return

            snapshot = (
                self.live_feed.next()
            )

            self.engine.process_snapshot(
                snapshot
            )

        except (
            ccxt.NetworkError,
            ccxt.ExchangeError,
            ConnectionError,
            TimeoutError,
        ):

            logger.exception(
                "Paper runner cycle failed."
            )

    def run(self):

        logger.info("")
        logger.info("=" * 50)
        logger.info(
            "PAPER RUNNER STARTED"
        )
        logger.info("=" * 50)

        while self.running:

            self.run_once()

            time.sleep(
                SCAN_INTERVAL
            )

    def stop(self):

        self.running = False

        logger.info(
            "Paper runner stopped."
        )