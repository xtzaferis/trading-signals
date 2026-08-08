from datetime import datetime, timezone

from app.core.logger import logger
from app.storage.decision_repository import (
    DecisionRepository,
)


class DecisionLogger:

    def __init__(self):

        self.repository = (
            DecisionRepository()
        )

    def log(
        self,
        symbol: str,
        price: float,
        score: int,
        action: str,
    ):

        timestamp = datetime.now(
            timezone.utc
        )

        self.repository.save(
            timestamp=timestamp,
            symbol=symbol,
            price=price,
            score=score,
            action=action,
        )

        logger.info(
            ""
        )

        logger.info(
            "TRADING DECISION"
        )

        logger.info(
            f"Time: {timestamp.isoformat()}"
        )

        logger.info(
            f"Symbol: {symbol}"
        )

        logger.info(
            f"Price: {price:.2f}"
        )

        logger.info(
            f"Score: {score}"
        )

        logger.info(
            f"Action: {action}"
        )