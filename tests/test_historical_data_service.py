from unittest.mock import Mock

from app.services.historical_data_service import HistoricalDataService


def test_load_paginates_and_removes_incomplete_candle():
    exchange = Mock()
    exchange.parse_timeframe.return_value = 60
    exchange.milliseconds.return_value = 1_000_000
    exchange.fetch_ohlcv.return_value = [
        [1_000_000, 1, 1, 1, 1, 1],
        [880_000, 1, 1, 1, 1, 1],
        [940_000, 1, 1, 1, 1, 1],
        [820_000, 1, 1, 1, 1, 1],
    ]
    client = Mock(exchange=exchange)

    candles = HistoricalDataService(client=client).load(
        symbol="BTC/USDC",
        timeframe="1m",
        limit=3,
    )

    assert [candle[0] for candle in candles] == [
        820_000,
        880_000,
        940_000,
    ]
    exchange.fetch_ohlcv.assert_called_once_with(
        symbol="BTC/USDC",
        timeframe="1m",
        since=760_000,
        limit=3,
        params={
            "paginate": True,
            "paginationCalls": 2,
        },
    )
