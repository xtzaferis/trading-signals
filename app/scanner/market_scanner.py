from app.exchange.okx_client import OKXClient
from app.config.settings import QUOTE_CURRENCY


class MarketScanner:

    def __init__(self):
        self.client = OKXClient()

    def get_spot_pairs(self):

        markets = self.client.load_markets()

        pairs = []

        for symbol, market in markets.items():

            if (
                market.get("spot")
                and market.get("quote") == QUOTE_CURRENCY
                and market.get("active")
            ):
                pairs.append(symbol)

        return sorted(pairs)