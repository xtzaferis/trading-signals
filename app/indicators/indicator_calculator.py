import ta


class IndicatorCalculator:

    def calculate(self, df):

        df = df.copy()

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

        df["macd"] = macd.macd()

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