from datetime import datetime, timezone

from app.config.settings import ACCOUNT_SIZE
from app.models.position import Position
from app.storage.database import Database
from app.trading.portfolio import Portfolio


class PaperStateRepository:
    """Atomically persist the complete paper portfolio snapshot."""

    def __init__(self):
        self.database = Database()

    def save(
        self,
        portfolio: Portfolio,
        symbol_state: dict[str, dict] | None = None,
    ) -> None:
        updated_at = datetime.now(timezone.utc).isoformat()
        positions = (
            list(portfolio.open_positions)
            + list(portfolio.closed_positions)
        )

        with self.database.connection:
            cursor = self.database.connection.cursor()
            cursor.execute(
                """
                INSERT INTO paper_portfolio (
                    id, initial_balance, cash, peak_equity,
                    max_drawdown, updated_at
                ) VALUES (1, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    initial_balance = excluded.initial_balance,
                    cash = excluded.cash,
                    peak_equity = excluded.peak_equity,
                    max_drawdown = excluded.max_drawdown,
                    updated_at = excluded.updated_at
                """,
                (
                    portfolio.initial_balance,
                    portfolio.cash,
                    portfolio.peak_equity,
                    portfolio.max_drawdown,
                    updated_at,
                ),
            )
            cursor.execute("DELETE FROM paper_positions")
            cursor.executemany(
                """
                INSERT INTO paper_positions (
                    symbol, entry_price, quantity, stop_loss,
                    take_profit, opened_at, closed_at, current_price,
                    highest_price, status, break_even, realized_pnl,
                    initial_risk, trailing_stop, entry_fee, exit_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [self._position_values(position) for position in positions],
            )
            if symbol_state is not None:
                cursor.execute("DELETE FROM paper_symbol_state")
                cursor.executemany(
                    """
                    INSERT INTO paper_symbol_state (
                        symbol, last_entry_timestamp, cooldown_until
                    ) VALUES (?, ?, ?)
                    """,
                    [
                        (
                            symbol,
                            self._datetime_value(
                                state.get("last_entry_timestamp")
                            ),
                            self._datetime_value(
                                state.get("cooldown_until")
                            ),
                        )
                        for symbol, state in symbol_state.items()
                    ],
                )

    def load(self) -> Portfolio:
        portfolio = Portfolio()
        cursor = self.database.connection.execute(
            """
            SELECT initial_balance, cash, peak_equity, max_drawdown
            FROM paper_portfolio WHERE id = 1
            """
        )
        row = cursor.fetchone()
        if row is None:
            return portfolio

        portfolio.initial_balance = float(row[0])
        portfolio.cash = float(row[1])
        portfolio.peak_equity = float(row[2])
        portfolio.max_drawdown = float(row[3])

        rows = self.database.connection.execute(
            """
            SELECT symbol, entry_price, quantity, stop_loss,
                   take_profit, opened_at, closed_at, current_price,
                   highest_price, status, break_even, realized_pnl,
                   initial_risk, trailing_stop, entry_fee, exit_reason
            FROM paper_positions ORDER BY id
            """
        ).fetchall()
        for position_row in rows:
            position = self._position_from_row(position_row)
            if position.status == "OPEN":
                portfolio.open_positions.append(position)
            else:
                portfolio.closed_positions.append(position)

        return portfolio

    def load_symbol_state(self) -> dict[str, dict]:
        rows = self.database.connection.execute(
            """
            SELECT symbol, last_entry_timestamp, cooldown_until
            FROM paper_symbol_state
            """
        ).fetchall()
        return {
            row[0]: {
                "last_entry_timestamp": self._parse_datetime(row[1]),
                "cooldown_until": self._parse_datetime(row[2]),
            }
            for row in rows
        }

    def status(self) -> dict[str, str | int | float | None]:
        row = self.database.connection.execute(
            """
            SELECT initial_balance, cash, peak_equity,
                   max_drawdown, updated_at
            FROM paper_portfolio WHERE id = 1
            """
        ).fetchone()
        if row is None:
            return {
                "updated_at": None,
                "cash": ACCOUNT_SIZE,
                "open_positions": 0,
                "closed_positions": 0,
            }
        counts = dict(self.database.connection.execute(
            """
            SELECT status, COUNT(*) FROM paper_positions GROUP BY status
            """
        ).fetchall())
        return {
            "updated_at": row[4],
            "cash": float(row[1]),
            "open_positions": int(counts.get("OPEN", 0)),
            "closed_positions": int(counts.get("CLOSED", 0)),
        }

    @staticmethod
    def _position_values(position: Position) -> tuple:
        return (
            position.symbol,
            position.entry_price,
            position.quantity,
            position.stop_loss,
            position.take_profit,
            position.opened_at.isoformat(),
            position.closed_at.isoformat() if position.closed_at else None,
            position.current_price,
            position.highest_price,
            position.status,
            int(position.break_even),
            position.realized_pnl,
            position.initial_risk,
            position.trailing_stop,
            position.entry_fee,
            position.exit_reason,
        )

    @staticmethod
    def _datetime_value(value) -> str | None:
        return value.isoformat() if value is not None else None

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        return datetime.fromisoformat(value) if value else None

    @staticmethod
    def _position_from_row(row: tuple) -> Position:
        position = Position(
            symbol=row[0],
            entry_price=float(row[1]),
            quantity=float(row[2]),
            stop_loss=float(row[3]),
            take_profit=float(row[4]),
            opened_at=datetime.fromisoformat(row[5]),
        )
        position.closed_at = (
            datetime.fromisoformat(row[6]) if row[6] else None
        )
        position.current_price = float(row[7])
        position.highest_price = float(row[8])
        position.status = row[9]
        position.break_even = bool(row[10])
        position.realized_pnl = float(row[11])
        position.initial_risk = float(row[12])
        position.trailing_stop = float(row[13])
        position.entry_fee = float(row[14])
        position.exit_reason = row[15]
        return position
