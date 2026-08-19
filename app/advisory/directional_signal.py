from dataclasses import dataclass

from app.advisory.derivatives_context import DerivativesContext
from app.config.settings import MIN_SCORE


@dataclass(frozen=True)
class DirectionalSignal:
    symbol: str
    direction: str
    score: int
    reasons: tuple[str, ...]


class DirectionalSignalEngine:
    """Use 1h/15m/5m as the entry gate and higher periods as context."""

    def evaluate(
        self,
        symbol: str,
        data: dict,
        context: DerivativesContext | None = None,
    ) -> DirectionalSignal:
        context_note = "Derivatives pressure unavailable"
        if context is not None:
            context_note = f"Derivatives pressure: {context.label}"

        evaluations = {}
        for direction in ("LONG", "SHORT"):
            score = self._score(data, direction)
            if context is not None:
                alignment = 1 if direction == "LONG" else -1
                score = max(
                    0,
                    min(100, score + 5 * context.pressure * alignment),
                )
            evaluations[direction] = (
                score,
                self._entry_failure(data, direction),
            )

        qualified = {
            direction: score
            for direction, (score, failure) in evaluations.items()
            if failure is None and score >= MIN_SCORE
        }
        if not qualified:
            direction = max(
                evaluations,
                key=lambda candidate: evaluations[candidate][0],
            )
            score, failure = evaluations[direction]
            reason = failure or f"{direction.title()} score below {MIN_SCORE}"
            return DirectionalSignal(symbol, "WAIT", score, (reason, context_note))

        direction = max(qualified, key=qualified.get)
        score = qualified[direction]

        setup = (
            "Trend-aligned"
            if self._regime_aligned(data, direction)
            else "Counter-trend"
        )
        return DirectionalSignal(
            symbol,
            direction,
            score,
            (
                f"{setup} {direction.lower()} confirmed on 1h/15m/5m",
                context_note,
            ),
        )

    @classmethod
    def _score(cls, data: dict, direction: str) -> int:
        sign = 1 if direction == "LONG" else -1
        regime, trend = data["regime"], data["trend"]
        confirm, entry = data["confirm"], data["entry"]
        trigger = data["trigger"]
        score = 0
        score += 5 if sign * (regime["close"] - regime["ema200"]) > 0 else 0
        score += 5 if sign * regime["ema20_slope_pct"] > 0 else 0
        score += 5 if sign * (trend["close"] - trend["ema200"]) > 0 else 0
        score += 5 if sign * (trend["ema20"] - trend["ema50"]) > 0 else 0
        score += 5 if sign * trend["ema20_slope_pct"] > 0 else 0
        score += cls._timeframe_score(confirm, direction, 25)
        score += cls._timeframe_score(entry, direction, 30)
        score += cls._timeframe_score(trigger, direction, 20)
        return min(100, score)

    @staticmethod
    def _timeframe_score(row, direction: str, weight: int) -> int:
        sign = 1 if direction == "LONG" else -1
        checks = [
            sign * (row["close"] - row["ema20"]) > 0,
            sign * row["macd_histogram"] > 0,
            (42 <= row["rsi"] <= 70)
            if direction == "LONG"
            else (30 <= row["rsi"] <= 58),
            row.get("adx", 0) >= 15,
        ]
        portions = (0.35, 0.30, 0.20, 0.15)
        return round(
            weight * sum(portion for portion, passed in zip(portions, checks) if passed)
        )

    @staticmethod
    def _entry_failure(data: dict, direction: str) -> str | None:
        sign = 1 if direction == "LONG" else -1
        for label, row in (
            ("1h", data["confirm"]),
            ("15m", data["entry"]),
            ("5m", data["trigger"]),
        ):
            if not (
                sign * (row["close"] - row["ema20"]) > 0
                and sign * row["macd_histogram"] > 0
            ):
                return f"{label} {direction.lower()} timing is not confirmed"
        if data["entry"].get("adx", 0) < 15:
            return "15m trend strength is too low"
        if data["entry"].get("atr_pct", 0) < 0.0005:
            return "15m volatility is too low"
        return None

    @staticmethod
    def _regime_aligned(data: dict, direction: str) -> bool:
        sign = 1 if direction == "LONG" else -1
        return (
            sign * (data["regime"]["close"] - data["regime"]["ema200"]) > 0
            and sign * (data["trend"]["close"] - data["trend"]["ema200"]) > 0
        )
