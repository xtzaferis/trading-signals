from abc import ABC, abstractmethod


class Broker(ABC):

    @abstractmethod
    def open(
        self,
        *args,
        **kwargs,
    ):
        pass

    @abstractmethod
    def update(
        self,
        *args,
        **kwargs,
    ):
        pass

    @abstractmethod
    def close(
        self,
        *args,
        **kwargs,
    ):
        pass