from datetime import datetime, timedelta, timezone

from app.backtesting.market_provider import (
    MarketProvider,
)
from app.backtesting.trade_cooldown import cooldown_bars_for_exit
from app.config.settings import (
    MARKET_SYMBOL,
    MAX_DRAWDOWN_PCT,
    MAX_ENTRY_CANDLE_AGE_SECONDS,
    PAPER_STATE_PERSISTENCE_ENABLED,
    TRADING_MODE,
)
from app.core.logger import logger
from app.execution.broker_factory import create_broker
from app.paper.live_feed import (
    LiveFeed,
)
from app.risk.risk_manager import (
    RiskManager,
)
from app.services.decision_logger import (
    DecisionLogger,
)
from app.services.recovery_shadow_tracker import (
    RecoveryShadowTracker,
)
from app.services.statistics_printer import (
    StatisticsPrinter,
)
from app.services.statistics_service import (
    StatisticsService,
)
from app.storage.paper_state_repository import (
    PaperStateRepository,
)
from app.strategy.signal_engine import (
    SignalEngine,
)
from app.trading.portfolio import (
    Portfolio,
)


class PaperEngine:

    def __init__(
        self,
        state_repository=None,
        persist_state: bool = PAPER_STATE_PERSISTENCE_ENABLED,
        trading_mode: str = TRADING_MODE,
        broker=None,
        client=None,
    ):

        self.symbol = MARKET_SYMBOL
        self.trading_mode = trading_mode
        self.entries_enabled = True

        self.feed = LiveFeed()

        self.feeds = {self.symbol: self.feed}

        self.state_repository = (
            state_repository
            or (
                PaperStateRepository()
                if persist_state and trading_mode == "paper"
                else None
            )
        )

        self.portfolio = (
            self.state_repository.load()
            if self.state_repository is not None
            else Portfolio()
        )

        if self.portfolio.open_positions:
            logger.info(
                "Restored paper positions: "
                f"{len(self.portfolio.open_positions)}"
            )

        self.market_provider = MarketProvider(
            self.feed
        )

        self.market_providers = {
            self.symbol: self.market_provider
        }

        self.signal_engine = SignalEngine()

        self.risk_manager = RiskManager()

        self.broker = broker or create_broker(
            self.portfolio,
            trading_mode=trading_mode,
            client=client,
        )

        self.statistics = StatisticsService()

        self.printer = StatisticsPrinter()

        self.decision_logger = DecisionLogger()

        self.shadow_tracker = RecoveryShadowTracker()

        restored_state = (
            self.state_repository.load_symbol_state()
            if self.state_repository is not None
            else {}
        )
        if not isinstance(restored_state, dict):
            restored_state = {}
        self.last_processed_entry = {
            symbol: state.get("last_entry_timestamp")
            for symbol, state in restored_state.items()
        }
        self.cooldown_until = {
            symbol: state.get("cooldown_until")
            for symbol, state in restored_state.items()
            if state.get("cooldown_until") is not None
        }

    def process_snapshot(
        self,
        snapshot: dict,
        symbol: str | None = None,
    ):

        symbol = symbol or self.symbol

        if symbol not in self.feeds:
            feed = LiveFeed()
            self.feeds[symbol] = feed
            self.market_providers[symbol] = MarketProvider(feed)

        feed = self.feeds[symbol]
        provider = self.market_providers[symbol]

        feed.update(
            snapshot
        )

        if not provider.has_next():

            return

        market, data = (
            provider.next()
        )

        entry = market[
            "entry"
        ]

        if entry is None:
            return

        entry_timestamp = self._as_datetime(entry.get("timestamp"))
        if self._is_stale_entry(entry_timestamp):
            logger.warning(
                f"Skipping stale completed candle for {symbol}: "
                f"{entry_timestamp}"
            )
            return
        if (
            entry_timestamp is not None
            and self.last_processed_entry.get(symbol) == entry_timestamp
        ):
            return
        if entry_timestamp is not None:
            self.last_processed_entry[symbol] = entry_timestamp

        closed_this_cycle = False
        for position in list(self.portfolio.open_positions):
            if position.symbol != symbol:
                continue
            closed = self.broker.update(
                position,
                high=entry.get("high", entry["close"]),
                low=entry.get("low", entry["close"]),
                close=entry["close"],
                timestamp=data.get("timestamp"),
            )
            if closed:
                closed_this_cycle = True
                cooldown_bars = cooldown_bars_for_exit(
                    position.exit_reason
                )
                self.cooldown_until[symbol] = (
                    self._as_datetime(data.get("timestamp"))
                    or datetime.now(timezone.utc)
                ) + timedelta(minutes=15 * cooldown_bars)

        self._save_state()

        self.shadow_tracker.observe(
            symbol,
            market,
            data.get("timestamp"),
        )

        if closed_this_cycle:
            return

        cooldown_until = self.cooldown_until.get(symbol)
        now = self._as_datetime(data.get("timestamp")) or datetime.now(
            timezone.utc
        )
        if cooldown_until is not None and now <= cooldown_until:
            logger.info(
                f"Entry cooldown active for {symbol} until "
                f"{cooldown_until.isoformat()}"
            )
            return

        signal = (
            self.signal_engine.evaluate(
                symbol,
                market,
            )
        )

        self.decision_logger.log(
            symbol=symbol,
            price=entry["close"],
            score=signal.score,
            action=signal.action,
            reasons=signal.reasons,
        )

        logger.info(
            f"{entry['close']:.2f} | "
            f"Score={signal.score} | "
            f"Action={signal.action}"
        )

        if signal.action != "BUY":

            return

        if not self.entries_enabled:
            logger.warning(
                "New entry blocked: exchange reconciliation is unresolved."
            )
            return
        if hasattr(self.broker, "entries_allowed"):
            allowed, reason = self.broker.entries_allowed()
            if not allowed:
                logger.warning(f"New entry blocked by circuit breaker: {reason}")
                return

        trade_plan = (
            self.risk_manager.create_trade_plan(
                signal,
                entry,
                available_cash=self.portfolio.available_cash,
            )
        )

        if trade_plan is None:
            return

        self.portfolio.update_peak_equity()
        if self.portfolio.is_max_drawdown_exceeded(
            MAX_DRAWDOWN_PCT
        ):
            logger.warning(
                "Paper entry blocked: maximum drawdown exceeded."
            )
            self._save_state()
            return

        position = (
            self.broker.open(
                trade_plan,
                opened_at=data.get(
                    "timestamp"
                ),
            )
        )

        if position is None:

            return
        self._save_state()

    def _save_state(self) -> None:
        if self.state_repository is not None:
            symbols = set(self.last_processed_entry) | set(
                self.cooldown_until
            )
            symbol_state = {
                symbol: {
                    "last_entry_timestamp": (
                        self.last_processed_entry.get(symbol)
                    ),
                    "cooldown_until": self.cooldown_until.get(symbol),
                }
                for symbol in symbols
            }
            self.state_repository.save(
                self.portfolio,
                symbol_state,
            )

    def save_state(self) -> None:
        """Persist the latest portfolio and per-symbol processing state."""
        self._save_state()

    def reconcile_execution(self) -> dict:
        if self.trading_mode == "paper":
            self.entries_enabled = True
            return {"safe": True}

        result = self.broker.reconcile()
        self.entries_enabled = bool(result.get("safe"))
        if self.entries_enabled:
            result["available_cash"] = self.broker.sync_balance()
        else:
            logger.error(
                "Exchange reconciliation unresolved; new entries disabled."
            )
        return result

    @staticmethod
    def _is_stale_entry(value) -> bool:
        if value is None:
            return False
        if hasattr(value, "to_pydatetime"):
            value = value.to_pydatetime()
        if not isinstance(value, datetime):
            return False
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        candle_closed_at = value + timedelta(minutes=15)
        age = datetime.now(timezone.utc) - candle_closed_at
        return age.total_seconds() > MAX_ENTRY_CANDLE_AGE_SECONDS

    @staticmethod
    def _as_datetime(value) -> datetime | None:
        if value is None:
            return None
        if hasattr(value, "to_pydatetime"):
            value = value.to_pydatetime()
        if not isinstance(value, datetime):
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
