from app.exceptions import OrderValidationError


def fee_cost_in_quote(order: dict, symbol: str, price: float) -> float:
    """Return all exchange fees in the market quote currency."""
    fees = order.get("fees")
    if not fees:
        fee = order.get("fee")
        fees = [fee] if fee else []
    base, quote = symbol.split("/", maxsplit=1)
    total = 0.0
    for fee in fees:
        if not fee:
            continue
        cost = abs(float(fee.get("cost") or 0.0))
        currency = str(fee.get("currency") or quote).upper()
        if currency == quote.upper():
            total += cost
        elif currency == base.upper():
            total += cost * price
        elif cost:
            raise OrderValidationError(
                f"Cannot normalize {currency} fee for {symbol}."
            )
    return total
