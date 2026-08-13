from app.storage.database import Database


class ExecutionRiskRepository:
    def __init__(self):
        self.database = Database()

    def load(self, mode: str) -> dict | None:
        row = self.database.connection.execute(
            """
            SELECT trading_day, day_start_equity, daily_pnl,
                   consecutive_losses, orders_today, halted_reason, updated_at
            FROM execution_risk_state WHERE mode = ?
            """,
            (mode,),
        ).fetchone()
        if row is None:
            return None
        return {
            "trading_day": row[0],
            "day_start_equity": float(row[1]),
            "daily_pnl": float(row[2]),
            "consecutive_losses": int(row[3]),
            "orders_today": int(row[4]),
            "halted_reason": row[5],
            "updated_at": row[6],
        }

    def save(self, mode: str, state: dict) -> None:
        self.database.execute(
            """
            INSERT INTO execution_risk_state (
                mode, trading_day, day_start_equity, daily_pnl,
                consecutive_losses, orders_today, halted_reason, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(mode) DO UPDATE SET
                trading_day = excluded.trading_day,
                day_start_equity = excluded.day_start_equity,
                daily_pnl = excluded.daily_pnl,
                consecutive_losses = excluded.consecutive_losses,
                orders_today = excluded.orders_today,
                halted_reason = excluded.halted_reason,
                updated_at = excluded.updated_at
            """,
            (
                mode,
                state["trading_day"],
                state["day_start_equity"],
                state["daily_pnl"],
                state["consecutive_losses"],
                state["orders_today"],
                state.get("halted_reason"),
                state["updated_at"],
            ),
        )
