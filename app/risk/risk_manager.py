from app.config.settings import (
    ACCOUNT_SIZE,
    ATR_MULTIPLIER,
    MAX_POSITION_SIZE,
    MIN_STOP_DISTANCE_PCT,
    RISK_PER_TRADE,
    RISK_REWARD_RATIO,
    SLIPPAGE,
    TRADING_FEE,
)
from app.core.logger import logger
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


        stop_distance = max(
            atr * ATR_MULTIPLIER,
            entry * MIN_STOP_DISTANCE_PCT,
        )


        stop_loss = (
            entry
            - stop_distance
        )


        risk = stop_distance


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


        # Small ATR targets can be nominally profitable while losing money
        # after round-trip fees and slippage. Reject them before entry.
        execution_entry = (
            entry
            * (1 + SLIPPAGE)
        )

        execution_target = (
            execution_entry
            + risk * RISK_REWARD_RATIO
        ) * (1 - SLIPPAGE)

        quantity = (
            position_size
            / execution_entry
        )

        expected_net_profit = (
            (
                execution_target
                - execution_entry
            )
            * quantity
            - position_size * TRADING_FEE
            - execution_target
            * quantity
            * TRADING_FEE
        )

        if expected_net_profit <= 0:
            logger.debug(
                "Trade rejected: target does not cover "
                "fees and slippage (expected net=%s)",
                expected_net_profit,
            )
            return None


        logger.debug(
            "RISK | ENTRY=%s ATR=%s SL=%s TP=%s RISK=%s POSITION=%s",
            entry,
            atr,
            stop_loss,
            take_profit,
            risk,
            position_size,
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
