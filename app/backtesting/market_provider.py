from app.backtesting.historical_feed import (
    HistoricalFeed,
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
        feed: HistoricalFeed,
    ):

        self.feed = feed

        self.builder = (
            CandleDataFrameBuilder()
        )

        self.calculator = (
            IndicatorCalculator()
        )

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

        df = self.builder.build(
            candles
        )

        df = self.calculator.calculate(
            df
        )

        return df.iloc[-1]