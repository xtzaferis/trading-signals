from uuid import uuid4

from app.config.settings import (
    LIVE_ACCOUNT_SIZE,
    LIVE_CANARY_ORDER_VALUE,
    LIVE_CANARY_STOP_LOSS_PCT,
    LIVE_CANARY_SYMBOL,
    LIVE_TRADING_ENABLED,
    MAX_EXCHANGE_ORDER_VALUE,
    QUOTE_CURRENCY,
)
from app.core.logger import logger
from app.exceptions import OrderValidationError, TradingModeError
from app.exchange.kraken_client import KrakenClient


def preview(
    client=None,
    symbol: str = LIVE_CANARY_SYMBOL,
    quote_cost: float = LIVE_CANARY_ORDER_VALUE,
    client_order_id: str | None = None,
) -> dict:
    """Ask Kraken to validate a market buy without executing it."""
    if LIVE_TRADING_ENABLED:
        raise TradingModeError(
            "Validate-only preview requires LIVE_TRADING_ENABLED=false."
        )
    if quote_cost <= 0:
        raise OrderValidationError("Preview value must be positive.")
    safety_limit = min(LIVE_ACCOUNT_SIZE, MAX_EXCHANGE_ORDER_VALUE)
    if quote_cost > safety_limit:
        raise OrderValidationError(
            f"Preview value exceeds the {safety_limit:.2f} "
            f"{QUOTE_CURRENCY} safety limit."
        )

    client = client or KrakenClient(
        trading_mode="live",
        live_trading_enabled=False,
    )
    market = client.load_markets().get(symbol)
    if market is None or not market.get("spot", False):
        raise OrderValidationError(
            f"Kraken Spot market {symbol} is unavailable."
        )
    if market.get("active") is False:
        raise OrderValidationError(
            f"Kraken Spot market {symbol} is not active."
        )

    balance = client.get_balance()
    free = (balance.get("free") or {}).get(QUOTE_CURRENCY)
    if free is None:
        free = (balance.get(QUOTE_CURRENCY) or {}).get("free", 0.0)
    free = max(0.0, float(free or 0.0))
    if free < quote_cost:
        raise OrderValidationError(
            f"Available balance is {free:.2f} {QUOTE_CURRENCY}; "
            f"the preview requires {quote_cost:.2f} {QUOTE_CURRENCY}."
        )

    ticker = client.get_ticker(symbol)
    reference_price = float(ticker.get("ask") or ticker.get("last") or 0.0)
    if reference_price <= 0:
        raise OrderValidationError("Kraken returned no usable preview price.")
    stop_loss = reference_price * (1.0 - LIVE_CANARY_STOP_LOSS_PCT)
    stop_loss = client.price_to_precision(symbol, stop_loss)
    client_order_id = client_order_id or f"preview-{uuid4().hex[:10]}"
    response = client.preview_market_buy(
        symbol,
        quote_cost,
        client_order_id,
        stop_loss=stop_loss,
    )
    return {
        "exchange": "kraken",
        "symbol": symbol,
        "side": "buy",
        "quote_cost": quote_cost,
        "quote_currency": QUOTE_CURRENCY,
        "client_order_id": client_order_id,
        "stop_loss": stop_loss,
        "exchange_response": response,
        "submitted": False,
    }


def main() -> None:
    result = preview()
    logger.info("KRAKEN VALIDATE-ONLY ORDER PREVIEW")
    logger.info(f"Symbol:            {result['symbol']}")
    logger.info(f"Side:              {result['side'].upper()}")
    logger.info(
        f"Preview Value:     {result['quote_cost']:.2f} "
        f"{result['quote_currency']}"
    )
    logger.info(f"Client Order ID:   {result['client_order_id']}")
    logger.info(f"Attached Stop:     {result['stop_loss']:.2f}")
    logger.info("Validation:        accepted by Kraken")
    logger.info("No order was sent to the matching engine.")


if __name__ == "__main__":
    main()
