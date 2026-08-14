from app.config.settings import (
    COINBASE_EXPECTED_PORTFOLIO_ID,
    MARKET_SYMBOL,
    QUOTE_CURRENCY,
)
from app.core.logger import logger
from app.exceptions import TradingModeError
from app.exchange.coinbase_client import CoinbaseClient


def check(client=None) -> dict:
    """Perform authenticated Coinbase checks without placing an order."""
    client = client or CoinbaseClient(
        trading_mode="live",
        live_trading_enabled=False,
    )
    permissions = client.get_key_permissions()
    if not permissions.get("can_view", False):
        raise TradingModeError("Coinbase API key requires View permission.")
    if not permissions.get("can_trade", False):
        raise TradingModeError("Coinbase API key requires Trade permission.")
    if permissions.get("can_transfer", False):
        raise TradingModeError(
            "Coinbase API key must not have Transfer permission."
        )

    portfolio_id = str(permissions.get("portfolio_uuid") or "")
    if (
        COINBASE_EXPECTED_PORTFOLIO_ID
        and portfolio_id != COINBASE_EXPECTED_PORTFOLIO_ID
    ):
        raise TradingModeError(
            "Coinbase API key is scoped to an unexpected portfolio."
        )

    markets = client.load_markets()
    market = markets.get(MARKET_SYMBOL)
    if market is None or not market.get("spot", False):
        raise TradingModeError(
            f"Coinbase spot market {MARKET_SYMBOL} is unavailable."
        )
    if market.get("active") is False:
        raise TradingModeError(
            f"Coinbase spot market {MARKET_SYMBOL} is not active."
        )

    balance = client.get_balance()
    free = (balance.get("free") or {}).get(QUOTE_CURRENCY)
    if free is None:
        free = (balance.get(QUOTE_CURRENCY) or {}).get("free", 0.0)
    open_orders = client.fetch_open_orders(None)
    enabled_permissions = sorted(
        name.removeprefix("can_")
        for name, enabled in permissions.items()
        if name.startswith("can_") and enabled
    )
    return {
        "exchange": "coinbase",
        "permissions": enabled_permissions,
        "portfolio_id": portfolio_id,
        "free_quote": max(0.0, float(free or 0.0)),
        "quote_currency": QUOTE_CURRENCY,
        "market_symbol": MARKET_SYMBOL,
        "open_order_count": len(open_orders),
    }


def main():
    result = check()
    logger.info("COINBASE LIVE READ-ONLY PREFLIGHT")
    logger.info(f"Permissions:       {','.join(result['permissions'])}")
    logger.info(f"Portfolio ID:      {result['portfolio_id'] or 'unknown'}")
    logger.info(f"Spot Market:       {result['market_symbol']}")
    logger.info(
        f"Free Balance:      {result['free_quote']:.2f} "
        f"{result['quote_currency']}"
    )
    logger.info(f"Open Orders:       {result['open_order_count']}")
    logger.info("No order was sent.")


if __name__ == "__main__":
    main()
