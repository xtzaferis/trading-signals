import json
from datetime import datetime
from pathlib import Path

from app.storage.database import Database


class AdvisorySignalRepository:
    """Persist advisory observations locally; it has no exchange access."""

    def __init__(self, database: Database | None = None):
        self.database = database or Database()

    def save_report(self, report) -> None:
        shortlisted = {candidate.symbol for candidate in report.shortlist}
        for candidate in report.candidates:
            trade = candidate.trade
            context = candidate.derivatives
            self.database.execute(
                """
                INSERT OR IGNORE INTO advisory_signals (
                    generated_at, symbol, direction, score, risk,
                    reference_price, stop_loss, take_profit, net_risk_reward,
                    reasons_json, funding_rate, open_interest_change_pct,
                    long_short_ratio, taker_buy_sell_ratio, shortlisted,
                    outcome_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.generated_at.isoformat(),
                    candidate.symbol,
                    candidate.status,
                    candidate.score,
                    candidate.risk,
                    candidate.price,
                    trade.stop_loss if trade else None,
                    trade.take_profit if trade else None,
                    trade.net_risk_reward if trade else None,
                    json.dumps(candidate.reasons),
                    context.funding_rate if context else None,
                    context.open_interest_change_pct if context else None,
                    context.long_short_ratio if context else None,
                    context.taker_buy_sell_ratio if context else None,
                    int(candidate.symbol in shortlisted),
                    "OPEN" if trade else "NOT_APPLICABLE",
                ),
            )

    def list_open(self) -> list[dict]:
        rows = self.database.execute(
            """
            SELECT id, generated_at, symbol, direction, reference_price,
                   stop_loss, take_profit, funding_rate
            FROM advisory_signals
            WHERE outcome_status = 'OPEN'
            ORDER BY generated_at, symbol
            """
        ).fetchall()
        columns = (
            "id",
            "generated_at",
            "symbol",
            "direction",
            "reference_price",
            "stop_loss",
            "take_profit",
            "funding_rate",
        )
        return [dict(zip(columns, row)) for row in rows]

    def resolve(
        self,
        signal_id: int,
        resolved_at: datetime,
        exit_price: float,
        outcome: str,
        net_return_pct: float,
    ) -> None:
        self.database.execute(
            """
            UPDATE advisory_signals
            SET outcome_status = 'RESOLVED', resolved_at = ?, exit_price = ?,
                outcome = ?, net_return_pct = ?
            WHERE id = ? AND outcome_status = 'OPEN'
            """,
            (
                resolved_at.isoformat(),
                exit_price,
                outcome,
                net_return_pct,
                signal_id,
            ),
        )

    def statistics(self) -> dict:
        row = self.database.execute(
            """
            SELECT COUNT(*),
                   SUM(CASE WHEN outcome = 'TARGET' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN outcome = 'STOP' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN outcome = 'TIMEOUT' THEN 1 ELSE 0 END),
                   AVG(net_return_pct),
                   SUM(net_return_pct)
            FROM advisory_signals
            WHERE outcome_status = 'RESOLVED' AND shortlisted = 1
            """
        ).fetchone()
        return {
            "resolved": int(row[0] or 0),
            "targets": int(row[1] or 0),
            "stops": int(row[2] or 0),
            "timeouts": int(row[3] or 0),
            "average_return_pct": float(row[4] or 0.0),
            "total_return_pct": float(row[5] or 0.0),
        }

    def export_public_history(self, path: Path) -> None:
        cursor = self.database.execute(
            "SELECT * FROM advisory_signals ORDER BY generated_at, symbol"
        )
        columns = tuple(description[0] for description in cursor.description)
        records = [dict(zip(columns, row)) for row in cursor.fetchall()]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    def import_public_history(self, path: Path) -> int:
        if not path.exists():
            return 0
        records = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise TypeError("Advisory history must contain a JSON list.")
        allowed_columns = self._columns()
        imported = 0
        for record in records:
            if not isinstance(record, dict):
                raise TypeError("Each advisory history item must be an object.")
            values = {key: record[key] for key in allowed_columns if key in record}
            required = {"generated_at", "symbol", "direction", "score", "risk"}
            if not required.issubset(values):
                raise ValueError("Advisory history item is missing required fields.")
            columns = tuple(values)
            placeholders = ", ".join("?" for _ in columns)
            self.database.execute(
                f"INSERT OR IGNORE INTO advisory_signals "
                f"({', '.join(columns)}) VALUES ({placeholders})",
                tuple(values[column] for column in columns),
            )
            imported += 1
        return imported

    def _columns(self) -> tuple[str, ...]:
        rows = self.database.execute("PRAGMA table_info(advisory_signals)").fetchall()
        return tuple(row[1] for row in rows if row[1] != "id")
