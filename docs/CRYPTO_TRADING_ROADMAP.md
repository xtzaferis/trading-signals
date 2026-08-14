# Coinbase Crypto Trading Roadmap

## Objective

Build a fail-closed Coinbase Advanced spot-trading service using a dedicated
EUR portfolio. Profitability is a validation outcome, not a guaranteed monthly
return. No phase may be skipped because a backtest looks attractive.

## Phase 1 — Account and read-only validation

- Create a dedicated Coinbase Advanced portfolio for the bot.
- Create a CDP key scoped only to that portfolio.
- Enable View and Trade.
- Disable Transfer and Receive.
- Keep `LIVE_TRADING_ENABLED=false`.
- Configure `COINBASE_API_KEY`, `COINBASE_API_SECRET` and
  `COINBASE_EXPECTED_PORTFOLIO_ID` outside Git.
- Run `python -m app.live.preflight`.
- Confirm the expected portfolio, EUR balance, market availability and open
  orders.

Exit gate: authenticated preflight passes repeatedly and sends no order.

## Phase 2 — Market and strategy validation

- Confirm every selected EUR spot market exists and is sufficiently liquid.
- Download fresh Coinbase EUR candle history.
- Model Coinbase fees, spread and conservative slippage.
- Run chronological out-of-sample and walk-forward tests.
- Report trade count, expectancy, profit factor, drawdown and monthly returns.
- Reject parameters that work only on one asset or one short period.
- Establish a benchmark and compare the strategy with holding cash and BTC.

Exit gate: positive out-of-sample expectancy, acceptable drawdown and a
statistically useful number of trades. A 5% monthly return is not an exit gate.

## Phase 3 — Execution engine

Implement and test:

- Coinbase order previews.
- Quote-sized spot market entries.
- Unique, persistent client order IDs.
- Idempotent retry behavior.
- Exact fills, partial fills and commissions.
- Attached exchange-native TP/SL orders.
- Bracket-order verification immediately after entry.
- Order, balance and position reconciliation after restart.
- Emergency market exit if native protection cannot be established.
- Daily-loss, drawdown, order-count and consecutive-loss circuit breakers.
- A dedicated Coinbase live database and capital allocation.

Coinbase attached TP/SL uses a `trigger_bracket_gtc` configuration. When one
exit fills, the other side is disabled. Stop execution can still suffer
slippage during volatile markets.

Exit gate: every tested failure leaves the position protected, safely closed,
or blocks all additional entries.

## Phase 4 — Forward paper observation

- Deploy the service with live Coinbase market data and paper execution.
- Run continuously for at least 30 days.
- Record every signal, rejection, stale candle, API failure and restart.
- Reconcile state automatically after process and server restarts.
- Produce weekly performance and health reports.
- Require no unresolved orders or positions.

Coinbase's API sandbox returns static mocked responses. It is useful for
response-shape tests but does not validate realistic fills or a complete
production lifecycle.

Exit gate: at least 30 observed days, sufficient closed trades, acceptable
performance and no unresolved operational failures.

## Phase 5 — Live canary

- Allocate no more than EUR 100.
- Submit one EUR 5–10 order.
- Permit one open position only.
- Verify the entry fill and native bracket directly in Coinbase.
- Stop after the first completed trade and reconcile balances, fills and fees.
- Review each of the first 20–30 trades before increasing automation.

Exit gate: confirmed entry, protection and exit lifecycle with exact accounting
and no manual repair required.

## Phase 6 — Limited production

- Deploy on the Frankfurt crypto server described in
  [HOSTING_ARCHITECTURE.md](HOSTING_ARCHITECTURE.md).
- Add external monitoring and alerts.
- Maintain a hard server-side allocation ceiling.
- Review performance and execution quality weekly.
- Increase capital only after several stable, profitable months.
- Keep a documented emergency-stop and recovery procedure.

## Sources

- [Coinbase Advanced Trade endpoints](https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/rest-api)
- [Coinbase bracket and attached TP/SL orders](https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/guides/orders)
- [Coinbase API authentication](https://docs.cdp.coinbase.com/api-reference/authentication)
