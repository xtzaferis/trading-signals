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
