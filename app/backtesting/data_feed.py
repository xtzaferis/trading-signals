from abc import ABC, abstractmethod


class DataFeed(ABC):

    @abstractmethod
    def has_next(self) -> bool:
        """Return True if more market data exists."""
        ...

    @abstractmethod
    def next(self) -> dict:
        """
        Return the next synchronized market snapshot.

        Example:
        {
            "15m": [...],
            "1h": [...],
            "4h": [...],
        }
        """
        ...