import pytest

from app.backtesting.validation import ChronologicalValidator


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
