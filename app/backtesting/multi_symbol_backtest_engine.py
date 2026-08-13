from collections import Counter, defaultdict
from datetime import datetime
from heapq import heappop, heappush

import ccxt

from app.backtesting.backtest_broker import BacktestBroker
from app.backtesting.historical_feed import HistoricalFeed
from app.backtesting.market_provider import MarketProvider
from app.backtesting.trade_cooldown import (
    cooldown_bars_for_exit,
)
from app.config.settings import (
    BACKTEST_CANDLE_LIMITS,
    BACKTEST_DATA_QUOTE_CURRENCY,
    BACKTEST_MIN_HISTORY_RATIO,
    MAX_DRAWDOWN_PCT,
    QUOTE_CURRENCY,
    SLIPPAGE,
    TOP_COINS,
    TRADING_FEE,
)
from app.core.logger import logger
from app.risk.risk_manager import RiskManager
from app.scanner.market_scanner import MarketScanner
from app.services.historical_data_service import HistoricalDataService
from app.services.statistics_printer import StatisticsPrinter
from app.services.statistics_service import StatisticsService
from app.strategy.signal_engine import SignalEngine
from app.trading.portfolio import Portfolio


class MultiSymbolBacktestEngine:
    """Run synchronized spot signals against one shared cash portfolio."""

    def __init__(self):
        self.scanner = MarketScanner()
        self.portfolio = Portfolio()
        self.broker = BacktestBroker(self.portfolio)
        self.signal_engine = SignalEngine()
        self.risk_manager = RiskManager()
        self.statistics = StatisticsService()
        self.printer = StatisticsPrinter()
        self.symbols: list[str] = []
        self.rejection_counts = Counter()
        self.rejections_by_symbol: dict[str, Counter] = {}

    def run(
        self,
        symbols: list[str] | None = None,
        data: dict[str, dict] | None = None,
        start_at: datetime | float | None = None,
        end_at: datetime | float | None = None,
    ):
        logger.info("")
        logger.info("=" * 60)
        logger.info("MULTI-SYMBOL SPOT BACKTEST")
        logger.info("=" * 60)

        if data is not None:
            self.symbols = list(
                symbols or data.keys()
            )
        else:
            self.symbols = list(
                symbols
                or self.scanner.get_top_spot_pairs(
                    TOP_COINS
                )
            )
            data = self._load_data(self.symbols)
            self.symbols = [
                symbol
                for symbol in self.symbols
                if symbol in data
            ]

        logger.info(
            "Selected pairs: "
            + ", ".join(self.symbols)
        )

        start_timestamp = self._timestamp_ms(start_at)
        end_timestamp = self._timestamp_ms(end_at)
        if (
            start_timestamp is not None
            and end_timestamp is not None
            and start_timestamp > end_timestamp
        ):
            raise ValueError("start_at must be before end_at")

        providers: dict[str, MarketProvider] = {}
        event_heap = []
        total_events = 0

        for symbol in self.symbols:
            symbol_data = data.get(symbol)
            if not symbol_data:
                continue

            feed = HistoricalFeed()
            feed.load(symbol_data)
            provider = MarketProvider(feed)
            providers[symbol] = provider
            total_events += len(
                symbol_data["15m"]
            )
            self._push_next_event(
                event_heap,
                symbol,
                provider,
            )

        processed_events = 0
        last_entries = {}
        last_timestamps = {}
        last_closed_bar: dict[str, int] = {}
        required_cooldowns: dict[str, int] = {}
        symbol_bars = Counter()
        rejection_counts = Counter()
        rejections_by_symbol = defaultdict(Counter)
        benchmark_prices: dict[str, list[float]] = {}

        while event_heap:
            timestamp = event_heap[0][0]
            if (
                end_timestamp is not None
                and timestamp > end_timestamp
            ):
                break
            events = []

            while (
                event_heap
                and event_heap[0][0] == timestamp
            ):
                _, symbol, market, snapshot = (
                    heappop(event_heap)
                )
                events.append((
                    symbol,
                    market,
                    snapshot,
                ))
                processed_events += 1

            candidates = []
            closed_symbols = set()

            for symbol, market, snapshot in events:
                provider = providers[symbol]
                self._push_next_event(
                    event_heap,
                    symbol,
                    provider,
                )

                if any(
                    market.get(timeframe) is None
                    for timeframe in (
                        "regime",
                        "trend",
                        "confirm",
                        "entry",
                    )
                ):
                    continue

                if (
                    start_timestamp is not None
                    and snapshot["timestamp"] < start_timestamp
                ):
                    continue

                entry = market["entry"]
                prices = benchmark_prices.setdefault(
                    symbol,
                    [float(entry["close"]), float(entry["close"])],
                )
                prices[1] = float(entry["close"])
                symbol_bars[symbol] += 1
                bar_number = symbol_bars[symbol]
                last_entries[symbol] = entry
                last_timestamps[symbol] = snapshot[
                    "timestamp"
                ]
                evaluated_at = self.broker._as_datetime(
                    snapshot["timestamp"]
                )
                if (
                    self.portfolio.backtest_started_at is None
                    or evaluated_at
                    < self.portfolio.backtest_started_at
                ):
                    self.portfolio.backtest_started_at = (
                        evaluated_at
                    )
                if (
                    self.portfolio.backtest_ended_at is None
                    or evaluated_at
                    > self.portfolio.backtest_ended_at
                ):
                    self.portfolio.backtest_ended_at = evaluated_at

                for position in list(
                    self.portfolio.open_positions
                ):
                    if position.symbol != symbol:
                        continue

                    if self.broker.update(
                        position,
                        high=entry.get(
                            "high",
                            entry["close"],
                        ),
                        low=entry.get(
                            "low",
                            entry["close"],
                        ),
                        close=entry["close"],
                        timestamp=snapshot["timestamp"],
                    ):
                        last_closed_bar[symbol] = (
                            bar_number
                        )
                        required_cooldowns[symbol] = (
                            cooldown_bars_for_exit(
                                position.exit_reason
                            )
                        )
                        closed_symbols.add(symbol)

                if (
                    symbol in closed_symbols
                    or self.portfolio.has_open_position(
                        symbol
                    )
                ):
                    continue

                last_close = last_closed_bar.get(
                    symbol
                )
                if (
                    last_close is not None
                    and bar_number - last_close
                    <= required_cooldowns.get(symbol, 0)
                ):
                    continue

                signal = self.signal_engine.evaluate(
                    symbol,
                    market,
                )
                if signal.action != "BUY":
                    reason = (
                        signal.reasons[0]
                        if signal.reasons
                        else "Unspecified signal rejection"
                    )
                    rejection_counts[reason] += 1
                    rejections_by_symbol[symbol][reason] += 1
                    continue

                candidates.append((
                    signal.score,
                    symbol,
                    signal,
                    entry,
                    snapshot["timestamp"],
                ))

            self.portfolio.update_peak_equity()
            drawdown_exceeded = (
                self.portfolio.is_max_drawdown_exceeded(
                    MAX_DRAWDOWN_PCT
                )
            )

            if not drawdown_exceeded:
                for (
                    _,
                    symbol,
                    signal,
                    entry,
                    opened_at,
                ) in sorted(
                    candidates,
                    key=lambda item: (
                        -item[0],
                        item[1],
                    ),
                ):
                    trade_plan = (
                        self.risk_manager.create_trade_plan(
                            signal,
                            entry,
                            available_cash=(
                                self.portfolio.available_cash
                            ),
                        )
                    )
                    if trade_plan is None:
                        rejection_counts[
                            "Trade plan rejected"
                        ] += 1
                        rejections_by_symbol[symbol][
                            "Trade plan rejected"
                        ] += 1
                        continue

                    position = self.broker.open(
                        trade_plan,
                        opened_at=opened_at,
                    )
                    if position:
                        logger.info(
                            f"OPENED: {symbol} "
                            f"@ {position.entry_price:.6f}"
                        )

            if (
                processed_events % 10_000 == 0
                or processed_events == total_events
            ):
                logger.info(
                    "Portfolio backtest progress: "
                    f"{processed_events}/{total_events} "
                    f"({processed_events / total_events:.0%})"
                )

        for position in list(
            self.portfolio.open_positions
        ):
            entry = last_entries.get(
                position.symbol
            )
            if entry is None:
                continue
            self.broker.close(
                position,
                float(entry["close"]),
                "END_OF_BACKTEST",
                timestamp=last_timestamps.get(
                    position.symbol
                ),
            )

        report = self.statistics.generate(
            self.portfolio
        )
        report.benchmark_return = self._benchmark_return(
            benchmark_prices
        )
        report.alpha = (
            report.total_return
            - report.benchmark_return
        )
        self.printer.print(report)

        logger.info("Signal rejection summary:")
        for reason, count in (
            rejection_counts.most_common()
        ):
            logger.info(f"  {reason}: {count}")

        logger.info("Signal rejections by symbol:")
        for symbol in self.symbols:
            counts = rejections_by_symbol[symbol]
            if not counts:
                logger.info(f"  {symbol}: none")
                continue
            summary = ", ".join(
                f"{reason}={count}"
                for reason, count in counts.most_common()
            )
            logger.info(f"  {symbol}: {summary}")

        logger.info("Trades by symbol:")
        trade_counts = Counter(
            position.symbol
            for position in self.portfolio.closed_positions
        )
        pnl_by_symbol = defaultdict(float)
        for position in self.portfolio.closed_positions:
            pnl_by_symbol[position.symbol] += position.realized_pnl
        for symbol in self.symbols:
            logger.info(
                f"  {symbol}: {trade_counts[symbol]} trades, "
                f"{pnl_by_symbol[symbol]:+.2f} USDC"
            )

        self.rejection_counts = rejection_counts
        self.rejections_by_symbol = {
            symbol: Counter(counts)
            for symbol, counts in rejections_by_symbol.items()
        }

        return report

    @staticmethod
    def _push_next_event(
        event_heap: list,
        symbol: str,
        provider: MarketProvider,
    ) -> None:
        if not provider.has_next():
            return

        market, snapshot = provider.next()
        heappush(
            event_heap,
            (
                snapshot["timestamp"],
                symbol,
                market,
                snapshot,
            ),
        )

    @staticmethod
    def _load_data(
        symbols: list[str],
    ) -> dict[str, dict]:
        loaded = {}

        for index, symbol in enumerate(
            symbols,
            start=1,
        ):
            data_symbol = (
                MultiSymbolBacktestEngine._data_symbol(
                    symbol
                )
            )
            proxy_note = (
                f" using {data_symbol} history proxy"
                if data_symbol != symbol
                else ""
            )
            logger.info(
                f"Loading pair {index}/{len(symbols)}: "
                f"{symbol}{proxy_note}"
            )
            history = HistoricalDataService()

            try:
                symbol_data = {
                    timeframe: history.load(
                        symbol=data_symbol,
                        timeframe=timeframe,
                        limit=limit,
                    )
                    for timeframe, limit in (
                        BACKTEST_CANDLE_LIMITS.items()
                    )
                }
            except (
                ccxt.NetworkError,
                ccxt.ExchangeError,
            ):
                logger.exception(
                    f"Skipping {symbol}: history load failed."
                )
                continue

            incomplete = {
                timeframe: (
                    len(symbol_data[timeframe]),
                    MultiSymbolBacktestEngine._minimum_history(
                        required
                    ),
                )
                for timeframe, required in (
                    BACKTEST_CANDLE_LIMITS.items()
                )
                if len(symbol_data[timeframe])
                < MultiSymbolBacktestEngine._minimum_history(
                    required
                )
            }

            if not incomplete:
                loaded[symbol] = symbol_data
            else:
                logger.warning(
                    f"Skipping {symbol}: incomplete history "
                    f"{incomplete}."
                )

        return loaded

    @staticmethod
    def _minimum_history(requested: int) -> int:
        return int(
            requested * BACKTEST_MIN_HISTORY_RATIO
        )

    @staticmethod
    def _data_symbol(execution_symbol: str) -> str:
        base, _, _ = execution_symbol.partition("/")
        if not base:
            return execution_symbol
        if BACKTEST_DATA_QUOTE_CURRENCY == QUOTE_CURRENCY:
            return execution_symbol
        return f"{base}/{BACKTEST_DATA_QUOTE_CURRENCY}"

    @staticmethod
    def _timestamp_ms(
        value: datetime | float | None,
    ) -> float | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.timestamp() * 1000
        numeric = float(value)
        return numeric * 1000 if numeric < 10_000_000_000 else numeric

    @staticmethod
    def _benchmark_return(
        prices: dict[str, list[float]],
    ) -> float:
        returns = []
        for first, last in prices.values():
            if first <= 0:
                continue
            entry_cost = first * (1 + SLIPPAGE) * (1 + TRADING_FEE)
            exit_value = last * (1 - SLIPPAGE) * (1 - TRADING_FEE)
            returns.append(
                (exit_value / entry_cost - 1) * 100
            )
        return sum(returns) / len(returns) if returns else 0.0
