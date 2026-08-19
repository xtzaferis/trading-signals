from unittest.mock import Mock

from app.exchange.binance_market_data_client import BinanceMarketDataClient


def test_binance_client_uses_keyless_market_data_host():
    exchange = Mock()
    exchange.urls = {"api": {"public": "https://api.binance.com/api/v3"}}

    BinanceMarketDataClient(exchange=exchange)

    assert exchange.urls["api"]["public"] == ("https://data-api.binance.vision/api/v3")


def test_binance_client_exposes_only_public_data_operations():
    public_methods = {
        name for name in dir(BinanceMarketDataClient) if not name.startswith("_")
    }

    assert public_methods == {
        "PUBLIC_BASE_URL",
        "get_ohlcv",
        "get_ohlcv_range",
        "get_ohlcv_since",
        "get_funding_rates_range",
        "get_futures_market_summaries",
        "get_derivatives_context",
        "get_tickers",
        "load_markets",
    }


def test_binance_client_normalizes_public_futures_positioning_data():
    exchange = Mock()
    exchange.urls = {"api": {"public": "https://api.binance.com/api/v3"}}
    exchange.fapiPublicGetPremiumIndex.return_value = {
        "lastFundingRate": "0.0001",
        "markPrice": "65000.5",
    }
    exchange.fapiDataGetOpenInterestHist.return_value = [
        {"sumOpenInterestValue": "100"},
        {"sumOpenInterestValue": "101"},
    ]
    exchange.fapiDataGetGlobalLongShortAccountRatio.return_value = [
        {"longShortRatio": "1.2"}
    ]
    exchange.fapiDataGetTakerlongshortRatio.return_value = [{"buySellRatio": "1.1"}]

    context = BinanceMarketDataClient(exchange).get_derivatives_context("BTC/USDT")

    assert context.funding_rate == 0.0001
    assert context.open_interest_change_pct == 1.0
    assert context.long_short_ratio == 1.2
    assert context.taker_buy_sell_ratio == 1.1
    assert context.mark_price == 65000.5
    assert context.label == "BULLISH"


def test_binance_client_summarizes_tradeable_perpetual_liquidity():
    exchange = Mock()
    exchange.urls = {"api": {"public": "https://api.binance.com/api/v3"}}
    exchange.fapiPublicGetExchangeInfo.return_value = {
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "baseAsset": "BTC",
                "quoteAsset": "USDT",
                "status": "TRADING",
                "contractType": "PERPETUAL",
                "onboardDate": 0,
            },
            {
                "symbol": "ETHUSDT_260925",
                "baseAsset": "ETH",
                "quoteAsset": "USDT",
                "status": "TRADING",
                "contractType": "CURRENT_QUARTER",
                "onboardDate": 0,
            },
        ]
    }
    exchange.fapiPublicGetTicker24hr.return_value = [
        {"symbol": "BTCUSDT", "quoteVolume": "100000000"}
    ]
    exchange.fapiPublicGetTickerBookTicker.return_value = [
        {"symbol": "BTCUSDT", "bidPrice": "100", "askPrice": "100.05"}
    ]

    markets = BinanceMarketDataClient(exchange).get_futures_market_summaries()

    assert len(markets) == 1
    assert markets[0]["symbol"] == "BTC/USDT"
    assert markets[0]["quote_volume"] == 100_000_000
    assert 4.9 < markets[0]["spread_bps"] < 5.1


def test_binance_client_returns_only_completed_futures_candles():
    exchange = Mock()
    exchange.urls = {"api": {"public": "https://api.binance.com/api/v3"}}
    exchange.milliseconds.return_value = 2_000
    exchange.fapiPublicGetKlines.return_value = [
        [0, "10", "12", "9", "11", "100", 999],
        [1_000, "11", "13", "10", "12", "110", 1_999],
        [2_000, "12", "14", "11", "13", "120", 2_999],
    ]

    candles = BinanceMarketDataClient(exchange).get_ohlcv(
        "BTC/USDT", timeframe="5m", limit=2
    )

    assert candles == [
        [0, 10.0, 12.0, 9.0, 11.0, 100.0],
        [1_000, 11.0, 13.0, 10.0, 12.0, 110.0],
    ]
    exchange.fapiPublicGetKlines.assert_called_once_with(
        {"symbol": "BTCUSDT", "interval": "5m", "limit": 3}
    )


def test_binance_client_paginates_historical_futures_candles():
    exchange = Mock()
    exchange.urls = {"api": {"public": "https://api.binance.com/api/v3"}}
    exchange.milliseconds.return_value = 10_000
    full_page = [[index, "1", "2", "0.5", "1.5", "10", index] for index in range(1500)]
    exchange.fapiPublicGetKlines.side_effect = [
        full_page,
        [[1_500, "2", "3", "1", "2.5", "20", 1_500]],
    ]

    result = BinanceMarketDataClient(exchange).get_ohlcv_range(
        "BTC/USDT", "1h", 0, 2_000
    )

    assert len(result) == 1501
    assert result[-1][0] == 1_500
    assert exchange.fapiPublicGetKlines.call_count == 2


def test_binance_client_normalizes_historical_funding_rates():
    exchange = Mock()
    exchange.urls = {"api": {"public": "https://api.binance.com/api/v3"}}
    exchange.fapiPublicGetFundingRate.return_value = [
        {"fundingTime": "1000", "fundingRate": "0.0001"},
        {"fundingTime": "2000", "fundingRate": "-0.0002"},
    ]

    rates = BinanceMarketDataClient(exchange).get_funding_rates_range(
        "BTC/USDT", 0, 3_000
    )

    assert rates == [(1_000, 0.0001), (2_000, -0.0002)]
