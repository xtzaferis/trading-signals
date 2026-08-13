import pandas as pd
import ta


class IndicatorCalculator:

    MIN_CANDLES = 200

    def calculate(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:

        df = df.copy()

        # Important:
        # HistoricalFeed creates dataframe slices.
        # Reset index before ta indicators.
        df = (
            df.reset_index(
                drop=True
            )
        )

        required = (
            "open",
            "high",
            "low",
            "close",
            "volume",
        )

        for column in required:

            if column not in df.columns:

                df[column] = 0.0


        # Ensure numeric data

        for column in required:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )


        df = df.fillna(0.0)


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


        # -------------------------
        # EMA
        # -------------------------

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


        # -------------------------
        # RSI
        # -------------------------

        df["rsi"] = ta.momentum.rsi(
            df["close"],
            window=14,
        )


        # -------------------------
        # MACD
        # -------------------------

        macd = ta.trend.MACD(
            df["close"],
        )

        df["macd"] = macd.macd()

        df["macd_signal"] = (
            macd.macd_signal()
        )

        df["macd_histogram"] = (
            df["macd"]
            - df["macd_signal"]
        )

        df["macd_histogram_prev"] = (
            df["macd_histogram"].shift(1)
        )


        # -------------------------
        # ADX
        # -------------------------

        try:

            df["adx"] = ta.trend.adx(
                high=df["high"],
                low=df["low"],
                close=df["close"],
                window=14,
            )

        except (
            ValueError,
            KeyError,
            TypeError,
        ):

            df["adx"] = 0.0


        # -------------------------
        # ATR
        # -------------------------

        df["atr"] = self._calculate_atr(
            df
        )


        # -------------------------
        # Causal strategy features
        # -------------------------

        df["ema20_slope_pct"] = (
            df["ema20"].pct_change(3)
        )

        df["close_prev"] = (
            df["close"].shift(1)
        )

        df["ema20_prev"] = (
            df["ema20"].shift(1)
        )

        df["rsi_prev"] = (
            df["rsi"].shift(1)
        )

        df["volume_sma20"] = (
            df["volume"]
            .shift(1)
            .rolling(20)
            .mean()
        )

        df["volume_ratio"] = (
            df["volume"]
            / df["volume_sma20"]
        )

        df["breakout_high_20"] = (
            df["high"]
            .shift(1)
            .rolling(20)
            .max()
        )

        df["atr_pct"] = (
            df["atr"]
            / df["close"]
        )


        # -------------------------
        # Final cleanup
        # -------------------------

        df = df.fillna(0.0)


        return df



    def _calculate_atr(
        self,
        df: pd.DataFrame,
        period: int = 14,
    ) -> pd.Series:


        high_low = (
            df["high"]
            -
            df["low"]
        )


        high_close = (
            df["high"]
            -
            df["close"].shift()
        ).abs()


        low_close = (
            df["low"]
            -
            df["close"].shift()
        ).abs()


        true_range = pd.concat(
            [
                high_low,
                high_close,
                low_close,
            ],
            axis=1,
        ).max(
            axis=1
        )


        atr = (
            true_range
            .rolling(
                period
            )
            .mean()
        )


        return atr.fillna(0.0)
