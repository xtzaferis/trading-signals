import sys

from app.config.settings import (
    TRADING_MODE,
)
from app.core.logger import logger
from app.paper.paper_runner import (
    PaperRunner,
)


def main():

    if TRADING_MODE not in {"paper", "okx_demo"}:

        logger.error(
            "This runner supports only paper and okx_demo modes."
        )

        sys.exit(1)

    logger.info("")
    logger.info("=" * 50)
    logger.info(
        f"TRADING STARTED | mode={TRADING_MODE}"
    )
    logger.info("=" * 50)

    runner = PaperRunner(trading_mode=TRADING_MODE)

    try:

        runner.run()

    except KeyboardInterrupt:

        logger.info("")
        logger.info(
            "Paper trading stopped."
        )


if __name__ == "__main__":

    main()
