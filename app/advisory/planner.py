from dataclasses import dataclass

from app.config.settings import (
    ADVISORY_FUTURES_FEE,
    ADVISORY_FUTURES_SLIPPAGE,
    ATR_MULTIPLIER,
    MIN_NET_RISK_REWARD,
    MIN_STOP_DISTANCE_PCT,
    RISK_REWARD_RATIO,
)


@dataclass(frozen=True)
class AdvisoryLevels:
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    net_risk_reward: float


class FuturesAdvisoryPlanner:
    """Calculate indicative levels; it does not size or create an order."""

    def create(self, direction: str, entry_data) -> AdvisoryLevels | None:
        entry = float(entry_data["close"])
        atr = float(entry_data.get("atr") or 0.0)
        if entry <= 0 or atr <= 0:
            return None
        distance = max(atr * ATR_MULTIPLIER, entry * MIN_STOP_DISTANCE_PCT)
        if direction == "LONG":
            stop = entry - distance
            target = entry + distance * RISK_REWARD_RATIO
            net_reward, net_risk = self._long_outcomes(entry, target, stop)
        elif direction == "SHORT":
            stop = entry + distance
            target = entry - distance * RISK_REWARD_RATIO
            if target <= 0:
                return None
            net_reward, net_risk = self._short_outcomes(entry, target, stop)
        else:
            return None
        net_rr = net_reward / net_risk if net_risk > 0 else 0.0
        if net_reward <= 0 or net_rr < MIN_NET_RISK_REWARD:
            return None
        return AdvisoryLevels(
            direction=direction,
            entry=round(entry, 8),
            stop_loss=round(stop, 8),
            take_profit=round(target, 8),
            net_risk_reward=round(net_rr, 4),
        )

    @staticmethod
    def _long_outcomes(entry: float, target: float, stop: float):
        opened = entry * (1 + ADVISORY_FUTURES_SLIPPAGE)
        won = target * (1 - ADVISORY_FUTURES_SLIPPAGE)
        lost = stop * (1 - ADVISORY_FUTURES_SLIPPAGE)
        reward = won - opened - (opened + won) * ADVISORY_FUTURES_FEE
        risk = opened - lost + (opened + lost) * ADVISORY_FUTURES_FEE
        return reward, risk

    @staticmethod
    def _short_outcomes(entry: float, target: float, stop: float):
        opened = entry * (1 - ADVISORY_FUTURES_SLIPPAGE)
        won = target * (1 + ADVISORY_FUTURES_SLIPPAGE)
        lost = stop * (1 + ADVISORY_FUTURES_SLIPPAGE)
        reward = opened - won - (opened + won) * ADVISORY_FUTURES_FEE
        risk = lost - opened + (opened + lost) * ADVISORY_FUTURES_FEE
        return reward, risk
