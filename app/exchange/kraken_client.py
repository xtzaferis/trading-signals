import re
import zlib

import ccxt

from app.config.settings import (
    KRAKEN_API_KEY,
    KRAKEN_API_SECRET,
    LIVE_TRADING_ENABLED,
    TRADING_MODE,
)
from app.exceptions import (
    LiveTradingDisabledError,
    MissingApiKeysError,
    OrderValidationError,
    TradingModeError,
)


class KrakenClient:
    """Safety-focused wrapper around Kraken Pro Spot through CCXT."""

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
                "Kraken supports paper or live mode; no Spot execution "
                "sandbox is used by this bot."
            )

        self.trading_mode = trading_mode
        self.live_trading_enabled = live_trading_enabled
        self.api_key = (api_key or KRAKEN_API_KEY or "").strip() or None
        self.secret = (secret or KRAKEN_API_SECRET or "").strip() or None

        config = {
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        }
        if self.api_key and self.secret:
            config["apiKey"] = self.api_key
            config["secret"] = self.secret
        self.exchange = exchange or ccxt.kraken(config)

    def _require_credentials(self) -> None:
        if not (self.api_key and self.secret):
            raise MissingApiKeysError(
                "Kraken API key and private signing secret are not configured."
            )

    def _require_order_mode(self) -> None:
        if self.trading_mode != "live":
            raise TradingModeError("Kraken orders are disabled outside live mode.")
        if not self.live_trading_enabled:
            raise LiveTradingDisabledError(
                "Kraken live orders require LIVE_TRADING_ENABLED=true."
            )

    def get_key_info(self) -> dict:
        self._require_credentials()
        response = self.exchange.privatePostGetApiKeyInfo()
        return response.get("result") or response

    def get_balance(self) -> dict:
        self._require_credentials()
        return self.exchange.fetch_balance()

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

    def price_to_precision(self, symbol: str, price: float) -> float:
        return float(self.exchange.price_to_precision(symbol, price))

    def preview_market_buy(
        self,
        symbol: str,
        quote_cost: float,
        client_order_id: str,
        stop_loss: float | None = None,
    ) -> dict:
        """Validate a quote-sized Kraken order without submitting it."""
        self._require_credentials()
        if quote_cost <= 0:
            raise OrderValidationError("Preview quote cost must be positive.")
        self._validate_client_order_id(client_order_id)
        params = {"cost": quote_cost, "validate": True}
        if stop_loss is not None:
            if stop_loss <= 0:
                raise OrderValidationError(
                    "Preview stop-loss price must be positive."
                )
            params["close"] = {
                "ordertype": "stop-loss",
                "price": stop_loss,
            }
            params["userref"] = self._userref(client_order_id)
        else:
            params["clientOrderId"] = client_order_id
        return self.exchange.create_order(
            symbol=symbol,
            type="market",
            side="buy",
            amount=quote_cost,
            price=None,
            params=params,
        )

    def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        client_order_id: str,
        quote_cost: float | None = None,
        stop_loss: float | None = None,
    ) -> dict:
        """Submit one Kraken Spot order after both live gates pass."""
        self._require_credentials()
        self._require_order_mode()
        side = side.lower()
        if side not in {"buy", "sell"} or amount <= 0:
            raise OrderValidationError("Invalid Kraken spot market order.")
        self._validate_client_order_id(client_order_id)
        params = {}
        if quote_cost is not None:
            if side != "buy" or quote_cost <= 0:
                raise OrderValidationError(
                    "Quote-cost sizing is supported only for market buys."
                )
            params["cost"] = quote_cost
        if stop_loss is not None:
            if side != "buy" or stop_loss <= 0:
                raise OrderValidationError(
                    "Attached stop loss is supported only for market buys."
                )
            params["close"] = {
                "ordertype": "stop-loss",
                "price": stop_loss,
            }
            # Kraken rejects cl_ord_id on entries with conditional closes.
            # userref remains queryable and is derived from our persisted ID.
            params["userref"] = self._userref(client_order_id)
        else:
            params["clientOrderId"] = client_order_id
        return self.exchange.create_order(
            symbol=symbol,
            type="market",
            side=side,
            amount=amount,
            price=None,
            params=params,
        )

    def create_post_only_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        client_order_id: str,
        stop_loss: float | None = None,
    ) -> dict:
        """Submit a maker-only Spot limit order; Kraken rejects any taker fill."""
        self._require_credentials()
        self._require_order_mode()
        side = side.lower()
        if side not in {"buy", "sell"} or amount <= 0 or price <= 0:
            raise OrderValidationError("Invalid Kraken post-only limit order.")
        self._validate_client_order_id(client_order_id)
        params = {"postOnly": True}
        if stop_loss is not None:
            if side != "buy" or not 0 < stop_loss < price:
                raise OrderValidationError(
                    "Attached stop loss must be below a post-only buy price."
                )
            params["close"] = {
                "ordertype": "stop-loss",
                "price": stop_loss,
            }
            params["userref"] = self._userref(client_order_id)
        else:
            params["clientOrderId"] = client_order_id
        return self.exchange.create_order(
            symbol=symbol,
            type="limit",
            side=side,
            amount=amount,
            price=price,
            params=params,
        )

    def create_stop_loss_order(
        self,
        symbol: str,
        amount: float,
        stop_loss: float,
        client_order_id: str,
    ) -> dict:
        """Place a native stop-market sell protecting Spot inventory."""
        self._require_credentials()
        self._require_order_mode()
        if amount <= 0 or stop_loss <= 0:
            raise OrderValidationError("Invalid Kraken stop-loss order.")
        self._validate_client_order_id(client_order_id)
        return self.exchange.create_order(
            symbol=symbol,
            type="stop-loss",
            side="sell",
            amount=amount,
            price=stop_loss,
            params={"clientOrderId": client_order_id},
        )

    def fetch_order(self, order_id: str, symbol: str) -> dict:
        self._require_credentials()
        return self.exchange.fetch_order(order_id, symbol)

    def fetch_open_orders(self, symbol: str | None = None) -> list[dict]:
        self._require_credentials()
        return self.exchange.fetch_open_orders(symbol)

    def fetch_closed_orders(self, symbol: str | None = None) -> list[dict]:
        self._require_credentials()
        return self.exchange.fetch_closed_orders(symbol)

    def find_order_by_client_id(
        self,
        client_order_id: str,
        symbol: str,
    ) -> dict | None:
        """Find a Kraken order after an ambiguous submission response."""
        self._require_credentials()
        client_params = {"clientOrderId": client_order_id}
        orders = self.exchange.fetch_open_orders(
            symbol, params=client_params
        )
        orders += self.exchange.fetch_closed_orders(
            symbol, params=client_params
        )
        matched = next(
            (
                order
                for order in orders
                if self._client_order_id(order) == client_order_id
            ),
            None,
        )
        if matched is not None:
            return matched

        userref = self._userref(client_order_id)
        orders = self.exchange.fetch_open_orders(symbol, params={"userref": userref})
        orders += self.exchange.fetch_closed_orders(
            symbol, params={"userref": userref}
        )
        return next(
            (
                order
                for order in orders
                if self._client_order_id(order) == client_order_id
                or self._order_userref(order) == userref
            ),
            None,
        )

    def find_attached_stop(
        self,
        symbol: str,
        entry_order_id: str,
    ) -> dict | None:
        """Find the stop order created by a filled conditional entry."""
        self._require_credentials()
        orders = self.exchange.fetch_open_orders(symbol)
        orders += self.exchange.fetch_closed_orders(symbol)
        return next(
            (
                order
                for order in orders
                if self._parent_order_id(order) == entry_order_id
                and self._order_type(order) == "stop-loss"
            ),
            None,
        )

    def cancel_order(self, order_id: str, symbol: str) -> dict:
        self._require_credentials()
        self._require_order_mode()
        return self.exchange.cancel_order(order_id, symbol)

    @staticmethod
    def _validate_client_order_id(client_order_id: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9-]{1,18}", client_order_id or ""):
            raise OrderValidationError(
                "Kraken client order ID must be 1-18 letters, numbers, "
                "or hyphens."
            )

    @staticmethod
    def _client_order_id(order: dict) -> str | None:
        info = order.get("info") or {}
        value = order.get("clientOrderId") or info.get("cl_ord_id")
        return str(value) if value is not None else None

    @staticmethod
    def _parent_order_id(order: dict) -> str | None:
        info = order.get("info") or {}
        value = info.get("refid") or info.get("ref_id")
        return str(value) if value is not None else None

    @staticmethod
    def _order_type(order: dict) -> str:
        info = order.get("info") or {}
        description = info.get("descr") or {}
        value = (
            description.get("ordertype")
            or info.get("ordertype")
            or order.get("type")
        )
        return str(value or "").lower().replace(" ", "-")

    @staticmethod
    def _order_userref(order: dict) -> int | None:
        value = (order.get("info") or {}).get("userref")
        return int(value) if value is not None else None

    @staticmethod
    def _userref(client_order_id: str) -> int:
        value = zlib.crc32(client_order_id.encode("ascii")) & 0x7FFFFFFF
        return value or 1
