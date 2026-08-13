from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from app.exceptions import OrderValidationError
from app.execution.okx_demo_broker import OKXDemoBroker
from app.models.trade_plan import TradePlan
from app.storage.exchange_order_repository import ExchangeOrderRepository
from app.storage.exchange_position_repository import (
    ExchangePositionRepository,
)
from app.trading.portfolio import Portfolio

NOW = datetime(2026, 8, 13, tzinfo=timezone.utc)


def trade_plan():
    return TradePlan(
        symbol="BTC/USDC",
        action="BUY",
        entry=100.0,
        stop_loss=90.0,
        take_profit=120.0,
        position_size=100.0,
        risk_reward=2.0,
    )


def filled_order(order_id, price, amount=1.0, fee=0.1):
    return {
        "id": order_id,
        "status": "closed",
        "filled": amount,
        "remaining": 0,
        "average": price,
        "fee": {"cost": fee},
    }


def create_broker(*orders):
    gateway = Mock()
    gateway.submit_market_order.side_effect = list(orders)
    gateway.order_repository = Mock()
    gateway.client.create_protective_oco.return_value = {
        "id": "protection-order",
        "status": "open",
    }
    gateway.client.get_balance.return_value = {
        "free": {"USDC": 1000.0},
        "total": {"BTC": 10.0, "USDC": 1000.0},
    }
    identifiers = iter(("entry1", "protect1", "exit1", "extra1"))
    broker = OKXDemoBroker(
        Portfolio(),
        gateway,
        ExchangePositionRepository(),
        id_factory=lambda prefix: next(identifiers),
    )
    return broker, gateway


def test_confirmed_entry_fill_creates_position_from_actual_fill():
    broker, gateway = create_broker(filled_order("order-entry", 101.0))

    position = broker.open(trade_plan(), NOW)

    assert position is not None
    assert position.entry_price == 101.0
    assert position.quantity == 1.0
    assert position.stop_loss == 91.0
    assert position.take_profit == 121.0
    assert position.entry_fee == 0.1
    assert broker.positions.find_active("BTC/USDC")["status"] == "OPEN"
    gateway.submit_market_order.assert_called_once()


def test_partial_entry_fill_does_not_invent_open_position():
    partial = {
        "id": "order-entry",
        "status": "open",
        "filled": 0.5,
        "remaining": 0.5,
        "average": 101.0,
    }
    broker, _ = create_broker(partial)

    position = broker.open(trade_plan(), NOW)

    assert position is None
    assert broker.portfolio.open_positions == []
    assert broker.positions.find_active("BTC/USDC")["status"] == (
        "PENDING_ENTRY"
    )


def test_active_native_protection_prevents_duplicate_take_profit_sell():
    broker, gateway = create_broker(
        filled_order("order-entry", 101.0),
        filled_order("order-exit", 122.0),
    )
    position = broker.open(trade_plan(), NOW)

    closed = broker.update(
        position,
        high=122.0,
        low=100.0,
        close=122.0,
        timestamp=NOW,
    )

    assert closed is False
    assert len(broker.portfolio.closed_positions) == 0
    assert gateway.submit_market_order.call_count == 1


def test_failed_native_protection_uses_application_stop_fallback():
    broker, _ = create_broker(
        filled_order("order-entry", 101.0),
        filled_order("order-exit", 90.0),
    )
    position = broker.open(trade_plan(), NOW)
    stored = broker.positions.find_active("BTC/USDC")
    broker.positions.record_protection(
        stored["entry_client_order_id"], "FAILED", error="order failed"
    )

    closed = broker.update(
        position,
        high=102.0,
        low=90.0,
        close=90.0,
        timestamp=NOW,
    )

    assert closed is True
    assert position.exit_reason == "STOP_LOSS"


def test_restart_restores_confirmed_open_position():
    repository = ExchangePositionRepository()
    repository.prepare_entry("entry1", "BTC/USDC", 1, 100, 90, 120)
    repository.activate(
        "entry1", "exchange-entry", 1, 101, 0.1, 91, 121, NOW
    )

    broker = OKXDemoBroker(
        Portfolio(),
        Mock(),
        repository,
    )

    assert len(broker.portfolio.open_positions) == 1
    restored = broker.portfolio.open_positions[0]
    assert restored.entry_price == 101
    assert restored.stop_loss == 91


def test_reconciliation_activates_recovered_entry_with_fee():
    positions = ExchangePositionRepository()
    positions.prepare_entry("entry1", "BTC/USDC", 1, 100, 90, 120)
    orders = ExchangeOrderRepository()
    orders.prepare("entry1", "BTC/USDC", "buy", "market", 1, 100)
    orders.record_order(
        "entry1",
        filled_order("exchange-entry", 101.0, fee=0.15),
    )
    gateway = Mock()
    gateway.order_repository = orders
    gateway.reconcile_intents.return_value = {
        "resolved": 1,
        "unresolved_client_order_ids": [],
        "safe": True,
    }
    gateway.client.get_balance.return_value = {
        "total": {"BTC": 1.0, "USDC": 1000.0}
    }
    broker = OKXDemoBroker(Portfolio(), gateway, positions)

    result = broker.reconcile()

    assert result["restored_entries"] == 1
    restored = broker.portfolio.open_positions[0]
    assert restored.entry_price == 101
    assert restored.entry_fee == 0.15


