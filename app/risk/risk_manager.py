from app.config.settings import (
    ACCOUNT_SIZE,
    ATR_MULTIPLIER,
    MAX_POSITION_SIZE,
    RISK_PER_TRADE,
    RISK_REWARD_RATIO,
)
from app.models.trade_plan import TradePlan


class RiskManager:

    def create_trade_plan(
        self,
        signal,
        indicators,
    ):

        entry = float(indicators["close"])

        atr = float(indicators["atr"])

        stop_loss = entry - (
            atr * ATR_MULTIPLIER
        )

        risk = entry - stop_loss

        if risk <= 0:
            raise ValueError(
                "Invalid risk calculation."
            )

        take_profit = entry + (
            risk * RISK_REWARD_RATIO
        )

        capital_at_risk = (
            ACCOUNT_SIZE * RISK_PER_TRADE
        )

        # units implied by the capital we're willing to risk
        units = capital_at_risk / risk

        # position value (cash) = units * entry price
        position_value = units * entry

        max_position_value = (
            ACCOUNT_SIZE * MAX_POSITION_SIZE
        )

        # cap position value to maximum allowed position size (as cash)
        position_value = min(
            position_value,
            max_position_value,
        )

        position_size = position_value

        return TradePlan(
            symbol=signal.symbol,
            action=signal.action,
            entry=round(entry, 6),
            stop_loss=round(stop_loss, 6),
            take_profit=round(take_profit, 6),
            position_size=round(position_size, 2),
            risk_reward=RISK_REWARD_RATIO,
        )