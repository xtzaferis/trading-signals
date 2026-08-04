from app.scanner.market_scanner import MarketScanner
from app.indicators.indicator_engine import IndicatorEngine
from app.strategy.signal_engine import SignalEngine


class ScreenerService:

    def __init__(self):

        self.scanner = MarketScanner()
        self.indicators = IndicatorEngine()
        self.signal = SignalEngine()

    def run(self):

        results = []

        pairs = self.scanner.get_spot_pairs()

        print(f"Scanning {len(pairs)} pairs...\n")

        # Προσωρινά θα σκανάρουμε μόνο τα πρώτα 10
        # για να δοκιμάσουμε ότι όλα δουλεύουν.
        for symbol in pairs[:10]:

            try:

                data = self.indicators.calculate(symbol)

                result = self.signal.evaluate(symbol, data)

                results.append(result)

            except Exception as e:

                print(f"{symbol}: {e}")

        results.sort(
            key=lambda x: x.score,
            reverse=True
        )

        return results