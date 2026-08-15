import argparse
import time

import ccxt

from app.config.settings import LIVE_ACCOUNT_SIZE, SCAN_INTERVAL
from app.core.logger import logger
from app.exchange.kraken_client import KrakenClient
from app.execution.kraken_live_broker import KrakenLiveBroker
from app.execution.kraken_order_gateway import KrakenOrderGateway
from app.trading.portfolio import Portfolio


def monitor_once(broker=None) -> dict:
    if broker is None:
        client = KrakenClient()
        broker = KrakenLiveBroker(
            Portfolio(initial_balance=LIVE_ACCOUNT_SIZE),
            KrakenOrderGateway(client),
        )
    reconciliation = broker.reconcile()
    for position in broker.portfolio.open_positions.copy():
        ticker = broker.gateway.client.get_ticker(position.symbol)
        price = float(ticker.get("last") or 0.0)
        if price > 0:
            broker.update(position, price, price, price, ticker.get("datetime"))
    return {
        "reconciliation": reconciliation,
        "open_positions": len(broker.portfolio.open_positions),
        "pending_entries": len(broker.positions.pending_entries()),
        "closed_positions": len(broker.portfolio.closed_positions),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconcile and monitor protected Kraken positions."
    )
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Keep waiting when no Kraken position exists yet.",
    )
    args = parser.parse_args()
    while True:
        try:
            result = monitor_once()
            logger.info(
                "KRAKEN MONITOR | "
                f"open={result['open_positions']} | "
                f"pending={result['pending_entries']} | "
                f"closed={result['closed_positions']} | "
                f"safe={result['reconciliation'].get('safe', False)}"
            )
            if args.once or (
                not args.wait
                and result["open_positions"] == 0
                and result["pending_entries"] == 0
            ):
                return
        except (
            ccxt.NetworkError,
            ccxt.ExchangeError,
            ConnectionError,
            TimeoutError,
        ):
            logger.exception("Kraken monitor cycle failed; native stop remains.")
            if args.once:
                raise
        time.sleep(max(5, SCAN_INTERVAL))


if __name__ == "__main__":
    main()
