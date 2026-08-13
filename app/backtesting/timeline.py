from bisect import bisect_right
from typing import ClassVar


class Timeline:

    TIMEFRAME_MS: ClassVar[dict[str, int]] = {
        "15m": 15 * 60 * 1000,
        "1h": 60 * 60 * 1000,
        "4h": 4 * 60 * 60 * 1000,
        "1d": 24 * 60 * 60 * 1000,
    }

    def __init__(self):

        self.data = {}
        self.close_timestamps = {}
        self.current_index = 0


    def load(
        self,
        data: dict,
    ):

        self.data = data
        self.close_timestamps = {
            timeframe: [
                candle[0]
                + self.TIMEFRAME_MS[timeframe]
                for candle in candles
            ]
            for timeframe, candles in data.items()
        }
        self.current_index = 0


    def has_next(
        self,
    ) -> bool:

        return bool(
            self.current_index
            < len(self.data["15m"])
        )


    def step(
        self,
    ):

        self.current_index += 1


    def current_timestamp(
        self,
    ):

        candle = self.data[
            "15m"
        ][
            self.current_index
        ]

        # OHLCV timestamps identify the candle's opening time. Its final OHLC
        # values only become available when the candle closes.
        return (
            candle[0]
            + self.TIMEFRAME_MS["15m"]
        )


    def latest_index(
        self,
        timeframe: str,
    ) -> int:

        target = self.current_timestamp()

        return (
            bisect_right(
                self.close_timestamps[timeframe],
                target,
            )
            - 1
        )
