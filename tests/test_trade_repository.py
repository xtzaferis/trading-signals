from datetime import datetime, timezone
from unittest.mock import Mock

from app.models.trade_record import (
    TradeRecord,
)
from app.storage.trade_repository import (
    TradeRepository,
)


def test_trade_repository_saves_trade():

    trade = TradeRecord(
        symbol="BTC/USDC",
        entry_price=100.0,
        exit_price=110.0,
        quantity=2.0,
        opened_at=datetime.now(
            timezone.utc
        ),
        closed_at=datetime.now(
            timezone.utc
        ),
        exit_reason="TAKE_PROFIT",
        pnl=20.0,
    )

    repository = TradeRepository()

    repository.database = Mock()

    repository.save(
        trade
    )

    repository.database.execute.assert_called_once()