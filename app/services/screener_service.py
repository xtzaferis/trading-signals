import ccxt

from app.core.logger import logger
from app.indicators.indicator_engine import IndicatorEngine
from app.models.trade_candidate import TradeCandidate
from app.risk.risk_manager import RiskManager
from app.scanner.market_scanner import MarketScanner
from app.strategy.signal_engine import SignalEngine


class ScreenerService:

    def __init__(self):
        self.scanner = MarketScanner()
        self.indicators = IndicatorEngine()
        self.signal = SignalEngine()
        self.risk = RiskManager()

    def run(self):

        candidates = []

        pairs = self.scanner.get_top_spot_pairs()

        logger.info(f"Scanning {len(pairs)} pairs...")

        # Προσωρινά σκανάρουμε μόνο τα πρώτα 10
        for symbol in pairs:

            try:

                data = self.indicators.calculate_multi_timeframe(
                    symbol=symbol,
                )

                signal = self.signal.evaluate(
                    symbol=symbol,
                    data=data,
                )

                if signal.action != "BUY":
                    continue

                trade = self.risk.create_trade_plan(
                    signal=signal,
                    indicators=data["entry"],
                )

                candidates.append(
                    TradeCandidate(
                        signal=signal,
                        trade=trade,
                    )
                )

            except (
                ccxt.NetworkError,
                ccxt.ExchangeError,
            ) as e:

                logger.error(f"{symbol}: {e}")

        candidates.sort(
            key=lambda c: c.signal.score,
            reverse=True,
        )

        return candidates
