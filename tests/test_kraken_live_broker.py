from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from app.execution.kraken_live_broker import KrakenLiveBroker
from app.models.trade_plan import TradePlan
from app.storage.exchange_position_repository import ExchangePositionRepository
from app.trading.portfolio import Portfolio

NOW = datetime(2026, 8, 15, tzinfo=timezone.utc)


def plan():
    return TradePlan(
        symbol="BTC/EUR",
        action="BUY",
        entry=100.0,
        stop_loss=98.0,
        take_profit=104.0,
        position_size=10.0,
        risk_reward=2.0,
    )


def filled(order_id, price, amount=0.1, fee=0.01):
    return {
        "id": order_id,
        "status": "closed",
        "filled": amount,
        "remaining": 0,
        "average": price,
        "fee": {"cost": fee},
    }


def open_stop(order_id="stop-1"):
    return {
        "id": order_id,
        "status": "open",
        "type": "stop-loss",
        "filled": 0,
        "info": {"refid": "entry-order", "ordertype": "stop-loss"},
    }


def create_broker(*orders):
    gateway = Mock()
    gateway.submit_market_order.side_effect = list(orders)
    gateway.order_repository = Mock()
    gateway.reconcile_intents.return_value = {"safe": True, "resolved": 0}
    gateway.client.find_attached_stop.return_value = open_stop()
    gateway.client.get_balance.return_value = {
        "free": {"EUR": 20.0},
        "total": {"BTC": 1.0, "EUR": 20.0},
    }
    gateway.client.fetch_open_orders.return_value = []
    breaker = Mock()
    breaker.can_open.return_value = (True, None)
    identifiers = iter(("kentry-1", "kprotect-1", "kexit-1", "kextra-1"))
    broker = KrakenLiveBroker(
        Portfolio(initial_balance=20.0),
        gateway,
        ExchangePositionRepository(),
        id_factory=lambda prefix: next(identifiers),
        circuit_breaker=breaker,
    )
    return broker, gateway


def test_confirmed_entry_is_persisted_and_native_stop_is_discovered():
    broker, gateway = create_broker(filled("entry-order", 101.0))

    position = broker.open(plan(), NOW)

    assert position is not None
    assert position.entry_price == 101.0
    assert round(position.stop_loss, 2) == 98.98
    assert round(position.take_profit, 2) == 105.04
    stored = broker.positions.find_active("BTC/EUR")
    assert stored["status"] == "OPEN"
    assert stored["protection_status"] == "ACTIVE"
    assert stored["protection_order_id"] == "stop-1"
    gateway.submit_market_order.assert_called_once()


def test_partial_entry_does_not_invent_position():
    partial = {
        "id": "entry-order",
        "status": "open",
        "filled": 0.05,
        "remaining": 0.05,
        "average": 101.0,
    }
    broker, _ = create_broker(partial)

    assert broker.open(plan(), NOW) is None
    assert broker.portfolio.open_positions == []
    assert broker.positions.find_active("BTC/EUR")["status"] == "PENDING_ENTRY"


def test_take_profit_cancels_stop_before_market_sell():
    broker, gateway = create_broker(
        filled("entry-order", 100.0),
        filled("exit-order", 104.0),
    )
    position = broker.open(plan(), NOW)
    gateway.client.fetch_order.side_effect = [
        open_stop(),
        {"id": "stop-1", "status": "canceled", "type": "stop-loss"},
    ]

    closed = broker.update(position, 104.0, 104.0, 104.0, NOW)

    assert closed is True
    gateway.client.cancel_order.assert_called_once_with("stop-1", "BTC/EUR")
    assert gateway.submit_market_order.call_count == 2
    assert position.exit_reason == "TAKE_PROFIT"
    assert broker.portfolio.open_positions == []


def test_maximum_hold_cancels_stop_before_market_sell():
    broker, gateway = create_broker(
        filled("entry-order", 100.0),
        filled("exit-order", 100.5),
    )
    position = broker.open(plan(), NOW - timedelta(hours=25))
    gateway.client.fetch_order.side_effect = [
        open_stop(),
        {"id": "stop-1", "status": "canceled", "type": "stop-loss"},
    ]

    closed = broker.update(position, 100.5, 100.5, 100.5, NOW)

    assert closed is True
    gateway.client.cancel_order.assert_called_once_with("stop-1", "BTC/EUR")
    assert gateway.submit_market_order.call_count == 2
    assert position.exit_reason == "MAX_HOLD_TIME"
    assert broker.portfolio.open_positions == []


def test_take_profit_has_priority_when_maximum_hold_is_reached():
    broker, gateway = create_broker(
        filled("entry-order", 100.0),
        filled("exit-order", 104.0),
    )
    position = broker.open(plan(), NOW - timedelta(hours=25))
    gateway.client.fetch_order.side_effect = [
        open_stop(),
        {"id": "stop-1", "status": "canceled", "type": "stop-loss"},
    ]

    broker.update(position, 104.0, 104.0, 104.0, NOW)

    assert position.exit_reason == "TAKE_PROFIT"


def test_filled_native_stop_closes_persisted_position():
    broker, gateway = create_broker(filled("entry-order", 100.0))
    position = broker.open(plan(), NOW)
    gateway.client.fetch_order.return_value = filled("stop-1", 98.0)

    result = broker.reconcile()

    assert result["safe"] is True
    assert position.exit_reason == "STOP_LOSS"
    assert broker.portfolio.open_positions == []


def test_missing_attached_stop_makes_reconciliation_unsafe():
    broker, gateway = create_broker(filled("entry-order", 100.0))
    gateway.client.find_attached_stop.return_value = None
    broker.open(plan(), NOW)

    result = broker.reconcile()

    assert result["safe"] is False
    assert result["unprotected_symbols"] == ["BTC/EUR"]


def test_restart_restores_confirmed_position():
    repository = ExchangePositionRepository()
    repository.prepare_entry("kentry-1", "BTC/EUR", 0.1, 100, 98, 104)
    repository.activate(
        "kentry-1", "entry-order", 0.1, 100, 0.01, 98, 104, NOW
    )

    broker = KrakenLiveBroker(Portfolio(initial_balance=20), Mock(), repository)

    assert len(broker.portfolio.open_positions) == 1
    assert broker.portfolio.open_positions[0].entry_price == 100
