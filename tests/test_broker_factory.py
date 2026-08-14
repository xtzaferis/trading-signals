import pytest

from app.exceptions import TradingModeError
from app.execution.broker_factory import create_broker
from app.execution.paper_broker import PaperBroker
from app.trading.portfolio import Portfolio


def test_factory_returns_paper_broker():
    broker = create_broker(Portfolio(), trading_mode="paper")

    assert isinstance(broker, PaperBroker)


def test_factory_keeps_coinbase_live_execution_disconnected():
    with pytest.raises(TradingModeError, match="not connected yet"):
        create_broker(Portfolio(), trading_mode="live")


def test_factory_rejects_unknown_mode():
    with pytest.raises(TradingModeError, match="remains disabled"):
        create_broker(Portfolio(), trading_mode="unsupported")
