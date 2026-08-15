from pathlib import Path

from app.storage import database as database_module


def test_kraken_live_database_is_isolated_from_legacy_state(monkeypatch):
    monkeypatch.setattr(
        database_module,
        "DATABASE_PATH",
        Path("data/trading.db"),
    )

    assert database_module.mode_database_path("kraken-live") == Path(
        "data/trading-kraken-live.db"
    )
