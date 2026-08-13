from typing import Any

from app.backtesting.data_feed import DataFeed
from app.indicators.indicator_calculator import IndicatorCalculator


class HistoricalFeed(DataFeed):

    WINDOW_SIZE = IndicatorCalculator.MIN_CANDLES

    def __init__(self):

        self.data: dict[str, Any] = {}

        self.timeline: Any = None


    def load(
        self,
        data: dict[str, Any],
    ):

        self.data = data

        from app.backtesting.timeline import Timeline

        self.timeline = Timeline()

        self.timeline.load(
            data
        )


    def has_next(
        self,
    ) -> bool:

        return bool(
            self.timeline.has_next()
        )


    def validate_candles(
        self,
        candles: list,
        timeframe: str,
    ):

        for candle in candles:

            if (
                not isinstance(candle, list)
                or len(candle) != 6
            ):

                raise ValueError(
                    f"Invalid candle format "
                    f"in {timeframe}: {candle}"
                )


    def next(
        self,
    ) -> dict:


        regime_index = (
            self.timeline.latest_index(
                "1d"
            )
        )


        trend_index = (
            self.timeline.latest_index(
                "4h"
            )
        )


        confirm_index = (
            self.timeline.latest_index(
                "1h"
            )
        )


        entry_index = (
            self.timeline.latest_index(
                "15m"
            )
        )


        regime_candles = (
            self._window(
                "1d",
                regime_index,
            )
        )


        trend_candles = (
            self._window(
                "4h",
                trend_index,
            )
        )


        confirm_candles = (
            self._window(
                "1h",
                confirm_index,
            )
        )


        entry_candles = (
            self._window(
                "15m",
                entry_index,
            )
        )


        #
        # Validate before sending downstream
        #

        self.validate_candles(
            regime_candles,
            "1d",
        )

        self.validate_candles(
            trend_candles,
            "4h",
        )

        self.validate_candles(
            confirm_candles,
            "1h",
        )

        self.validate_candles(
            entry_candles,
            "15m",
        )


        snapshot = {

            "regime": {

                "candles": regime_candles,

            },

            "trend": {

                "candles": trend_candles,

            },


            "confirm": {

                "candles": confirm_candles,

            },


            "entry": {

                "candles": entry_candles,

            },


            "timestamp": (
                self.timeline.current_timestamp()
            ),
        }


        #
        # HistoricalFeed owns movement
        #

        self.timeline.step()


        return snapshot


    def _window(
        self,
        timeframe: str,
        latest_index: int,
    ) -> list:

        if latest_index < 0:
            return []

        start = max(
            0,
            latest_index + 1 - self.WINDOW_SIZE,
        )
        return self.data[timeframe][
            start: latest_index + 1
        ]
