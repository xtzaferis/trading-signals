from datetime import datetime, timezone

from app.config.settings import (
    EMERGENCY_STOP,
    LIVE_ACCOUNT_SIZE,
    LIVE_CANARY_CONFIRMATION,
    LIVE_CANARY_ENABLED,
    LIVE_CANARY_ORDER_VALUE,
    LIVE_CANARY_STOP_LOSS_PCT,
    LIVE_CANARY_SYMBOL,
    LIVE_CANARY_TAKE_PROFIT_PCT,
    LIVE_TRADING_ENABLED,
    MAX_EXCHANGE_ORDER_VALUE,
    QUOTE_CURRENCY,
    TRADING_MODE,
)
from app.core.logger import logger
from app.exceptions import OrderValidationError, TradingModeError
from app.exchange.kraken_client import KrakenClient
from app.execution.kraken_live_broker import KrakenLiveBroker
from app.execution.kraken_order_gateway import KrakenOrderGateway
from app.live.preflight import check as preflight_check
from app.models.trade_plan import TradePlan
from app.trading.portfolio import Portfolio

REQUIRED_CONFIRMATION = "I_ACCEPT_REAL_MONEY_RISK"


def open_canary(
    client=None,
    gateway=None,
    broker=None,
) -> dict:
    """Open one explicitly authorized, exchange-protected Kraken canary."""
    _require_canary_gates()
    client = client or KrakenClient()
    preflight = preflight_check(client)
    if preflight["open_order_count"]:
        raise TradingModeError(
            "Canary requires zero pre-existing Kraken open orders."
        )

    ticker = client.get_ticker(LIVE_CANARY_SYMBOL)
    reference_price = float(ticker.get("ask") or ticker.get("last") or 0.0)
    if reference_price <= 0:
        raise OrderValidationError("Kraken returned no usable entry price.")
    stop_loss = reference_price * (1.0 - LIVE_CANARY_STOP_LOSS_PCT)
    stop_loss = client.price_to_precision(LIVE_CANARY_SYMBOL, stop_loss)
    take_profit = reference_price * (1.0 + LIVE_CANARY_TAKE_PROFIT_PCT)

    portfolio = Portfolio(initial_balance=LIVE_ACCOUNT_SIZE)
    gateway = gateway or KrakenOrderGateway(
        client,
        max_order_value=MAX_EXCHANGE_ORDER_VALUE,
    )
    broker = broker or KrakenLiveBroker(portfolio, gateway)
    available = broker.sync_balance()
    if available < LIVE_CANARY_ORDER_VALUE:
        raise OrderValidationError(
            f"Canary needs {LIVE_CANARY_ORDER_VALUE:.2f} {QUOTE_CURRENCY}; "
            f"only {available:.2f} is free."
        )
    if broker.positions.find_active(LIVE_CANARY_SYMBOL) is not None:
        raise TradingModeError("A persisted Kraken position is already active.")

    reconciliation = broker.reconcile()
    if not reconciliation.get("safe", False):
        raise TradingModeError(
            f"Kraken reconciliation is unsafe: {reconciliation}"
        )
    plan = TradePlan(
        symbol=LIVE_CANARY_SYMBOL,
        action="BUY",
        entry=reference_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        position_size=LIVE_CANARY_ORDER_VALUE,
        risk_reward=(
            LIVE_CANARY_TAKE_PROFIT_PCT / LIVE_CANARY_STOP_LOSS_PCT
        ),
    )
    position = broker.open(plan, datetime.now(timezone.utc))
    stored = broker.positions.find_active(LIVE_CANARY_SYMBOL)
    return {
        "symbol": LIVE_CANARY_SYMBOL,
        "quote_cost": LIVE_CANARY_ORDER_VALUE,
        "reference_price": reference_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "position_open": position is not None,
        "status": stored["status"] if stored else "UNKNOWN",
        "protection_status": (
            stored["protection_status"] if stored else None
        ),
    }


def _require_canary_gates() -> None:
    if TRADING_MODE != "live":
        raise TradingModeError("Canary requires TRADING_MODE=live.")
    if not LIVE_TRADING_ENABLED:
        raise TradingModeError("Canary requires LIVE_TRADING_ENABLED=true.")
    if EMERGENCY_STOP:
        raise TradingModeError("Canary requires EMERGENCY_STOP=false.")
    if not LIVE_CANARY_ENABLED:
        raise TradingModeError("Canary requires LIVE_CANARY_ENABLED=true.")
    if LIVE_CANARY_CONFIRMATION != REQUIRED_CONFIRMATION:
        raise TradingModeError(
            "Canary confirmation phrase is missing or incorrect."
        )
    if LIVE_CANARY_ORDER_VALUE > min(
        LIVE_ACCOUNT_SIZE, MAX_EXCHANGE_ORDER_VALUE
    ):
        raise TradingModeError("Canary value exceeds a configured safety cap.")


def main() -> None:
    logger.warning("KRAKEN REAL-MONEY CANARY")
    result = open_canary()
    logger.info(f"Symbol:            {result['symbol']}")
    logger.info(
        f"Order Value:       {result['quote_cost']:.2f} {QUOTE_CURRENCY}"
    )
    logger.info(f"Reference Price:   {result['reference_price']:.2f}")
    logger.info(f"Stop Loss:         {result['stop_loss']:.2f}")
    logger.info(f"Take Profit:       {result['take_profit']:.2f}")
    logger.info(f"Position Status:   {result['status']}")
    logger.info(
        f"Protection Status: {result['protection_status'] or 'pending fill'}"
    )
    logger.warning(
        "Keep app.live.monitor running until the canary is closed."
    )


if __name__ == "__main__":
    main()
