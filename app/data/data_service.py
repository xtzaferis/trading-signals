from app.cache.candle_cache import cache
from app.data.data_provider import DataProvider
from app.exchange.kraken_client import KrakenClient


class DataService(DataProvider):

    def __init__(self, client=None):
        self.client = client or KrakenClient()

    def get_ohlcv(
        self,
        symbol,
        timeframe,
        limit,
    ):

        cache_key = f"{symbol}:{timeframe}:{limit}"

        candles = cache.get(cache_key)

        if candles is not None:
            return candles

        candles = self.client.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
        )

        cache.set(
            cache_key,
            candles,
            ttl_seconds=60,
        )

        return candles
