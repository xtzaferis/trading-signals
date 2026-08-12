from app.backtesting.data_feed import (
    DataFeed,
)
from app.indicators.candle_dataframe_builder import (
    CandleDataFrameBuilder,
)
from app.indicators.indicator_calculator import (
    IndicatorCalculator,
)


class MarketProvider:


    def __init__(
        self,
        feed: DataFeed,
    ):

        self.feed = feed

        self.builder = (
            CandleDataFrameBuilder()
        )

        self.calculator = (
            IndicatorCalculator()
        )

        self.cache = {}

        self.precomputed = {}

        self._precompute_indicators()


    def _precompute_indicators(self):

        data = getattr(
            self.feed,
            "data",
            {},
        )

        if not isinstance(data, dict):
            return

        timeframe_keys = {
            "trend": "4h",
            "confirm": "1h",
            "entry": "15m",
        }

        for label, data_key in timeframe_keys.items():
            candles = data.get(data_key, [])
            if not candles:
                continue

            df = self.builder.build(candles)
            df = self.calculator.calculate(df)

            for raw_candle, (_, row) in zip(
                candles,
                df.iterrows(),
                strict=False,
            ):
                self.precomputed[
                    (label, raw_candle[0])
                ] = row


    def has_next(
        self,
    ) -> bool:

        return self.feed.has_next()



    def next(
        self,
    ) -> tuple[dict, dict]:


        snapshot = (
            self.feed.next()
        )


        market = {

            "trend": self.calculate(
                snapshot["trend"]["candles"],
                "trend",
            ),


            "confirm": self.calculate(
                snapshot["confirm"]["candles"],
                "confirm",
            ),


            "entry": self.calculate(
                snapshot["entry"]["candles"],
                "entry",
            ),
        }


        return (
            market,
            snapshot,
        )



    def calculate(
        self,
        candles: list,
        timeframe: str = "default",
    ):


        if not candles:

            return None


        #
        # Need enough candles for indicators
        #

        if len(candles) < self.calculator.MIN_CANDLES:

            return None



        #
        # Cache by latest candle timestamp
        #

        key = (
            timeframe,
            candles[-1][0],
        )


        if key in self.precomputed:
            return self.precomputed[key]


        if key in self.cache:

            return self.cache[key]



        df = self.builder.build(
            candles
        )


        if len(df) < self.calculator.MIN_CANDLES:

            return None



        df = self.calculator.calculate(
            df
        )


        result = (
            df.iloc[-1]
        )


        self.cache[key] = result


        return result
