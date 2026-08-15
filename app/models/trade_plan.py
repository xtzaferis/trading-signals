from dataclasses import dataclass


@dataclass
class TradePlan:

    symbol: str

    action: str

    entry: float

    stop_loss: float

    take_profit: float

    position_size: float

    risk_reward: float

    net_risk_reward: float = 0.0
