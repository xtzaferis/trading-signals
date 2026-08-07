from app.backtesting.historical_feed import (
    HistoricalFeed,
)


def create_candles(
    count: int,
    step_ms: int,
):

    candles = []

    timestamp = 0

    for _ in range(count):

        candles.append([
            timestamp,
            1,
            2,
            0,
            1,
            100,
        ])

        timestamp += step_ms

    return candles


def create_data():

    return {

        "15m": create_candles(
            100,
            15 * 60 * 1000,
        ),

        "1h": create_candles(
            25,
            60 * 60 * 1000,
        ),

        "4h": create_candles(
            10,
            4 * 60 * 60 * 1000,
        ),
    }


def test_load():

    feed = HistoricalFeed()

    feed.load(
        create_data()
    )

    assert feed.has_next()


def test_next_returns_snapshot():

    feed = HistoricalFeed()

    feed.load(
        create_data()
    )

    snapshot = feed.next()

    assert "trend" in snapshot
    assert "confirm" in snapshot
    assert "entry" in snapshot


def test_snapshot_contains_candles():

    feed = HistoricalFeed()

    feed.load(
        create_data()
    )

    snapshot = feed.next()

    assert len(
        snapshot["trend"]["candles"]
    ) > 0

    assert len(
        snapshot["confirm"]["candles"]
    ) > 0

    assert len(
        snapshot["entry"]["candles"]
    ) > 0


def test_timeline_moves_forward():

    feed = HistoricalFeed()

    feed.load(
        create_data()
    )

    first = feed.next()

    second = feed.next()

    assert (
        len(second["entry"]["candles"])
        >
        len(first["entry"]["candles"])
    )