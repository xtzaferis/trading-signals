from datetime import datetime, timezone

from app.config.settings import ACCOUNT_SIZE
from app.storage.database import Database


class ExchangePositionRepository:
    """Persist exchange positions independently from paper state."""

    def __init__(self, database=None):
        self.database = database or Database()

    def prepare_entry(
        self,
        client_order_id: str,
        symbol: str,
        requested_amount: float,
        planned_entry: float,
        stop_loss: float,
        take_profit: float,
    ) -> bool:
        cursor = self.database.execute(
            """
            INSERT OR IGNORE INTO exchange_positions (
                entry_client_order_id, symbol, requested_amount,
                planned_entry, stop_loss, take_profit, status, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING_ENTRY', ?)
            """,
            (
                client_order_id,
                symbol,
                requested_amount,
                planned_entry,
                stop_loss,
                take_profit,
                self._now(),
            ),
        )
        return cursor.rowcount == 1

    def record_entry_status(
        self,
        client_order_id: str,
        status: str,
        error: str | None = None,
    ) -> None:
        self.database.execute(
            """
            UPDATE exchange_positions SET status = ?, last_error = ?,
                updated_at = ? WHERE entry_client_order_id = ?
            """,
            (status, error, self._now(), client_order_id),
        )

    def activate(
        self,
        client_order_id: str,
        exchange_order_id: str | None,
        quantity: float,
        entry_price: float,
        entry_fee: float,
        stop_loss: float,
        take_profit: float,
        opened_at: datetime,
    ) -> None:
        self.database.execute(
            """
            UPDATE exchange_positions SET
                entry_exchange_order_id = ?, quantity = ?, entry_price = ?,
                entry_fee = ?, stop_loss = ?, take_profit = ?, status = 'OPEN',
                opened_at = ?, last_error = NULL, updated_at = ?
            WHERE entry_client_order_id = ?
            """,
            (
                exchange_order_id,
                quantity,
                entry_price,
                entry_fee,
                stop_loss,
                take_profit,
                opened_at.isoformat(),
                self._now(),
                client_order_id,
            ),
        )

    def prepare_exit(
        self,
        entry_client_order_id: str,
        exit_client_order_id: str,
        reason: str,
    ) -> bool:
        cursor = self.database.execute(
            """
            UPDATE exchange_positions SET
                exit_client_order_id = ?, exit_reason = ?,
                status = 'PENDING_EXIT', updated_at = ?
            WHERE entry_client_order_id = ?
              AND status = 'OPEN' AND exit_client_order_id IS NULL
            """,
            (
                exit_client_order_id,
                reason,
                self._now(),
                entry_client_order_id,
            ),
        )
        return cursor.rowcount == 1

    def reset_exit(self, entry_client_order_id: str, error: str) -> None:
        self.database.execute(
            """
            UPDATE exchange_positions SET
                exit_client_order_id = NULL, exit_reason = NULL,
                status = 'OPEN', last_error = ?, updated_at = ?
            WHERE entry_client_order_id = ? AND status = 'PENDING_EXIT'
            """,
            (error, self._now(), entry_client_order_id),
        )

    def prepare_protection(
        self,
        entry_client_order_id: str,
        client_order_id: str,
    ) -> bool:
        cursor = self.database.execute(
            """
            UPDATE exchange_positions SET
                protection_client_order_id = ?,
                protection_status = 'PENDING', protection_error = NULL,
                updated_at = ?
            WHERE entry_client_order_id = ? AND status = 'OPEN'
              AND protection_client_order_id IS NULL
            """,
            (client_order_id, self._now(), entry_client_order_id),
        )
        return cursor.rowcount == 1

    def record_protection(
        self,
        entry_client_order_id: str,
        status: str,
        order_id: str | None = None,
        error: str | None = None,
    ) -> None:
        self.database.execute(
            """
            UPDATE exchange_positions SET
                protection_order_id = COALESCE(?, protection_order_id),
                protection_status = ?, protection_error = ?, updated_at = ?
            WHERE entry_client_order_id = ?
            """,
            (order_id, status, error, self._now(), entry_client_order_id),
        )

    def close(
        self,
        entry_client_order_id: str,
        exchange_order_id: str | None,
        exit_price: float,
        exit_fee: float,
        realized_pnl: float,
        closed_at: datetime,
        exit_reason: str | None = None,
    ) -> None:
        self.database.execute(
            """
            UPDATE exchange_positions SET
                exit_exchange_order_id = ?, exit_price = ?,
                exit_fee = ?, realized_pnl = ?, closed_at = ?, status = 'CLOSED',
                exit_reason = COALESCE(?, exit_reason),
                last_error = NULL, updated_at = ?
            WHERE entry_client_order_id = ?
            """,
            (
                exchange_order_id,
                exit_price,
                exit_fee,
                realized_pnl,
                closed_at.isoformat(),
                exit_reason,
                self._now(),
                entry_client_order_id,
            ),
        )

    def operational_summary(self) -> dict:
        rows = self.database.connection.execute(
            """
            SELECT status, protection_status, realized_pnl, opened_at, closed_at
            FROM exchange_positions ORDER BY updated_at
            """
        ).fetchall()
        closed_pnl = [float(row[2]) for row in rows if row[2] is not None]
        dated_pnl = [
            (datetime.fromisoformat(row[4]), float(row[2]))
            for row in rows
            if row[2] is not None and row[4]
        ]
        gross_profit = sum(value for value in closed_pnl if value > 0)
        gross_loss = abs(sum(value for value in closed_pnl if value < 0))
        daily_pnl: dict[str, float] = {}
        monthly_pnl: dict[str, float] = {}
        equity = float(ACCOUNT_SIZE)
        peak = equity
        max_drawdown_pct = 0.0
        for closed_at, pnl in dated_pnl:
            day = closed_at.date().isoformat()
            month = closed_at.strftime("%Y-%m")
            daily_pnl[day] = daily_pnl.get(day, 0.0) + pnl
            monthly_pnl[month] = monthly_pnl.get(month, 0.0) + pnl
            equity += pnl
            peak = max(peak, equity)
            if peak > 0:
                max_drawdown_pct = max(
                    max_drawdown_pct,
                    (peak - equity) / peak * 100,
                )
        return {
            "positions": len(rows),
            "open_positions": sum(row[0] == "OPEN" for row in rows),
            "pending_positions": sum(
                row[0] not in {
                    "OPEN", "CLOSED", "ENTRY_REJECTED", "ENTRY_CANCELED"
                }
                for row in rows
            ),
            "unprotected_positions": sum(
                row[0] == "OPEN" and row[1] != "ACTIVE" for row in rows
            ),
            "closed_trades": len(closed_pnl),
            "wins": sum(value > 0 for value in closed_pnl),
            "losses": sum(value < 0 for value in closed_pnl),
            "net_profit": sum(closed_pnl),
            "profit_factor": (
                gross_profit / gross_loss if gross_loss > 0 else 0.0
            ),
            "max_drawdown_pct": max_drawdown_pct,
            "daily_pnl": daily_pnl,
            "monthly_pnl": monthly_pnl,
            "first_opened_at": next((row[3] for row in rows if row[3]), None),
            "last_closed_at": next(
                (row[4] for row in reversed(rows) if row[4]), None
            ),
        }

    def find_active(self, symbol: str) -> dict | None:
        row = self.database.connection.execute(
            """
            SELECT entry_client_order_id, exit_client_order_id, symbol,
                   requested_amount, quantity, planned_entry, entry_price,
                   entry_fee, stop_loss, take_profit, status, entry_exchange_order_id,
                   exit_exchange_order_id, opened_at, closed_at, exit_price,
                   exit_fee, exit_reason, realized_pnl, last_error, updated_at
                   , protection_client_order_id, protection_order_id,
                   protection_status, protection_error
            FROM exchange_positions
            WHERE symbol = ? AND status IN (
                'PENDING_ENTRY', 'ENTRY_UNKNOWN', 'OPEN', 'PENDING_EXIT',
                'EXIT_UNKNOWN'
            )
            ORDER BY updated_at DESC LIMIT 1
            """,
            (symbol,),
        ).fetchone()
        return self._row(row) if row else None

    def pending_entries(self) -> list[dict]:
        return self._select_statuses(("PENDING_ENTRY", "ENTRY_UNKNOWN"))

    def open_positions(self) -> list[dict]:
        return self._select_statuses(("OPEN", "PENDING_EXIT", "EXIT_UNKNOWN"))

    def _select_statuses(self, statuses: tuple[str, ...]) -> list[dict]:
        placeholders = ", ".join("?" for _ in statuses)
        rows = self.database.connection.execute(
            f"""
            SELECT entry_client_order_id, exit_client_order_id, symbol,
                   requested_amount, quantity, planned_entry, entry_price,
                   entry_fee, stop_loss, take_profit, status, entry_exchange_order_id,
                   exit_exchange_order_id, opened_at, closed_at, exit_price,
                   exit_fee, exit_reason, realized_pnl, last_error, updated_at
                   , protection_client_order_id, protection_order_id,
                   protection_status, protection_error
            FROM exchange_positions WHERE status IN ({placeholders})
            ORDER BY updated_at
            """,
            statuses,
        ).fetchall()
        return [self._row(row) for row in rows]

    @staticmethod
    def _row(row: tuple) -> dict:
        keys = (
            "entry_client_order_id", "exit_client_order_id", "symbol",
            "requested_amount", "quantity", "planned_entry", "entry_price",
            "entry_fee", "stop_loss", "take_profit", "status", "entry_exchange_order_id",
            "exit_exchange_order_id", "opened_at", "closed_at", "exit_price",
            "exit_fee", "exit_reason", "realized_pnl", "last_error", "updated_at",
            "protection_client_order_id", "protection_order_id",
            "protection_status", "protection_error",
        )
        result = dict(zip(keys, row, strict=True))
        for key in (
            "requested_amount", "quantity", "planned_entry", "entry_price",
            "entry_fee", "stop_loss", "take_profit", "exit_price", "exit_fee",
            "realized_pnl",
        ):
            if result[key] is not None:
                result[key] = float(result[key])
        return result

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
