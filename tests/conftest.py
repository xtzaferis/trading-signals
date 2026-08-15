import os
from pathlib import Path
from uuid import uuid4

import pytest

# Unit tests must never inherit operational exchange mode or safety switches
# from the developer's real .env file.
os.environ["TRADING_MODE"] = "paper"
os.environ["EMERGENCY_STOP"] = "false"
os.environ["QUOTE_CURRENCY"] = "USDC"
os.environ["LIVE_TRADING_ENABLED"] = "false"
os.environ["LIVE_CANARY_ENABLED"] = "false"
os.environ["LIVE_CANARY_CONFIRMATION"] = ""

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
