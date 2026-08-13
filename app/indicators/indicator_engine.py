from app.config.settings import (
    CANDLE_LIMIT,
    ENTRY_TIMEFRAME,
    REGIME_TIMEFRAME,
)
from app.data.data_service import (
    DataService,
)
from app.indicators.candle_dataframe_builder import (
    CandleDataFrameBuilder,
)
from app.indicators.indicator_calculator import (
    IndicatorCalculator,
)


class IndicatorEngine:

    def __init__(
        self,
        data_service=None,
    ):

        self.data_service = (
            data_service
            or DataService()
        )

        self.builder = (
            CandleDataFrameBuilder()
        )

        self.calculator = (
            IndicatorCalculator()
        )

    def get_dataframe(
        self,
        symbol: str,
        timeframe: str = ENTRY_TIMEFRAME,
        limit: int = CANDLE_LIMIT,
    ):

        candles = (
            self.data_service.get_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
            )
        )

        return self.builder.build(
            candles
        )

    def calculate(
        self,
        symbol: str,
        timeframe: str = ENTRY_TIMEFRAME,
    ):

        df = self.get_dataframe(
            symbol=symbol,
            timeframe=timeframe,
        )

        df = self.calculator.calculate(
            df
        )

        return df.iloc[-1]

    def calculate_multi_timeframe(
        self,
        symbol: str,
    ):

        return {

            "regime": self.calculate(
                symbol=symbol,
                timeframe=REGIME_TIMEFRAME,
            ),

            "trend": self.calculate(
                symbol=symbol,
                timeframe="4h",
            ),

            "confirm": self.calculate(
                symbol=symbol,
                timeframe="1h",
            ),

            "entry": self.calculate(
                symbol=symbol,
                timeframe="15m",
            ),
        }
