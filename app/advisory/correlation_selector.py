import numpy as np


class CorrelationAwareSelector:
    """Avoid shortlisting multiple expressions of effectively the same bet."""

    def __init__(self, max_correlation: float):
        self.max_correlation = max_correlation

    def select(self, candidates, returns_by_symbol: dict, limit: int) -> tuple:
        selected = []
        for candidate in candidates:
            if candidate.status not in {"LONG", "SHORT"}:
                continue
            if all(
                not self._same_exposure(candidate, existing, returns_by_symbol)
                for existing in selected
            ):
                selected.append(candidate)
            if len(selected) == limit:
                break
        return tuple(selected)

    def _same_exposure(self, candidate, existing, returns_by_symbol: dict) -> bool:
        first = returns_by_symbol.get(candidate.symbol)
        second = returns_by_symbol.get(existing.symbol)
        if first is None or second is None:
            return False
        size = min(len(first), len(second))
        if size < 20:
            return False
        correlation = float(np.corrcoef(first[-size:], second[-size:])[0, 1])
        if not np.isfinite(correlation):
            return False
        first_sign = 1 if candidate.status == "LONG" else -1
        second_sign = 1 if existing.status == "LONG" else -1
        effective_correlation = correlation * first_sign * second_sign
        return effective_correlation >= self.max_correlation
