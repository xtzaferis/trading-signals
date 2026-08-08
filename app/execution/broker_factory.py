from app.backtesting.backtest_broker import BacktestBroker
from app.config.settings import PAPER_TRADING
from app.execution.paper_broker import PaperBroker
from app.trading.portfolio import Portfolio


def create_broker(
    portfolio: Portfolio,
):

    if PAPER_TRADING:

        return PaperBroker(
            portfolio
        )

    return BacktestBroker(
        portfolio
    )