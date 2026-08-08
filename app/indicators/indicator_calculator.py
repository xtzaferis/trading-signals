import ta


class IndicatorCalculator:

    MIN_CANDLES = 200

    def calculate(
        self,
        df,
    ):

        df = df.copy()

        if len(df) < self.MIN_CANDLES:

            df["ema20"] = 0.0
            df["ema50"] = 0.0
            df["ema200"] = 0.0
            df["rsi"] = 0.0
            df["macd"] = 0.0
            df["macd_signal"] = 0.0
            df["adx"] = 0.0
            df["atr"] = 0.0

            return df

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

        macd = ta.trend.MACD(
            df["close"]
        )

        df["macd"] = (
            macd.macd()
        )

        df["macd_signal"] = (
            macd.macd_signal()
        )

        df["adx"] = ta.trend.adx(
            df["high"],
            df["low"],
            df["close"],
        )

        df["atr"] = (
            ta.volatility.average_true_range(
                df["high"],
                df["low"],
                df["close"],
            )
        )

        return df