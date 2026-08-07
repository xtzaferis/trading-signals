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

        df = pd.DataFrame(
            candles,
            columns=self.COLUMNS,
        )

        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            unit="ms",
        )

        for column in self.NUMERIC_COLUMNS:

            df[column] = pd.to_numeric(
                df[column]
            )

        return df