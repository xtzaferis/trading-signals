import pandas as pd
import ta

from app.exchange.okx_client import OKXClient
from app.config.settings import (
    ENTRY_TIMEFRAME,
    CANDLE_LIMIT
)


class IndicatorEngine:

    def __init__(self):
        self.client = OKXClient()

    def get_dataframe(
        self,
        symbol: str,
        timeframe: str = ENTRY_TIMEFRAME,
        limit: int = CANDLE_LIMIT,
    ):

        candles = self.client.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit
        )

        df = pd.DataFrame(
            candles,
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]
        )

        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

        return df

    def calculate(self, symbol: str):

        df = self.get_dataframe(symbol)

        # ======================
        # Trend
        # ======================

        df["ema20"] = ta.trend.ema_indicator(df["close"], window=20)
        df["ema50"] = ta.trend.ema_indicator(df["close"], window=50)
        df["ema200"] = ta.trend.ema_indicator(df["close"], window=200)

        # EMA slope
        df["ema20_prev"] = df["ema20"].shift(1)

        # ======================
        # Momentum
        # ======================

        df["rsi"] = ta.momentum.rsi(
            df["close"],
            window=14
        )

        macd = ta.trend.MACD(df["close"])

        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_hist"] = macd.macd_diff()

        # ======================
        # Trend Strength
        # ======================

        df["adx"] = ta.trend.adx(
            df["high"],
            df["low"],
            df["close"]
        )

        # ======================
        # Volatility
        # ======================

        df["atr"] = ta.volatility.average_true_range(
            df["high"],
            df["low"],
            df["close"]
        )

        # ATR ως ποσοστό της τιμής
        df["atr_percent"] = (
            df["atr"] / df["close"]
        ) * 100

        # ======================
        # Volume
        # ======================

        df["volume_ma20"] = (
            df["volume"]
            .rolling(20)
            .mean()
        )

        # ======================
        # Bollinger Bands
        # ======================

        bb = ta.volatility.BollingerBands(
            close=df["close"],
            window=20,
            window_dev=2
        )

        df["bb_upper"] = bb.bollinger_hband()
        df["bb_middle"] = bb.bollinger_mavg()
        df["bb_lower"] = bb.bollinger_lband()

        return df.iloc[-1]