import time

from app.config.settings import (
    PAPER_MONITOR_CONTINUOUS,
    SCAN_INTERVAL,
)
from app.core.logger import logger
from app.models.trade_candidate import TradeCandidate
from app.trading.paper_trader import PaperTrader
from app.trading.position_monitor import PositionMonitor


class TradingService:

    def __init__(self):

        self.paper_trader = PaperTrader()
        self.monitor = PositionMonitor()

    def execute(
        self,
        candidates: list[TradeCandidate],
    ):

        if not candidates:

            logger.info("No trades to execute.")
            return

        logger.info("")
        logger.info("=" * 50)
        logger.info("EXECUTING PAPER TRADES")
        logger.info("=" * 50)

        # ----------------------------------
        # Open positions
        # ----------------------------------

        for candidate in candidates:

            self.paper_trader.execute_buy(
                candidate
            )

        self.paper_trader.print_portfolio()

        # ----------------------------------
        # Development Mode
        # ----------------------------------

        if not PAPER_MONITOR_CONTINUOUS:

            logger.info("")
            logger.info("Development mode.")
            logger.info("Running one monitor cycle...")

            self.monitor.monitor(
                self.paper_trader.portfolio
            )

            return

        # ----------------------------------
        # Production Mode
        # ----------------------------------

        logger.info("")
        logger.info("Production mode.")
        logger.info("Starting continuous monitoring...")

        while self.paper_trader.portfolio.open_positions:

            self.monitor.monitor(
                self.paper_trader.portfolio
            )

            time.sleep(
                SCAN_INTERVAL
            )

        logger.info("")
        logger.info("=" * 50)
        logger.info("ALL POSITIONS CLOSED")
        logger.info("=" * 50)

        self.paper_trader.print_portfolio()