from app.backtesting.timeline import (
    Timeline,
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
            0,
            0,
            0,
            0,
            0,
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

    timeline = Timeline()

    timeline.load(
        create_data()
    )

    assert (
        timeline.current_index
        == 0
    )


def test_has_next():

    timeline = Timeline()

    timeline.load(
        create_data()
    )

    assert timeline.has_next()


def test_step():

    timeline = Timeline()

    timeline.load(
        create_data()
    )

    timeline.step()

    assert (
        timeline.current_index
        == 1
    )


def test_current_timestamp():

    timeline = Timeline()

    timeline.load(
        create_data()
    )

    assert (
        timeline.current_timestamp()
        == 0
    )

    timeline.step()

    assert (
        timeline.current_timestamp()
        == 15 * 60 * 1000
    )


def test_latest_15m():

    timeline = Timeline()

    timeline.load(
        create_data()
    )

    for _ in range(8):

        timeline.step()

    assert (
        timeline.latest_index(
            "15m"
        )
        == 8
    )


def test_latest_1h():

    timeline = Timeline()

    timeline.load(
        create_data()
    )

    for _ in range(8):

        timeline.step()

    #
    # 8 * 15min = 120min
    # τελευταίο κλεισμένο
    # 1h candle = index 2
    #

    assert (
        timeline.latest_index(
            "1h"
        )
        == 2
    )


def test_latest_4h():

    timeline = Timeline()

    timeline.load(
        create_data()
    )

    for _ in range(20):

        timeline.step()

    #
    # 20 * 15min = 300min
    # τελευταίο 4h candle
    # είναι στις 240min
    #

    assert (
        timeline.latest_index(
            "4h"
        )
        == 1
    )