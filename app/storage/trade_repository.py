from app.models.trade_record import (
    TradeRecord,
)
from app.storage.database import (
    Database,
)


class TradeRepository:

    def __init__(self):

        self.database = Database()

    def save(
        self,
        trade: TradeRecord,
    ):

        self.database.execute(
            """
            INSERT INTO trades
            (
                symbol,
                entry_price,
                exit_price,
                quantity,
                opened_at,
                closed_at,
                exit_reason,
                pnl
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade.symbol,
                trade.entry_price,
                trade.exit_price,
                trade.quantity,
                trade.opened_at.isoformat(),
                trade.closed_at.isoformat(),
                trade.exit_reason,
                trade.pnl,
            ),
        )

    def get_all(self):

        cursor = self.database.execute(
            """
            SELECT
                symbol,
                entry_price,
                exit_price,
                quantity,
                opened_at,
                closed_at,
                exit_reason,
                pnl

            FROM trades

            ORDER BY id ASC
            """
        )

        return cursor.fetchall()