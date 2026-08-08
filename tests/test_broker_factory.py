from unittest.mock import patch

from app.backtesting.backtest_broker import (
    BacktestBroker,
)
from app.execution.broker_factory import (
    create_broker,
)
from app.execution.paper_broker import (
    PaperBroker,
)
from app.trading.portfolio import (
    Portfolio,
)


def test_factory_returns_backtest_broker():

    portfolio = Portfolio()

    with patch(
        "app.execution.broker_factory.PAPER_TRADING",
        False,
    ):

        broker = create_broker(
            portfolio
        )

    assert isinstance(
        broker,
        BacktestBroker,
    )


def test_factory_returns_paper_broker():

    portfolio = Portfolio()

    with patch(
        "app.execution.broker_factory.PAPER_TRADING",
        True,
    ):

        broker = create_broker(
            portfolio
        )

    assert isinstance(
        broker,
        PaperBroker,
    )