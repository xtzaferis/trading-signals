from app.config.settings import TRADING_MODE
from app.exceptions import TradingModeError
from app.exchange.okx_client import OKXClient
from app.execution.okx_demo_broker import OKXDemoBroker
from app.execution.okx_order_gateway import OKXOrderGateway
from app.execution.paper_broker import PaperBroker
from app.trading.portfolio import Portfolio


def create_broker(
    portfolio: Portfolio,
    trading_mode: str = TRADING_MODE,
    client=None,
):

    if trading_mode == "paper":

        return PaperBroker(
            portfolio
        )

    if trading_mode == "okx_demo":
        client = client or OKXClient(trading_mode="okx_demo")
        return OKXDemoBroker(
            portfolio,
            OKXOrderGateway(client),
        )

    raise TradingModeError(
        f"Broker for {trading_mode!r} is not connected yet; "
        "exchange execution remains disabled."
    )
