from dataclasses import dataclass


@dataclass
class BacktestResult:

    trades: int = 0

    wins: int = 0

    losses: int = 0

    win_rate: float = 0.0

    net_profit: float = 0.0

    profit_factor: float = 0.0

    max_drawdown: float = 0.0

    final_equity: float = 0.0