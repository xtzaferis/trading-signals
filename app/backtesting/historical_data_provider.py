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

        self.index = 0

    def step(self):

        if self.index < len(self.candles):

            self.index += 1

    def has_next(self):

        return (
            self.index
            < len(self.candles)
        )

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