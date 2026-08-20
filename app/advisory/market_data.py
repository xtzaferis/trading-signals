from app.config.settings import ADVISORY_DATA_SOURCE
from app.exchange.binance_market_data_client import BinanceMarketDataClient
from app.exchange.kraken_futures_market_data_client import (
    KrakenFuturesMarketDataClient,
)


def create_advisory_market_data_client():
    if ADVISORY_DATA_SOURCE == "kraken":
        return KrakenFuturesMarketDataClient()
    return BinanceMarketDataClient()
