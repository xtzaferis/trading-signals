# Project status — Coinbase spot trading bot

## Current capabilities

- Multi-timeframe strategy and historical backtesting
- Persistent paper-trading state and health reporting
- Risk sizing, stop-loss, take-profit, drawdown and execution circuit breakers
- Coinbase Advanced public market data through CCXT
- Coinbase authenticated read-only preflight
- Dedicated Coinbase portfolio identity check
- API safety policy requiring View and Trade while rejecting Transfer

## Safety status

Coinbase live order routing is intentionally disconnected. The next production
phase is to implement and test the complete attached bracket-order lifecycle,
including entry-fill reconciliation, exchange-native TP/SL verification,
partial fills, restarts, and emergency flattening. Until then,
`LIVE_TRADING_ENABLED` must remain `false`.
