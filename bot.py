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

    candidates = service.run()

    logger.info("")
    logger.info("=" * 50)
    logger.info("TOP TRADING CANDIDATES")
    logger.info("=" * 50)

    if not candidates:
        logger.info("No BUY candidates found.")
        return

    for candidate in candidates[:10]:

        signal = candidate.signal
        trade = candidate.trade

        logger.info(
            f"{signal.symbol:<15}"
            f" Score: {signal.score:<3}"
            f" Confidence: {signal.confidence:.2f}"
            f" Action: {signal.action}"
        )

        for reason in signal.reasons:
            logger.info(f"   ✓ {reason}")

        logger.info(
            f"   Entry:         {trade.entry}"
        )

        logger.info(
            f"   Stop Loss:     {trade.stop_loss}"
        )

        logger.info(
            f"   Take Profit:   {trade.take_profit}"
        )

        logger.info(
            f"   Position Size: {trade.position_size:.2f} USDC"
        )

        logger.info(
            f"   RR:            {trade.risk_reward}:1"
        )

        logger.info("-" * 50)


if __name__ == "__main__":
    main()