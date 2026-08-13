from app.config.settings import (
    SHADOW_MIN_CLOSED_TRADES,
    SHADOW_MIN_PROFIT_FACTOR,
)
from app.core.logger import logger
from app.services.recovery_shadow_tracker import RecoveryShadowTracker


def main():
    report = RecoveryShadowTracker().summary()

    logger.info("")
    logger.info("=" * 50)
    logger.info("RECOVERY SHADOW VALIDATION")
    logger.info("=" * 50)
    logger.info(f"Open Shadows:      {report['open']}")
    logger.info(f"Closed Shadows:    {report['trades']}")
    logger.info(f"Wins:              {report['wins']}")
    logger.info(f"Losses:            {report['losses']}")
    logger.info(f"Net Profit:        {report['net_profit']:.2f} USDC")
    logger.info(f"Profit Factor:     {report['profit_factor']:.2f}")
    logger.info(f"Expectancy:        {report['expectancy']:.2f} USDC")
    logger.info(
        "Promotion Criteria: "
        f">={SHADOW_MIN_CLOSED_TRADES} trades, "
        f"PF>={SHADOW_MIN_PROFIT_FACTOR:.2f}, expectancy>0"
    )
    logger.info(
        "Recovery Trading:   "
        + ("ELIGIBLE FOR REVIEW" if report["ready"] else "DISABLED")
    )
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
