from datetime import datetime, timezone

from app.config.settings import PAPER_HEALTH_STALE_SECONDS
from app.storage.database import Database


class PaperHealthRepository:
    def __init__(self):
        self.database = Database()

    def start_cycle(self, expected_symbols: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.database.execute(
            """
            INSERT INTO paper_health (
                id, cycle_started_at, cycle_completed_at, cycle_status,
                expected_symbols, successful_symbols, failed_symbols,
                last_error
            ) VALUES (1, ?, NULL, 'RUNNING', ?, 0, 0, NULL)
            ON CONFLICT(id) DO UPDATE SET
                cycle_started_at = excluded.cycle_started_at,
                cycle_completed_at = NULL,
                cycle_status = 'RUNNING',
                expected_symbols = excluded.expected_symbols,
                successful_symbols = 0,
                failed_symbols = 0,
                last_error = NULL
            """,
            (now, expected_symbols),
        )

    def record_success(self, symbol: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.database.execute(
            """
            INSERT INTO paper_symbol_health (
                symbol, last_success_at, consecutive_failures
            ) VALUES (?, ?, 0)
            ON CONFLICT(symbol) DO UPDATE SET
                last_success_at = excluded.last_success_at,
                consecutive_failures = 0,
                last_error = NULL
            """,
            (symbol, now),
        )

    def record_failure(self, symbol: str, error: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.database.execute(
            """
            INSERT INTO paper_symbol_health (
                symbol, last_failure_at, consecutive_failures, last_error
            ) VALUES (?, ?, 1, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                last_failure_at = excluded.last_failure_at,
                consecutive_failures = consecutive_failures + 1,
                last_error = excluded.last_error
            """,
            (symbol, now, error),
        )

    def complete_cycle(
        self,
        successful_symbols: int,
        failed_symbols: int,
        last_error: str | None = None,
    ) -> None:
        status = "SUCCESS" if failed_symbols == 0 else "DEGRADED"
        self.database.execute(
            """
            UPDATE paper_health SET
                cycle_completed_at = ?, cycle_status = ?,
                successful_symbols = ?, failed_symbols = ?, last_error = ?
            WHERE id = 1
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                status,
                successful_symbols,
                failed_symbols,
                last_error,
            ),
        )

    def record_scan_failure(self, error: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.database.execute(
            """
            INSERT INTO paper_health (
                id, cycle_started_at, cycle_completed_at, cycle_status,
                expected_symbols, successful_symbols, failed_symbols,
                last_error
            ) VALUES (1, ?, ?, 'FAILED', 0, 0, 0, ?)
            ON CONFLICT(id) DO UPDATE SET
                cycle_started_at = excluded.cycle_started_at,
                cycle_completed_at = excluded.cycle_completed_at,
                cycle_status = 'FAILED',
                expected_symbols = 0,
                successful_symbols = 0,
                failed_symbols = 0,
                last_error = excluded.last_error
            """,
            (now, now, error),
        )

    def status(self) -> dict:
        row = self.database.connection.execute(
            """
            SELECT cycle_started_at, cycle_completed_at, cycle_status,
                   expected_symbols, successful_symbols, failed_symbols,
                   last_error
            FROM paper_health WHERE id = 1
            """
        ).fetchone()
        if row is None:
            return {
                "health": "UNKNOWN",
                "completed_at": None,
                "successful_symbols": 0,
                "failed_symbols": 0,
                "last_error": None,
                "symbol_failures": {},
            }

        completed_at = row[1]
        health = "HEALTHY" if row[2] == "SUCCESS" else "DEGRADED"
        reference = completed_at or row[0]
        if reference:
            observed_at = datetime.fromisoformat(reference)
            age = datetime.now(timezone.utc) - observed_at
            if age.total_seconds() > PAPER_HEALTH_STALE_SECONDS:
                health = "STALE"

        failures = self.database.connection.execute(
            """
            SELECT symbol, consecutive_failures, last_error
            FROM paper_symbol_health WHERE consecutive_failures > 0
            ORDER BY symbol
            """
        ).fetchall()
        return {
            "health": health,
            "completed_at": completed_at,
            "successful_symbols": int(row[4]),
            "failed_symbols": int(row[5]),
            "last_error": row[6],
            "symbol_failures": {
                failure[0]: {
                    "count": int(failure[1]),
                    "error": failure[2],
                }
                for failure in failures
            },
        }
