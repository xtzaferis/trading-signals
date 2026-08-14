from app.backtesting.historical_data_provider import (
    HistoricalDataProvider,
)
from app.config.settings import MARKET_SYMBOL
from app.core.logger import logger
from app.indicators.indicator_engine import (
    IndicatorEngine,
)
from app.services.historical_data_service import (
    HistoricalDataService,
)
from app.strategy.signal_engine import (
    SignalEngine,
)


class Backtester:

    def __init__(self):

        self.history = (
            HistoricalDataService()
        )

        self.provider = (
            HistoricalDataProvider()
        )

        self.indicators = (
            IndicatorEngine(
                data_service=self.provider
            )
        )

        self.signal_engine = (
            SignalEngine()
        )

    def run(self):

        logger.info("")
        logger.info("=" * 50)
        logger.info("BACKTEST ENGINE")
        logger.info("=" * 50)

        data = (
            self.history.load_multiple(
                symbol=MARKET_SYMBOL,
                timeframes=[
                    "4h",
                    "1h",
                    "15m",
                ],
                limit=300,
            )
        )

        self.provider.load(
            data
        )

        logger.info(
            f"15m candles: "
            f"{len(data['15m'])}"
        )

        logger.info(
            f"1h candles: "
            f"{len(data['1h'])}"
        )

        logger.info(
            f"4h candles: "
            f"{len(data['4h'])}"
        )

        self.execute()

        logger.info("")
        logger.info(
            "Backtest finished."
        )

    def execute(self):

        while self.provider.has_next():

            data = (
                self.indicators.calculate_multi_timeframe(
                    symbol=MARKET_SYMBOL,
                )
            )

            signal = (
                self.signal_engine.evaluate(
                    symbol=MARKET_SYMBOL,
                    data=data,
                )
            )

            entry = data["entry"]

            if (
                self.provider.index
                % 10
                == 0
            ):

                logger.info(
                    f"{self.provider.index:>3} | "
                    f"Close={entry['close']:.2f} | "
                    f"EMA20={entry['ema20']:.2f} | "
                    f"EMA50={entry['ema50']:.2f} | "
                    f"EMA200={entry['ema200']:.2f} | "
                    f"RSI={entry['rsi']:.2f} | "
                    f"Action={signal.action} | "
                    f"Score={signal.score} | "
                    f"Reasons={signal.reasons}"
                )

            self.provider.step()

        logger.info("")

        logger.info(
            f"Processed "
            f"{self.provider.total} candles."
        )
