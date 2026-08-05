from app.core.logger import logger
from app.market.market_analyzer import MarketAnalyzer
from app.services.screener_service import ScreenerService


def main():

    logger.info("=" * 50)
    logger.info("OKX Trading Bot")
    logger.info("=" * 50)

    # ----------------------------------
    # Market Analysis
    # ----------------------------------

    analyzer = MarketAnalyzer()

    market = analyzer.analyze()

    logger.info("Market Analysis")
    logger.info("-" * 50)
    logger.info(f"Score: {market.score}")
    logger.info(f"Bullish: {market.bullish}")

    for reason in market.reasons:
        logger.info(f"✓ {reason}")

    if not market.bullish:
        logger.warning("Market is bearish.")
        logger.warning("Skipping scan.")
        return

    logger.info("Market is bullish.")
    logger.info("Starting screener...")

    # ----------------------------------
    # Screener
    # ----------------------------------

    service = ScreenerService()

    results = service.run()

    logger.info("Top Trading Signals")

    for signal in results[:10]:

        logger.info(
            f"{signal.symbol:<15}"
            f" Score: {signal.score:<3}"
            f" Action: {signal.action}"
        )

        for reason in signal.reasons:
            logger.info(f"   - {reason}")
        
if __name__ == "__main__":
    main()