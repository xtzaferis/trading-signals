# Interactive Brokers Stock Trading Roadmap

## Objective

Add stock and ETF trading through Interactive Brokers after Coinbase execution
is operationally stable. The first target should be a small universe of liquid
ETFs, not speculative individual stocks.

## Phase 1 — Multi-asset architecture

Extract and formalize exchange-independent interfaces:

- `MarketDataProvider`
- `Broker`
- `OrderGateway`
- `Instrument`
- `TradingCalendar`
- `CommissionModel`
- `PositionRepository`

Coinbase and IBKR must have separate adapters, processes, databases, logs,
capital allocations and safety switches. Shared strategy code must not be able
to confuse a crypto symbol with a stock contract.

Exit gate: paper and backtesting tests pass through the common interfaces
without importing either execution adapter.

## Phase 2 — Stock backtesting

Add stock-specific behavior:

- Exchange trading sessions, holidays and shortened sessions.
- Opening and overnight gaps.
- Split- and dividend-adjusted historical prices.
- Survivorship-bias controls.
- Stock commissions, exchange fees and minimum tick sizes.
- Limit-order and partial-fill modeling.
- Currency conversion for non-EUR instruments.
- Maximum sector, symbol and overnight exposure.

Start with one or two liquid ETFs and a daily or hourly strategy. Avoid
high-frequency assumptions that cannot be reproduced through the broker API.

Exit gate: chronological out-of-sample results remain positive after realistic
costs and gap risk.

## Phase 3 — IBKR paper adapter

Use the official TWS API through IB Gateway and implement:

- Stock and ETF contract qualification.
- Market-data subscriptions and delayed-data detection.
- Account and paper/live identity checks.
- Parent/child bracket orders.
- Correct `transmit` sequencing for atomic bracket submission.
- Order IDs, executions, commissions and partial fills.
- Cancel/replace behavior.
- Connection-loss and daily-restart recovery.
- Persistent reconciliation of orders, positions and cash.
- Trading-session and holiday entry restrictions.

IB Gateway paper sessions normally use port `4002`; the value must remain
configurable and live ports must be rejected while paper mode is selected.

Exit gate: the adapter cannot transmit to a live account and can recover every
paper position after a restart.

## Phase 4 — Paper operation

- Run against the IBKR paper account for at least 60 trading days.
- Test normal openings and closings, holidays and shortened sessions.
- Exercise partial fills, canceled orders and rejected contracts.
- Test daily IB Gateway restarts and weekly manual reauthentication.
- Verify bracket orders after every reconnect.
- Compare paper fills with observed market prices and spreads.
- Produce weekly operational and performance reports.

IBKR warns that paper execution behavior may differ from live execution. Paper
results validate integration and risk controls, not guaranteed profitability.

Exit gate: 60 observed trading days, no unresolved orders or positions, and
acceptable out-of-sample performance.

## Phase 5 — Stock live canary

- Use a dedicated IBKR username and capital allocation.
- Trade one liquid ETF.
- Start with one share.
- Require a native bracket order for every entry.
- Avoid overnight holding initially.
- Review every fill and commission manually.
- Increase scope only after sufficient live evidence.

Exit gate: stable live reconciliation and protection across a meaningful sample
of minimal-size trades.

## Operational limitations

- TWS or IB Gateway must be running before the API client can connect.
- IBKR requires two-factor authentication.
- Completely headless GUI-less operation is not officially supported.
- Daily auto-restart can work during the week, but manual authentication is
  normally required after the weekend reset.
- A username can have only one active brokerage session.
- Market-data subscriptions may be username-specific and have separate fees.

These constraints are why IBKR will use the separate stock runtime described in
[HOSTING_ARCHITECTURE.md](HOSTING_ARCHITECTURE.md).

## Sources

- [IBKR TWS API documentation](https://ibkrcampus.com/campus/ibkr-api-page/twsapi-doc/)
- [Installing and configuring TWS for the API](https://ibkrcampus.com/campus/trading-lessons/installing-configuring-tws-for-the-api/)
- [IBKR connection parameters and paper ports](https://ibkrcampus.com/docs/excel/rtd/connection-parameters)
- [IBKR paper account API guidance](https://ibkrcampus.com/campus/ibkr-api-page/third-party-connections/)
