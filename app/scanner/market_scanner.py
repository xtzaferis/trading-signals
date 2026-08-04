from app.exchange.okx_client import OKXClient


class MarketScanner:
    def __init__(self):
        self.client = OKXClient()

    def get_spot_usdt_pairs(self):
        markets = self.client.load_markets()

        pairs = []

        for symbol, market in markets.items():

            if (
                market.get("spot")
                and market.get("quote") == "USDT"
                and market.get("active")
            ):
                pairs.append(symbol)

        return sorted(pairs)