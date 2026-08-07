from dataclasses import dataclass


@dataclass
class StatisticsReport:

    trades: int = 0

    wins: int = 0

    losses: int = 0

    win_rate: float = 0.0

    gross_profit: float = 0.0

    gross_loss: float = 0.0

    net_profit: float = 0.0

    profit_factor: float = 0.0

    average_winner: float = 0.0

    average_loser: float = 0.0

    best_trade: float = 0.0

    worst_trade: float = 0.0

    current_equity: float = 0.0