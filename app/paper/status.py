from app.core.logger import logger
from app.services.recovery_shadow_tracker import RecoveryShadowTracker
from app.storage.paper_state_repository import PaperStateRepository


def main():
    paper = PaperStateRepository().status()
    shadow = RecoveryShadowTracker().summary()

    logger.info("")
    logger.info("=" * 50)
    logger.info("PAPER OPERATIONS STATUS")
    logger.info("=" * 50)
    logger.info(f"Last State Save:   {paper['updated_at'] or 'never'}")
    logger.info(f"Paper Cash:        {paper['cash']:.2f} USDC")
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
