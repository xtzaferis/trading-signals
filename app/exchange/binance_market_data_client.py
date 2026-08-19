from datetime import datetime, timezone

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

    def get_futures_market_summaries(self) -> list[dict]:
        """Return active USD-M perpetual liquidity without API credentials."""
        exchange_info = self.exchange.fapiPublicGetExchangeInfo()
        tickers = self.exchange.fapiPublicGetTicker24hr()
        books = self.exchange.fapiPublicGetTickerBookTicker()
        ticker_by_id = {row.get("symbol"): row for row in self._as_rows(tickers)}
        book_by_id = {row.get("symbol"): row for row in self._as_rows(books)}
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        summaries = []
        for market in exchange_info.get("symbols", []):
            if not (
                market.get("status") == "TRADING"
                and market.get("contractType") == "PERPETUAL"
                and market.get("quoteAsset") == "USDT"
            ):
                continue
            market_id = market.get("symbol")
            ticker = ticker_by_id.get(market_id, {})
            book = book_by_id.get(market_id, {})
            bid = self._optional_float(book.get("bidPrice"))
            ask = self._optional_float(book.get("askPrice"))
            spread_bps = None
            if bid is not None and ask is not None and bid > 0 and ask >= bid:
                spread_bps = (ask - bid) / ((ask + bid) / 2) * 10_000
            onboarded = int(market.get("onboardDate") or now_ms)
            summaries.append(
                {
                    "symbol": f"{market.get('baseAsset')}/USDT",
                    "base": market.get("baseAsset"),
                    "quote_volume": self._optional_float(ticker.get("quoteVolume")),
                    "spread_bps": spread_bps,
                    "contract_age_days": max(0, (now_ms - onboarded) / 86_400_000),
                }
            )
        return summaries

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "15m",
        limit: int = 200,
    ) -> list:
        """Return completed USD-M futures candles in CCXT OHLCV shape."""
        market_id = self._market_id(symbol)
        rows = self.exchange.fapiPublicGetKlines(
            {
                "symbol": market_id,
                "interval": timeframe,
                "limit": min(limit + 1, 1500),
            }
        )
        return self._normalize_completed(rows, limit)

    def get_ohlcv_since(
        self,
        symbol: str,
        timeframe: str,
        since_ms: int,
        limit: int = 300,
    ) -> list:
        rows = self.exchange.fapiPublicGetKlines(
            {
                "symbol": self._market_id(symbol),
                "interval": timeframe,
                "startTime": since_ms,
                "limit": min(limit, 1500),
            }
        )
        return self._normalize_completed(rows, limit)

    def get_ohlcv_range(
        self,
        symbol: str,
        timeframe: str,
        since_ms: int,
        until_ms: int,
    ) -> list:
        candles = []
        cursor = since_ms
        while cursor < until_ms:
            rows = self.exchange.fapiPublicGetKlines(
                {
                    "symbol": self._market_id(symbol),
                    "interval": timeframe,
                    "startTime": cursor,
                    "endTime": until_ms,
                    "limit": 1500,
                }
            )
            if not rows:
                break
            candles.extend(self._normalize_completed(rows, len(rows)))
            next_cursor = int(rows[-1][0]) + 1
            if next_cursor <= cursor:
                break
            cursor = next_cursor
            if len(rows) < 1500:
                break
        unique = {candle[0]: candle for candle in candles}
        return [unique[timestamp] for timestamp in sorted(unique)]

    def get_funding_rates_range(
        self,
        symbol: str,
        since_ms: int,
        until_ms: int,
    ) -> list[tuple[int, float]]:
        rates = []
        cursor = since_ms
        while cursor < until_ms:
            rows = self.exchange.fapiPublicGetFundingRate(
                {
                    "symbol": self._market_id(symbol),
                    "startTime": cursor,
                    "endTime": until_ms,
                    "limit": 1000,
                }
            )
            if not rows:
                break
            rates.extend(
                (int(row["fundingTime"]), float(row["fundingRate"])) for row in rows
            )
            next_cursor = int(rows[-1]["fundingTime"]) + 1
            if next_cursor <= cursor:
                break
            cursor = next_cursor
            if len(rows) < 1000:
                break
        return sorted(set(rates))

    def _normalize_completed(self, rows: list, limit: int) -> list:
        now = self.exchange.milliseconds()
        completed = [row for row in rows if int(row[6]) < now]
        return [
            [
                int(row[0]),
                float(row[1]),
                float(row[2]),
                float(row[3]),
                float(row[4]),
                float(row[5]),
            ]
            for row in completed[-limit:]
        ]

    def get_derivatives_context(self, symbol: str) -> DerivativesContext:
        """Return keyless USD-M futures positioning data for a spot-style symbol."""
        market_id = self._market_id(symbol)
        premium = self.exchange.fapiPublicGetPremiumIndex({"symbol": market_id})
        interest = self.exchange.fapiDataGetOpenInterestHist(
            {"symbol": market_id, "period": "5m", "limit": 13}
        )
        ratios = self.exchange.fapiDataGetGlobalLongShortAccountRatio(
            {"symbol": market_id, "period": "5m", "limit": 1}
        )
        taker = self.exchange.fapiDataGetTakerlongshortRatio(
            {"symbol": market_id, "period": "5m", "limit": 12}
        )
        return DerivativesContext(
            funding_rate=self._optional_float(premium.get("lastFundingRate")),
            open_interest_change_pct=self._open_interest_change(interest, 1),
            open_interest_change_15m_pct=self._open_interest_change(interest, 3),
            open_interest_change_1h_pct=self._open_interest_change(interest, 12),
            long_short_ratio=self._last_float(ratios, "longShortRatio"),
            taker_buy_sell_ratio=self._mean_last(taker, "buySellRatio", 1),
            taker_buy_sell_ratio_15m=self._mean_last(taker, "buySellRatio", 3),
            taker_buy_sell_ratio_1h=self._mean_last(taker, "buySellRatio", 12),
            mark_price=self._optional_float(premium.get("markPrice")),
        )

    @staticmethod
    def _market_id(symbol: str) -> str:
        base, quote = symbol.split("/", maxsplit=1)
        return f"{base}{quote.split(':', maxsplit=1)[0]}".upper()

    @classmethod
    def _open_interest_change(cls, rows: list, periods: int = 1) -> float | None:
        if len(rows) <= periods:
            return None
        previous = cls._optional_float(rows[-(periods + 1)].get("sumOpenInterestValue"))
        current = cls._optional_float(rows[-1].get("sumOpenInterestValue"))
        if previous in {None, 0.0} or current is None:
            return None
        return round((current / previous - 1) * 100, 8)

    @classmethod
    def _last_float(cls, rows: list, key: str) -> float | None:
        return cls._optional_float(rows[-1].get(key)) if rows else None

    @classmethod
    def _mean_last(cls, rows: list, key: str, periods: int) -> float | None:
        values = [
            value
            for row in rows[-periods:]
            if (value := cls._optional_float(row.get(key))) is not None
        ]
        return sum(values) / len(values) if values else None

    @staticmethod
    def _as_rows(value) -> list[dict]:
        if isinstance(value, list):
            return value
        return [value] if isinstance(value, dict) else []

    @staticmethod
    def _optional_float(value) -> float | None:
        return float(value) if value not in {None, ""} else None
