import ccxt

from app.config.settings import (
    LIVE_TRADING_ENABLED,
    OKX_API_KEY,
    OKX_PASSPHRASE,
    OKX_SECRET,
    TRADING_MODE,
    VALID_TRADING_MODES,
)
from app.exceptions import (
    LiveTradingDisabledError,
    MissingApiKeysError,
    OrderValidationError,
    TradingModeError,
)


class OKXClient:

    def __init__(
        self,
        trading_mode: str = TRADING_MODE,
        live_trading_enabled: bool = LIVE_TRADING_ENABLED,
        api_key: str | None = OKX_API_KEY,
        secret: str | None = OKX_SECRET,
        passphrase: str | None = OKX_PASSPHRASE,
        exchange=None,
    ):

        if trading_mode not in VALID_TRADING_MODES:
            raise TradingModeError(f"Unsupported trading mode: {trading_mode}")

        self.trading_mode = trading_mode
        self.live_trading_enabled = live_trading_enabled
        self.api_key = api_key
        self.secret = secret
        self.passphrase = passphrase

        config = {
            "enableRateLimit": True,
        }

        if (
            api_key
            and secret
            and passphrase
        ):
            config["apiKey"] = api_key
            config["secret"] = secret
            config["password"] = passphrase

        self.exchange = exchange or ccxt.okx(config)

        if self.trading_mode == "okx_demo":
            self.exchange.set_sandbox_mode(True)

    def _require_credentials(self) -> None:
        if not (self.api_key and self.secret and self.passphrase):
            raise MissingApiKeysError(
                "API keys are not configured."
            )

    def _require_order_mode(self) -> None:
        if self.trading_mode == "paper":
            raise TradingModeError(
                "Exchange orders are disabled in paper mode."
            )
        if self.trading_mode == "live" and not self.live_trading_enabled:
            raise LiveTradingDisabledError(
                "Live orders require LIVE_TRADING_ENABLED=true."
            )

    def load_markets(self):
        return self.exchange.load_markets()

    def amount_to_precision(self, symbol: str, amount: float) -> float:
        return float(self.exchange.amount_to_precision(symbol, amount))

    def get_balance(self):

        self._require_credentials()

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
        client_order_id: str | None = None,
    ):
        """Create a spot trading order on OKX."""
        self._require_credentials()
        self._require_order_mode()
        if amount <= 0:
            raise OrderValidationError("Order amount must be positive.")
        if client_order_id is not None and (
            len(client_order_id) > 32 or not client_order_id.isalnum()
        ):
            raise OrderValidationError(
                "Client order ID must be 1-32 alphanumeric characters."
            )

        params = {"tdMode": "cash"}
        if client_order_id:
            params["clOrdId"] = client_order_id
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
                params=params,
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
        self._require_credentials()
        self._require_order_mode()
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
        self._require_credentials()
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
        self._require_credentials()
        try:
            return self.exchange.fetch_order(
                id=order_id,
                symbol=symbol,
            )
        except ccxt.ExchangeError as e:
            msg = f"Failed to fetch order {order_id}: {e!s}"
            raise ccxt.ExchangeError(msg) from e
