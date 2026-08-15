# Project status — Kraken Pro spot trading bot

## Current capabilities

- Multi-timeframe strategy and historical backtesting
- Persistent paper-trading state and health reporting
- Risk sizing, stop-loss, take-profit, drawdown and execution circuit breakers
- Kraken Pro public market data through CCXT
- Kraken authenticated read-only preflight
- Dedicated Kraken API-key name guard
- API safety policy requiring order-query/trading permissions while rejecting
  all funding and withdrawal permissions

## Safety status

Kraken live order routing is intentionally disconnected. The next production
phase is to implement and test the complete protective-order lifecycle,
including entry-fill reconciliation, stop-loss and take-profit coordination,
partial fills, restarts and emergency flattening. Until then,
`LIVE_TRADING_ENABLED` must remain `false`.
