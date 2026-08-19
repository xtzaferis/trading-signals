from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import ClassVar
from zoneinfo import ZoneInfo

import pandas as pd

from app.advisory.directional_signal import DirectionalSignalEngine
from app.advisory.planner import FuturesAdvisoryPlanner
from app.config.settings import (
    ADVISORY_END_HOUR,
    ADVISORY_FUTURES_FEE,
    ADVISORY_FUTURES_SLIPPAGE,
    ADVISORY_START_HOUR,
    ADVISORY_TIMEZONE,
    MAX_POSITION_HOLD_HOURS,
)
from app.indicators.candle_dataframe_builder import CandleDataFrameBuilder
from app.indicators.indicator_calculator import IndicatorCalculator


@dataclass(frozen=True)
class AdvisoryReplayTrade:
    opened_at: datetime
    closed_at: datetime
    symbol: str
    direction: str
    score: int
    entry: float
    exit_price: float
    outcome: str
    net_return_pct: float


@dataclass(frozen=True)
class AdvisoryReplayResult:
    trades: tuple[AdvisoryReplayTrade, ...]

    @property
    def wins(self) -> int:
        return sum(trade.net_return_pct > 0 for trade in self.trades)

    @property
    def losses(self) -> int:
        return sum(trade.net_return_pct < 0 for trade in self.trades)

    @property
    def win_rate(self) -> float:
        return self.wins / len(self.trades) * 100 if self.trades else 0.0

    @property
    def average_return_pct(self) -> float:
        if not self.trades:
            return 0.0
        return sum(trade.net_return_pct for trade in self.trades) / len(self.trades)

    @property
    def compounded_return_pct(self) -> float:
        equity = 1.0
        for trade in self.trades:
            equity *= 1 + trade.net_return_pct / 100
        return (equity - 1) * 100


