import ccxt

from app.core.logger import logger
from app.indicators.indicator_engine import IndicatorEngine
from app.scanner.market_scanner import MarketScanner
from app.strategy.signal_engine import SignalEngine


class ScreenerService:

    def __init__(self):
        self.scanner = MarketScanner()
        self.indicators = IndicatorEngine()
        self.signal = SignalEngine()

    def run(self):

        results = []

        pairs = self.scanner.get_spot_pairs()

        logger.info(f"Scanning {len(pairs)} pairs...")

        # Προσωρινά σκανάρουμε μόνο τα πρώτα 10
        for symbol in pairs[:10]:

            try:

                data = self.indicators.calculate_multi_timeframe(
                    symbol=symbol,
                )

                result = self.signal.evaluate(
                    symbol,
                    data,
                )

                results.append(result)

            except (
                ccxt.NetworkError,
                ccxt.ExchangeError,
            ) as e:

                logger.error(f"{symbol}: {e}")

        results.sort(
            key=lambda x: x.score,
            reverse=True,
        )

        return results