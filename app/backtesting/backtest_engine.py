from app.backtesting.historical_feed import (
    HistoricalFeed,
)
from app.backtesting.market_provider import (
    MarketProvider,
)
from app.config.settings import (
    MARKET_SYMBOL,
)
from app.core.logger import logger
from app.execution.broker_factory import (
    create_broker,
)
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

        self.symbol = MARKET_SYMBOL

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

        self.broker = create_broker(
            self.portfolio
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
                limit=2000,
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

            market, snapshot = (
                self.market_provider.next()
            )

            entry = market[
                "entry"
            ]


            #
            # 1. Manage existing positions
            #

            for position in list(
                self.portfolio.open_positions
            ):

                closed = (
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
                        timestamp=snapshot.get(
                            "timestamp"
                        ),
                    )
                )


                if closed:

                    logger.info(
                        "Position closed."
                    )

                    logger.info(
                        f"OPEN POSITIONS AFTER CLOSE: "
                        f"{len(self.portfolio.open_positions)}"
                    )

                    logger.info(
                        f"CLOSED POSITIONS: "
                        f"{len(self.portfolio.closed_positions)}"
)


            #
            # 2. Evaluate new signal
            #

            signal = (
                self.signal_engine.evaluate(
                    self.symbol,
                    market,
                )
            )

            if signal.action == "BUY":
                logger.info(
                    f"BUY SIGNAL FOUND AT INDEX "
                    f"{self.feed.timeline.current_index}"
                )


            logger.info(
                f"{entry['close']:.2f} | "
                f"Score={signal.score} | "
                f"Action={signal.action}"
            )


            if signal.action != "BUY":

                continue


            #
            # 3. Create trade plan
            #

            trade_plan = (
                self.risk_manager.create_trade_plan(
                    signal,
                    entry,
                )
            )


            if trade_plan is None:

                logger.warning(
                    "Trade plan rejected."
                )

                continue


            # Log trade plan details for debugging
            logger.info(
                f"TRADE PLAN -> symbol={trade_plan.symbol} "
                f"entry={trade_plan.entry} stop_loss={trade_plan.stop_loss} "
                f"take_profit={trade_plan.take_profit} position_value={trade_plan.position_size}"
            )

            #
            # 4. Open position
            #

            position = (
                self.broker.open(
                    trade_plan,
                    opened_at=snapshot.get(
                        "timestamp"
                    ),
                )
            )


            if position:

                logger.info(
                    f"OPENED: {position.symbol} "
                    f"@ {position.entry_price}"
                )

                # Log opened position summary
                logger.info(
                    f"POSITION OPENED -> qty={position.quantity:.8f} "
                    f"entry_fee={getattr(position,'entry_fee',0.0):.6f} "
                    f"initial_risk={getattr(position,'initial_risk',0.0):.6f}"
                )


        #
        # Statistics
        #

        report = (
            self.statistics.generate(
                self.portfolio
            )
        )


        self.printer.print(
            report
        )


        logger.info("")

        logger.info(
            "Closed positions: "
            f"{len(self.portfolio.closed_positions)}"
        )


        logger.info(
            "Backtest finished."
        )