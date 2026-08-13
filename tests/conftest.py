from pathlib import Path
from uuid import uuid4

import pytest

from app.storage import database as storage_database


@pytest.fixture(autouse=True)
def isolate_trading_database(monkeypatch):
    """Prevent tests from reading or mutating forward-paper state."""

    database_dir = Path(".pytest_cache") / "test_databases"
    database_dir.mkdir(parents=True, exist_ok=True)
    database_path = database_dir / f"trading-{uuid4().hex}.db"
    monkeypatch.setattr(
        storage_database,
        "DATABASE_PATH",
        database_path,
    )
    return database_path
