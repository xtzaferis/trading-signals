from app.config.settings import QUOTE_CURRENCY
from app.core.logger import logger
from app.services.recovery_shadow_tracker import RecoveryShadowTracker
from app.storage.paper_health_repository import PaperHealthRepository
from app.storage.paper_state_repository import PaperStateRepository


def main():
    paper = PaperStateRepository().status()
    shadow = RecoveryShadowTracker().summary()
    health = PaperHealthRepository().status()

    logger.info("")
    logger.info("=" * 50)
    logger.info("PAPER OPERATIONS STATUS")
    logger.info("=" * 50)
    logger.info(f"Last State Save:   {paper['updated_at'] or 'never'}")
    logger.info(f"Runner Health:     {health['health']}")
    logger.info(
        f"Last Cycle:        {health['completed_at'] or 'never'}"
    )
    logger.info(
        "Symbol Results:    "
        f"{health['successful_symbols']} successful, "
        f"{health['failed_symbols']} failed"
    )
    if health["last_error"]:
        logger.info(f"Last Error:        {health['last_error']}")
    for symbol, failure in health["symbol_failures"].items():
        logger.info(
            f"  {symbol}: {failure['count']} consecutive failures "
            f"({failure['error']})"
        )
    logger.info(
        f"Paper Cash:        {paper['cash']:.2f} {QUOTE_CURRENCY}"
    )
    logger.info(f"Open Positions:    {paper['open_positions']}")
    logger.info(f"Closed Positions:  {paper['closed_positions']}")
    logger.info(f"Open Shadows:      {shadow['open']}")
    logger.info(f"Closed Shadows:    {shadow['trades']}")
    logger.info(
        "Recovery Trading:  "
        + ("ELIGIBLE FOR REVIEW" if shadow["ready"] else "DISABLED")
    )
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
