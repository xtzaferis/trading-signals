from datetime import datetime, timezone
from typing import ClassVar

import ccxt
import requests

from app.advisory.derivatives_context import DerivativesContext


class KrakenFuturesMarketDataClient:
    """Keyless Kraken Futures market data used only by the advisory system."""

    TRADING_BASE_URL = "https://futures.kraken.com/derivatives/api/v3"
    CHARTS_BASE_URL = "https://futures.kraken.com/api/charts/v1"
    REQUEST_TIMEOUT = 20
    TIMEFRAME_SECONDS: ClassVar[dict[str, int]] = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "4h": 14400,
        "12h": 43200,
        "1d": 86400,
        "1w": 604800,
    }

    def __init__(self, session=None):
        self.session = session or requests.Session()
        self._symbol_ids: dict[str, str] = {}
        self._tickers: dict[str, dict] = {}

    def get_futures_market_summaries(self) -> list[dict]:
        instruments = self._get("trading", "instruments").get("instruments", [])
        tickers = self._get("trading", "tickers").get("tickers", [])
        self._tickers = {str(row.get("symbol")): row for row in tickers}
        now = datetime.now(timezone.utc)
        summaries = []
        for instrument in instruments:
            market_id = str(instrument.get("symbol", ""))
            ticker = self._tickers.get(market_id, {})
            if not (
                market_id.startswith("PF_")
                and instrument.get("tradeable") is True
                and not instrument.get("isExpired", False)
                and str(instrument.get("quote", "")).upper() == "USD"
                and ticker
                and not ticker.get("suspended", False)
            ):
                continue
            base = str(instrument.get("base", "")).upper()
            symbol = f"{base}/USD"
            self._symbol_ids[symbol] = market_id
            bid = self._optional_float(ticker.get("bid"))
            ask = self._optional_float(ticker.get("ask"))
            spread_bps = self._spread_bps(bid, ask)
            opened_at = self._parse_datetime(instrument.get("openingDate"))
            age = (now - opened_at).total_seconds() / 86400 if opened_at else None
            summaries.append(
                {
                    "symbol": symbol,
                    "base": base,
                    "quote_volume": self._optional_float(ticker.get("volumeQuote")),
                    "spread_bps": spread_bps,
                    "contract_age_days": max(0.0, age) if age is not None else None,
                }
            )
        return summaries

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "15m",
        limit: int = 200,
    ) -> list:
        payload = self._candles(
            symbol,
            timeframe,
            params={"count": limit + 1},
        )
        return self._normalize_completed(payload.get("candles", []), timeframe)[-limit:]

    def get_ohlcv_since(
        self,
        symbol: str,
        timeframe: str,
        since_ms: int,
        limit: int = 300,
    ) -> list:
        payload = self._candles(
            symbol,
            timeframe,
            params={"from": since_ms // 1000, "count": limit + 1},
        )
        candles = self._normalize_completed(payload.get("candles", []), timeframe)
        return [row for row in candles if row[0] >= since_ms][:limit]

    def get_ohlcv_range(
        self,
        symbol: str,
        timeframe: str,
        since_ms: int,
        until_ms: int,
    ) -> list:
        timeframe_seconds = self._timeframe_seconds(timeframe)
        cursor = since_ms
        candles = []
        while cursor < until_ms:
            payload = self._candles(
                symbol,
                timeframe,
                params={
                    "from": cursor // 1000,
                    "to": until_ms // 1000,
                    "count": 5000,
                },
            )
            page = self._normalize_completed(payload.get("candles", []), timeframe)
            page = [row for row in page if cursor <= row[0] < until_ms]
            if not page:
                break
            candles.extend(page)
            next_cursor = page[-1][0] + timeframe_seconds * 1000
            if next_cursor <= cursor or not payload.get("more_candles", False):
                break
            cursor = next_cursor
        unique = {row[0]: row for row in candles}
        return [unique[timestamp] for timestamp in sorted(unique)]

    def get_derivatives_context(self, symbol: str) -> DerivativesContext:
        market_id = self._market_id(symbol)
        now_seconds = int(datetime.now(timezone.utc).timestamp())
        since = now_seconds - 13 * 300
        interest = self._safe_analytics(market_id, "open-interest", since, 300)
        cvd = self._safe_analytics(market_id, "cvd", since, 300)
        ratios = self._safe_analytics(market_id, "long-short-ratio", since, 300)
        funding = self._safe_analytics(market_id, "funding", since, 300)
        ticker = self._ticker(market_id)

        interest_values = self._ohlc_closes(interest)
        buy_values = self._series(cvd, "buy_volume")
        sell_values = self._series(cvd, "sell_volume")
        ratio_values = self._plain_series(ratios)
        funding_values = self._series(funding, "relativeRate", ohlc=True)
        return DerivativesContext(
            funding_rate=funding_values[-1] if funding_values else None,
            open_interest_change_pct=self._change(interest_values, 1),
            open_interest_change_15m_pct=self._change(interest_values, 3),
            open_interest_change_1h_pct=self._change(interest_values, 12),
            long_short_ratio=ratio_values[-1] if ratio_values else None,
            taker_buy_sell_ratio=self._volume_ratio(buy_values, sell_values, 1),
            taker_buy_sell_ratio_15m=self._volume_ratio(buy_values, sell_values, 3),
            taker_buy_sell_ratio_1h=self._volume_ratio(buy_values, sell_values, 12),
            mark_price=self._optional_float(ticker.get("markPrice")),
        )

    def get_futures_order_book_quality(
        self,
        symbol: str,
        limit: int = 20,
    ) -> dict:
        payload = self._get(
            "trading",
            "orderbook",
            params={"symbol": self._market_id(symbol)},
        )
        book = payload.get("orderBook", {})
        bids = sorted(self._levels(book.get("bids", [])), reverse=True)[:limit]
        asks = sorted(self._levels(book.get("asks", [])))[:limit]
        best_bid = bids[0][0] if bids else None
        best_ask = asks[0][0] if asks else None
        bid_depth = sum(price * quantity for price, quantity in bids)
        ask_depth = sum(price * quantity for price, quantity in asks)
        total_depth = bid_depth + ask_depth
        return {
            "spread_bps": self._spread_bps(best_bid, best_ask),
            "bid_depth_usdt": bid_depth,
            "ask_depth_usdt": ask_depth,
            "total_depth_usdt": total_depth,
            "imbalance": (
                (bid_depth - ask_depth) / total_depth if total_depth > 0 else None
            ),
        }

    def get_funding_rates_range(
        self,
        symbol: str,
        since_ms: int,
        until_ms: int,
    ) -> list[tuple[int, float]]:
        result = self._analytics(
            self._market_id(symbol),
            "funding",
            since_ms // 1000,
            3600,
            until_ms // 1000,
        )
        timestamps = result.get("timestamp", [])
        rates = self._series(result, "relativeRate", ohlc=True)
        normalized = []
        for timestamp, rate in zip(timestamps, rates):
            value = int(timestamp)
            timestamp_ms = value if value >= 1_000_000_000_000 else value * 1000
            if since_ms <= timestamp_ms <= until_ms:
                normalized.append((timestamp_ms, rate))
        return normalized

    def _candles(self, symbol: str, timeframe: str, params: dict) -> dict:
        self._timeframe_seconds(timeframe)
        path = f"trade/{self._market_id(symbol)}/{timeframe}"
        return self._get("charts", path, params=params)

    def _analytics(
        self,
        market_id: str,
        kind: str,
        since: int,
        interval: int,
        until: int | None = None,
    ) -> dict:
        params = {"since": since, "interval": interval}
        if until is not None:
            params["to"] = until
        payload = self._get("charts", f"analytics/{market_id}/{kind}", params=params)
        return payload.get("result", {})

    def _safe_analytics(
        self,
        market_id: str,
        kind: str,
        since: int,
        interval: int,
    ) -> dict:
        try:
            return self._analytics(market_id, kind, since, interval)
        except (ccxt.NetworkError, ccxt.ExchangeError, TypeError, ValueError):
            return {}

    def _ticker(self, market_id: str) -> dict:
        if market_id not in self._tickers:
            rows = self._get("trading", "tickers").get("tickers", [])
            self._tickers = {str(row.get("symbol")): row for row in rows}
        return self._tickers.get(market_id, {})

    def _get(self, api: str, path: str, params: dict | None = None) -> dict:
        base = self.TRADING_BASE_URL if api == "trading" else self.CHARTS_BASE_URL
        url = f"{base}/{path}"
        try:
            response = self.session.get(
                url,
                params=params,
                headers={"Accept": "application/json"},
                timeout=self.REQUEST_TIMEOUT,
            )
        except requests.RequestException as error:
            raise ccxt.NetworkError(f"Kraken Futures request failed: {error}") from error
        if response.status_code >= 400:
            raise ccxt.ExchangeError(
                f"Kraken Futures GET {url} returned {response.status_code}: "
                f"{response.text[:500]}"
            )
        try:
            payload = response.json()
        except ValueError as error:
            raise ccxt.ExchangeError(
                f"Kraken Futures GET {url} returned invalid JSON"
            ) from error
        errors = payload.get("errors", []) if isinstance(payload, dict) else []
        if errors:
            raise ccxt.ExchangeError(f"Kraken Futures GET {url} failed: {errors}")
        return payload

    def _market_id(self, symbol: str) -> str:
        if symbol in self._symbol_ids:
            return self._symbol_ids[symbol]
        base = symbol.split("/", maxsplit=1)[0].upper()
        kraken_base = "XBT" if base == "BTC" else base
        return f"PF_{kraken_base}USD"

    def _normalize_completed(self, rows: list, timeframe: str) -> list:
        duration_ms = self._timeframe_seconds(timeframe) * 1000
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        completed = [row for row in rows if int(row["time"]) + duration_ms <= now_ms]
        return [
            [
                int(row["time"]),
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                float(row["volume"]),
            ]
            for row in completed
        ]

    @classmethod
    def _timeframe_seconds(cls, timeframe: str) -> int:
        try:
            return cls.TIMEFRAME_SECONDS[timeframe]
        except KeyError as error:
            raise ValueError(f"Unsupported Kraken timeframe: {timeframe}") from error

    @staticmethod
    def _parse_datetime(value) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    @staticmethod
    def _optional_float(value) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _spread_bps(bid: float | None, ask: float | None) -> float | None:
        if bid is None or ask is None or bid <= 0 or ask < bid:
            return None
        return (ask - bid) / ((ask + bid) / 2) * 10_000

    @classmethod
    def _levels(cls, rows) -> list[tuple[float, float]]:
        levels = []
        for row in rows or []:
            if not isinstance(row, (list, tuple)) or len(row) < 2:
                continue
            price = cls._optional_float(row[0])
            quantity = cls._optional_float(row[1])
            if price is not None and quantity is not None and price > 0 and quantity > 0:
                levels.append((price, quantity))
        return levels

    @classmethod
    def _ohlc_closes(cls, result: dict) -> list[float]:
        values = []
        for row in result.get("data", []) if isinstance(result, dict) else []:
            value = row[-1] if isinstance(row, (list, tuple)) and row else row
            parsed = cls._optional_float(value)
            if parsed is not None:
                values.append(parsed)
        return values

    @classmethod
    def _plain_series(cls, result: dict) -> list[float]:
        if not isinstance(result, dict):
            return []
        return [
            parsed
            for value in result.get("data", [])
            if (parsed := cls._optional_float(value)) is not None
        ]

    @classmethod
    def _series(cls, result: dict, key: str, ohlc: bool = False) -> list[float]:
        if not isinstance(result, dict):
            return []
        data = result.get("data", {})
        if not isinstance(data, dict):
            return []
        values = data.get(key, data.get(cls._snake_to_camel(key), []))
        normalized = []
        for row in values or []:
            value = row[-1] if ohlc and isinstance(row, (list, tuple)) and row else row
            parsed = cls._optional_float(value)
            if parsed is not None:
                normalized.append(parsed)
        return normalized

    @staticmethod
    def _snake_to_camel(value: str) -> str:
        first, *rest = value.split("_")
        return first + "".join(item.title() for item in rest)

    @staticmethod
    def _change(values: list[float], periods: int) -> float | None:
        if len(values) <= periods or values[-(periods + 1)] == 0:
            return None
        return round((values[-1] / values[-(periods + 1)] - 1) * 100, 8)

    @staticmethod
    def _volume_ratio(
        buys: list[float],
        sells: list[float],
        periods: int,
    ) -> float | None:
        buy = sum(buys[-periods:])
        sell = sum(sells[-periods:])
        return buy / sell if sell > 0 else None
