from datetime import datetime, timezone

from app.storage.database import Database


class ExchangePositionRepository:
    """Persist demo positions independently from simulated paper state."""

    def __init__(self):
        self.database = Database()

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

    def close(
        self,
        entry_client_order_id: str,
        exchange_order_id: str | None,
        exit_price: float,
        exit_fee: float,
        realized_pnl: float,
        closed_at: datetime,
    ) -> None:
        self.database.execute(
            """
            UPDATE exchange_positions SET
                exit_exchange_order_id = ?, exit_price = ?,
                exit_fee = ?, realized_pnl = ?, closed_at = ?, status = 'CLOSED',
                last_error = NULL, updated_at = ?
            WHERE entry_client_order_id = ?
            """,
            (
                exchange_order_id,
                exit_price,
                exit_fee,
                realized_pnl,
                closed_at.isoformat(),
                self._now(),
                entry_client_order_id,
            ),
        )

    def find_active(self, symbol: str) -> dict | None:
        row = self.database.connection.execute(
            """
            SELECT entry_client_order_id, exit_client_order_id, symbol,
                   requested_amount, quantity, planned_entry, entry_price,
                   entry_fee, stop_loss, take_profit, status, entry_exchange_order_id,
                   exit_exchange_order_id, opened_at, closed_at, exit_price,
                   exit_fee, exit_reason, realized_pnl, last_error, updated_at
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
