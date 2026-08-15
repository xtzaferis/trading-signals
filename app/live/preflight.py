from app.config.settings import (
    KRAKEN_EXPECTED_KEY_NAME,
    MARKET_SYMBOL,
    QUOTE_CURRENCY,
)
from app.core.logger import logger
from app.exceptions import TradingModeError
from app.exchange.kraken_client import KrakenClient

REQUIRED_PERMISSIONS = {
    "query-funds",
    "query-open-trades",
    "query-closed-trades",
    "modify-trades",
    "close-trades",
}
FORBIDDEN_PERMISSIONS = {
    "add-funds",
    "withdraw-funds",
    "earn-funds",
    "add-withdraw-address",
    "update-withdraw-address",
}


def check(client=None) -> dict:
    """Perform authenticated Kraken checks without placing an order."""
    client = client or KrakenClient(
        trading_mode="live",
        live_trading_enabled=False,
    )
    key_info = client.get_key_info()
    permissions = {
        str(permission).strip().lower()
        for permission in key_info.get("permissions") or []
        if str(permission).strip()
    }
    missing = sorted(REQUIRED_PERMISSIONS - permissions)
    if missing:
        raise TradingModeError(
            "Kraken API key is missing required permissions: "
            + ", ".join(missing)
        )
    forbidden = sorted(FORBIDDEN_PERMISSIONS & permissions)
    if forbidden:
        raise TradingModeError(
            "Kraken API key has forbidden funding permissions: "
            + ", ".join(forbidden)
        )

    key_name = str(key_info.get("apiKeyName") or "")
    if KRAKEN_EXPECTED_KEY_NAME and key_name != KRAKEN_EXPECTED_KEY_NAME:
        raise TradingModeError(
            "Authenticated Kraken API key has an unexpected name."
        )

    markets = client.load_markets()
    market = markets.get(MARKET_SYMBOL)
    if market is None or not market.get("spot", False):
        raise TradingModeError(
            f"Kraken spot market {MARKET_SYMBOL} is unavailable."
        )
    if market.get("active") is False:
        raise TradingModeError(
            f"Kraken spot market {MARKET_SYMBOL} is not active."
        )

    balance = client.get_balance()
    free = (balance.get("free") or {}).get(QUOTE_CURRENCY)
    if free is None:
        free = (balance.get(QUOTE_CURRENCY) or {}).get("free", 0.0)
    open_orders = client.fetch_open_orders(None)
    ip_allowlist = sorted(
        str(value) for value in key_info.get("ipAllowlist") or []
    )
    return {
        "exchange": "kraken",
        "permissions": sorted(permissions),
        "key_name": key_name,
        "ip_allowlist": ip_allowlist,
        "free_quote": max(0.0, float(free or 0.0)),
        "quote_currency": QUOTE_CURRENCY,
        "market_symbol": MARKET_SYMBOL,
        "open_order_count": len(open_orders),
    }


def main():
    result = check()
    logger.info("KRAKEN LIVE READ-ONLY PREFLIGHT")
    logger.info(f"Key Name:          {result['key_name'] or 'unknown'}")
    logger.info(f"Permissions:       {','.join(result['permissions'])}")
    logger.info(
        "IP Allowlist:      "
        + (",".join(result["ip_allowlist"]) or "not configured")
    )
    logger.info(f"Spot Market:       {result['market_symbol']}")
    logger.info(
        f"Free Balance:      {result['free_quote']:.2f} "
        f"{result['quote_currency']}"
    )
    logger.info(f"Open Orders:       {result['open_order_count']}")
    logger.info("No order was sent.")


if __name__ == "__main__":
    main()
