# Algorithmic Trading Platform Roadmap

This project will be developed in two sequential tracks. Kraken spot trading
comes first. Interactive Brokers stock trading begins only after the Kraken
execution and recovery lifecycle is stable.

## Roadmap documents

- [Hosting architecture](HOSTING_ARCHITECTURE.md)
- [Kraken crypto trading roadmap](CRYPTO_TRADING_ROADMAP.md)
- [Interactive Brokers stock trading roadmap](STOCK_TRADING_ROADMAP.md)
- [Backtesting architecture](backtesting_architecture.md)

## Current status

- Strategy, risk management, backtesting and paper execution exist.
- Public market-data consumers now use Kraken.
- The authenticated Kraken read-only preflight exists.
- Kraken live order routing is intentionally disconnected.
- IBKR integration has not started.

## Required sequence

1. Rename and privatize the source repository.
2. Configure a dedicated Kraken API key with no funding permissions.
3. Pass the Kraken read-only preflight.
4. Revalidate the strategy using Kraken EUR markets and costs.
5. Implement and test Kraken protective orders and reconciliation.
6. Complete at least 30 days of forward paper observation.
7. Run a EUR 5–10 Kraken live canary with at most EUR 100 allocated.
8. Deploy limited Kraken production on the dedicated crypto server.
9. Extract the multi-asset interfaces.
10. Implement the IBKR adapter and complete at least 60 trading days in paper.
11. Run a one-share IBKR live canary.

No deployment phase is approved solely because a backtest produces a target
monthly return. Each phase requires both performance evidence and operational
safety evidence.
