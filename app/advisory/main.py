import argparse

from app.advisory.service import EntryAdvisoryService
from app.config.settings import (
    ADVISORY_END_HOUR,
    ADVISORY_START_HOUR,
    ADVISORY_TIMEZONE,
)


def _number(value: float | None) -> str:
    if value is None:
        return "-"
    if abs(value) >= 1000:
        return f"{value:,.2f}"
    return f"{value:.6f}".rstrip("0").rstrip(".")


def print_report(report) -> None:
    print("=" * 96)
    print("READ-ONLY FUTURES ADVISORY - NO ORDER WILL BE SENT")
    print(f"Generated: {report.generated_at.isoformat()}")
    print("=" * 96)
    if not report.window_open and not report.forced:
        print(
            f"Trading window is closed. Run between {ADVISORY_START_HOUR:02d}:00 "
            f"and {ADVISORY_END_HOUR:02d}:00 {ADVISORY_TIMEZONE}."
        )
        return
    if report.forced and not report.window_open:
        print("Outside configured session: clock restriction bypassed by --force.")
    if not report.candidates:
        print("No markets could be evaluated.")
    else:
        header = (
            f"{'#':>2}  {'PAIR':<12} {'SIDE':<6} {'RISK':<7} {'SCORE':>5} "
            f"{'PRICE':>14} {'STOP':>14} {'TARGET':>14} {'NET R:R':>7}"
        )
        print(header)
        print("-" * len(header))
        for rank, candidate in enumerate(report.candidates, start=1):
            trade = candidate.trade
            print(
                f"{rank:>2}  {candidate.symbol:<12} {candidate.status:<6} "
                f"{candidate.risk:<7} {candidate.score:>5} "
                f"{_number(candidate.price):>14} "
                f"{_number(trade.stop_loss if trade else None):>14} "
                f"{_number(trade.take_profit if trade else None):>14} "
                f"{(f'{trade.net_risk_reward:.2f}' if trade else '-'):>7}"
            )
            print(f"    Reason: {candidate.reasons[0] if candidate.reasons else '-'}")
            context = candidate.derivatives
            if context is not None:
                funding = (
                    f"{context.funding_rate * 100:.4f}%"
                    if context.funding_rate is not None
                    else "-"
                )
                oi_change = (
                    f"{context.open_interest_change_pct:+.2f}%"
                    if context.open_interest_change_pct is not None
                    else "-"
                )
                ratio = (
                    f"{context.long_short_ratio:.2f}"
                    if context.long_short_ratio is not None
                    else "-"
                )
                taker = (
                    f"{context.taker_buy_sell_ratio:.2f}"
                    if context.taker_buy_sell_ratio is not None
                    else "-"
                )
                print(
                    f"    Pressure: {context.label} | funding={funding} | "
                    f"OI 5m={oi_change} | accounts L/S={ratio} | taker B/S={taker}"
                )
            if candidate.trade is not None:
                book = candidate.order_book or {}
                spread = _number(book.get("spread_bps"))
                imbalance = _number(book.get("imbalance"))
                deviation = _number(candidate.entry_deviation_pct)
                expiry = (
                    candidate.expires_at.isoformat(timespec="seconds")
                    if candidate.expires_at
                    else "-"
                )
                print(
                    f"    Execution: deviation={deviation}% | spread={spread} bps | "
                    f"book imbalance={imbalance} | valid until={expiry}"
                )
        if report.shortlist:
            print("\nTOP ACTIONABLE SETUPS (maximum two):")
            for candidate in report.shortlist:
                print(
                    f"- {candidate.symbol}: {candidate.status}, "
                    f"score={candidate.score}, risk={candidate.risk}"
                )
        else:
            print("\nTOP ACTIONABLE SETUPS: none; do not force a trade.")
    if report.errors:
        print("\nUnavailable markets:")
        for error in report.errors:
            print(f"- {error}")
    if not any(item.status in {"LONG", "SHORT"} for item in report.candidates):
        print("\nNo qualifying long or short right now. WAIT is a valid result.")
    print("\nConfirm price, spread and order details manually before trading.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only crypto futures direction advisory"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="scan outside the configured session (still never sends orders)",
    )
    args = parser.parse_args()
    print(
        "Starting keyless Binance market-data scan...",
        flush=True,
    )
    service = EntryAdvisoryService(progress=lambda message: print(message, flush=True))
    print_report(service.scan(force=args.force))


if __name__ == "__main__":
    main()
