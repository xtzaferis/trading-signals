from app.risk import execution_circuit_breaker as breaker_module
from app.risk.execution_circuit_breaker import ExecutionCircuitBreaker


def test_daily_loss_blocks_new_entries(monkeypatch):
    monkeypatch.setattr(breaker_module, "MAX_DAILY_LOSS_PCT", 0.02)
    breaker = ExecutionCircuitBreaker("exchange_test")
    breaker.record_trade(-21.0, 1000.0)

    allowed, reason = breaker.can_open(979.0, 2.1)

    assert allowed is False
    assert reason == "MAX_DAILY_LOSS"


def test_consecutive_losses_survive_new_instance(monkeypatch):
    monkeypatch.setattr(breaker_module, "MAX_CONSECUTIVE_LOSSES", 2)
    first = ExecutionCircuitBreaker("exchange_test")
    first.record_trade(-1.0, 1000.0)
    first.record_trade(-1.0, 999.0)

    restored = ExecutionCircuitBreaker("exchange_test")
    allowed, reason = restored.can_open(998.0, 0.2)

    assert allowed is False
    assert reason == "MAX_CONSECUTIVE_LOSSES"


def test_order_limit_reserves_entry_and_protection_capacity(monkeypatch):
    monkeypatch.setattr(breaker_module, "MAX_EXCHANGE_ORDERS_PER_DAY", 3)
    breaker = ExecutionCircuitBreaker("exchange_test")
    breaker.record_order(1000.0)
    breaker.record_order(1000.0)

    allowed, reason = breaker.can_open(1000.0, 0.0, projected_orders=2)

    assert allowed is False
    assert reason == "MAX_DAILY_ORDERS"


def test_emergency_stop_blocks_entries_but_is_reported(monkeypatch):
    monkeypatch.setattr(breaker_module, "EMERGENCY_STOP", True)
    breaker = ExecutionCircuitBreaker("exchange_test")

    allowed, reason = breaker.can_open(1000.0, 0.0)

    assert allowed is False
    assert reason == "EMERGENCY_STOP"
