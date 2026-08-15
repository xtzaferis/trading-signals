import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt

from app.config.settings import (
    LIVE_ACCOUNT_SIZE,
    LIVE_MONITOR_ALERT_COOLDOWN_SECONDS,
    LIVE_MONITOR_HEALTH_PATH,
    LIVE_MONITOR_WEBHOOK_TIMEOUT_SECONDS,
    LIVE_MONITOR_WEBHOOK_URL,
    SCAN_INTERVAL,
)
from app.core.logger import logger
from app.exchange.kraken_client import KrakenClient
from app.execution.kraken_live_broker import KrakenLiveBroker
from app.execution.kraken_order_gateway import KrakenOrderGateway
from app.live.monitor_alerts import MonitorAlerts
from app.trading.portfolio import Portfolio


def monitor_once(broker=None) -> dict:
    if broker is None:
        client = KrakenClient()
        broker = KrakenLiveBroker(
            Portfolio(initial_balance=LIVE_ACCOUNT_SIZE),
            KrakenOrderGateway(client),
        )
    reconciliation = broker.reconcile()
    positions = []
    closed_symbols = []
    for position in broker.portfolio.open_positions.copy():
        ticker = broker.gateway.client.get_ticker(position.symbol)
        price = float(ticker.get("last") or 0.0)
        if price > 0:
            closed = broker.update(
                position,
                price,
                price,
                price,
                ticker.get("datetime") or datetime.now(timezone.utc),
            )
            positions.append(_position_snapshot(position, price))
            if closed:
                closed_symbols.append(position.symbol)
    return {
        "reconciliation": reconciliation,
        "open_positions": len(broker.portfolio.open_positions),
        "pending_entries": len(broker.positions.pending_entries()),
        "closed_positions": len(broker.portfolio.closed_positions),
        "positions": positions,
        "closed_symbols": closed_symbols,
    }


def _position_snapshot(position, price: float) -> dict:
    entry = float(position.entry_price)
    stop = float(position.stop_loss)
    target = float(position.take_profit)
    return {
        "symbol": position.symbol,
        "price": price,
        "entry": entry,
        "stop_loss": stop,
        "take_profit": target,
        "unrealized_pnl": (price - entry) * float(position.quantity),
        "return_pct": ((price / entry) - 1.0) * 100 if entry else 0.0,
        "distance_to_stop_pct": ((price / stop) - 1.0) * 100 if stop else 0.0,
        "distance_to_target_pct": ((target / price) - 1.0) * 100 if price else 0.0,
    }


def write_health_snapshot(
    result: dict | None,
    status: str,
    path: Path = LIVE_MONITOR_HEALTH_PATH,
    error: str | None = None,
    consecutive_failures: int = 0,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "consecutive_failures": consecutive_failures,
        "error": error,
    }
    if result is not None:
        payload.update(
            {
                "safe": bool(result["reconciliation"].get("safe", False)),
                "open_positions": result["open_positions"],
                "pending_entries": result["pending_entries"],
                "positions": result["positions"],
            }
        )
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def write_health_safely(*args, **kwargs) -> bool:
    try:
        write_health_snapshot(*args, **kwargs)
    except OSError:
        logger.exception("Kraken monitor health snapshot could not be written.")
        return False
    return True


def log_monitor_result(result: dict) -> None:
    reconciliation = result["reconciliation"]
    logger.info(
        "KRAKEN MONITOR | "
        f"open={result['open_positions']} | "
        f"pending={result['pending_entries']} | "
        f"closed={result['closed_positions']} | "
        f"safe={reconciliation.get('safe', False)}"
    )
    for position in result["positions"]:
        logger.info(
            "KRAKEN POSITION | "
            f"{position['symbol']} | price={position['price']:.2f} | "
            f"entry={position['entry']:.2f} | "
            f"sl={position['stop_loss']:.2f} "
            f"({position['distance_to_stop_pct']:+.2f}%) | "
            f"tp={position['take_profit']:.2f} "
            f"({position['distance_to_target_pct']:+.2f}%) | "
            f"pnl={position['unrealized_pnl']:+.4f} "
            f"({position['return_pct']:+.2f}%)"
        )


def _unsafe_details(result: dict) -> dict:
    reconciliation = result["reconciliation"]
    return {
        "unprotected_symbols": reconciliation.get("unprotected_symbols", []),
        "balance_mismatches": reconciliation.get("balance_mismatches", []),
        "unexpected_open_order_ids": reconciliation.get(
            "unexpected_open_order_ids", []
        ),
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
    alerts = MonitorAlerts(
        LIVE_MONITOR_WEBHOOK_URL,
        LIVE_MONITOR_WEBHOOK_TIMEOUT_SECONDS,
        LIVE_MONITOR_ALERT_COOLDOWN_SECONDS,
    )
    previous_safe = None
    consecutive_failures = 0
    while True:
        try:
            result = monitor_once()
            safe = bool(result["reconciliation"].get("safe", False))
            log_monitor_result(result)
            write_health_safely(result, "healthy" if safe else "unsafe")
            consecutive_failures = 0
            if not safe:
                alerts.send(
                    "unsafe-position",
                    "Kraken position reconciliation is unsafe.",
                    severity="critical",
                    details=_unsafe_details(result),
                    force=previous_safe is not False,
                )
            elif previous_safe is False:
                alerts.send(
                    "monitor-recovered",
                    "Kraken position reconciliation recovered.",
                    severity="info",
                    force=True,
                )
            for symbol in result["closed_symbols"]:
                alerts.send(
                    f"position-closed:{symbol}",
                    f"Kraken position closed: {symbol}.",
                    severity="info",
                    force=True,
                )
            previous_safe = safe
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
            consecutive_failures += 1
            logger.exception("Kraken monitor cycle failed; native stop remains.")
            error = "Exchange or network monitor cycle failure."
            write_health_safely(
                None,
                "error",
                error=error,
                consecutive_failures=consecutive_failures,
            )
            alerts.send(
                "monitor-cycle-failed",
                error,
                severity="critical",
                details={"consecutive_failures": consecutive_failures},
            )
            if args.once:
                raise
        time.sleep(max(5, SCAN_INTERVAL))


if __name__ == "__main__":
    main()
