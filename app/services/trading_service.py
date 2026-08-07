import time

from app.config.settings import (
    PAPER_MONITOR_CONTINUOUS,
    SCAN_INTERVAL,
)
from app.core.logger import logger
from app.models.trade_candidate import TradeCandidate
from app.services.statistics_printer import (
    StatisticsPrinter,
)
from app.services.statistics_service import (
    StatisticsService,
)
from app.trading.paper_trader import PaperTrader
from app.trading.position_monitor import PositionMonitor
from app.trading.rules.cash_rule import CashRule
from app.trading.rules.duplicate_rule import (
    DuplicateRule,
)
from app.trading.rules.max_positions_rule import (
    MaxPositionsRule,
)


class TradingService:

    def __init__(self):

        self.paper_trader = PaperTrader()

        self.monitor = PositionMonitor()

        self.statistics = (
            StatisticsService()
        )

        self.printer = (
            StatisticsPrinter()
        )

        self.rules = [
            MaxPositionsRule(),
            DuplicateRule(),
            CashRule(),
        ]

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
        logger.info(
            "EXECUTING PAPER TRADES"
        )
        logger.info("=" * 50)

        portfolio = (
            self.paper_trader.portfolio
        )

        # ----------------------------------
        # Trading Rules
        # ----------------------------------

        for candidate in candidates:

            allowed = True

            for rule in self.rules:

                ok, reason = rule.validate(
                    portfolio,
                    candidate,
                )

                if not ok:

                    logger.info(
                        reason
                    )

                    allowed = False

                    break

            if not allowed:
                continue

            self.paper_trader.execute_buy(
                candidate
            )

        self.paper_trader.print_portfolio()

        # ----------------------------------
        # Development Mode
        # ----------------------------------

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

            self.print_statistics(
                portfolio
            )

            return

        # ----------------------------------
        # Production Mode
        # ----------------------------------

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

        self.print_statistics(
            portfolio
        )

    def print_statistics(
        self,
        portfolio,
    ):

        if not portfolio.closed_positions:
            return

        report = (
            self.statistics.generate(
                portfolio
            )
        )

        self.printer.print(
            report
        )