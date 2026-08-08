from app.backtesting.data_feed import DataFeed


class LiveFeed(DataFeed):

    def __init__(self):

        self.current_snapshot = None

    def update(
        self,
        snapshot: dict,
    ):

        self.current_snapshot = snapshot

    def has_next(self) -> bool:

        return (
            self.current_snapshot
            is not None
        )

    def next(self) -> dict:

        snapshot = (
            self.current_snapshot
        )

        self.current_snapshot = None

        return snapshot