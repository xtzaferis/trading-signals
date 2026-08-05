from app.config.settings import (
    ACCOUNT_SIZE,
    ATR_MULTIPLIER,
    MAX_POSITION_SIZE,
    RISK_PER_TRADE,
    RISK_REWARD_RATIO,
)
from app.risk.trade_plan import TradePlan


class RiskManager:

    def create_trade_plan(
        self,
        signal,
        indicators,
    ):

        if signal.action != "BUY":
            return None

        entry = float(indicators["close"])

        atr = float(indicators["atr"])

        stop_loss = entry - (atr * ATR_MULTIPLIER)

        risk = entry - stop_loss

        take_profit = entry + (
            risk * RISK_REWARD_RATIO
        )

        capital_at_risk = (
            ACCOUNT_SIZE * RISK_PER_TRADE
        )

        position_size = capital_at_risk / risk

        max_position = (
            ACCOUNT_SIZE * MAX_POSITION_SIZE
        )

        position_size = min(
            position_size,
            max_position,
        )

        return TradePlan(
            symbol=signal.symbol,
            action=signal.action,
            entry=round(entry, 6),
            stop_loss=round(stop_loss, 6),
            take_profit=round(take_profit, 6),
            position_size=round(position_size, 2),
            risk_reward=RISK_REWARD_RATIO,
        )