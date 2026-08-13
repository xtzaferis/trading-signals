from unittest.mock import Mock

import pytest

from app.exceptions import TradingModeError
from app.execution.broker_factory import (
    create_broker,
)
from app.execution.okx_demo_broker import OKXDemoBroker
from app.execution.paper_broker import (
    PaperBroker,
)
from app.trading.portfolio import (
    Portfolio,
)


def test_factory_returns_okx_demo_broker():

    portfolio = Portfolio()
    client = Mock()

    broker = create_broker(
        portfolio,
        trading_mode="okx_demo",
        client=client,
    )

    assert isinstance(broker, OKXDemoBroker)


def test_factory_keeps_live_mode_blocked():
    with pytest.raises(TradingModeError, match="not connected"):
        create_broker(Portfolio(), trading_mode="live")


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
