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

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS shadow_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                regime TEXT NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                quantity REAL NOT NULL,
                opened_at TEXT NOT NULL,
                status TEXT NOT NULL,
                closed_at TEXT,
                exit_price REAL,
                exit_reason TEXT,
                pnl REAL,
                UNIQUE(symbol, opened_at)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_portfolio (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                initial_balance REAL NOT NULL,
                cash REAL NOT NULL,
                peak_equity REAL NOT NULL,
                max_drawdown REAL NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                entry_price REAL NOT NULL,
                quantity REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                opened_at TEXT NOT NULL,
                closed_at TEXT,
                current_price REAL NOT NULL,
                highest_price REAL NOT NULL,
                status TEXT NOT NULL,
                break_even INTEGER NOT NULL,
                realized_pnl REAL NOT NULL,
                initial_risk REAL NOT NULL,
                trailing_stop REAL NOT NULL,
                entry_fee REAL NOT NULL,
                exit_reason TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_symbol_state (
                symbol TEXT PRIMARY KEY,
                last_entry_timestamp TEXT,
                cooldown_until TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_health (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                cycle_started_at TEXT,
                cycle_completed_at TEXT,
                cycle_status TEXT NOT NULL,
                expected_symbols INTEGER NOT NULL,
                successful_symbols INTEGER NOT NULL,
                failed_symbols INTEGER NOT NULL,
                last_error TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_symbol_health (
                symbol TEXT PRIMARY KEY,
                last_success_at TEXT,
                last_failure_at TEXT,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                last_error TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS exchange_order_intents (
                client_order_id TEXT PRIMARY KEY,
                exchange_order_id TEXT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                requested_amount REAL NOT NULL,
                reference_price REAL NOT NULL,
                status TEXT NOT NULL,
                filled_amount REAL NOT NULL DEFAULT 0,
                average_price REAL,
                fee_cost REAL NOT NULL DEFAULT 0,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS exchange_positions (
                entry_client_order_id TEXT PRIMARY KEY,
                exit_client_order_id TEXT UNIQUE,
                symbol TEXT NOT NULL,
                requested_amount REAL NOT NULL,
                quantity REAL NOT NULL DEFAULT 0,
                planned_entry REAL NOT NULL,
                entry_price REAL,
                entry_fee REAL NOT NULL DEFAULT 0,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                status TEXT NOT NULL,
                entry_exchange_order_id TEXT,
                exit_exchange_order_id TEXT,
                opened_at TEXT,
                closed_at TEXT,
                exit_price REAL,
                exit_fee REAL NOT NULL DEFAULT 0,
                exit_reason TEXT,
                realized_pnl REAL,
                protection_client_order_id TEXT,
                protection_order_id TEXT,
                protection_status TEXT,
                protection_error TEXT,
                last_error TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )

        self._ensure_column(
            cursor,
            "exchange_order_intents",
            "fee_cost",
            "REAL NOT NULL DEFAULT 0",
        )
        for column in (
            "protection_client_order_id",
            "protection_order_id",
            "protection_status",
            "protection_error",
        ):
            self._ensure_column(
                cursor,
                "exchange_positions",
                column,
                "TEXT",
            )
        self._ensure_column(
            cursor,
            "exchange_positions",
            "entry_fee",
            "REAL NOT NULL DEFAULT 0",
        )
        self._ensure_column(
            cursor,
            "exchange_positions",
            "exit_fee",
            "REAL NOT NULL DEFAULT 0",
        )

        self.connection.commit()

    @staticmethod
    def _ensure_column(cursor, table: str, column: str, definition: str):
        columns = {
            row[1]
            for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            cursor.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
            )

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