def test_rejected_exit_returns_position_to_open_for_next_retry():
    broker, gateway = create_broker(filled_order("order-entry", 101.0))
    position = broker.open(trade_plan(), NOW)
    stored = broker.positions.find_active("BTC/USDC")
    broker.positions.record_protection(
        stored["entry_client_order_id"], "FAILED", error="order failed"
    )
    gateway.submit_market_order.side_effect = OrderValidationError(
        "insufficient balance"
    )

    with pytest.raises(OrderValidationError):
        broker.update(position, high=102, low=90, close=90, timestamp=NOW)

    stored = broker.positions.find_active("BTC/USDC")
    assert stored["status"] == "OPEN"
    assert stored["exit_client_order_id"] is None


def test_demo_balance_sets_available_cash_ceiling():
    broker, gateway = create_broker()
    gateway.client.get_balance.return_value = {
        "free": {"USDC": 432.10}
    }

    available = broker.sync_balance()

    assert available == 432.10
    assert broker.portfolio.available_cash == 432.10


def test_demo_balance_is_capped_at_configured_bot_allocation():
    broker, gateway = create_broker()
    gateway.client.get_balance.return_value = {
        "free": {"USDC": 100_000.0}
    }

    available = broker.sync_balance()

    assert available == broker.portfolio.initial_balance


def test_demo_balance_cap_accounts_for_committed_position_cash():
    broker, gateway = create_broker(filled_order("order-entry", 101.0))
    broker.open(trade_plan(), NOW)
    gateway.client.get_balance.return_value = {
        "free": {"USDC": 100_000.0}
    }

    available = broker.sync_balance()

    assert available == pytest.approx(898.9)


def test_live_native_protection_keeps_reconciliation_safe():
    broker, gateway = create_broker(filled_order("order-entry", 101.0))
    broker.open(trade_plan(), NOW)
    gateway.reconcile_intents.return_value = {"safe": True, "resolved": 0}
    gateway.client.find_protective_oco.return_value = {
        "id": "algo1",
        "status": "open",
        "info": {"state": "live", "algoClOrdId": "protect1"},
    }

    result = broker.reconcile()

    assert result["safe"] is True
    assert result["unprotected_symbols"] == []


def test_missing_native_protection_blocks_new_entries():
    broker, gateway = create_broker(filled_order("order-entry", 101.0))
    broker.open(trade_plan(), NOW)
    gateway.reconcile_intents.return_value = {"safe": True, "resolved": 0}
    gateway.client.find_protective_oco.return_value = None

    result = broker.reconcile()

    assert result["safe"] is False
    assert result["unprotected_symbols"] == ["BTC/USDC"]


def test_rejected_native_protection_is_persisted_as_failed():
    broker, gateway = create_broker(filled_order("order-entry", 101.0))
    gateway.client.create_protective_oco.side_effect = OrderValidationError(
        "invalid protection"
    )

    with pytest.raises(OrderValidationError, match="invalid protection"):
        broker.open(trade_plan(), NOW)

    stored = broker.positions.find_active("BTC/USDC")
    assert stored["status"] == "OPEN"
    assert stored["protection_status"] == "FAILED"


def test_triggered_oco_closes_position_from_exact_exchange_fills():
    broker, gateway = create_broker(filled_order("order-entry", 101.0))
    position = broker.open(trade_plan(), NOW)
    gateway.reconcile_intents.return_value = {"safe": True, "resolved": 0}
    gateway.client.find_protective_oco.return_value = {
        "id": "algo1",
        "status": "closed",
        "info": {
            "state": "effective",
            "ordId": "exit-order",
            "actualSide": "tp",
        },
    }
    gateway.client.fetch_order_execution.return_value = {
        "order_id": "exit-order",
        "filled": 1.0,
        "cost": 122.0,
        "average": 122.0,
        "fees": [{"cost": 0.2, "currency": "USDC"}],
    }

    result = broker.reconcile()

    assert result["safe"] is True
    assert result["unprotected_symbols"] == []
    assert broker.portfolio.open_positions == []
    assert position.exit_reason == "TAKE_PROFIT"
    assert position.realized_pnl == 20.7


def test_balance_mismatch_blocks_reconciliation():
    broker, gateway = create_broker(filled_order("order-entry", 101.0))
    broker.open(trade_plan(), NOW)
    gateway.reconcile_intents.return_value = {"safe": True, "resolved": 0}
    gateway.client.find_protective_oco.return_value = {
        "id": "algo1",
        "status": "open",
        "info": {"state": "live"},
    }
    gateway.client.get_balance.return_value = {
        "total": {"BTC": 0.5, "USDC": 1000.0}
    }

    result = broker.reconcile()

    assert result["safe"] is False
    assert result["balance_mismatches"] == ["BTC/USDC"]
