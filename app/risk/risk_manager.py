from app.config.settings import (
    ACCOUNT_SIZE,
    ATR_MULTIPLIER,
    MAX_POSITION_SIZE,
    RISK_PER_TRADE,
    RISK_REWARD_RATIO,
)
from app.models.trade_plan import (
    TradePlan,
)


class RiskManager:

    def create_trade_plan(
        self,
        signal,
        indicators,
        available_cash: float | None = None,
    ):

        entry = float(
            indicators["close"]
        )

        atr = float(
            indicators.get(
                "atr",
                0.0,
            )
        )


        if atr <= 0:

            raise ValueError(
                "Invalid ATR value."
            )


        stop_loss = (
            entry
            -
            (
                atr
                *
                ATR_MULTIPLIER
            )
        )


        risk = (
            entry
            -
            stop_loss
        )


        if risk <= 0:

            raise ValueError(
                "Invalid risk calculation."
            )


        take_profit = (
            entry
            +
            (
                risk
                *
                RISK_REWARD_RATIO
            )
        )


        capital = (
            available_cash
            if available_cash is not None
            else ACCOUNT_SIZE
        )


        capital_at_risk = (
            capital
            *
            RISK_PER_TRADE
        )


        units = (
            capital_at_risk
            /
            risk
        )


        position_value = (
            units
            *
            entry
        )


        max_position_value = (
            capital
            *
            MAX_POSITION_SIZE
        )


        position_value = min(
            position_value,
            max_position_value,
        )


        position_size = (
            position_value
        )


        print(
            "RISK DEBUG |",
            f"ENTRY={entry}",
            f"ATR={atr}",
            f"SL={stop_loss}",
            f"TP={take_profit}",
            f"RISK={risk}",
            f"POSITION={position_size}",
        )


        return TradePlan(

            symbol=signal.symbol,

            action=signal.action,

            entry=round(
                entry,
                6,
            ),

            stop_loss=round(
                stop_loss,
                6,
            ),

            take_profit=round(
                take_profit,
                6,
            ),

            position_size=round(
                position_size,
                2,
            ),

            risk_reward=(
                RISK_REWARD_RATIO
            ),
        )