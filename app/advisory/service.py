from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import ccxt

from app.advisory.derivatives_context import DerivativesContext
from app.advisory.directional_signal import DirectionalSignalEngine
from app.advisory.planner import AdvisoryLevels, FuturesAdvisoryPlanner
from app.config.settings import (
    ADVISORY_END_HOUR,
    ADVISORY_MAX_SIGNALS,
    ADVISORY_QUOTE_CURRENCY,
    ADVISORY_SPOT_BASES,
    ADVISORY_START_HOUR,
    ADVISORY_TIMEZONE,
    ADVISORY_TOP_COINS,
)
from app.data.data_service import DataService
from app.exchange.binance_market_data_client import BinanceMarketDataClient
from app.indicators.indicator_engine import IndicatorEngine
from app.scanner.market_scanner import MarketScanner


@dataclass(frozen=True)
class AdvisoryCandidate:
    symbol: str
    status: str
    score: int
    price: float | None
    trade: AdvisoryLevels | None = None
    reasons: tuple[str, ...] = ()
    derivatives: DerivativesContext | None = None
    risk: str = "UNKNOWN"


@dataclass(frozen=True)
class AdvisoryReport:
    generated_at: datetime
    window_open: bool
    forced: bool = False
    candidates: tuple[AdvisoryCandidate, ...] = ()
    shortlist: tuple[AdvisoryCandidate, ...] = ()
    errors: tuple[str, ...] = ()


class EntryAdvisoryService:
    """Rank manual-trading ideas without connecting to any execution path."""

    def __init__(
        self,
        scanner=None,
        indicators=None,
        signal_engine=None,
        planner=None,
        timezone_name: str = ADVISORY_TIMEZONE,
        start_hour: int = ADVISORY_START_HOUR,
        end_hour: int = ADVISORY_END_HOUR,
        limit: int = ADVISORY_TOP_COINS,
        progress: Callable[[str], None] | None = None,
        context_client=None,
        max_signals: int = ADVISORY_MAX_SIGNALS,
    ):
        public_client = BinanceMarketDataClient()
        self.scanner = scanner or MarketScanner(
            client=public_client,
            quote_currency=ADVISORY_QUOTE_CURRENCY,
            allowed_bases=ADVISORY_SPOT_BASES,
        )
        self.indicators = indicators or IndicatorEngine(
            data_service=DataService(client=public_client)
        )
        self.signal_engine = signal_engine or DirectionalSignalEngine()
        self.planner = planner or FuturesAdvisoryPlanner()
        self.timezone = ZoneInfo(timezone_name)
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.limit = limit
        self.progress = progress or (lambda message: None)
        self.context_client = context_client or public_client
        self.max_signals = max_signals

    def is_window_open(self, now: datetime | None = None) -> bool:
        local_now = self._local_time(now)
        return self.start_hour <= local_now.hour < self.end_hour

    def scan(
        self,
        now: datetime | None = None,
        force: bool = False,
    ) -> AdvisoryReport:
        local_now = self._local_time(now)
        window_open = self.is_window_open(local_now)
        if not window_open and not force:
            return AdvisoryReport(local_now, False)

        candidates = []
        errors = []
        self.progress("Loading Binance USDT markets and 24-hour volumes...")
        try:
            symbols = self.scanner.get_top_spot_pairs(self.limit)
        except (ccxt.NetworkError, ccxt.ExchangeError) as error:
            return AdvisoryReport(
                local_now,
                window_open,
                forced=force,
                errors=(f"Market scan failed: {error}",),
            )

        for index, symbol in enumerate(symbols, start=1):
            self.progress(
                f"[{index}/{len(symbols)}] Loading {symbol} indicators "
                "(1d, 4h, 1h, 15m, 5m + futures positioning)..."
            )
            try:
                data = self.indicators.calculate_multi_timeframe(symbol)
                data["trigger"] = self.indicators.calculate(symbol, "5m")
                context = self._load_context(symbol)
                signal = self.signal_engine.evaluate(symbol, data, context)
                trade = None
                reasons = list(signal.reasons)
                status = signal.direction
                if status in {"LONG", "SHORT"}:
                    trade = self.planner.create(status, data["entry"])
                    if trade is None:
                        status = "WAIT"
                        reasons.append("Net reward/risk is too low after costs")
                candidates.append(
                    AdvisoryCandidate(
                        symbol=symbol,
                        status=status,
                        score=signal.score,
                        price=self._float_or_none(data["entry"].get("close")),
                        trade=trade,
                        reasons=tuple(reasons),
                        derivatives=context,
                        risk=self._risk_label(data["entry"].get("atr_pct")),
                    )
                )
                self.progress(
                    f"[{index}/{len(symbols)}] {symbol}: "
                    f"{status} score={signal.score}"
                )
            except (
                ccxt.NetworkError,
                ccxt.ExchangeError,
                KeyError,
                TypeError,
                ValueError,
            ) as error:
                errors.append(f"{symbol}: {error}")
                self.progress(f"[{index}/{len(symbols)}] {symbol}: unavailable")

        candidates.sort(
            key=lambda candidate: (
                candidate.status == "WAIT",
                -candidate.score,
                candidate.symbol,
            )
        )
        visible_candidates = tuple(candidates[: self.limit])
        shortlist = tuple(
            candidate
            for candidate in visible_candidates
            if candidate.status in {"LONG", "SHORT"}
        )[: self.max_signals]
        return AdvisoryReport(
            generated_at=local_now,
            window_open=window_open,
            forced=force,
            candidates=visible_candidates,
            shortlist=shortlist,
            errors=tuple(errors),
        )

    def _local_time(self, value: datetime | None) -> datetime:
        if value is None:
            return datetime.now(self.timezone)
        if value.tzinfo is None:
            raise ValueError("Advisory timestamps must be timezone-aware.")
        return value.astimezone(self.timezone)

    @staticmethod
    def _float_or_none(value) -> float | None:
        return float(value) if value is not None else None

    def _load_context(self, symbol: str) -> DerivativesContext | None:
        try:
            return self.context_client.get_derivatives_context(symbol)
        except (
            ccxt.NetworkError,
            ccxt.ExchangeError,
            KeyError,
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _risk_label(atr_pct) -> str:
        if atr_pct is None:
            return "UNKNOWN"
        value = float(atr_pct)
        if value >= 0.007:
            return "HIGH"
        if value >= 0.0035:
            return "MEDIUM"
        return "LOW"
