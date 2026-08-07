from app.backtesting.data_feed import (
    DataFeed,
)
from app.backtesting.timeline import (
    Timeline,
)
from app.models.market_snapshot import (
    MarketSnapshot,
)


class HistoricalFeed(DataFeed):

    def __init__(self):

        self.timeline = Timeline()

        self.data = {}

    def load(
        self,
        data: dict,
    ):

        self.data = data

        self.timeline.load(
            data
        )

    def has_next(
        self,
    ) -> bool:

        return self.timeline.has_next()

    def next(
        self,
    ) -> dict:

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

        current = self.data[
            "15m"
        ][
            entry_index
        ]

        snapshot = {

            "trend": {

                "timeframe": "4h",

                "candles": self.data[
                    "4h"
                ][
                    : trend_index + 1
                ],
            },

            "confirm": {

                "timeframe": "1h",

                "candles": self.data[
                    "1h"
                ][
                    : confirm_index + 1
                ],
            },

            "entry": {

                "timeframe": "15m",

                "candles": self.data[
                    "15m"
                ][
                    : entry_index + 1
                ],

                "current": MarketSnapshot(
                    timestamp=current[0],
                    open=current[1],
                    high=current[2],
                    low=current[3],
                    close=current[4],
                    volume=current[5],
                ),
            },
        }

        self.timeline.step()

        return snapshot