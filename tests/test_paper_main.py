from unittest.mock import Mock, patch

import pytest

from app.paper.main import main


def test_paper_main_starts_runner():

    with patch(
        "app.paper.main.PaperRunner"
    ) as runner:

        instance = Mock()

        runner.return_value = instance

        main()

        instance.run.assert_called_once()


def test_live_mode_is_rejected_by_runner_entry_point():
    with patch(
        "app.paper.main.TRADING_MODE", "live"
    ), pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 1
