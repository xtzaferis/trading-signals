class CandlePlayer:

    def __init__(self):

        self.candles = []

        self.index = 0

    def load(
        self,
        candles: list,
    ):

        self.candles = candles

        self.index = 0

    def reset(self):

        self.index = 0

    def has_next(self) -> bool:

        return bool(
            self.index
            < len(self.candles)
        )

    def next(self):

        if not self.has_next():
            return None

        candle = self.candles[
            self.index
        ]

        self.index += 1

        return candle

    @property
    def current(self):

        if self.index == 0:
            return None

        return self.candles[
            self.index - 1
        ]

    @property
    def progress(self) -> float:

        if not self.candles:
            return 0.0

        return float(
            (
                self.index
                / len(self.candles)
            ) * 100
        )