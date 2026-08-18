from datetime import datetime, timedelta, timezone
from math import ceil

import ccxt

from app.config.settings import (
    ADVISORY_FUTURES_FEE,
    ADVISORY_FUTURES_SLIPPAGE,
    MAX_POSITION_HOLD_HOURS,
)


class AdvisoryOutcomeTracker:
    """Resolve journaled advisory plans from completed futures candles."""

    def __init__(self, client, repository):
        self.client = client
        self.repository = repository

    def resolve_open(self, now: datetime | None = None) -> int:
        resolved = 0
        current = now or datetime.now(timezone.utc)
        for signal in self.repository.list_open():
            try:
                if self._resolve(signal, current):
                    resolved += 1
            except (ccxt.NetworkError, ccxt.ExchangeError, ValueError, TypeError):
                continue
        return resolved

    def _resolve(self, signal: dict, now: datetime) -> bool:
        opened = datetime.fromisoformat(signal["generated_at"])
        if opened.tzinfo is None:
            opened = opened.replace(tzinfo=timezone.utc)
        expiry = opened + timedelta(hours=MAX_POSITION_HOLD_HOURS)
        candles = self.client.get_ohlcv_since(
            signal["symbol"],
            "5m",
            int(opened.timestamp() * 1000),
            limit=MAX_POSITION_HOLD_HOURS * 12 + 2,
        )
        eligible = [
            candle for candle in candles if candle[0] <= int(expiry.timestamp() * 1000)
        ]
        for candle in eligible:
            outcome, exit_price = self._bar_outcome(signal, candle)
            if outcome is not None:
                resolved_at = datetime.fromtimestamp(candle[0] / 1000, timezone.utc)
                self._save(signal, resolved_at, exit_price, outcome)
                return True
        if now >= expiry and eligible:
            self._save(signal, expiry, float(eligible[-1][4]), "TIMEOUT")
            return True
        return False

    @staticmethod
    def _bar_outcome(signal: dict, candle: list) -> tuple[str | None, float | None]:
        high, low = float(candle[2]), float(candle[3])
        stop, target = float(signal["stop_loss"]), float(signal["take_profit"])
        if signal["direction"] == "LONG":
            stop_hit, target_hit = low <= stop, high >= target
        else:
            stop_hit, target_hit = high >= stop, low <= target
        if stop_hit:
            return "STOP", stop
        if target_hit:
            return "TARGET", target
        return None, None

    def _save(
        self,
        signal: dict,
        resolved_at: datetime,
        exit_price: float,
        outcome: str,
    ) -> None:
        opened = datetime.fromisoformat(signal["generated_at"])
        hours = max(0.0, (resolved_at - opened).total_seconds() / 3600)
        funding_periods = ceil(hours / 8) if hours else 0
        funding_rate = float(signal.get("funding_rate") or 0.0)
        direction = signal["direction"]
        entry_reference = float(signal["reference_price"])
        if direction == "LONG":
            entry = entry_reference * (1 + ADVISORY_FUTURES_SLIPPAGE)
            exit_value = exit_price * (1 - ADVISORY_FUTURES_SLIPPAGE)
            gross = (exit_value - entry) / entry
            funding = funding_rate * funding_periods
        else:
            entry = entry_reference * (1 - ADVISORY_FUTURES_SLIPPAGE)
            exit_value = exit_price * (1 + ADVISORY_FUTURES_SLIPPAGE)
            gross = (entry - exit_value) / entry
            funding = -funding_rate * funding_periods
        fees = ADVISORY_FUTURES_FEE * (1 + exit_value / entry)
        net_return_pct = (gross - fees - funding) * 100
        self.repository.resolve(
            signal["id"],
            resolved_at,
            exit_price,
            outcome,
            round(net_return_pct, 6),
        )
