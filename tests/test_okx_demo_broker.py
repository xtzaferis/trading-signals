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
    identifiers = iter(("entry1", "exit1", "extra1"))
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


def test_take_profit_submits_sell_and_closes_from_fill():
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

    assert closed is True
    assert len(broker.portfolio.closed_positions) == 1
    assert position.exit_reason == "TAKE_PROFIT"
    assert round(position.realized_pnl, 8) == 20.8
    assert broker.positions.find_active("BTC/USDC") is None
    assert gateway.submit_market_order.call_count == 2


def test_stop_loss_submits_sell_with_stop_reason():
    broker, _ = create_broker(
        filled_order("order-entry", 101.0),
        filled_order("order-exit", 90.0),
    )
    position = broker.open(trade_plan(), NOW)

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
    broker = OKXDemoBroker(Portfolio(), gateway, positions)

    result = broker.reconcile()

    assert result["restored_entries"] == 1
    restored = broker.portfolio.open_positions[0]
    assert restored.entry_price == 101
    assert restored.entry_fee == 0.15


def test_rejected_exit_returns_position_to_open_for_next_retry():
    broker, gateway = create_broker(filled_order("order-entry", 101.0))
    position = broker.open(trade_plan(), NOW)
    gateway.submit_market_order.side_effect = OrderValidationError(
        "insufficient balance"
    )

    with pytest.raises(OrderValidationError):
        broker.update(position, high=102, low=90, close=90, timestamp=NOW)

    stored = broker.positions.find_active("BTC/USDC")
    assert stored["status"] == "OPEN"
    assert stored["exit_client_order_id"] is None
