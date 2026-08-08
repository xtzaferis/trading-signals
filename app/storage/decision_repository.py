from datetime import datetime

from app.storage.database import (
    Database,
)


class DecisionRepository:

    def __init__(self):

        self.database = Database()

    def save(
        self,
        timestamp: datetime,
        symbol: str,
        price: float,
        score: int,
        action: str,
    ):

        self.database.execute(
            """
            INSERT INTO decisions
            (
                timestamp,
                symbol,
                price,
                score,
                action
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                timestamp.isoformat(),
                symbol,
                price,
                score,
                action,
            ),
        )