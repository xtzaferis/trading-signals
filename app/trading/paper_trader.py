from app.core.logger import logger
from app.database.repositories.portfolio_repository import (
    PortfolioRepository,
)
from app.database.repositories.position_repository import (
    PositionRepository,
)
from app.models.position import Position
from app.models.trade_candidate import TradeCandidate
from app.trading.portfolio import Portfolio


class PaperTrader:

    def __init__(self):

        self.portfolio_repository = (
            PortfolioRepository()
        )

        self.position_repository = (
            PositionRepository()
        )

        if self.portfolio_repository.exists():

            logger.info(
                "Loading portfolio..."
            )

            self.portfolio = (
                self.portfolio_repository.load()
            )

        else:

            logger.info(
                "Creating new portfolio..."
            )

            self.portfolio = Portfolio()

            self.portfolio_repository.save(
                self.portfolio
            )

    def execute_buy(
        self,
        candidate: TradeCandidate,
    ) -> Position:

        trade = candidate.trade

        quantity = (
            trade.position_size
            / trade.entry
        )

        position = Position(
            symbol=trade.symbol,
            entry_price=trade.entry,
            quantity=quantity,
            stop_loss=trade.stop_loss,
            take_profit=trade.take_profit,
        )

        position.update_price(
            trade.entry
        )

        self.portfolio.add_position(
            position
        )

        self.portfolio_repository.save(
            self.portfolio
        )

        self.position_repository.save(
            position
        )

        logger.info(
            f"Opened paper position: {position.symbol}"
        )

        return position

    def print_portfolio(self):

        logger.info("=" * 50)
        logger.info("PAPER PORTFOLIO")
        logger.info("=" * 50)

        logger.info(
            f"Cash: {self.portfolio.cash:.2f} USDC"
        )

        logger.info(
            f"Equity: {self.portfolio.equity:.2f} USDC"
        )

        logger.info(
            f"Open Positions: {len(self.portfolio.open_positions)}"
        )

        logger.info(
            f"Closed Positions: {len(self.portfolio.closed_positions)}"
        )