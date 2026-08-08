import sys

from app.config.settings import (
    PAPER_TRADING,
)
from app.core.logger import logger
from app.paper.paper_runner import (
    PaperRunner,
)


def main():

    if not PAPER_TRADING:

        logger.error(
            "Paper trading is disabled."
        )

        sys.exit(1)

    logger.info("")
    logger.info("=" * 50)
    logger.info(
        "PAPER TRADING STARTED"
    )
    logger.info("=" * 50)

    runner = PaperRunner()

    try:

        runner.run()

    except KeyboardInterrupt:

        logger.info("")
        logger.info(
            "Paper trading stopped."
        )


if __name__ == "__main__":

    main()