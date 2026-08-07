import pandas as pd

from app.config.settings import (
    CANDLE_LIMIT,
    ENTRY_TIMEFRAME,
)
from app.data.data_service import DataService
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

        df = pd.DataFrame(
            candles,
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ],
        )

        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            unit="ms",
        )

        numeric_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        for column in numeric_columns:

            df[column] = pd.to_numeric(
                df[column]
            )

        return df

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