from dataclasses import dataclass

from app.backtesting.multi_symbol_backtest_engine import (
    MultiSymbolBacktestEngine,
)
from app.config.settings import TOP_COINS
from app.core.logger import logger
from app.models.statistics_report import StatisticsReport
from app.scanner.market_scanner import MarketScanner


@dataclass
class ChronologicalValidationResult:
    split_timestamp: int
    development: StatisticsReport
    out_of_sample: StatisticsReport
    passed: bool
    failures: list[str]


@dataclass(frozen=True)
class ValidationCriteria:
    min_trades: int = 30
    min_profit_factor: float = 1.20
    min_expectancy: float = 0.0
    max_drawdown_pct: float = 10.0

    def evaluate(self, report: StatisticsReport) -> list[str]:
        failures = []
        if report.trades < self.min_trades:
            failures.append(
                f"trades {report.trades} < required {self.min_trades}"
            )
        if report.profit_factor < self.min_profit_factor:
            failures.append(
                f"profit factor {report.profit_factor:.2f} < required "
                f"{self.min_profit_factor:.2f}"
            )
        if report.expectancy <= self.min_expectancy:
            failures.append(
                f"expectancy {report.expectancy:.4f} <= required "
                f"{self.min_expectancy:.4f}"
            )
        if report.max_drawdown > self.max_drawdown_pct:
            failures.append(
                f"drawdown {report.max_drawdown:.2f}% > allowed "
                f"{self.max_drawdown_pct:.2f}%"
            )
        return failures


class ChronologicalValidator:
    """Compare earlier development history with a later unseen period."""

    ENTRY_TIMEFRAME_MS = 15 * 60 * 1000

    def run(
        self,
        symbols: list[str] | None = None,
        data: dict[str, dict] | None = None,
        development_ratio: float = 0.70,
        criteria: ValidationCriteria | None = None,
    ) -> ChronologicalValidationResult:
        if not 0 < development_ratio < 1:
            raise ValueError("development_ratio must be between 0 and 1")

        if data is None:
            selected = symbols or MarketScanner().get_top_spot_pairs(
                TOP_COINS
            )
            data = MultiSymbolBacktestEngine._load_data(selected)
            symbols = [symbol for symbol in selected if symbol in data]
        else:
            symbols = list(symbols or data.keys())

        split_timestamp = self._split_timestamp(
            data,
            development_ratio,
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info("DEVELOPMENT PERIOD (EARLIEST 70%)")
        logger.info("=" * 60)
        development = MultiSymbolBacktestEngine().run(
            symbols=symbols,
            data=data,
            end_at=split_timestamp,
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info("OUT-OF-SAMPLE PERIOD (LATEST 30%)")
        logger.info("=" * 60)
        out_of_sample = MultiSymbolBacktestEngine().run(
            symbols=symbols,
            data=data,
            start_at=split_timestamp + 1,
        )

        failures = (criteria or ValidationCriteria()).evaluate(out_of_sample)
        logger.info(
            "VALIDATION GATE | %s%s",
            "PASS" if not failures else "FAIL",
            "" if not failures else " | " + "; ".join(failures),
        )
        return ChronologicalValidationResult(
            split_timestamp=split_timestamp,
            development=development,
            out_of_sample=out_of_sample,
            passed=not failures,
            failures=failures,
        )

    @classmethod
    def _split_timestamp(
        cls,
        data: dict[str, dict],
        ratio: float,
    ) -> int:
        starts = []
        ends = []
        for symbol_data in data.values():
            candles = symbol_data.get("15m", [])
            if not candles:
                continue
            starts.append(int(candles[0][0]))
            ends.append(int(candles[-1][0]))

        if not starts or not ends:
            raise ValueError("15m history is required for validation")

        common_start = max(starts) + 200 * cls.ENTRY_TIMEFRAME_MS
        common_end = min(ends) + cls.ENTRY_TIMEFRAME_MS
        if common_start >= common_end:
            raise ValueError("insufficient common history for validation")

        return int(
            common_start
            + (common_end - common_start) * ratio
        )
