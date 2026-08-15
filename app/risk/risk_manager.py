from app.config.settings import (
    ACCOUNT_SIZE,
    ATR_MULTIPLIER,
    MAX_POSITION_SIZE,
    MIN_NET_RISK_REWARD,
    MIN_STOP_DISTANCE_PCT,
    RISK_PER_TRADE,
    RISK_REWARD_RATIO,
)
from app.core.logger import logger
from app.models.trade_plan import (
    TradePlan,
)
from app.trading.execution_costs import BACKTEST_COSTS


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


        costs = BACKTEST_COSTS
        execution_entry = costs.buy_price(entry)
        broker_stop = execution_entry - risk
        execution_stop = costs.sell_price(broker_stop)
        loss_per_unit = (
            execution_entry
            - execution_stop
            + costs.entry_fee_cost(execution_entry, 1.0)
            + costs.exit_fee_cost(execution_stop, 1.0)
        )

        units = capital_at_risk / loss_per_unit


        position_value = (
            units * execution_entry
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
        execution_target = (
            execution_entry
            + risk * RISK_REWARD_RATIO
        )
        execution_target = costs.sell_price(execution_target)

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
            - costs.entry_fee_cost(execution_entry, quantity)
            - costs.exit_fee_cost(execution_target, quantity)
        )

        expected_net_loss = loss_per_unit * quantity
        net_risk_reward = expected_net_profit / expected_net_loss

        if expected_net_profit <= 0 or net_risk_reward < MIN_NET_RISK_REWARD:
            logger.debug(
                "Trade rejected: net reward/risk %.3f is below %.3f "
                "(expected net=%s)",
                net_risk_reward,
                MIN_NET_RISK_REWARD,
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
            net_risk_reward=round(net_risk_reward, 4),
        )
