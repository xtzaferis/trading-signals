from unittest.mock import Mock, patch

from app.services.decision_logger import (
    DecisionLogger,
)


def test_decision_logger_logs_trade_decision():

    with patch(
        "app.services.decision_logger.DecisionRepository"
    ) as repository:

        instance = Mock()

        repository.return_value = instance

        logger_service = DecisionLogger()

        with patch(
            "app.services.decision_logger.logger"
        ) as logger:

            logger_service.log(
                symbol="BTC/USDC",
                price=100.0,
                score=95,
                action="BUY",
            )

            instance.save.assert_called_once()

            assert (
                logger.info.call_count
                == 7
            )

            logger.info.assert_any_call(
                "TRADING DECISION"
            )

            logger.info.assert_any_call(
                "Symbol: BTC/USDC"
            )

            logger.info.assert_any_call(
                "Price: 100.00"
            )

            logger.info.assert_any_call(
                "Score: 95"
            )

            logger.info.assert_any_call(
                "Action: BUY"
            )


def test_decision_logger_includes_signal_reasons():
    with patch(
        "app.services.decision_logger.DecisionRepository"
    ) as repository, patch(
        "app.services.decision_logger.logger"
    ) as logger:
        logger_service = DecisionLogger()

        logger_service.log(
            symbol="BTC/USDC",
            price=100.0,
            score=0,
            action="HOLD",
            reasons=["Daily regime filter failed"],
        )

        repository.return_value.save.assert_called_once()
        logger.info.assert_any_call(
            "Reason: Daily regime filter failed"
        )
