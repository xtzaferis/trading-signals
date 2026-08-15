import pytest

from app.exceptions import TradingModeError
from app.execution.broker_factory import create_broker
from app.execution.kraken_live_broker import KrakenLiveBroker
from app.execution.paper_broker import PaperBroker
from app.trading.portfolio import Portfolio


def test_factory_returns_paper_broker():
    broker = create_broker(Portfolio(), trading_mode="paper")

    assert isinstance(broker, PaperBroker)


def test_factory_returns_fail_closed_kraken_live_broker():
    broker = create_broker(Portfolio(), trading_mode="live")

    assert isinstance(broker, KrakenLiveBroker)
    assert broker.gateway.client.live_trading_enabled is False


def test_factory_rejects_unknown_mode():
    with pytest.raises(TradingModeError, match="remains disabled"):
        create_broker(Portfolio(), trading_mode="unsupported")
