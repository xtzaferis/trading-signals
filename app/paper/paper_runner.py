import time

import ccxt

from app.config.settings import (
    CANDLE_LIMIT,
    CONFIRM_TIMEFRAME,
    ENTRY_TIMEFRAME,
    REGIME_TIMEFRAME,
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
from app.scanner.market_scanner import MarketScanner


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

        self.scanner = MarketScanner()

        self.running = True

    def run_once(self):

        try:

            symbols = self.scanner.get_top_spot_pairs()

        except (
            ccxt.NetworkError,
            ccxt.ExchangeError,
            ConnectionError,
            TimeoutError,
        ):

            logger.exception(
                "Paper runner market scan failed."
            )

            return

        for symbol in symbols:
            try:
                self._process_symbol(symbol)
            except (
                ccxt.NetworkError,
                ccxt.ExchangeError,
                ConnectionError,
                TimeoutError,
            ):
                logger.exception(
                    f"Paper cycle failed for {symbol}."
                )

    def _process_symbol(self, symbol: str):

        snapshot = (
            self.market.get_snapshot(
                symbol=symbol,
                regime_timeframe=REGIME_TIMEFRAME,
                trend_timeframe=TREND_TIMEFRAME,
                confirm_timeframe=CONFIRM_TIMEFRAME,
                entry_timeframe=ENTRY_TIMEFRAME,
                limit=CANDLE_LIMIT,
            )
        )

        self.okx_feed.update_candles(
            regime_candles=snapshot["regime"]["candles"],
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
            snapshot,
            symbol=symbol,
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
