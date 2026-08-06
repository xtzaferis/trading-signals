import time

from app.config.settings import SCAN_INTERVAL
from app.core.logger import logger
from app.engine.state import BotState
from app.market.market_analyzer import MarketAnalyzer
from app.services.screener_service import ScreenerService
from app.services.trading_service import TradingService


class BotEngine:

    def __init__(self):

        self.state = BotState.STARTING

        self.running = True

        self.market_analyzer = MarketAnalyzer()
        self.screener = ScreenerService()
        self.trading = TradingService()

    def run(self):

        self.start()

        try:

            while self.running:

                self.run_cycle()

                self.sleep()

        except KeyboardInterrupt:

            self.stop()

    def run_cycle(self):

        if not self.analyze_market():
            return

        candidates = self.scan_market()

        self.show_candidates(
            candidates
        )

        self.execute_trades(
            candidates
        )

    def start(self):

        self.state = BotState.STARTING

        logger.info("=" * 50)
        logger.info("OKX Trading Bot")
        logger.info("=" * 50)

    def stop(self):

        self.state = BotState.STOPPING

        logger.info("")
        logger.info("=" * 50)
        logger.info("Stopping Bot...")
        logger.info("=" * 50)

        self.running = False

    def sleep(self):

        self.state = BotState.SLEEPING

        logger.info("")
        logger.info(
            f"Sleeping {SCAN_INTERVAL} seconds..."
        )

        time.sleep(
            SCAN_INTERVAL
        )

    def analyze_market(self):

        self.state = (
            BotState.ANALYZING_MARKET
        )

        market = (
            self.market_analyzer.analyze()
        )

        logger.info("")
        logger.info("Market Analysis")
        logger.info("-" * 50)

        logger.info(
            f"Score: {market.score}"
        )

        logger.info(
            f"Bullish: {market.bullish}"
        )

        for reason in market.reasons:

            logger.info(
                f"✓ {reason}"
            )

        if not market.bullish:

            logger.warning(
                "Market is bearish."
            )

            logger.warning(
                "Skipping scan."
            )

            return False

        logger.info(
            "Market is bullish."
        )

        return True

    def scan_market(self):

        self.state = (
            BotState.SCANNING
        )

        logger.info(
            "Starting screener..."
        )

        return self.screener.run()

    def show_candidates(
        self,
        candidates,
    ):

        logger.info("")
        logger.info("=" * 50)
        logger.info(
            "TOP TRADING CANDIDATES"
        )
        logger.info("=" * 50)

        if not candidates:

            logger.info(
                "No BUY candidates found."
            )

            return

        for candidate in candidates:

            signal = candidate.signal
            trade = candidate.trade

            logger.info(
                f"{signal.symbol:<15}"
                f" Score: {signal.score:<3}"
                f" Confidence: "
                f"{signal.confidence:.2f}"
                f" Action: {signal.action}"
            )

            for reason in signal.reasons:

                logger.info(
                    f"   ✓ {reason}"
                )

            logger.info(
                f"   Entry:         {trade.entry}"
            )

            logger.info(
                f"   Stop Loss:     {trade.stop_loss}"
            )

            logger.info(
                f"   Take Profit:   {trade.take_profit}"
            )

            logger.info(
                f"   Position Size: "
                f"{trade.position_size:.2f} USDC"
            )

            logger.info(
                f"   RR:            "
                f"{trade.risk_reward}:1"
            )

            logger.info("-" * 50)

    def execute_trades(
        self,
        candidates,
    ):

        if not candidates:
            return

        self.state = (
            BotState.EXECUTING
        )

        self.trading.execute(
            candidates
        )