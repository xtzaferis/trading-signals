import ccxt

from app.config.settings import (
    COINBASE_API_KEY,
    COINBASE_API_SECRET,
    LIVE_TRADING_ENABLED,
    TRADING_MODE,
)
from app.exceptions import (
    LiveTradingDisabledError,
    MissingApiKeysError,
    OrderValidationError,
    TradingModeError,
)


class CoinbaseClient:
    """Small, safety-focused wrapper around Coinbase Advanced Trade."""

    def __init__(
        self,
        trading_mode: str = TRADING_MODE,
        live_trading_enabled: bool = LIVE_TRADING_ENABLED,
        api_key: str | None = None,
        secret: str | None = None,
        exchange=None,
    ):
        if trading_mode not in {"paper", "live"}:
            raise TradingModeError(
                "Coinbase supports paper or live mode; its API sandbox returns "
                "static responses and is not an execution simulator."
            )

        self.trading_mode = trading_mode
        self.live_trading_enabled = live_trading_enabled
        self.api_key = api_key or COINBASE_API_KEY
        self.secret = self._normalize_private_key(
            secret or COINBASE_API_SECRET
        )

        config = {
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",
                "fetchBalance": "v3PrivateGetBrokerageAccounts",
            },
        }
        if self.api_key and self.secret:
            config["apiKey"] = self.api_key
            config["secret"] = self.secret
        self.exchange = exchange or ccxt.coinbase(config)

    @staticmethod
    def _normalize_private_key(secret: str | None) -> str | None:
        if secret is None:
            return None
        return secret.strip().strip('"').replace("\\n", "\n")

    def _require_credentials(self) -> None:
        if not (self.api_key and self.secret):
            raise MissingApiKeysError(
                "Coinbase CDP API key and private key are not configured."
            )

    def _require_order_mode(self) -> None:
        if self.trading_mode != "live":
            raise TradingModeError("Coinbase orders are disabled outside live mode.")
        if not self.live_trading_enabled:
            raise LiveTradingDisabledError(
                "Coinbase live orders require LIVE_TRADING_ENABLED=true."
            )

    def get_key_permissions(self) -> dict:
        self._require_credentials()
        return self.exchange.v3_private_get_brokerage_key_permissions()

    def get_balance(self) -> dict:
        self._require_credentials()
        return self.exchange.fetch_balance()

    def fetch_open_orders(self, symbol: str | None = None) -> list[dict]:
        self._require_credentials()
        return self.exchange.fetch_open_orders(symbol)

    def load_markets(self) -> dict:
        return self.exchange.load_markets()

    def get_ticker(self, symbol: str) -> dict:
        return self.exchange.fetch_ticker(symbol)

    def get_tickers(self) -> dict:
        return self.exchange.fetch_tickers()

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "15m",
        limit: int = 200,
    ) -> list:
        return self.exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            limit=limit,
        )

    def amount_to_precision(self, symbol: str, amount: float) -> float:
        return float(self.exchange.amount_to_precision(symbol, amount))

    def preview_market_buy(
        self,
        symbol: str,
        quote_cost: float,
        client_order_id: str,
    ) -> dict:
        """Ask Coinbase to validate an order without submitting it."""
        self._require_credentials()
        if quote_cost <= 0:
            raise OrderValidationError("Preview quote cost must be positive.")
        if not client_order_id:
            raise OrderValidationError("Preview client order ID is required.")
        return self.exchange.create_order(
            symbol=symbol,
            type="market",
            side="buy",
            amount=quote_cost,
            price=None,
            params={
                "cost": quote_cost,
                "client_order_id": client_order_id,
                "preview": True,
            },
        )

    def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        client_order_id: str,
        quote_cost: float | None = None,
    ) -> dict:
        """Submit one Coinbase order after both global live gates pass."""
        self._require_credentials()
        self._require_order_mode()
        side = side.lower()
        if side not in {"buy", "sell"} or amount <= 0:
            raise OrderValidationError("Invalid Coinbase spot market order.")
        params = {"client_order_id": client_order_id}
        if quote_cost is not None:
            if side != "buy" or quote_cost <= 0:
                raise OrderValidationError(
                    "Quote-cost sizing is supported only for market buys."
                )
            params["cost"] = quote_cost
        return self.exchange.create_order(
            symbol=symbol,
            type="market",
            side=side,
            amount=amount,
            price=None,
            params=params,
        )
