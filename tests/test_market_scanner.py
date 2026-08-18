from unittest.mock import Mock

from app.scanner.market_scanner import MarketScanner


def test_top_spot_pairs_are_ranked_by_quote_volume():
    scanner = MarketScanner()
    scanner.client = Mock()
    scanner.client.load_markets.return_value = {
        "BTC/USDC": {
            "spot": True,
            "quote": "USDC",
            "base": "BTC",
            "active": True,
        },
        "ETH/USDC": {
            "spot": True,
            "quote": "USDC",
            "base": "ETH",
            "active": True,
        },
        "SOL/USDC": {
            "spot": True,
            "quote": "USDC",
            "base": "SOL",
            "active": True,
        },
        "HYPE/USDC": {
            "spot": True,
            "quote": "USDC",
            "base": "HYPE",
            "active": True,
        },
        "USDT/USDC": {
            "spot": True,
            "quote": "USDC",
            "base": "USDT",
            "active": True,
        },
    }
    scanner.client.get_tickers.return_value = {
        "BTC/USDC": {"quoteVolume": 1000},
        "ETH/USDC": {"quoteVolume": 3000},
        "SOL/USDC": {
            "quoteVolume": None,
            "baseVolume": 100,
            "last": 20,
        },
        "HYPE/USDC": {"quoteVolume": 10000},
        "USDT/USDC": {"quoteVolume": 9999},
    }

    assert scanner.get_top_spot_pairs(2) == [
        "ETH/USDC",
        "SOL/USDC",
    ]


def test_scanner_can_use_advisory_quote_currency():
    client = Mock()
    client.load_markets.return_value = {
        "BTC/USDT": {
            "spot": True, "quote": "USDT", "base": "BTC", "active": True
        },
        "BTC/EUR": {
            "spot": True, "quote": "EUR", "base": "BTC", "active": True
        },
    }
    client.get_tickers.return_value = {
        "BTC/USDT": {"quoteVolume": 1000},
        "BTC/EUR": {"quoteVolume": 2000},
    }

    assert MarketScanner(client, quote_currency="USDT").get_top_spot_pairs() == [
        "BTC/USDT"
    ]


def test_scanner_can_use_a_broader_advisory_universe():
    client = Mock()
    client.load_markets.return_value = {
        "BTC/USDT": {
            "spot": True, "quote": "USDT", "base": "BTC", "active": True
        },
        "SUI/USDT": {
            "spot": True, "quote": "USDT", "base": "SUI", "active": True
        },
    }
    client.get_tickers.return_value = {
        "BTC/USDT": {"quoteVolume": 1000},
        "SUI/USDT": {"quoteVolume": 2000},
    }

    scanner = MarketScanner(
        client,
        quote_currency="USDT",
        allowed_bases=("BTC", "SUI"),
    )

    assert scanner.get_top_spot_pairs(2) == ["SUI/USDT", "BTC/USDT"]
