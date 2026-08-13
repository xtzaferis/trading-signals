import ccxt

from app.config.settings import (
    OKX_API_KEY,
    OKX_PASSPHRASE,
    OKX_SECRET,
)
from app.exceptions import MissingApiKeysError


class OKXClient:

    def __init__(self):

        config = {
            "enableRateLimit": True,
        }

        if (
            OKX_API_KEY
            and OKX_SECRET
            and OKX_PASSPHRASE
        ):
            config["apiKey"] = OKX_API_KEY
            config["secret"] = OKX_SECRET
            config["password"] = OKX_PASSPHRASE

        self.exchange = ccxt.okx(config)

    def load_markets(self):
        return self.exchange.load_markets()

    def get_balance(self):

        if not (
            OKX_API_KEY
            and OKX_SECRET
            and OKX_PASSPHRASE
        ):
            raise MissingApiKeysError(
                "API keys are not configured."
            )

        return self.exchange.fetch_balance()

    def get_ticker(self, symbol):
        return self.exchange.fetch_ticker(symbol)

    def get_tickers(self):
        return self.exchange.fetch_tickers()

    def get_ohlcv(
        self,
        symbol,
        timeframe="15m",
        limit=200,
    ):

        return self.exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            limit=limit,
        )

    def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: float | None = None,
    ):
        """Create a spot trading order on OKX."""
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
            )
            return order
        except ccxt.ExchangeError as e:
            msg = f"Failed to create {side} order for {symbol}: {e!s}"
            raise ccxt.ExchangeError(msg) from e

    def cancel_order(
        self,
        symbol: str,
        order_id: str,
    ):
        """Cancel an open order on OKX."""
        try:
            return self.exchange.cancel_order(
                id=order_id,
                symbol=symbol,
            )
        except ccxt.ExchangeError as e:
            msg = f"Failed to cancel order {order_id}: {e!s}"
            raise ccxt.ExchangeError(msg) from e

    def fetch_open_orders(
        self,
        symbol: str | None = None,
    ):
        """Fetch open orders from OKX."""
        try:
            return self.exchange.fetch_open_orders(
                symbol=symbol
            )
        except ccxt.ExchangeError as e:
            msg = f"Failed to fetch open orders: {e!s}"
            raise ccxt.ExchangeError(msg) from e

    def fetch_order(
        self,
        order_id: str,
        symbol: str | None = None,
    ):
        """Fetch a specific order status from OKX."""
        try:
            return self.exchange.fetch_order(
                id=order_id,
                symbol=symbol,
            )
        except ccxt.ExchangeError as e:
            msg = f"Failed to fetch order {order_id}: {e!s}"
            raise ccxt.ExchangeError(msg) from e
