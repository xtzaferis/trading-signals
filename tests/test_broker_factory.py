import pytest

from app.exceptions import TradingModeError
from app.execution.broker_factory import (
    create_broker,
)
from app.execution.paper_broker import (
    PaperBroker,
)
from app.trading.portfolio import (
    Portfolio,
)


def test_factory_fails_closed_for_exchange_mode():

    portfolio = Portfolio()

    with pytest.raises(TradingModeError, match="not connected"):
        create_broker(
            portfolio,
            trading_mode="okx_demo",
        )


def test_factory_returns_paper_broker():

    portfolio = Portfolio()

    broker = create_broker(
        portfolio,
        trading_mode="paper",
    )

    assert isinstance(
        broker,
        PaperBroker,
    )
