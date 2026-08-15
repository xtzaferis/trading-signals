import pytest

from app.backtesting.validation import ChronologicalValidator, ValidationCriteria
from app.models.statistics_report import StatisticsReport


def test_split_timestamp_uses_common_history():
    data = {
        "BTC/USDC": {
            "15m": [
                [0, 1, 1, 1, 1, 1],
                [1_000_000_000, 1, 1, 1, 1, 1],
            ]
        },
        "ETH/USDC": {
            "15m": [
                [100_000_000, 1, 1, 1, 1, 1],
                [900_000_000, 1, 1, 1, 1, 1],
            ]
        },
    }

    split = ChronologicalValidator._split_timestamp(data, 0.5)

    expected_start = 100_000_000 + 200 * 15 * 60 * 1000
    expected_end = 900_000_000 + 15 * 60 * 1000
    assert split == int(expected_start + (expected_end - expected_start) * 0.5)


def test_split_rejects_missing_entry_history():
    with pytest.raises(ValueError):
        ChronologicalValidator._split_timestamp({}, 0.7)


def test_validation_criteria_rejects_small_or_unprofitable_samples():
    report = StatisticsReport(
        trades=17,
        profit_factor=1.43,
        expectancy=0.88,
        max_drawdown=1.0,
    )

    failures = ValidationCriteria(min_trades=30).evaluate(report)

    assert failures == ["trades 17 < required 30"]


def test_validation_criteria_accepts_robust_out_of_sample_result():
    report = StatisticsReport(
        trades=50,
        profit_factor=1.5,
        expectancy=0.5,
        max_drawdown=4.0,
    )

    assert ValidationCriteria().evaluate(report) == []
