from unittest.mock import Mock, patch

from app.paper.main import main


def test_paper_main_starts_runner():

    with patch(
        "app.paper.main.PaperRunner"
    ) as runner:

        instance = Mock()

        runner.return_value = instance

        main()

        instance.run.assert_called_once()