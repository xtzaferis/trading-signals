import ccxt

from app.config.settings import (
    OKX_API_KEY,
    OKX_SECRET,
    OKX_PASSPHRASE
)


class OKXClient:

    def __init__(self):

        self.exchange = ccxt.okx({
            "apiKey": OKX_API_KEY,
            "secret": OKX_SECRET,
            "password": OKX_PASSPHRASE,
            "enableRateLimit": True
        })

    def load_markets(self):
        return self.exchange.load_markets()

    def get_balance(self):
        return self.exchange.fetch_balance()

    def get_ticker(self, symbol):
        return self.exchange.fetch_ticker(symbol)

    def get_ohlcv(self, symbol, timeframe="15m", limit=200):
        return self.exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            limit=limit
        )