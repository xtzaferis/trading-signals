import ccxt

from app.advisory.derivatives_context import DerivativesContext


class BinanceMarketDataClient:
    """Unauthenticated Binance client restricted to public market data."""

    PUBLIC_BASE_URL = "https://data-api.binance.vision/api/v3"

    def __init__(self, exchange=None):
        self.exchange = exchange or ccxt.binance({"enableRateLimit": True})
        self.exchange.urls["api"]["public"] = self.PUBLIC_BASE_URL

    def load_markets(self) -> dict:
        return self.exchange.load_markets()

    def get_tickers(self) -> dict:
        return self.exchange.fetch_tickers()

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "15m",
        limit: int = 200,
    ) -> list:
        return self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    def get_derivatives_context(self, symbol: str) -> DerivativesContext:
        """Return keyless USD-M futures positioning data for a spot-style symbol."""
        market_id = symbol.replace("/", "").replace(":", "")
        premium = self.exchange.fapiPublicGetPremiumIndex({"symbol": market_id})
        interest = self.exchange.fapiDataGetOpenInterestHist(
            {"symbol": market_id, "period": "5m", "limit": 2}
        )
        ratios = self.exchange.fapiDataGetGlobalLongShortAccountRatio(
            {"symbol": market_id, "period": "5m", "limit": 1}
        )
        taker = self.exchange.fapiDataGetTakerlongshortRatio(
            {"symbol": market_id, "period": "5m", "limit": 1}
        )
        return DerivativesContext(
            funding_rate=self._optional_float(premium.get("lastFundingRate")),
            open_interest_change_pct=self._open_interest_change(interest),
            long_short_ratio=self._last_float(ratios, "longShortRatio"),
            taker_buy_sell_ratio=self._last_float(taker, "buySellRatio"),
        )

    @classmethod
    def _open_interest_change(cls, rows: list) -> float | None:
        if len(rows) < 2:
            return None
        previous = cls._optional_float(rows[-2].get("sumOpenInterestValue"))
        current = cls._optional_float(rows[-1].get("sumOpenInterestValue"))
        if previous in {None, 0.0} or current is None:
            return None
        return round((current / previous - 1) * 100, 8)

    @classmethod
    def _last_float(cls, rows: list, key: str) -> float | None:
        return cls._optional_float(rows[-1].get(key)) if rows else None

    @staticmethod
    def _optional_float(value) -> float | None:
        return float(value) if value not in {None, ""} else None
