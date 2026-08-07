import sqlite3


def create_schema(
    connection: sqlite3.Connection,
):

    cursor = connection.cursor()

    # ----------------------------------
    # Portfolio
    # ----------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio (

            id INTEGER PRIMARY KEY,

            cash REAL NOT NULL,

            equity REAL NOT NULL,

            updated_at TEXT
        )
        """
    )

    # ----------------------------------
    # Positions
    # ----------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS positions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            symbol TEXT NOT NULL,

            entry_price REAL NOT NULL,

            quantity REAL NOT NULL,

            stop_loss REAL NOT NULL,

            take_profit REAL NOT NULL,

            current_price REAL,

            status TEXT NOT NULL,

            opened_at TEXT,

            closed_at TEXT,

            realized_pnl REAL
        )
        """
    )

    # ----------------------------------
    # Trades
    # ----------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            symbol TEXT NOT NULL,

            side TEXT NOT NULL,

            price REAL NOT NULL,

            quantity REAL NOT NULL,

            timestamp TEXT NOT NULL
        )
        """
    )

    connection.commit()