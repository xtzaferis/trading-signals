from abc import ABC, abstractmethod


class DataProvider(ABC):

    @abstractmethod
    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ):
        """Return OHLCV candles."""
        raise NotImplementedError