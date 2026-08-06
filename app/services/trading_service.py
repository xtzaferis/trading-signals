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

            logger.info(
                "No trades to execute."
            )

            return

        logger.info("")
        logger.info("=" * 50)
        logger.info("EXECUTING PAPER TRADES")
        logger.info("=" * 50)

        portfolio = self.paper_trader.portfolio

        for candidate in candidates:

            symbol = candidate.signal.symbol

            if portfolio.has_open_position(
                symbol
            ):

                logger.info(
                    f"Skipping {symbol} "
                    f"(already open)."
                )

                continue

            self.paper_trader.execute_buy(
                candidate
            )

        self.paper_trader.print_portfolio()

        if not PAPER_MONITOR_CONTINUOUS:

            logger.info("")
            logger.info(
                "Development mode."
            )

            logger.info(
                "Running one monitor cycle..."
            )

            self.monitor.monitor(
                portfolio
            )

            return

        logger.info("")
        logger.info(
            "Production mode."
        )

        logger.info(
            "Starting continuous monitoring..."
        )

        while portfolio.open_positions:

            self.monitor.monitor(
                portfolio
            )

            time.sleep(
                SCAN_INTERVAL
            )

        logger.info("")
        logger.info("=" * 50)
        logger.info(
            "ALL POSITIONS CLOSED"
        )
        logger.info("=" * 50)

        self.paper_trader.print_portfolio()