import sqlite3
from pathlib import Path

DATABASE_PATH = Path(
    "data/trading.db"
)


class Database:

    def __init__(self):

        DATABASE_PATH.parent.mkdir(
            exist_ok=True
        )

        self.connection = sqlite3.connect(
            DATABASE_PATH
        )

        self.create_tables()

    def create_tables(self):

        cursor = (
            self.connection.cursor()
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                timestamp TEXT NOT NULL,

                symbol TEXT NOT NULL,

                price REAL NOT NULL,

                score INTEGER NOT NULL,

                action TEXT NOT NULL

            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                symbol TEXT NOT NULL,

                entry_price REAL NOT NULL,

                exit_price REAL NOT NULL,

                quantity REAL NOT NULL,

                opened_at TEXT NOT NULL,

                closed_at TEXT NOT NULL,

                exit_reason TEXT NOT NULL,

                pnl REAL NOT NULL

            )
            """
        )

        self.connection.commit()

    def execute(
        self,
        query: str,
        params: tuple = (),
    ):

        cursor = (
            self.connection.cursor()
        )

        cursor.execute(
            query,
            params,
        )

        self.connection.commit()

        return cursor