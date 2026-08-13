from datetime import datetime, timezone

from app.models.position import Position
from app.storage import database as database_module
from app.storage.paper_state_repository import PaperStateRepository
from app.trading.portfolio import Portfolio


def test_paper_state_round_trip_preserves_risk_state(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        database_module,
        "DATABASE_PATH",
        tmp_path / "paper-state.db",
    )
    repository = PaperStateRepository()
    portfolio = Portfolio()
    position = Position(
        symbol="BTC/USDC",
        entry_price=100,
        quantity=2,
        stop_loss=102,
        take_profit=130,
        opened_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    position.current_price = 110
    position.highest_price = 115
    position.initial_risk = 10
    position.trailing_stop = 102
    position.break_even = True
    position.entry_fee = 0.2
    portfolio.cash = 799.8
    portfolio.open_positions.append(position)

    repository.save(portfolio)
    restored = repository.load()

    assert restored.cash == 799.8
    assert len(restored.open_positions) == 1
    restored_position = restored.open_positions[0]
    assert restored_position.opened_at == position.opened_at
    assert restored_position.highest_price == 115
    assert restored_position.initial_risk == 10
    assert restored_position.trailing_stop == 102
    assert restored_position.break_even is True
    assert restored_position.entry_fee == 0.2
