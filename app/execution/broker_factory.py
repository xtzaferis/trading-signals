from app.config.settings import (
    TRADING_MODE,
)
from app.exceptions import TradingModeError
from app.execution.paper_broker import PaperBroker
from app.trading.portfolio import Portfolio


def create_broker(
    portfolio: Portfolio,
    trading_mode: str = TRADING_MODE,
    **_,
):

    if trading_mode == "paper":

        return PaperBroker(
            portfolio
        )

    if trading_mode == "live":
        raise TradingModeError(
            "Kraken live broker is not connected yet; live execution "
            "remains disabled."
        )

    raise TradingModeError(
        f"Broker for {trading_mode!r} is not connected yet; "
        "exchange execution remains disabled."
    )
