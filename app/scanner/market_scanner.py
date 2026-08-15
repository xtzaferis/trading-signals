from typing import ClassVar

from app.config.settings import (
    CORE_SPOT_BASES,
    QUOTE_CURRENCY,
    TOP_COINS,
)
from app.exchange.kraken_client import KrakenClient


class MarketScanner:

    STABLECOINS: ClassVar[frozenset[str]] = frozenset({
        "DAI",
        "FDUSD",
        "PYUSD",
        "TUSD",
        "USD",
        "USDC",
        "USDE",
        "USDT",
    })

    LEVERAGED_SUFFIXES: ClassVar[tuple[str, ...]] = (
        "2L",
        "2S",
        "3L",
        "3S",
        "5L",
        "5S",
        "BULL",
        "BEAR",
    )

    def __init__(self, client=None):
        self.client = client or KrakenClient()

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

    def get_top_spot_pairs(
        self,
        limit: int = TOP_COINS,
    ) -> list[str]:

        markets = self.client.load_markets()
        tickers = self.client.get_tickers()
        ranked = []

        for symbol, market in markets.items():
            base = str(market.get("base", "")).upper()

            if not (
                market.get("spot")
                and market.get("quote") == QUOTE_CURRENCY
                and market.get("active")
                and base in CORE_SPOT_BASES
                and base not in self.STABLECOINS
                and not base.endswith(
                    self.LEVERAGED_SUFFIXES
                )
            ):
                continue

            ticker = tickers.get(symbol, {})
            quote_volume = ticker.get(
                "quoteVolume"
            )

            if quote_volume is None:
                base_volume = ticker.get(
                    "baseVolume"
                )
                last = ticker.get("last")
                if base_volume is not None and last is not None:
                    quote_volume = (
                        float(base_volume)
                        * float(last)
                    )

            if quote_volume is None:
                continue

            ranked.append((
                float(quote_volume),
                symbol,
            ))

        ranked.sort(
            key=lambda item: (
                -item[0],
                item[1],
            )
        )

        return [
            symbol
            for _, symbol in ranked[:limit]
        ]
