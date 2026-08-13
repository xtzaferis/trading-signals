from app.config.settings import (
    MIN_BARS_AFTER_STOP_LOSS,
    MIN_BARS_BETWEEN_TRADES,
)


def cooldown_bars_for_exit(exit_reason: str | None) -> int:
    if exit_reason == "STOP_LOSS":
        return MIN_BARS_AFTER_STOP_LOSS

    return MIN_BARS_BETWEEN_TRADES
