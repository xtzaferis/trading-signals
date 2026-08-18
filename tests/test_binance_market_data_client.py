from unittest.mock import Mock

from app.exchange.binance_market_data_client import BinanceMarketDataClient


def test_binance_client_uses_keyless_market_data_host():
    exchange = Mock()
    exchange.urls = {"api": {"public": "https://api.binance.com/api/v3"}}

    BinanceMarketDataClient(exchange=exchange)

    assert exchange.urls["api"]["public"] == (
        "https://data-api.binance.vision/api/v3"
    )


def test_binance_client_exposes_only_public_data_operations():
    public_methods = {
        name for name in dir(BinanceMarketDataClient) if not name.startswith("_")
    }

    assert public_methods == {
        "PUBLIC_BASE_URL",
        "get_ohlcv",
        "get_derivatives_context",
        "get_tickers",
        "load_markets",
    }


def test_binance_client_normalizes_public_futures_positioning_data():
    exchange = Mock()
    exchange.urls = {"api": {"public": "https://api.binance.com/api/v3"}}
    exchange.fapiPublicGetPremiumIndex.return_value = {
        "lastFundingRate": "0.0001"
    }
    exchange.fapiDataGetOpenInterestHist.return_value = [
        {"sumOpenInterestValue": "100"},
        {"sumOpenInterestValue": "101"},
    ]
    exchange.fapiDataGetGlobalLongShortAccountRatio.return_value = [
        {"longShortRatio": "1.2"}
    ]
    exchange.fapiDataGetTakerlongshortRatio.return_value = [
        {"buySellRatio": "1.1"}
    ]

    context = BinanceMarketDataClient(exchange).get_derivatives_context("BTC/USDT")

    assert context.funding_rate == 0.0001
    assert context.open_interest_change_pct == 1.0
    assert context.long_short_ratio == 1.2
    assert context.taker_buy_sell_ratio == 1.1
    assert context.label == "BULLISH"
