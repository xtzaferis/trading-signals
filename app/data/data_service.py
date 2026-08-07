from app.cache.candle_cache import cache
from app.exchange.okx_client import OKXClient
from app.data.data_provider import DataProvider


class DataService(DataProvider):

    def __init__(self):
        self.client = OKXClient()

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