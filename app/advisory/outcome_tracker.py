from datetime import datetime, timedelta, timezone

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
        for index, candle in enumerate(eligible):
            outcome, exit_price = self._bar_outcome(signal, candle)
            if outcome is not None:
                resolved_at = datetime.fromtimestamp(candle[0] / 1000, timezone.utc)
                self._save(
                    signal,
                    resolved_at,
                    exit_price,
                    outcome,
                    eligible[: index + 1],
                )
                return True
        if now >= expiry and eligible:
            self._save(
                signal,
                expiry,
                float(eligible[-1][4]),
                "TIMEOUT",
                eligible,
            )
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
        candles: list,
    ) -> None:
        opened = datetime.fromisoformat(signal["generated_at"])
        actual_funding = self._actual_funding(signal["symbol"], opened, resolved_at)
        direction = signal["direction"]
        entry_reference = float(signal["reference_price"])
        if direction == "LONG":
            entry = entry_reference * (1 + ADVISORY_FUTURES_SLIPPAGE)
            exit_value = exit_price * (1 - ADVISORY_FUTURES_SLIPPAGE)
            gross = (exit_value - entry) / entry
            funding = actual_funding
        else:
            entry = entry_reference * (1 - ADVISORY_FUTURES_SLIPPAGE)
            exit_value = exit_price * (1 + ADVISORY_FUTURES_SLIPPAGE)
            gross = (entry - exit_value) / entry
            funding = -actual_funding
        fees = ADVISORY_FUTURES_FEE * (1 + exit_value / entry)
        net_return_pct = (gross - fees - funding) * 100
        metrics = self._excursion_metrics(signal, opened, resolved_at, candles)
        metrics["actual_funding_rate"] = actual_funding
        self.repository.resolve(
            signal["id"],
            resolved_at,
            exit_price,
            outcome,
            round(net_return_pct, 6),
            metrics=metrics,
        )

    def _actual_funding(
        self,
        symbol: str,
        opened: datetime,
        resolved_at: datetime,
    ) -> float:
        try:
            rates = self.client.get_funding_rates_range(
                symbol,
                int(opened.timestamp() * 1000),
                int(resolved_at.timestamp() * 1000),
            )
            if not isinstance(rates, list):
                return 0.0
            return sum(float(rate) for _, rate in rates)
        except (
            ccxt.NetworkError,
            ccxt.ExchangeError,
            AttributeError,
            TypeError,
            ValueError,
        ):
            return 0.0

    @classmethod
    def _excursion_metrics(
        cls,
        signal: dict,
        opened: datetime,
        resolved_at: datetime,
        candles: list,
    ) -> dict:
        entry = float(signal["reference_price"])
        direction = signal["direction"]
        highs = [float(candle[2]) for candle in candles]
        lows = [float(candle[3]) for candle in candles]
        if direction == "LONG":
            favorable = (max(highs, default=entry) / entry - 1) * 100
            adverse = (1 - min(lows, default=entry) / entry) * 100
        else:
            favorable = (1 - min(lows, default=entry) / entry) * 100
            adverse = (max(highs, default=entry) / entry - 1) * 100
        metrics = {
            "max_favorable_excursion_pct": round(max(0.0, favorable), 6),
            "max_adverse_excursion_pct": round(max(0.0, adverse), 6),
            "time_to_exit_minutes": round(
                max(0.0, (resolved_at - opened).total_seconds() / 60),
                2,
            ),
        }
        for minutes, key in (
            (15, "return_15m_pct"),
            (60, "return_1h_pct"),
            (240, "return_4h_pct"),
            (1440, "return_24h_pct"),
        ):
            metrics[key] = cls._horizon_return(
                direction,
                entry,
                opened,
                candles,
                minutes,
            )
        return metrics

    @staticmethod
    def _horizon_return(
        direction: str,
        entry: float,
        opened: datetime,
        candles: list,
        minutes: int,
    ) -> float | None:
        target = int((opened + timedelta(minutes=minutes)).timestamp() * 1000)
        candle = next(
            (item for item in candles if int(item[0]) + 300_000 >= target),
            None,
        )
        if candle is None:
            return None
        close = float(candle[4])
        raw = close / entry - 1 if direction == "LONG" else 1 - close / entry
        return round(raw * 100, 6)
