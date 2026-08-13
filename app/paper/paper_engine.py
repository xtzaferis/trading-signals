from app.backtesting.market_provider import (
    MarketProvider,
)
from app.config.settings import MARKET_SYMBOL
from app.core.logger import logger
from app.execution.paper_broker import (
    PaperBroker,
)
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
from app.strategy.signal_engine import (
    SignalEngine,
)
from app.trading.portfolio import (
    Portfolio,
)


class PaperEngine:

    def __init__(self):

        self.symbol = MARKET_SYMBOL

        self.feed = LiveFeed()

        self.feeds = {self.symbol: self.feed}

        self.portfolio = Portfolio()

        self.market_provider = MarketProvider(
            self.feed
        )

        self.market_providers = {
            self.symbol: self.market_provider
        }

        self.signal_engine = SignalEngine()

        self.risk_manager = RiskManager()

        self.broker = PaperBroker(
            self.portfolio
        )

        self.statistics = StatisticsService()

        self.printer = StatisticsPrinter()

        self.decision_logger = DecisionLogger()

        self.shadow_tracker = RecoveryShadowTracker()

        self.last_processed_entry = {}

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

        entry_timestamp = entry.get("timestamp")
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
            closed_this_cycle = self.broker.update(
                position,
                high=entry.get("high", entry["close"]),
                low=entry.get("low", entry["close"]),
                close=entry["close"],
                timestamp=data.get("timestamp"),
            ) or closed_this_cycle

        self.shadow_tracker.observe(
            symbol,
            market,
            data.get("timestamp"),
        )

        if closed_this_cycle:
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
        )

        logger.info(
            f"{entry['close']:.2f} | "
            f"Score={signal.score} | "
            f"Action={signal.action}"
        )

        if signal.action != "BUY":

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
