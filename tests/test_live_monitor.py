import json
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from app.live.monitor import (
    log_monitor_result,
    monitor_once,
    write_health_safely,
    write_health_snapshot,
)
from app.live.monitor_alerts import MonitorAlerts
from app.models.position import Position


def _broker(price=102.0, closes=False):
    position = Position(
        symbol="BTC/EUR",
        entry_price=100.0,
        quantity=0.1,
        stop_loss=98.0,
        take_profit=104.0,
    )
    broker = Mock()
    broker.reconcile.return_value = {"safe": True}
    broker.portfolio.open_positions = [position]
    broker.portfolio.closed_positions = []
    broker.positions.pending_entries.return_value = []
    broker.gateway.client.get_ticker.return_value = {
        "last": price,
        "datetime": datetime(2026, 8, 15, tzinfo=timezone.utc),
    }
    broker.update.return_value = closes
    if closes:
        broker.update.side_effect = lambda *args: (
            broker.portfolio.open_positions.clear() or True
        )
    return broker


def test_monitor_once_reports_price_and_exit_distances():
    result = monitor_once(_broker())

    position = result["positions"][0]
    assert position["price"] == 102.0
    assert position["unrealized_pnl"] == pytest.approx(0.2)
    assert round(position["return_pct"], 2) == 2.0
    assert round(position["distance_to_stop_pct"], 2) == 4.08
    assert round(position["distance_to_target_pct"], 2) == 1.96


def test_monitor_once_reports_closed_symbol():
    result = monitor_once(_broker(price=104.0, closes=True))

    assert result["closed_symbols"] == ["BTC/EUR"]
    assert result["open_positions"] == 0


def test_health_snapshot_is_machine_readable(tmp_path):
    result = monitor_once(_broker())
    path = tmp_path / "health.json"

    write_health_snapshot(result, "healthy", path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "healthy"
    assert payload["safe"] is True
    assert payload["positions"][0]["take_profit"] == 104.0


def test_health_snapshot_failure_does_not_escape(monkeypatch):
    monkeypatch.setattr(
        "app.live.monitor.write_health_snapshot",
        Mock(side_effect=OSError("disk unavailable")),
    )

    assert write_health_safely(None, "error") is False


def test_webhook_alerts_are_deduplicated_within_cooldown():
    response = Mock()
    sender = Mock(return_value=response)
    clock = Mock(return_value=datetime(2026, 8, 15, tzinfo=timezone.utc))
    alerts = MonitorAlerts(
        "https://alerts.example.test",
        sender=sender,
        clock=clock,
    )

    assert alerts.send("unsafe", "Unsafe") is True
    assert alerts.send("unsafe", "Unsafe") is False
    sender.assert_called_once()
    response.raise_for_status.assert_called_once()


def test_log_result_includes_tp_and_sl(caplog):
    result = monitor_once(_broker())

    log_monitor_result(result)

    assert "sl=98.00" in caplog.text
    assert "tp=104.00" in caplog.text
