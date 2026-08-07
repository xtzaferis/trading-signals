from app.data.data_provider import DataProvider


class HistoricalDataProvider(DataProvider):

    def __init__(self):

        self.candles = []

        self.index = 0

    def load(
        self,
        candles: list,
    ):

        self.candles = candles

        # Ξεκινάμε όταν υπάρχουν αρκετά
        # candles για όλους τους indicators.
        self.index = 200

    def has_next(self) -> bool:

        return (
            self.index
            < len(self.candles)
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

        start = max(
            0,
            self.index - limit,
        )

        return self.candles[
            start:self.index
        ]

    @property
    def current_candle(self):

        if self.index == 0:

            return None

        return self.candles[
            self.index - 1
        ]

    @property
    def total(self):

        return len(
            self.candles
        )

    @property
    def progress(self):

        if self.total == 0:

            return 0.0

        return (
            self.index
            / self.total
        ) * 100