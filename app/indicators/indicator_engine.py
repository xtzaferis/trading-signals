import pandas as pd
import ta

from app.config.settings import CANDLE_LIMIT, ENTRY_TIMEFRAME
from app.data.data_service import DataService


class IndicatorEngine:

    def __init__(self):
        self.data_service = DataService()

    def get_dataframe(
        self,
        symbol: str,
        timeframe: str = ENTRY_TIMEFRAME,
        limit: int = CANDLE_LIMIT,
    ):

        candles = self.data_service.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
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
            df[column] = pd.to_numeric(df[column])

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

        df["ema20"] = ta.trend.ema_indicator(
            df["close"],
            window=20,
        )

        df["ema50"] = ta.trend.ema_indicator(
            df["close"],
            window=50,
        )

        df["ema200"] = ta.trend.ema_indicator(
            df["close"],
            window=200,
        )

        df["rsi"] = ta.momentum.rsi(
            df["close"],
            window=14,
        )

        macd = ta.trend.MACD(df["close"])

        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()

        df["adx"] = ta.trend.adx(
            df["high"],
            df["low"],
            df["close"],
        )

        df["atr"] = ta.volatility.average_true_range(
            df["high"],
            df["low"],
            df["close"],
        )

        return df.iloc[-1]