from datetime import datetime

from app.models.shadow_trade import ShadowTrade
from app.storage.database import Database


class ShadowTradeRepository:
    def __init__(self):
        self.database = Database()

    def save_open(self, trade: ShadowTrade) -> int:
        cursor = self.database.execute(
            """
            INSERT OR IGNORE INTO shadow_trades (
                symbol, regime, entry_price, stop_loss, take_profit,
                quantity, opened_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade.symbol,
                trade.regime,
                trade.entry_price,
                trade.stop_loss,
                trade.take_profit,
                trade.quantity,
                trade.opened_at.isoformat(),
                trade.status,
            ),
        )
        return int(cursor.lastrowid or 0)

    def get_open(self, symbol: str) -> ShadowTrade | None:
        cursor = self.database.execute(
            """
            SELECT id, symbol, regime, entry_price, stop_loss,
                   take_profit, quantity, opened_at, status,
                   closed_at, exit_price, exit_reason, pnl
            FROM shadow_trades
            WHERE symbol = ? AND status = 'OPEN'
            ORDER BY opened_at DESC
            LIMIT 1
            """,
            (symbol,),
        )
        row = cursor.fetchone()
        return self._from_row(row) if row else None

    def close(self, trade: ShadowTrade) -> None:
        self.database.execute(
            """
            UPDATE shadow_trades
            SET status = ?, closed_at = ?, exit_price = ?,
                exit_reason = ?, pnl = ?
            WHERE id = ?
            """,
            (
                trade.status,
                trade.closed_at.isoformat() if trade.closed_at else None,
                trade.exit_price,
                trade.exit_reason,
                trade.pnl,
                trade.id,
            ),
        )

    def get_closed(self) -> list[ShadowTrade]:
        cursor = self.database.execute(
            """
            SELECT id, symbol, regime, entry_price, stop_loss,
                   take_profit, quantity, opened_at, status,
                   closed_at, exit_price, exit_reason, pnl
            FROM shadow_trades
            WHERE status = 'CLOSED'
            ORDER BY closed_at
            """
        )
        return [self._from_row(row) for row in cursor.fetchall()]

    def count_open(self) -> int:
        cursor = self.database.execute(
            "SELECT COUNT(*) FROM shadow_trades WHERE status = 'OPEN'"
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0

    @staticmethod
    def _from_row(row: tuple) -> ShadowTrade:
        return ShadowTrade(
            id=int(row[0]),
            symbol=row[1],
            regime=row[2],
            entry_price=float(row[3]),
            stop_loss=float(row[4]),
            take_profit=float(row[5]),
            quantity=float(row[6]),
            opened_at=datetime.fromisoformat(row[7]),
            status=row[8],
            closed_at=(
                datetime.fromisoformat(row[9]) if row[9] else None
            ),
            exit_price=float(row[10]) if row[10] is not None else None,
            exit_reason=row[11],
            pnl=float(row[12]) if row[12] is not None else None,
        )
