

class Timeline:

    def __init__(self):

        self.data = {}

        self.current_index = 0

    def load(
        self,
        data: dict,
    ):

        self.data = data

        self.current_index = 0

    def has_next(
        self,
    ) -> bool:

        return (
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

        return candle[0]

    def latest_index(
        self,
        timeframe: str,
    ) -> int:

        target = (
            self.current_timestamp()
        )

        candles = self.data[
            timeframe
        ]

        latest = 0

        for index, candle in enumerate(
            candles
        ):

            if candle[0] <= target:

                latest = index

            else:

                break

        return latest