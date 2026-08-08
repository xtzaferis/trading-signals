from app.backtesting.market_provider import (
    MarketProvider,
)
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

        self.symbol = "BTC/USDC"

        self.feed = LiveFeed()

        self.portfolio = Portfolio()

        self.market_provider = MarketProvider(
            self.feed
        )

        self.signal_engine = SignalEngine()

        self.risk_manager = RiskManager()

        self.broker = PaperBroker(
            self.portfolio
        )

        self.statistics = StatisticsService()

        self.printer = StatisticsPrinter()

    def process_snapshot(
        self,
        snapshot: dict,
    ):

        self.feed.update(
            snapshot
        )

        if not self.market_provider.has_next():

            return

        market, data = (
            self.market_provider.next()
        )

        entry = market[
            "entry"
        ]

        signal = (
            self.signal_engine.evaluate(
                self.symbol,
                market,
            )
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
            )
        )

        position = self.broker.open(
            trade_plan,
            opened_at=data.get(
                "timestamp"
            ),
        )

        if position is None:

            return

        for position in list(
            self.portfolio.open_positions
        ):

            self.broker.update(
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
                timestamp=data.get(
                    "timestamp"
                ),
            )