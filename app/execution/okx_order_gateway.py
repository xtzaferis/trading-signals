from collections import Counter
from math import isfinite

from app.config.settings import MAX_EXCHANGE_ORDER_VALUE
from app.exceptions import OrderValidationError


class OKXOrderGateway:
    """Validate spot orders before delegating them to the OKX client."""

    def __init__(self, client, max_order_value=MAX_EXCHANGE_ORDER_VALUE):
        self.client = client
        self.max_order_value = float(max_order_value)
        self._require_positive("safety ceiling", self.max_order_value)

    def submit_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        reference_price: float,
        client_order_id: str,
    ) -> dict:
        side = side.lower()
        if side not in {"buy", "sell"}:
            raise OrderValidationError("Spot order side must be buy or sell.")
        self._require_positive("amount", amount)
        self._require_positive("reference price", reference_price)

        markets = self.client.load_markets()
        if symbol not in markets:
            raise OrderValidationError(f"Unknown OKX market: {symbol}")
        amount = self.client.amount_to_precision(symbol, amount)
        self._require_positive("amount after precision", amount)
        notional = amount * reference_price
        if notional > self.max_order_value:
            raise OrderValidationError(
                f"Order value {notional:.2f} exceeds the "
                f"{self.max_order_value:.2f} safety ceiling."
            )

        self._validate_market_limits(markets[symbol], amount, notional)
        self._validate_balance(symbol, side, amount, notional)

        return self.client.create_order(
            symbol=symbol,
            order_type="market",
            side=side,
            amount=amount,
            client_order_id=client_order_id,
        )

    def reconciliation_snapshot(self, symbol: str | None = None) -> dict:
        orders = self.client.fetch_open_orders(symbol)
        client_ids = [
            self._client_order_id(order)
            for order in orders
        ]
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
        if float(free or 0.0) < required:
            raise OrderValidationError(
                f"Insufficient free {currency} balance for order."
            )

    @staticmethod
    def _validate_limit(name: str, value: float, limit: dict) -> None:
        minimum = limit.get("min")
        maximum = limit.get("max")
        if minimum is not None and value < float(minimum):
            raise OrderValidationError(
                f"Order {name} is below the OKX minimum."
            )
        if maximum is not None and value > float(maximum):
            raise OrderValidationError(
                f"Order {name} exceeds the OKX maximum."
            )

    @staticmethod
    def _require_positive(name: str, value: float) -> None:
        if not isfinite(value) or value <= 0:
            raise OrderValidationError(f"Order {name} must be positive.")

    @staticmethod
    def _client_order_id(order: dict) -> str | None:
        return (
            order.get("clientOrderId")
            or (order.get("info") or {}).get("clOrdId")
            or None
        )
