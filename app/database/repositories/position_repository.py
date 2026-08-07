from app.database.database import Database
from app.models.position import Position


class PositionRepository:

    def __init__(self):

        self.database = Database()

    def save(
        self,
        position: Position,
    ):

        with self.database.connect() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO positions (

                    symbol,
                    entry_price,
                    quantity,
                    stop_loss,
                    take_profit,
                    current_price,
                    status,
                    opened_at,
                    realized_pnl

                )

                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
                """,
                (
                    position.symbol,
                    position.entry_price,
                    position.quantity,
                    position.stop_loss,
                    position.take_profit,
                    position.current_price,
                    "OPEN",
                    position.realized_pnl,
                ),
            )

            connection.commit()

    def load_open_positions(self) -> list[Position]:

        positions = []

        with self.database.connect() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT *

                FROM positions

                WHERE status = 'OPEN'
                """
            )

            rows = cursor.fetchall()

            for row in rows:

                position = Position(

                    symbol=row["symbol"],

                    entry_price=row["entry_price"],

                    quantity=row["quantity"],

                    stop_loss=row["stop_loss"],

                    take_profit=row["take_profit"],
                )

                position.update_price(
                    row["current_price"]
                )

                positions.append(
                    position
                )

        return positions

    def close(
        self,
        position: Position,
    ):

        with self.database.connect() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                UPDATE positions

                SET

                    status = ?,

                    current_price = ?,

                    realized_pnl = ?,

                    closed_at = datetime('now')

                WHERE

                    symbol = ?

                AND

                    status = 'OPEN'
                """,
                (
                    "CLOSED",
                    position.current_price,
                    position.realized_pnl,
                    position.symbol,
                ),
            )

            connection.commit()

    def delete_all(self):

        with self.database.connect() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                DELETE FROM positions
                """
            )

            connection.commit()