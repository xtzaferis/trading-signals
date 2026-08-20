from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import ccxt
import pandas as pd

from app.advisory.correlation_selector import CorrelationAwareSelector
from app.advisory.derivatives_context import DerivativesContext
from app.advisory.directional_signal import DirectionalSignalEngine
from app.advisory.outcome_tracker import AdvisoryOutcomeTracker
from app.advisory.planner import AdvisoryLevels, FuturesAdvisoryPlanner
from app.config.settings import (
    ADVISORY_END_HOUR,
    ADVISORY_MAX_BOOK_SPREAD_BPS,
    ADVISORY_MAX_CORRELATION,
    ADVISORY_MAX_ENTRY_DEVIATION_ATR,
    ADVISORY_MAX_FUTURES_SPREAD_BPS,
    ADVISORY_MAX_OPPOSING_BOOK_IMBALANCE,
    ADVISORY_MAX_SIGNALS,
    ADVISORY_MIN_BOOK_DEPTH_USDT,
    ADVISORY_MIN_CONTRACT_AGE_DAYS,
    ADVISORY_MIN_FUTURES_QUOTE_VOLUME,
    ADVISORY_ORDER_BOOK_LEVELS,
    ADVISORY_QUOTE_CURRENCY,
    ADVISORY_SIGNAL_TTL_MINUTES,
    ADVISORY_SPOT_BASES,
    ADVISORY_START_HOUR,
    ADVISORY_TIMEZONE,
    ADVISORY_TOP_COINS,
)
from app.data.data_service import DataService
from app.exchange.binance_market_data_client import BinanceMarketDataClient
from app.indicators.indicator_engine import IndicatorEngine
from app.scanner.market_scanner import MarketScanner
from app.storage.advisory_signal_repository import AdvisorySignalRepository


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
    market_regime: str = "UNKNOWN"
    setup_price: float | None = None
    entry_deviation_pct: float | None = None
    expires_at: datetime | None = None
    order_book: dict | None = None


