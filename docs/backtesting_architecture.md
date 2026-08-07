# Backtesting Engine Architecture

## Goal

Build a professional backtesting engine that shares the same trading logic as
Paper Trading and Live Trading.

Only the data source changes.

---

# Architecture

```
HistoricalDataService
        │
        ▼
HistoricalFeed
        │
        ▼
Timeline
        │
        ▼
IndicatorEngine
        │
        ▼
SignalEngine
        │
        ▼
RiskManager
        │
        ▼
BacktestBroker
        │
        ▼
Portfolio
        │
        ▼
StatisticsService
```

---

# Responsibilities

## HistoricalDataService

Loads historical candles.

Does not know anything about trading.

---

## HistoricalFeed

Replays historical market data.

Provides synchronized market snapshots.

Does not calculate indicators.

---

## Timeline

Synchronizes multiple timeframes using timestamps.

Provides the latest completed candle for every timeframe.

Does not know trading logic.

---

## IndicatorEngine

Calculates technical indicators.

No trading decisions.

---

## SignalEngine

Produces BUY / HOLD signals.

No execution.

---

## RiskManager

Creates Trade Plans.

Calculates:

- Position Size
- Stop Loss
- Take Profit

---

## BacktestBroker

Simulates exchange execution.

Responsible for:

- Opening positions
- Closing positions
- Stop Loss
- Take Profit
- Fees
- Slippage

---

## Portfolio

Stores portfolio state.

No business logic.

---

## StatisticsService

Produces:

- Win Rate
- Profit Factor
- Net Profit
- Drawdown
- Equity Curve

---

# Design Principles

- Single Responsibility Principle
- Dependency Injection
- Same Strategy for Live / Paper / Backtest
- Timestamp synchronization
- Modular architecture
- Unit tested

---

# Development Roadmap

## Phase 1

HistoricalFeed

Timeline

Replay

---

## Phase 2

BacktestBroker

Execution

---

## Phase 3

BacktestEngine

---

## Phase 4

Reports

Metrics

Analytics

---

# Rule

Strategy code must never know whether it runs on:

- Live
- Paper
- Backtesting

Only the DataFeed changes.