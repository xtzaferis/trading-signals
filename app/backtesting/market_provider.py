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
                snapshot["trend"]["candles"]
            ),


            "confirm": self.calculate(
                snapshot["confirm"]["candles"]
            ),


            "entry": self.calculate(
                snapshot["entry"]["candles"]
            ),
        }


        return (
            market,
            snapshot,
        )



    def calculate(
        self,
        candles: list,
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
            candles[-1][0]
        )


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