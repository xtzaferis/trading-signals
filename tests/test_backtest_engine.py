from unittest.mock import Mock

from app.backtesting.backtest_broker import (
    BacktestBroker,
)
from app.risk.risk_manager import (
    RiskManager,
)
from app.strategy.scoring import (
    SignalResult,
)
from app.trading.portfolio import (
    Portfolio,
)


def test_buy_signal_opens_position():

    portfolio = Portfolio()

    broker = BacktestBroker(
        portfolio
    )

    risk = RiskManager()

    signal = SignalResult(
        symbol="BTC/USDC",
        action="BUY",
    )

    indicators = {
        "close": 100.0,
        "atr": 5.0,
    }

    trade_plan = (
        risk.create_trade_plan(
            signal,
            indicators,
        )
    )

    position = broker.open(
        trade_plan,
        opened_at=Mock(),
    )

    assert position is not None

    assert (
        portfolio.open_positions_count
        == 1
    )

    assert (
        portfolio.has_open_position(
            "BTC/USDC"
        )
    )