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

    # Risk Metrics

    initial_equity: float = 0.0

    total_return: float = 0.0

    peak_equity: float = 0.0

    max_drawdown: float = 0.0

    current_drawdown: float = 0.0

    expectancy: float = 0.0

    average_r: float = 0.0