import argparse
from datetime import datetime, timezone

from app.config.settings import LIVE_ACCOUNT_SIZE, LIVE_CANARY_SYMBOL
from app.core.logger import logger
from app.exceptions import TradingModeError
from app.exchange.kraken_client import KrakenClient
from app.execution.kraken_live_broker import KrakenLiveBroker
from app.execution.kraken_order_gateway import KrakenOrderGateway
from app.trading.portfolio import Portfolio

CONFIRMATION = "I_ACCEPT_REAL_MARKET_EXIT"


def close_canary(
    broker=None,
    *,
    execute: bool = False,
    confirmation: str = "",
    symbol: str = LIVE_CANARY_SYMBOL,
) -> dict:
    if execute and confirmation != CONFIRMATION:
        raise TradingModeError("Real market exit confirmation is missing.")
    if broker is None:
        client = KrakenClient()
        broker = KrakenLiveBroker(
            Portfolio(initial_balance=LIVE_ACCOUNT_SIZE),
            KrakenOrderGateway(client),
        )

    reconciliation = broker.reconcile()
    if not reconciliation.get("safe", False):
        raise TradingModeError(
            "Kraken reconciliation is unsafe; controlled close aborted."
        )
    positions = [
        position
        for position in broker.portfolio.open_positions
        if position.symbol == symbol
    ]
    if len(positions) != 1:
        raise TradingModeError(
            f"Expected one open {symbol} canary, found "
            f"{len(positions)}."
        )

    position = positions[0]
    ticker = broker.gateway.client.get_ticker(position.symbol)
    price = float(ticker.get("last") or 0.0)
    if price <= 0:
        raise TradingModeError("Kraken returned an invalid exit reference price.")
    result = {
        "symbol": position.symbol,
        "quantity": position.quantity,
        "reference_price": price,
        "estimated_quote_value": position.quantity * price,
        "executed": False,
    }
    if not execute:
        return result

    timestamp = ticker.get("datetime") or datetime.now(timezone.utc)
    if not broker.close(position, price, "MANUAL", timestamp):
        raise TradingModeError(
            "Controlled close was not confirmed filled; reconciliation is required."
        )

    open_orders = broker.gateway.client.fetch_open_orders(position.symbol)
    balance = broker.gateway.client.get_balance()
    base, quote = position.symbol.split("/", maxsplit=1)
    free_quote = (balance.get("free") or {}).get(quote, 0.0)
    total_base = (balance.get("total") or {}).get(base, 0.0)
    result.update(
        {
            "executed": True,
            "exit_price": position.current_price,
            "realized_pnl": position.realized_pnl,
            "open_orders": len(open_orders),
            "free_quote": float(free_quote or 0.0),
            "remaining_base": float(total_base or 0.0),
        }
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preview or execute a controlled Kraken canary market exit."
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirmation", default="")
    args = parser.parse_args()
    result = close_canary(
        execute=args.execute,
        confirmation=args.confirmation,
    )
    logger.warning("KRAKEN CONTROLLED CANARY EXIT")
    for key, value in result.items():
        logger.info(f"{key}: {value}")
    if not result["executed"]:
        logger.info("Preview only. No order was changed or sent.")


if __name__ == "__main__":
    main()
