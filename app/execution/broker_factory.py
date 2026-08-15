from app.config.settings import (
    TRADING_MODE,
)
from app.exceptions import TradingModeError
from app.exchange.kraken_client import KrakenClient
from app.execution.kraken_live_broker import KrakenLiveBroker
from app.execution.kraken_order_gateway import KrakenOrderGateway
from app.execution.paper_broker import PaperBroker
from app.trading.portfolio import Portfolio


def create_broker(
    portfolio: Portfolio,
    trading_mode: str = TRADING_MODE,
    client=None,
    gateway=None,
    **kwargs,
):

    if trading_mode == "paper":

        return PaperBroker(
            portfolio
        )

    if trading_mode == "live":
        client = client or KrakenClient()
        gateway = gateway or KrakenOrderGateway(client)
        return KrakenLiveBroker(
            portfolio,
            gateway,
            **kwargs,
        )

    raise TradingModeError(
        f"Broker for {trading_mode!r} is not connected yet; "
        "exchange execution remains disabled."
    )
