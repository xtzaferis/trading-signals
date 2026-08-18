from app.advisory.correlation_selector import CorrelationAwareSelector
from app.advisory.service import AdvisoryCandidate


def candidate(symbol, direction, score):
    return AdvisoryCandidate(symbol, direction, score, 100.0)


def test_selector_skips_highly_correlated_same_direction_trade():
    candidates = (
        candidate("BTC/USDT", "LONG", 95),
        candidate("ETH/USDT", "LONG", 90),
        candidate("XRP/USDT", "SHORT", 85),
    )
    base = tuple(index / 100 for index in range(30))
    returns = {
        "BTC/USDT": base,
        "ETH/USDT": tuple(value * 2 for value in base),
        "XRP/USDT": tuple((-1) ** index / 100 for index in range(30)),
    }

    selected = CorrelationAwareSelector(0.8).select(candidates, returns, 2)

    assert [item.symbol for item in selected] == ["BTC/USDT", "XRP/USDT"]


def test_selector_allows_opposite_directions_on_positively_correlated_assets():
    candidates = (
        candidate("BTC/USDT", "LONG", 95),
        candidate("ETH/USDT", "SHORT", 90),
    )
    base = tuple(index / 100 for index in range(30))
    returns = {"BTC/USDT": base, "ETH/USDT": base}

    selected = CorrelationAwareSelector(0.8).select(candidates, returns, 2)

    assert selected == candidates


def test_selector_keeps_candidate_when_history_is_unavailable():
    candidates = (
        candidate("BTC/USDT", "LONG", 95),
        candidate("ETH/USDT", "LONG", 90),
    )

    selected = CorrelationAwareSelector(0.8).select(candidates, {}, 2)

    assert selected == candidates
