from app.exchange.okx_client import OKXClient

client = OKXClient()

markets = client.load_markets()

for symbol, market in markets.items():

    if (
        market.get("spot")
        and market.get("base") == "BTC"
    ):
        print(symbol)