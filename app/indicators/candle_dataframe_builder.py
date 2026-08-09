from typing import ClassVar

import pandas as pd


class CandleDataFrameBuilder:

    COLUMNS: ClassVar[tuple[str, ...]] = (
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    )

    NUMERIC_COLUMNS: ClassVar[tuple[str, ...]] = (
        "open",
        "high",
        "low",
        "close",
        "volume",
    )


    def build(
        self,
        candles: list,
    ) -> pd.DataFrame:

        if not candles:

            return pd.DataFrame(
                columns=self.COLUMNS
            )


        df = pd.DataFrame(
            candles,
            columns=self.COLUMNS,
        )


        # -------------------------
        # DEBUG TIMESTAMP
        # -------------------------

        print(
            "TIMESTAMP DEBUG:",
            df["timestamp"].head().tolist(),
            type(df["timestamp"].iloc[0]),
        )


        # -------------------------
        # TIMESTAMP NORMALIZATION
        # -------------------------

        timestamp_numeric = pd.to_numeric(
            df["timestamp"],
            errors="coerce",
        )


        # milliseconds timestamps

        df["timestamp"] = pd.to_datetime(
            timestamp_numeric,
            unit="ms",
            errors="coerce",
        )


        # fallback for string timestamps

        mask = df["timestamp"].isna()

        if mask.any():

            df.loc[mask, "timestamp"] = pd.to_datetime(
                df.loc[mask, "timestamp"],
                errors="coerce",
            )


        # -------------------------
        # NUMERIC VALUES
        # -------------------------

        for column in self.NUMERIC_COLUMNS:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )


        # -------------------------
        # REMOVE BAD ROWS
        # -------------------------

        df = df.dropna(
            subset=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        )


        # -------------------------
        # SORT
        # -------------------------

        df = (
            df
            .sort_values(
                "timestamp"
            )
            .reset_index(
                drop=True
            )
        )


        return df