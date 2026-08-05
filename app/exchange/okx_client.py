import ccxt

from app.config.settings import (
    OKX_API_KEY,
    OKX_PASSPHRASE,
    OKX_SECRET,
)
from app.exceptions import MissingApiKeysError


class OKXClient:

    def __init__(self):

        config = {
            "enableRateLimit": True,
        }

        if (
            OKX_API_KEY
            and OKX_SECRET
            and OKX_PASSPHRASE
        ):
            config["apiKey"] = OKX_API_KEY
            config["secret"] = OKX_SECRET
            config["password"] = OKX_PASSPHRASE

        self.exchange = ccxt.okx(config)

    def load_markets(self):
        return self.exchange.load_markets()

    def get_balance(self):

        if not (
            OKX_API_KEY
            and OKX_SECRET
            and OKX_PASSPHRASE
        ):
            raise MissingApiKeysError(
                "API keys are not configured."
            )

        return self.exchange.fetch_balance()

    def get_ticker(self, symbol):
        return self.exchange.fetch_ticker(symbol)

    def get_ohlcv(
        self,
        symbol,
        timeframe="15m",
        limit=200,
    ):

        return self.exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            limit=limit,
        )