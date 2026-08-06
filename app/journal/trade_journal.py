import csv
from pathlib import Path

from app.core.logger import logger
from app.models.position import Position


class TradeJournal:

    def __init__(self):

        self.file = Path(
            "logs/trade_journal.csv"
        )

        self.file.parent.mkdir(
            exist_ok=True
        )

        if not self.file.exists():

            with open(
                self.file,
                "w",
                newline="",
                encoding="utf-8",
            ) as csvfile:

                writer = csv.writer(csvfile)

                writer.writerow(
                    [
                        "opened_at",
                        "closed_at",
                        "symbol",
                        "entry",
                        "exit",
                        "quantity",
                        "pnl",
                        "result",
                    ]
                )

    def save(
        self,
        position: Position,
    ):

        result = (
            "WIN"
            if position.realized_pnl >= 0
            else "LOSS"
        )

        with open(
            self.file,
            "a",
            newline="",
            encoding="utf-8",
        ) as csvfile:

            writer = csv.writer(csvfile)

            writer.writerow(
                [
                    position.opened_at,
                    position.closed_at,
                    position.symbol,
                    round(position.entry_price, 6),
                    round(position.current_price, 6),
                    round(position.quantity, 6),
                    round(position.realized_pnl, 2),
                    result,
                ]
            )

        logger.info(
            f"Trade saved: {position.symbol}"
        )