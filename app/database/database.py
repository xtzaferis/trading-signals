from pathlib import Path
import sqlite3

from app.core.logger import logger


class Database:

    def __init__(self):

        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        self.db_path = data_dir / "trading.db"

    def connect(self) -> sqlite3.Connection:

        connection = sqlite3.connect(
            self.db_path
        )

        connection.row_factory = (
            sqlite3.Row
        )

        return connection

    def initialize(self):

        from app.database.schema import (
            create_schema,
        )

        with self.connect() as connection:

            create_schema(
                connection
            )

        logger.info(
            "Database initialized."
        )