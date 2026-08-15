from collections import Counter
from math import isfinite

import ccxt

from app.config.settings import MAX_EXCHANGE_ORDER_VALUE
from app.exceptions import (
    DuplicateOrderIntentError,
    OrderValidationError,
)
from app.storage.database import Database, mode_database_path
from app.storage.exchange_order_repository import ExchangeOrderRepository


class KrakenOrderGateway:
    """Persist and validate every Kraken Spot order before submission."""

    def __init__(
        self,
        client,
        max_order_value=MAX_EXCHANGE_ORDER_VALUE,
        order_repository=None,
    ):
        self.client = client
        self.max_order_value = float(max_order_value)
        self._require_positive("safety ceiling", self.max_order_value)
        self.order_repository = order_repository or ExchangeOrderRepository(
            Database(mode_database_path("kraken-live"))
        )

    def submit_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        reference_price: float,
        client_order_id: str,
        quote_cost: float | None = None,
        stop_loss: float | None = None,
    ) -> dict:
        side = side.lower()
        if side not in {"buy", "sell"}:
            raise OrderValidationError("Spot order side must be buy or sell.")
        self._require_positive("amount", amount)
        self._require_positive("reference price", reference_price)
        if quote_cost is not None:
            if side != "buy":
                raise OrderValidationError(
                    "Quote-cost sizing is supported only for market buys."
                )
            self._require_positive("quote cost", quote_cost)
        if stop_loss is not None and (
            side != "buy" or not 0 < stop_loss < reference_price
        ):
            raise OrderValidationError(
                "Attached stop loss must be below the buy reference price."
            )

        markets = self.client.load_markets()
        market = markets.get(symbol)
        if market is None or not market.get("spot", False):
            raise OrderValidationError(f"Unknown Kraken Spot market: {symbol}")
        if market.get("active") is False:
            raise OrderValidationError(f"Inactive Kraken market: {symbol}")
        if stop_loss is not None:
            stop_loss = self.client.price_to_precision(symbol, stop_loss)

        amount = self.client.amount_to_precision(symbol, amount)
        self._require_positive("amount after precision", amount)
        notional = quote_cost if quote_cost is not None else amount * reference_price
        if notional > self.max_order_value:
            raise OrderValidationError(
                f"Order value {notional:.2f} exceeds the "
                f"{self.max_order_value:.2f} safety ceiling."
            )
        self._validate_market_limits(market, amount, notional)
        self._validate_balance(symbol, side, amount, notional)

        if not self.order_repository.prepare(
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            order_type="market",
            amount=amount,
            reference_price=reference_price,
        ):
            raise DuplicateOrderIntentError(
                f"Order intent already exists: {client_order_id}"
            )

        try:
            order = self.client.create_market_order(
                symbol=symbol,
                side=side,
                amount=amount,
                client_order_id=client_order_id,
                quote_cost=quote_cost,
                stop_loss=stop_loss,
            )
        except Exception as error:
            if self._is_explicit_rejection(error):
                self.order_repository.mark_rejected(
                    client_order_id, str(error)
                )
                raise OrderValidationError(
                    f"Kraken rejected the order: {error}"
                ) from error
            self.order_repository.mark_unknown(client_order_id, str(error))
            raise

        self.order_repository.record_order(client_order_id, order)
        order_id = order.get("id")
        if order_id and self._order_status(order) != "FILLED":
            try:
                order = self.client.fetch_order(str(order_id), symbol)
            except (
                ccxt.NetworkError,
                ccxt.ExchangeError,
                ConnectionError,
                TimeoutError,
            ) as error:
                self.order_repository.mark_unknown(client_order_id, str(error))
                raise
            self.order_repository.record_order(client_order_id, order)
        return order

    def submit_stop_loss(
        self,
        symbol: str,
        amount: float,
        stop_loss: float,
        client_order_id: str,
    ) -> dict:
        markets = self.client.load_markets()
        market = markets.get(symbol)
        if market is None or not market.get("spot", False):
            raise OrderValidationError(f"Unknown Kraken Spot market: {symbol}")
        amount = self.client.amount_to_precision(symbol, amount)
        stop_loss = self.client.price_to_precision(symbol, stop_loss)
        self._require_positive("stop amount", amount)
        self._require_positive("stop price", stop_loss)
        self._validate_market_limits(market, amount, amount * stop_loss)
        self._validate_balance(symbol, "sell", amount, amount * stop_loss)
        return self.client.create_stop_loss_order(
            symbol,
            amount,
            stop_loss,
            client_order_id,
        )

    def reconcile_intents(self) -> dict:
        resolved = 0
        unresolved = []
        for intent in self.order_repository.pending():
            try:
                order = self._find_exchange_order(intent)
            except (
                ccxt.NetworkError,
                ccxt.ExchangeError,
                ConnectionError,
                TimeoutError,
            ) as error:
                self.order_repository.mark_unknown(
                    intent["client_order_id"], str(error)
                )
                unresolved.append(intent["client_order_id"])
                continue
            if order is None:
                unresolved.append(intent["client_order_id"])
                continue
            self.order_repository.record_order(intent["client_order_id"], order)
            resolved += 1
        return {
            "resolved": resolved,
            "unresolved_client_order_ids": unresolved,
            "safe": not unresolved,
        }

    def reconciliation_snapshot(self, symbol: str | None = None) -> dict:
        orders = self.client.fetch_open_orders(symbol)
        client_ids = [self._client_order_id(order) for order in orders]
        counts = Counter(value for value in client_ids if value)
        duplicates = sorted(
            value for value, count in counts.items() if count > 1
        )
        return {
            "open_orders": orders,
            "open_order_count": len(orders),
            "duplicate_client_order_ids": duplicates,
            "safe": not duplicates,
        }

    def _find_exchange_order(self, intent: dict) -> dict | None:
        exchange_order_id = intent["exchange_order_id"]
        if exchange_order_id:
            return self.client.fetch_order(exchange_order_id, intent["symbol"])
        return self.client.find_order_by_client_id(
            intent["client_order_id"], intent["symbol"]
        )

    def _validate_market_limits(
        self,
        market: dict,
        amount: float,
        notional: float,
    ) -> None:
        limits = market.get("limits") or {}
        self._validate_limit("amount", amount, limits.get("amount") or {})
        self._validate_limit("cost", notional, limits.get("cost") or {})

    def _validate_balance(
        self,
        symbol: str,
        side: str,
        amount: float,
        notional: float,
    ) -> None:
        base, quote = symbol.split("/", maxsplit=1)
        currency = quote if side == "buy" else base
        required = notional if side == "buy" else amount
        balance = self.client.get_balance()
        free = (balance.get("free") or {}).get(currency)
        if free is None:
            free = (balance.get(currency) or {}).get("free", 0.0)
        if float(free or 0.0) + 1e-12 < required:
            raise OrderValidationError(
                f"Insufficient free {currency} balance for order."
            )

    @staticmethod
    def _validate_limit(name: str, value: float, limit: dict) -> None:
        minimum = limit.get("min")
        maximum = limit.get("max")
        if minimum is not None and value < float(minimum):
            raise OrderValidationError(
                f"Order {name} is below the Kraken minimum."
            )
        if maximum is not None and value > float(maximum):
            raise OrderValidationError(
                f"Order {name} exceeds the Kraken maximum."
            )

    @staticmethod
    def _require_positive(name: str, value: float) -> None:
        if not isfinite(value) or value <= 0:
            raise OrderValidationError(f"Order {name} must be positive.")

    @staticmethod
    def _client_order_id(order: dict) -> str | None:
        info = order.get("info") or {}
        value = order.get("clientOrderId") or info.get("cl_ord_id")
        return str(value) if value is not None else None

    @staticmethod
    def _order_status(order: dict) -> str:
        status = str(order.get("status") or "").lower()
        return "FILLED" if status == "closed" else status.upper()

    @staticmethod
    def _is_explicit_rejection(error: Exception) -> bool:
        explicit_types = (
            ccxt.AuthenticationError,
            ccxt.PermissionDenied,
            ccxt.InsufficientFunds,
            ccxt.InvalidOrder,
            ccxt.BadRequest,
        )
        if isinstance(error, explicit_types):
            return True
        message = str(error).lower()
        return isinstance(error, ccxt.ExchangeError) and any(
            marker in message
            for marker in (
                "eorder:invalid",
                "eorder:insufficient funds",
                "permission denied",
                "order minimum",
            )
        )
