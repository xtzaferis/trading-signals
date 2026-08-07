from app.data.data_provider import DataProvider


class HistoricalDataProvider(DataProvider):

    def __init__(self):

        self.data = {
            "15m": [],
            "1h": [],
            "4h": [],
        }

        self.index = 200

    def load(
        self,
        data: dict,
    ):

        self.data = data

        self.index = 200

    def has_next(self) -> bool:

        return (
            self.index
            < len(self.data["15m"])
        )

    def step(self):

        if self.has_next():

            self.index += 1

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ):

        candles = self.data[
            timeframe
        ]

        #
        # Προσεγγιστική αντιστοίχιση
        # του 15m index στα μεγαλύτερα
        # timeframes.
        #

        if timeframe == "15m":

            index = self.index

        elif timeframe == "1h":

            index = max(
                50,
                self.index // 4,
            )

        elif timeframe == "4h":

            index = max(
                50,
                self.index // 16,
            )

        else:

            index = self.index

        start = max(
            0,
            index - limit,
        )

        return candles[
            start:index
        ]

    @property
    def current_candle(self):

        if self.index == 0:

            return None

        return self.data[
            "15m"
        ][
            self.index - 1
        ]

    @property
    def total(self):

        return len(
            self.data["15m"]
        )

    @property
    def progress(self):

        if self.total == 0:

            return 0.0

        return (
            self.index
            / self.total
        ) * 100