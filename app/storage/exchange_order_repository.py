from datetime import datetime, timezone

from app.storage.database import Database

TERMINAL_ORDER_STATUSES = {
    "FILLED",
    "CANCELED",
    "REJECTED",
    "EXPIRED",
}


class ExchangeOrderRepository:
    """Persist exchange intent before any order can leave the process."""

    def __init__(self, database=None):
        self.database = database or Database()

    def prepare(
        self,
        client_order_id: str,
        symbol: str,
        side: str,
        order_type: str,
        amount: float,
        reference_price: float,
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.database.execute(
            """
            INSERT OR IGNORE INTO exchange_order_intents (
                client_order_id, exchange_order_id, symbol, side,
                order_type, requested_amount, reference_price, status,
                filled_amount, average_price, fee_cost, last_error,
                created_at, updated_at
            ) VALUES (
                ?, NULL, ?, ?, ?, ?, ?, 'PREPARED', 0, NULL, 0, NULL, ?, ?
            )
            """,
            (
                client_order_id,
                symbol,
                side,
                order_type,
                amount,
                reference_price,
                now,
                now,
            ),
        )
        return cursor.rowcount == 1

    def record_order(self, client_order_id: str, order: dict) -> None:
        status = self.normalized_status(order)
        self.database.execute(
            """
            UPDATE exchange_order_intents SET
                exchange_order_id = COALESCE(?, exchange_order_id),
                status = ?, filled_amount = ?, average_price = ?,
                fee_cost = ?, last_error = NULL, updated_at = ?
            WHERE client_order_id = ?
            """,
            (
                self._string_value(order.get("id")),
                status,
                float(order.get("filled") or 0.0),
                self._float_value(order.get("average")),
                self._fee_cost(order),
                datetime.now(timezone.utc).isoformat(),
                client_order_id,
            ),
        )

    def mark_unknown(self, client_order_id: str, error: str) -> None:
        self.database.execute(
            """
            UPDATE exchange_order_intents SET
                status = 'UNKNOWN', last_error = ?, updated_at = ?
            WHERE client_order_id = ?
            """,
            (
                error,
                datetime.now(timezone.utc).isoformat(),
                client_order_id,
            ),
        )

    def mark_rejected(self, client_order_id: str, error: str) -> None:
        """Record an explicit exchange rejection as a terminal outcome."""
        self.database.execute(
            """
            UPDATE exchange_order_intents SET
                status = 'REJECTED', last_error = ?, updated_at = ?
            WHERE client_order_id = ?
            """,
            (
                error,
                datetime.now(timezone.utc).isoformat(),
                client_order_id,
            ),
        )

    def get(self, client_order_id: str) -> dict | None:
        row = self.database.connection.execute(
            """
            SELECT client_order_id, exchange_order_id, symbol, side,
                   order_type, requested_amount, reference_price, status,
                   filled_amount, average_price, fee_cost, last_error,
                   created_at, updated_at
            FROM exchange_order_intents WHERE client_order_id = ?
            """,
            (client_order_id,),
        ).fetchone()
        return self._row(row) if row else None

    def pending(self) -> list[dict]:
        placeholders = ", ".join("?" for _ in TERMINAL_ORDER_STATUSES)
        rows = self.database.connection.execute(
            f"""
            SELECT client_order_id, exchange_order_id, symbol, side,
                   order_type, requested_amount, reference_price, status,
                   filled_amount, average_price, fee_cost, last_error,
                   created_at, updated_at
            FROM exchange_order_intents
            WHERE status NOT IN ({placeholders})
            ORDER BY created_at
            """,
            tuple(sorted(TERMINAL_ORDER_STATUSES)),
        ).fetchall()
        return [self._row(row) for row in rows]

    @staticmethod
    def normalized_status(order: dict) -> str:
        status = str(order.get("status") or "").lower()
        filled = float(order.get("filled") or 0.0)
        remaining = order.get("remaining")
        if status == "closed":
            return "FILLED"
        if status in {"canceled", "cancelled"}:
            return "CANCELED"
        if status in {"rejected", "expired"}:
            return status.upper()
        if filled > 0 and (remaining is None or float(remaining) > 0):
            return "PARTIALLY_FILLED"
        if status == "open":
            return "OPEN"
        return "SUBMITTED"

    @staticmethod
    def _row(row: tuple) -> dict:
        return {
            "client_order_id": row[0],
            "exchange_order_id": row[1],
            "symbol": row[2],
            "side": row[3],
            "order_type": row[4],
            "requested_amount": float(row[5]),
            "reference_price": float(row[6]),
            "status": row[7],
            "filled_amount": float(row[8]),
            "average_price": (
                float(row[9]) if row[9] is not None else None
            ),
            "fee_cost": float(row[10]),
            "last_error": row[11],
            "created_at": row[12],
            "updated_at": row[13],
        }

    @staticmethod
    def _string_value(value) -> str | None:
        return str(value) if value is not None else None

    @staticmethod
    def _float_value(value) -> float | None:
        return float(value) if value is not None else None

    @staticmethod
    def _fee_cost(order: dict) -> float:
        fee = order.get("fee") or {}
        return abs(float(fee.get("cost") or 0.0))
