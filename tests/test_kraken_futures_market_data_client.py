from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import ccxt
import pytest

from app.exchange.kraken_futures_market_data_client import (
    KrakenFuturesMarketDataClient,
)


def response(payload, status=200, text=""):
    result = Mock()
    result.status_code = status
    result.text = text
    result.json.return_value = payload
    return result


def client_with_routes(routes):
    session = Mock()

    def get(url, **kwargs):
        for suffix, payload in routes.items():
            if suffix in url:
                return response(payload)
        raise AssertionError(f"Unexpected Kraken URL: {url}")

    session.get.side_effect = get
    return KrakenFuturesMarketDataClient(session=session)


def test_kraken_client_summarizes_tradeable_perpetual_liquidity():
    client = client_with_routes(
        {
            "/instruments": {
                "instruments": [
                    {
                        "symbol": "PF_XBTUSD",
                        "base": "BTC",
                        "quote": "USD",
                        "tradeable": True,
                        "isExpired": False,
                        "openingDate": "2022-03-22T13:15:36Z",
                    },
                    {
                        "symbol": "FI_XBTUSD_260925",
                        "base": "BTC",
                        "quote": "USD",
                        "tradeable": True,
                        "isExpired": False,
                        "openingDate": "2026-01-01T00:00:00Z",
                    },
                ]
            },
            "/tickers": {
                "tickers": [
                    {
                        "symbol": "PF_XBTUSD",
                        "bid": "100",
                        "ask": "100.05",
                        "volumeQuote": "100000000",
                        "suspended": False,
                    }
                ]
            },
        }
    )

    markets = client.get_futures_market_summaries()

    assert len(markets) == 1
    assert markets[0]["symbol"] == "BTC/USD"
    assert markets[0]["quote_volume"] == 100_000_000
    assert 4.9 < markets[0]["spread_bps"] < 5.1


def test_kraken_client_returns_only_completed_candles():
    now = datetime.now(timezone.utc)
    completed = int((now - timedelta(minutes=10)).timestamp() * 1000)
    incomplete = int((now - timedelta(minutes=1)).timestamp() * 1000)
    client = client_with_routes(
        {
            "/trade/PF_XBTUSD/5m": {
                "candles": [
                    {
                        "time": completed,
                        "open": "10",
                        "high": "12",
                        "low": "9",
                        "close": "11",
                        "volume": "100",
                    },
                    {
                        "time": incomplete,
                        "open": "11",
                        "high": "13",
                        "low": "10",
                        "close": "12",
                        "volume": "110",
                    },
                ],
                "more_candles": False,
            }
        }
    )

    assert client.get_ohlcv("BTC/USD", "5m", 2) == [
        [completed, 10.0, 12.0, 9.0, 11.0, 100.0]
    ]


def test_kraken_client_normalizes_futures_positioning_context():
    routes = {
        "/analytics/PF_XBTUSD/open-interest": {
            "result": {"data": [[99, 101, 98, 100], [100, 102, 99, 101]]},
            "errors": [],
        },
        "/analytics/PF_XBTUSD/cvd": {
            "result": {
                "data": {"buy_volume": ["20", "30"], "sell_volume": ["10", "10"]}
            },
            "errors": [],
        },
        "/analytics/PF_XBTUSD/long-short-ratio": {
            "result": {"data": ["1.2"]},
            "errors": [],
        },
        "/analytics/PF_XBTUSD/funding": {
            "result": {"data": {"relativeRate": [["0", "0", "0", "0.0001"]]}},
            "errors": [],
        },
        "/tickers": {
            "tickers": [{"symbol": "PF_XBTUSD", "markPrice": "65000.5"}]
        },
    }
    client = client_with_routes(routes)

    context = client.get_derivatives_context("BTC/USD")

    assert context.funding_rate == 0.0001
    assert context.open_interest_change_pct == 1.0
    assert context.long_short_ratio == 1.2
    assert context.taker_buy_sell_ratio == 3.0
    assert context.mark_price == 65000.5


def test_kraken_client_summarizes_order_book_quality():
    client = client_with_routes(
        {
            "/orderbook": {
                "orderBook": {
                    "bids": [[1, 100], [100, 20], [99, 10]],
                    "asks": [[100.05, 10], [101, 5], [1000, 1]],
                }
            }
        }
    )

    quality = client.get_futures_order_book_quality("BTC/USD", limit=2)

    assert 4.9 < quality["spread_bps"] < 5.1
    assert quality["bid_depth_usdt"] == 2990
    assert quality["ask_depth_usdt"] == 1505.5
    assert quality["imbalance"] > 0


def test_kraken_client_surfaces_http_restrictions():
    session = Mock()
    session.get.return_value = response({}, status=451, text="restricted")
    client = KrakenFuturesMarketDataClient(session=session)

    with pytest.raises(ccxt.ExchangeError, match="451"):
        client.get_futures_market_summaries()
