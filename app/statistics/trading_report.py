from app.statistics.statistics_service import (
    StatisticsService,
)
from app.statistics.statistics_printer import (
    StatisticsPrinter,
)


class TradingReport:

    def __init__(self):

        self.service = (
            StatisticsService()
        )

        self.printer = (
            StatisticsPrinter()
        )

    def generate(self):

        stats = (
            self.service.calculate()
        )

        self.printer.print(
            stats
        )

        return stats