from app.config.settings import (
    BREAK_EVEN_ENABLED,
    BREAK_EVEN_R,
    TRAILING_STOP_ENABLED,
)
from app.core.logger import logger
from app.exchange.okx_client import OKXClient
from app.journal.trade_journal import TradeJournal
from app.trading.portfolio import Portfolio


class PositionMonitor:

    def __init__(self):

        self.client = OKXClient()

        self.journal = TradeJournal()

    def monitor(
        self,
        portfolio: Portfolio,
    ):

        if not portfolio.open_positions:
            return

        logger.info("")
        logger.info("=" * 50)
        logger.info("POSITION MONITOR")
        logger.info("=" * 50)

        positions = portfolio.open_positions.copy()

        for position in positions:

            ticker = self.client.get_ticker(
                position.symbol
            )

            current_price = float(
                ticker["last"]
            )

            position.update_price(
                current_price
            )

            logger.info(
                f"{position.symbol} | "
                f"Price: {current_price:.6f}"
            )

            risk = (
                position.entry_price
                - position.stop_loss
            )

            # ----------------------------------
            # Break Even
            # ----------------------------------

            if (
                BREAK_EVEN_ENABLED
                and not position.break_even
            ):

                trigger = (
                    position.entry_price
                    + risk * BREAK_EVEN_R
                )

                if current_price >= trigger:

                    position.stop_loss = (
                        position.entry_price
                    )

                    position.break_even = True

                    logger.info(
                        f"{position.symbol} moved to Break Even."
                    )

            # ----------------------------------
            # Trailing Stop
            # ----------------------------------

            if (
                TRAILING_STOP_ENABLED
                and position.break_even
            ):

                trailing_stop = (
                    position.highest_price
                    - risk
                )

                if (
                    trailing_stop
                    > position.stop_loss
                ):

                    position.stop_loss = (
                        trailing_stop
                    )

                    logger.info(
                        f"{position.symbol} trailing SL -> "
                        f"{position.stop_loss:.6f}"
                    )

            # ----------------------------------
            # Stop Loss
            # ----------------------------------

            if current_price <= position.stop_loss:

                logger.warning(
                    f"{position.symbol} hit Stop Loss."
                )

                portfolio.close_position(
                    position,
                    current_price,
                )

                self.journal.save(
                    position
                )

                continue

            # ----------------------------------
            # Take Profit
            # ----------------------------------

            if current_price >= position.take_profit:

                logger.info(
                    f"{position.symbol} hit Take Profit."
                )

                portfolio.close_position(
                    position,
                    current_price,
                )

                self.journal.save(
                    position
                )

                continue

            logger.info(
                f"{position.symbol} still open."
            )

        logger.info("")

        logger.info(
            f"Cash: {portfolio.cash:.2f} USDC"
        )

        logger.info(
            f"Equity: {portfolio.equity:.2f} USDC"
        )

        logger.info(
            f"Open Positions: "
            f"{len(portfolio.open_positions)}"
        )

        logger.info(
            f"Closed Positions: "
            f"{len(portfolio.closed_positions)}"
        )