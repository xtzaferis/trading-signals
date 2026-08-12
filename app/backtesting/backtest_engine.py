from app.backtesting.backtest_broker import BacktestBroker
from app.backtesting.historical_feed import (
    HistoricalFeed,
)
from app.backtesting.market_provider import (
    MarketProvider,
)
from app.config.settings import (
    BACKTEST_CANDLE_LIMITS,
    MARKET_SYMBOL,
    MIN_BARS_BETWEEN_TRADES,
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

        # A backtest must not depend on the global paper/live mode.
        self.broker = BacktestBroker(
            self.portfolio
        )

        self.statistics = (
            StatisticsService()
        )

        self.printer = (
            StatisticsPrinter()
        )


    def run(
        self,
        data=None,
        close_open_positions: bool = True,
    ):

        logger.info("")
        logger.info("=" * 50)
        logger.info(
            "BACKTEST ENGINE"
        )
        logger.info("=" * 50)


        if data is None:
            data = {

                "4h": self.history.load(
                    symbol=self.symbol,
                    timeframe="4h",
                    limit=BACKTEST_CANDLE_LIMITS["4h"],
                ),

                "1h": self.history.load(
                    symbol=self.symbol,
                    timeframe="1h",
                    limit=BACKTEST_CANDLE_LIMITS["1h"],
                ),

                "15m": self.history.load(
                    symbol=self.symbol,
                    timeframe="15m",
                    limit=BACKTEST_CANDLE_LIMITS["15m"],
                ),
            }


        logger.info(
            f"4H candles: {len(data['4h'])}"
        )

        logger.info(
            f"1H candles: {len(data['1h'])}"
        )

        logger.info(
            f"15M candles: {len(data['15m'])}"
        )


        self.feed.load(
            data
        )


        self.market_provider = (
            MarketProvider(
                self.feed
            )
        )


        last_entry = None
        last_timestamp = None
        entry_bar = -1
        last_closed_bar = None

        while self.market_provider.has_next():

            market, snapshot = (
                self.market_provider.next()
            )


            entry = market.get(
                "entry"
            )


            if any(
                market.get(timeframe) is None
                for timeframe in (
                    "trend",
                    "confirm",
                    "entry",
                )
            ):

                continue

            last_entry = entry
            last_timestamp = snapshot.get(
                "timestamp"
            )
            entry_bar += 1


            #
            # Manage existing positions
            #

            position_closed_this_bar = False

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

                    position_closed_this_bar = True
                    last_closed_bar = entry_bar

                    logger.info(
                        "Position closed."
                    )

            #
            # Do not reopen immediately on the same candle
            # after a stop-loss/take-profit event.
            #
            if position_closed_this_bar:

                continue

            if self.portfolio.has_open_position(
                self.symbol
            ):
                continue

            if (
                last_closed_bar is not None
                and entry_bar - last_closed_bar
                <= MIN_BARS_BETWEEN_TRADES
            ):
                continue

            #
            # Evaluate signal
            #

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

                logger.info(
                    "BUY REJECTED"
                )

                continue


            #
            # Create trade plan
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


            #
            # Open position
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

        # Realize open PnL so the report includes every trade taken during the
        # requested period instead of silently omitting the final position.
        if close_open_positions and last_entry is not None:
            for position in list(
                self.portfolio.open_positions
            ):
                self.broker.close(
                    position,
                    float(last_entry["close"]),
                    "END_OF_BACKTEST",
                    timestamp=last_timestamp,
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