class AdvisoryReplayEngine:
    TIMEFRAME_MINUTES: ClassVar[dict[str, int]] = {
        "1d": 1440,
        "4h": 240,
        "1h": 60,
        "15m": 15,
        "5m": 5,
    }

    def __init__(self, signal_engine=None, planner=None):
        self.signal_engine = signal_engine or DirectionalSignalEngine()
        self.planner = planner or FuturesAdvisoryPlanner()
        self.builder = CandleDataFrameBuilder()
        self.calculator = IndicatorCalculator()

    def run(
        self,
        symbol: str,
        candles: dict[str, list],
        start: datetime,
        end: datetime,
        funding_rates: list[tuple[int, float]] | None = None,
    ) -> AdvisoryReplayResult:
        frames = {
            timeframe: self.calculator.calculate(self.builder.build(values))
            for timeframe, values in candles.items()
        }
        trades = []
        traded_dates = set()
        blocked_until = None
        for decision_at in self._decision_times(start, end):
            if decision_at.date() in traded_dates:
                continue
            if blocked_until is not None and decision_at < blocked_until:
                continue
            data = {
                "regime": self._row_at(frames["1d"], "1d", decision_at),
                "trend": self._row_at(frames["4h"], "4h", decision_at),
                "confirm": self._row_at(frames["1h"], "1h", decision_at),
                "entry": self._row_at(frames["15m"], "15m", decision_at),
                "trigger": self._row_at(frames["5m"], "5m", decision_at),
            }
            if any(row is None for row in data.values()):
                continue
            signal = self.signal_engine.evaluate(symbol, data)
            if signal.direction not in {"LONG", "SHORT"}:
                continue
            plan = self.planner.create(signal.direction, data["entry"])
            if plan is None:
                continue
            trade = self._resolve_trade(
                symbol,
                decision_at,
                signal.direction,
                signal.score,
                plan,
                frames["5m"],
                funding_rates or [],
            )
            if trade is not None:
                trades.append(trade)
                traded_dates.add(decision_at.date())
                blocked_until = trade.closed_at.astimezone(ZoneInfo(ADVISORY_TIMEZONE))
        return AdvisoryReplayResult(tuple(trades))

    def _decision_times(self, start: datetime, end: datetime):
        local_timezone = ZoneInfo(ADVISORY_TIMEZONE)
        local_start = start.astimezone(local_timezone)
        local_end = end.astimezone(local_timezone)
        session_start = local_start.replace(
            hour=ADVISORY_START_HOUR, minute=0, second=0, microsecond=0
        )
        while session_start <= local_end:
            session_end = session_start.replace(hour=ADVISORY_END_HOUR)
            current = max(session_start, local_start)
            minute_remainder = current.minute % 15
            if minute_remainder or current.second or current.microsecond:
                current = current.replace(second=0, microsecond=0) + timedelta(
                    minutes=15 - minute_remainder
                )
            while current < session_end and current <= local_end:
                yield current
                current += timedelta(minutes=15)
            session_start += timedelta(days=1)

    def _row_at(self, frame: pd.DataFrame, timeframe: str, decision_at: datetime):
        completed_before = decision_at.astimezone(timezone.utc).replace(
            tzinfo=None
        ) - timedelta(minutes=self.TIMEFRAME_MINUTES[timeframe])
        eligible = frame[frame["timestamp"] <= completed_before]
        if eligible.empty:
            return None
        row = eligible.iloc[-1]
        return row if row.get("ema200", 0) > 0 else None

    def _resolve_trade(
        self,
        symbol,
        opened_at,
        direction,
        score,
        plan,
        frame,
        funding_rates,
    ):
        naive_open = opened_at.astimezone(timezone.utc).replace(tzinfo=None)
        expires = opened_at + timedelta(hours=MAX_POSITION_HOLD_HOURS)
        eligible = frame[
            (frame["timestamp"] >= naive_open)
            & (
                frame["timestamp"]
                <= expires.astimezone(timezone.utc).replace(tzinfo=None)
            )
        ]
        if eligible.empty:
            return None
        outcome, exit_price, closed_at = (
            "TIMEOUT",
            float(eligible.iloc[-1]["close"]),
            expires,
        )
        for _, candle in eligible.iterrows():
            if direction == "LONG":
                stop_hit = candle["low"] <= plan.stop_loss
                target_hit = candle["high"] >= plan.take_profit
            else:
                stop_hit = candle["high"] >= plan.stop_loss
                target_hit = candle["low"] <= plan.take_profit
            if stop_hit:
                outcome, exit_price = "STOP", plan.stop_loss
            elif target_hit:
                outcome, exit_price = "TARGET", plan.take_profit
            else:
                continue
            closed_at = candle["timestamp"].tz_localize(ZoneInfo("UTC"))
            break
        funding = sum(
            rate
            for timestamp, rate in funding_rates
            if opened_at.timestamp() * 1000 <= timestamp <= closed_at.timestamp() * 1000
        )
        net_return = self._net_return(direction, plan.entry, exit_price, funding)
        return AdvisoryReplayTrade(
            opened_at,
            closed_at,
            symbol,
            direction,
            score,
            plan.entry,
            exit_price,
            outcome,
            round(net_return * 100, 6),
        )

    @staticmethod
    def _net_return(direction, entry_reference, exit_reference, funding):
        if direction == "LONG":
            entry = entry_reference * (1 + ADVISORY_FUTURES_SLIPPAGE)
            exit_price = exit_reference * (1 - ADVISORY_FUTURES_SLIPPAGE)
            gross = (exit_price - entry) / entry
            funding_cost = funding
        else:
            entry = entry_reference * (1 - ADVISORY_FUTURES_SLIPPAGE)
            exit_price = exit_reference * (1 + ADVISORY_FUTURES_SLIPPAGE)
            gross = (entry - exit_price) / entry
            funding_cost = -funding
        fees = ADVISORY_FUTURES_FEE * (1 + exit_price / entry)
        return gross - fees - funding_cost
