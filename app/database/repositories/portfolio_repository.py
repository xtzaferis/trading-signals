from app.config.settings import ACCOUNT_SIZE
from app.database.database import Database
from app.trading.portfolio import Portfolio


class PortfolioRepository:

    def __init__(self):

        self.database = Database()

    def exists(self) -> bool:

        with self.database.connect() as connection:

            cursor = connection.cursor()

            cursor.execute(
                "SELECT COUNT(*) FROM portfolio"
            )

            count: int = cursor.fetchone()[0]

            return count > 0

    def save(
        self,
        portfolio: Portfolio,
    ):

        with self.database.connect() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                DELETE FROM portfolio
                """
            )

            cursor.execute(
                """
                INSERT INTO portfolio (

                    id,
                    cash,
                    equity,
                    updated_at

                )

                VALUES (?, ?, ?, datetime('now'))
                """,
                (
                    1,
                    portfolio.cash,
                    portfolio.equity,
                ),
            )

            connection.commit()

    def load(self) -> Portfolio:

        portfolio = Portfolio()

        with self.database.connect() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    cash,
                    equity
                FROM portfolio
                LIMIT 1
                """
            )

            row = cursor.fetchone()

            if row is None:

                portfolio.cash = ACCOUNT_SIZE

                return portfolio

            portfolio.cash = row["cash"]

            return portfolio