from app.backtesting.backtest_broker import BacktestBroker
from app.config.settings import (
    ACCOUNT_SIZE,
    ATR_MULTIPLIER,
    MAX_POSITION_SIZE,
    RISK_PER_TRADE,
    RISK_REWARD_RATIO,
)
from app.risk.risk_manager import RiskManager
from app.strategy.scoring import SignalResult
from app.trading.portfolio import Portfolio


def create_signal():

    signal = SignalResult(
        symbol="BTC/USDC",
    )

    signal.action = "BUY"

    return signal


def create_indicators():

    return {
        "close": 100.0,
        "atr": 5.0,
    }


def test_trade_plan_creation():

    manager = RiskManager()

    plan = manager.create_trade_plan(
        create_signal(),
        create_indicators(),
    )

    assert plan.symbol == "BTC/USDC"
    assert plan.action == "BUY"
    assert plan.entry == 100.0


def test_stop_loss():

    manager = RiskManager()

    plan = manager.create_trade_plan(
        create_signal(),
        create_indicators(),
    )

    expected = (
        100.0
        - (5.0 * ATR_MULTIPLIER)
    )

    assert plan.stop_loss == round(
        expected,
        6,
    )


def test_take_profit():

    manager = RiskManager()

    plan = manager.create_trade_plan(
        create_signal(),
        create_indicators(),
    )

    risk = (
        plan.entry
        - plan.stop_loss
    )

    expected = (
        plan.entry
        + risk * RISK_REWARD_RATIO
    )

    assert plan.take_profit == round(
        expected,
        6,
    )


def test_position_size_limit():

    manager = RiskManager()

    plan = manager.create_trade_plan(
        create_signal(),
        create_indicators(),
    )

    assert (
        plan.position_size
        <= ACCOUNT_SIZE * MAX_POSITION_SIZE
    )


def test_invalid_risk():

    manager = RiskManager()

    indicators = {
        "close": 100,
        "atr": -5,
    }

    import pytest

    with pytest.raises(
        ValueError
    ):

        manager.create_trade_plan(
            create_signal(),
            indicators,
        )


def test_risk_reward_ratio():

    manager = RiskManager()

    plan = manager.create_trade_plan(
        create_signal(),
        create_indicators(),
    )

    assert (
        plan.risk_reward
        == RISK_REWARD_RATIO
    )


def test_capital_at_risk():

    manager = RiskManager()

    plan = manager.create_trade_plan(
        create_signal(),
        create_indicators(),
    )

    max_position = (
        ACCOUNT_SIZE
        * MAX_POSITION_SIZE
    )

    capital_at_risk = (
        ACCOUNT_SIZE
        * RISK_PER_TRADE
    )

    assert plan.position_size > 0
    assert plan.position_size <= max_position
    assert capital_at_risk > 0


def test_full_stop_includes_fees_and_slippage_in_risk_budget():
    portfolio = Portfolio()
    plan = RiskManager().create_trade_plan(
        create_signal(),
        create_indicators(),
    )
    broker = BacktestBroker(portfolio)
    position = broker.open(plan, opened_at=0)

    assert position is not None
    broker.close(position, position.stop_loss, "STOP_LOSS", timestamp=1)

    risk_budget = ACCOUNT_SIZE * RISK_PER_TRADE
    assert abs(position.realized_pnl) <= risk_budget + 0.01


def test_minimum_stop_distance_handles_low_volatility():

    manager = RiskManager()

    plan = manager.create_trade_plan(
        create_signal(),
        {
            "close": 100.0,
            "atr": 0.01,
        },
    )

    # Nominally valid, but not economically viable after Kraken's conservative
    # taker/taker round-trip costs.
    assert plan is None
