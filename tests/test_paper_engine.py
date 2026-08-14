from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from app.models.position import Position
from app.paper.paper_engine import PaperEngine
from app.trading.portfolio import Portfolio


def create_snapshot():

    return {
        "regime": {
            "candles": [],
        },
        "trend": {
            "candles": [],
        },
        "confirm": {
            "candles": [],
        },
        "entry": {
            "candles": [],
        },
        "timestamp": datetime.now(
            timezone.utc
        ),
    }


def test_paper_engine_opens_position():

    engine = PaperEngine(persist_state=False)

    mock_signal = Mock()

    mock_signal.action = "BUY"
    mock_signal.score = 95
    mock_signal.symbol = "BTC/USDC"

    market = {
        "entry": {
            "close": 100.0,
            "high": 101.0,
            "low": 99.0,
            "atr": 5.0,
        }
    }

    with patch.object(
        engine.signal_engine,
        "evaluate",
        return_value=mock_signal,
    ), patch.object(
        engine.market_provider,
        "next",
        return_value=(
            market,
            create_snapshot(),
        ),
    ):

        engine.process_snapshot(
            create_snapshot()
        )

    assert (
        engine.portfolio.open_positions_count
        == 1
    )


def test_paper_engine_monitors_position_during_hold_signal():
    engine = PaperEngine(persist_state=False)
    engine.shadow_tracker = Mock()
    position = Position(
        symbol="BTC/USDC",
        entry_price=100,
        quantity=1,
        stop_loss=95,
        take_profit=110,
    )
    engine.portfolio.open_positions.append(position)
    engine.broker.update = Mock(return_value=False)
    hold_signal = Mock(action="HOLD", score=0)
    market = {
        "entry": {
            "close": 100.0,
            "high": 101.0,
            "low": 99.0,
            "atr": 5.0,
        }
    }

    with patch.object(
        engine.signal_engine,
        "evaluate",
        return_value=hold_signal,
    ), patch.object(
        engine.market_provider,
        "next",
        return_value=(market, create_snapshot()),
    ):
        engine.process_snapshot(create_snapshot())

    engine.broker.update.assert_called_once()


def test_paper_engine_ignores_repeated_completed_candle():
    engine = PaperEngine(persist_state=False)
    engine.shadow_tracker = Mock()
    entry_timestamp = datetime.now(timezone.utc)
    market = {
        "entry": {
            "timestamp": entry_timestamp,
            "close": 100.0,
            "high": 101.0,
            "low": 99.0,
            "atr": 5.0,
        }
    }
    engine.signal_engine.evaluate = Mock(
        return_value=Mock(action="HOLD", score=0)
    )
    engine.market_provider.next = Mock(
        return_value=(market, create_snapshot())
    )

    engine.process_snapshot(create_snapshot())
    engine.process_snapshot(create_snapshot())

    engine.signal_engine.evaluate.assert_called_once()


def test_paper_engine_skips_stale_entry_candle():
    engine = PaperEngine(persist_state=False)
    engine.shadow_tracker = Mock()
    stale_timestamp = datetime(2020, 1, 1, tzinfo=timezone.utc)
    market = {
        "entry": {
            "timestamp": stale_timestamp,
            "close": 100.0,
            "high": 101.0,
            "low": 99.0,
            "atr": 5.0,
        }
    }
    engine.market_provider.next = Mock(
        return_value=(market, create_snapshot())
    )
    engine.signal_engine.evaluate = Mock()

    engine.process_snapshot(create_snapshot())

    engine.signal_engine.evaluate.assert_not_called()


def test_paper_engine_restores_and_saves_shared_state():
    repository = Mock()
    repository.load.return_value = Portfolio()
    engine = PaperEngine(state_repository=repository)
    engine.shadow_tracker = Mock()
    market = {
        "entry": {
            "close": 100.0,
            "high": 101.0,
            "low": 99.0,
            "atr": 5.0,
        }
    }
    engine.market_provider.next = Mock(
        return_value=(market, create_snapshot())
    )
    engine.signal_engine.evaluate = Mock(
        return_value=Mock(action="HOLD", score=0)
    )

    engine.process_snapshot(create_snapshot())

    repository.load.assert_called_once()
    repository.save.assert_called_once()
    assert repository.save.call_args.args[0] is engine.portfolio


def test_paper_engine_applies_24_hour_stop_cooldown():
    engine = PaperEngine(persist_state=False)
    engine.shadow_tracker = Mock()
    position = Position(
        symbol="BTC/USDC",
        entry_price=100,
        quantity=1,
        stop_loss=95,
        take_profit=130,
    )
    position.initial_risk = 5
    engine.portfolio.open_positions.append(position)
    observed_at = datetime.now(timezone.utc)
    market = {
        "entry": {
            "timestamp": observed_at - timedelta(minutes=15),
            "close": 95,
            "high": 100,
            "low": 94,
            "atr": 5,
        }
    }
    engine.market_provider.next = Mock(
        return_value=(
            market,
            {"timestamp": observed_at},
        )
    )
    engine.signal_engine.evaluate = Mock()

    engine.process_snapshot(create_snapshot())

    assert position.exit_reason == "STOP_LOSS"
    assert engine.cooldown_until["BTC/USDC"] == (
        observed_at + timedelta(hours=24)
    )
    engine.signal_engine.evaluate.assert_not_called()


def test_paper_engine_blocks_buy_after_maximum_drawdown():
    engine = PaperEngine(persist_state=False)
    engine.shadow_tracker = Mock()
    engine.portfolio.peak_equity = 1000
    engine.portfolio.cash = 800
    market = {
        "entry": {
            "close": 100,
            "high": 101,
            "low": 99,
            "atr": 5,
        }
    }
    engine.market_provider.next = Mock(
        return_value=(market, create_snapshot())
    )
    engine.signal_engine.evaluate = Mock(
        return_value=Mock(action="BUY", score=100)
    )
    engine.broker.open = Mock()

    engine.process_snapshot(create_snapshot())

    engine.broker.open.assert_not_called()


def test_live_reconciliation_disables_entries_when_unresolved():
    broker = Mock()
    broker.reconcile.return_value = {
        "safe": False,
        "unresolved_client_order_ids": ["entry1"],
    }
    engine = PaperEngine(
        persist_state=False,
        trading_mode="live",
        broker=broker,
    )

    result = engine.reconcile_execution()

    assert result["safe"] is False
    assert engine.entries_enabled is False
    broker.sync_balance.assert_not_called()


def test_live_reconciliation_refreshes_cash_when_safe():
    broker = Mock()
    broker.reconcile.return_value = {"safe": True}
    broker.sync_balance.return_value = 750.0
    engine = PaperEngine(
        persist_state=False,
        trading_mode="live",
        broker=broker,
    )

    result = engine.reconcile_execution()

    assert engine.entries_enabled is True
    assert result["available_cash"] == 750.0
    broker.sync_balance.assert_called_once()


def test_unresolved_live_reconciliation_blocks_buy_order():
    broker = Mock()
    engine = PaperEngine(
        persist_state=False,
        trading_mode="live",
        broker=broker,
    )
    engine.entries_enabled = False
    engine.shadow_tracker = Mock()
    market = {
        "entry": {
            "close": 100.0,
            "high": 101.0,
            "low": 99.0,
            "atr": 5.0,
        }
    }
    engine.market_provider.next = Mock(
        return_value=(market, create_snapshot())
    )
    engine.signal_engine.evaluate = Mock(
        return_value=Mock(action="BUY", score=100)
    )

    engine.process_snapshot(create_snapshot())

    broker.open.assert_not_called()
