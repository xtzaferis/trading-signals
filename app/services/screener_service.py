import ccxt

from app.core.logger import logger
from app.indicators.indicator_engine import IndicatorEngine
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

        trade_plans = []

        pairs = self.scanner.get_spot_pairs()

        logger.info(f"Scanning {len(pairs)} pairs...")

        # Προσωρινά σκανάρουμε μόνο τα πρώτα 10
        for symbol in pairs[:10]:

            try:

                data = self.indicators.calculate_multi_timeframe(
                    symbol=symbol,
                )

                signal = self.signal.evaluate(
                    symbol,
                    data,
                )

                trade = self.risk.create_trade_plan(
                    signal=signal,
                    indicators=data["entry"],
                )

                if trade is not None:
                    trade_plans.append(trade)

            except (
                ccxt.NetworkError,
                ccxt.ExchangeError,
            ) as e:

                logger.error(f"{symbol}: {e}")

        trade_plans.sort(
            key=lambda x: x.position_size,
            reverse=True,
        )

        return trade_plans