@dataclass(frozen=True)
class AdvisoryReport:
    generated_at: datetime
    window_open: bool
    forced: bool = False
    candidates: tuple[AdvisoryCandidate, ...] = ()
    shortlist: tuple[AdvisoryCandidate, ...] = ()
    errors: tuple[str, ...] = ()
    calibration: dict = field(default_factory=dict)


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
        journal=None,
        outcome_tracker=None,
        correlation_selector=None,
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
        self.journal = journal or AdvisorySignalRepository()
        self.outcome_tracker = outcome_tracker or AdvisoryOutcomeTracker(
            public_client, self.journal
        )
        self.correlation_selector = correlation_selector or CorrelationAwareSelector(
            ADVISORY_MAX_CORRELATION
        )

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

        if window_open:
            self.outcome_tracker.resolve_open(local_now)

        candidates = []
        returns_by_symbol = {}
        errors = []
        self.progress("Loading Binance USD-M futures liquidity and spreads...")
        try:
            symbols = self.scanner.get_top_futures_pairs(
                self.limit,
                min_quote_volume=ADVISORY_MIN_FUTURES_QUOTE_VOLUME,
                max_spread_bps=ADVISORY_MAX_FUTURES_SPREAD_BPS,
                min_contract_age_days=ADVISORY_MIN_CONTRACT_AGE_DAYS,
            )
        except (ccxt.NetworkError, ccxt.ExchangeError) as error:
            return AdvisoryReport(
                local_now,
                window_open,
                forced=force,
                errors=(f"Market scan failed: {error}",),
            )

        if not symbols:
            errors.append(
                "Market scan returned no eligible Binance USD-M futures markets."
            )

        for index, symbol in enumerate(symbols, start=1):
            self.progress(
                f"[{index}/{len(symbols)}] Loading {symbol} indicators "
                "(1d, 4h, 1h, 15m, 5m + futures positioning)..."
            )
            try:
                data = self.indicators.calculate_multi_timeframe(symbol)
                data["trigger"] = self.indicators.calculate(symbol, "5m")
                hourly_returns = self._load_hourly_returns(symbol)
                if hourly_returns is not None:
                    returns_by_symbol[symbol] = hourly_returns
                context = self._load_context(symbol)
                signal = self.signal_engine.evaluate(symbol, data, context)
                trade = None
                reasons = list(signal.reasons)
                status = signal.direction
                setup_price = self._float_or_none(data["entry"].get("close"))
                current_price = (
                    context.mark_price
                    if context is not None and context.mark_price is not None
                    else setup_price
                )
                entry_deviation_pct = self._entry_deviation_pct(
                    setup_price,
                    current_price,
                )
                order_book = None
                if status in {"LONG", "SHORT"}:
                    failure = self._entry_deviation_failure(
                        setup_price,
                        current_price,
                        data["entry"].get("atr"),
                    )
                    order_book = self._load_order_book(symbol)
                    failure = failure or self._order_book_failure(status, order_book)
                    if failure is not None:
                        status = "WAIT"
                        reasons.insert(0, failure)
                    else:
                        entry_data = data["entry"].copy()
                        if current_price is not None:
                            entry_data["close"] = current_price
                        trade = self.planner.create(status, entry_data)
                        if trade is None:
                            status = "WAIT"
                            reasons.insert(0, "Net reward/risk is too low after costs")
                candidates.append(
                    AdvisoryCandidate(
                        symbol=symbol,
                        status=status,
                        score=signal.score,
                        price=current_price,
                        trade=trade,
                        reasons=tuple(reasons),
                        derivatives=context,
                        risk=self._risk_label(data["entry"].get("atr_pct")),
                        market_regime=self._market_regime(data.get("trend", {})),
                        setup_price=setup_price,
                        entry_deviation_pct=entry_deviation_pct,
                        expires_at=(
                            local_now + timedelta(minutes=ADVISORY_SIGNAL_TTL_MINUTES)
                            if trade is not None
                            else None
                        ),
                        order_book=order_book,
                    )
                )
                self.progress(
                    f"[{index}/{len(symbols)}] {symbol}: {status} score={signal.score}"
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
        shortlist = self.correlation_selector.select(
            visible_candidates,
            returns_by_symbol,
            self.max_signals,
        )
        report = AdvisoryReport(
            generated_at=local_now,
            window_open=window_open,
            forced=force,
            candidates=visible_candidates,
            shortlist=shortlist,
            errors=tuple(errors),
            calibration=self._load_calibration(),
        )
        if window_open:
            self.journal.save_report(report)
        return report

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
            context = self.context_client.get_derivatives_context(symbol)
            return context if isinstance(context, DerivativesContext) else None
        except (
            ccxt.NetworkError,
            ccxt.ExchangeError,
            KeyError,
            TypeError,
            ValueError,
        ):
            return None

    def _load_order_book(self, symbol: str) -> dict | None:
        try:
            quality = self.context_client.get_futures_order_book_quality(
                symbol,
                limit=ADVISORY_ORDER_BOOK_LEVELS,
            )
            return quality if isinstance(quality, dict) else None
        except (
            ccxt.NetworkError,
            ccxt.ExchangeError,
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _entry_deviation_pct(
        setup_price: float | None,
        current_price: float | None,
    ) -> float | None:
        if setup_price in {None, 0.0} or current_price is None:
            return None
        return abs(current_price / setup_price - 1) * 100

    @staticmethod
    def _entry_deviation_failure(
        setup_price: float | None,
        current_price: float | None,
        atr,
    ) -> str | None:
        if setup_price is None or current_price is None or atr is None:
            return None
        maximum = float(atr) * ADVISORY_MAX_ENTRY_DEVIATION_ATR
        if abs(current_price - setup_price) > maximum:
            return "Mark price moved too far from the completed setup candle"
        return None

    @staticmethod
    def _order_book_failure(direction: str, quality: dict | None) -> str | None:
        if quality is None:
            return None
        spread = quality.get("spread_bps")
        if spread is not None and float(spread) > ADVISORY_MAX_BOOK_SPREAD_BPS:
            return "Current futures spread is too wide"
        depth = quality.get("total_depth_usdt")
        if depth is not None and float(depth) < ADVISORY_MIN_BOOK_DEPTH_USDT:
            return "Current futures order-book depth is too low"
        imbalance = quality.get("imbalance")
        if imbalance is not None:
            opposing = (
                direction == "LONG"
                and float(imbalance) < -ADVISORY_MAX_OPPOSING_BOOK_IMBALANCE
            ) or (
                direction == "SHORT"
                and float(imbalance) > ADVISORY_MAX_OPPOSING_BOOK_IMBALANCE
            )
            if opposing:
                return "Current order-book imbalance opposes the setup"
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

    @staticmethod
    def _market_regime(trend) -> str:
        close = float(trend.get("close", 0))
        ema200 = float(trend.get("ema200", 0))
        slope = float(trend.get("ema20_slope_pct", 0))
        if close > ema200 and slope > 0:
            return "BULL"
        if close < ema200 and slope < 0:
            return "BEAR"
        return "SIDEWAYS"

    def _load_calibration(self) -> dict:
        calibration = self.journal.calibration()
        return calibration if isinstance(calibration, dict) else {}

    def _load_hourly_returns(self, symbol: str) -> tuple[float, ...] | None:
        try:
            frame = self.indicators.get_dataframe(symbol, "1h")
            if not isinstance(frame, pd.DataFrame) or "close" not in frame.columns:
                return None
            values = frame["close"].pct_change().dropna().tail(96)
            return tuple(float(value) for value in values)
        except (KeyError, TypeError, ValueError):
            return None
