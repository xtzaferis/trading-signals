from app.backtesting.backtest_broker import (
    BacktestBroker,
)
from app.backtesting.historical_feed import (
    HistoricalFeed,
)
from app.backtesting.market_provider import (
    MarketProvider,
)
from app.core.logger import logger
from app.risk.risk_manager import (
    RiskManager,
)
from app.services.historical_data_service import (
    HistoricalDataService,
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


class BacktestEngine:

    def __init__(self):

        self.symbol = "BTC/USDC"

        self.history = (
            HistoricalDataService()
        )

        self.feed = (
            HistoricalFeed()
        )

        self.portfolio = (
            Portfolio()
        )

        self.market_provider = None

        self.signal_engine = (
            SignalEngine()
        )

        self.risk_manager = (
            RiskManager()
        )

        self.broker = (
            BacktestBroker(
                self.portfolio
            )
        )

        self.statistics = (
            StatisticsService()
        )

        self.printer = (
            StatisticsPrinter()
        )

    def run(self):

        logger.info("")
        logger.info("=" * 50)
        logger.info(
            "BACKTEST ENGINE"
        )
        logger.info("=" * 50)

        data = (
            self.history.load_multiple(
                symbol=self.symbol,
                timeframes=[
                    "4h",
                    "1h",
                    "15m",
                ],
                limit=300,
            )
        )

        self.feed.load(
            data
        )

        self.market_provider = (
            MarketProvider(
                self.feed
            )
        )

        while self.market_provider.has_next():

            market, _snapshot = (
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
                continue

            trade_plan = (
                self.risk_manager.create_trade_plan(
                    signal,
                    entry,
                )
            )

            self.broker.open(
                trade_plan,
                opened_at=_snapshot.get(
                    "timestamp"
                ),
            )

        logger.info("")
        logger.info(
            "Backtest finished."
        )