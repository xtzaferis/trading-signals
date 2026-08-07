from app.backtesting.data_feed import (
    DataFeed,
)
from app.backtesting.timeline import (
    Timeline,
)


class HistoricalFeed(DataFeed):

    def __init__(self):

        self.timeline = (
            Timeline()
        )

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

        market = {

            "trend": self.data[
                "4h"
            ][
                : trend_index + 1
            ],

            "confirm": self.data[
                "1h"
            ][
                : confirm_index + 1
            ],

            "entry": self.data[
                "15m"
            ][
                : entry_index + 1
            ],
        }

        self.timeline.step()

        return market