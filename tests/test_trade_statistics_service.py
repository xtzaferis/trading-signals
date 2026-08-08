from unittest.mock import Mock

from app.services.trade_statistics_service import (
    TradeStatisticsService,
)


def test_trade_statistics():

    service = (
        TradeStatisticsService()
    )

    service.repository = Mock()

    service.repository.get_all.return_value = [

        (
            "BTC/USDC",
            100.0,
            110.0,
            1.0,
            "",
            "",
            "TAKE_PROFIT",
            10.0,
        ),

        (
            "BTC/USDC",
            100.0,
            95.0,
            1.0,
            "",
            "",
            "STOP_LOSS",
            -5.0,
        ),
    ]

    result = (
        service.generate()
    )

    assert (
        result.trades
        == 2
    )

    assert (
        result.wins
        == 1
    )

    assert (
        result.losses
        == 1
    )

    assert (
        result.net_profit
        == 5.0
    )

    assert (
        result.win_rate
        == 50.0
    )

    assert (
        result.gross_profit
        == 10.0
    )

    assert (
        result.gross_loss
        == 5.0
    )

    assert (
        result.profit_factor
        == 2.0
    )

    assert (
        result.average_winner
        == 10.0
    )

    assert (
        result.average_loser
        == -5.0
    )

    assert (
        result.expectancy
        == 2.5
    )

    assert (
        result.initial_equity
        == 1000.0
    )

    assert (
        result.current_equity
        == 1005.0
    )

    assert (
        result.total_return
        == 0.5
    )

    assert (
        result.peak_equity
        == 1010.0
    )

    assert (
        result.max_drawdown
        > 0
    )

    assert (
        result.current_drawdown
        > 0
    )