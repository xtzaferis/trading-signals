# Kraken Pro Crypto Trading Roadmap

## Objective

Build a fail-closed Kraken Pro Spot trading service using EUR markets and a
dedicated API key. Profitability is a validation outcome, not a guaranteed
monthly return. No phase may be skipped because a backtest looks attractive.

## Phase 1 — Account and read-only validation

- Create a dedicated Kraken Spot API key for the bot.
- Enable Query Funds, Query Open Orders & Trades, Query Closed Orders & Trades,
  Create & Modify Orders, and Cancel & Close Orders.
- Disable deposits, withdrawals, withdrawal-address management, Earn and other
  funding permissions.
- Configure an IP allowlist after the production server receives a static IP.
- Keep `LIVE_TRADING_ENABLED=false`.
- Configure `KRAKEN_API_KEY`, `KRAKEN_API_SECRET` and
  `KRAKEN_EXPECTED_KEY_NAME` outside Git.
- Run `python -m app.live.preflight`.
- Confirm the expected key name, permissions, EUR balance, market availability
  and open orders.

Exit gate: authenticated preflight passes repeatedly and sends no order.

## Phase 2 — Market and strategy validation

- Confirm every selected EUR Spot market exists and is sufficiently liquid.
- Download fresh Kraken EUR candle history.
- Model Kraken's actual maker/taker fee tier, spread and conservative
  slippage. Backtests assume taker entry and exit costs until maker fill
  probability is modeled; this is intentionally pessimistic.
- Reject trades whose expected net reward/risk is below 1.5 after fees and
  slippage. Gross TP/SL ratios are not sufficient.
- Run chronological out-of-sample and walk-forward tests.
- Report trade count, expectancy, profit factor, drawdown and monthly returns.
- Reject parameters that work only on one asset or one short period.
- Compare the strategy with holding cash and BTC.

Exit gate: positive out-of-sample expectancy, acceptable drawdown and a
statistically useful number of trades. A 5% monthly return is not an exit gate.

## Phase 3 — Execution and protection engine

Implement and test:

- Kraken order validation using `validate=true`.
- Post-only limit entries so a signal cannot silently pay the taker fee.
- Cancel unfilled entry orders after 15 minutes; flag partial fills for manual
  reconciliation rather than inventing a full position.
- Unique, persistent `cl_ord_id` values.
- Idempotent retry behavior.
- Exact fills, partial fills and commissions.
- Stop-loss and take-profit order coordination.
- Immediate protective-order verification after every entry.
- Atomic sibling cancellation when one protective exit triggers.
- Detection and repair of missing, canceled or partially filled protection.
- Order, balance and position reconciliation after restart.
- Emergency market exit if protection cannot be established.
- Daily-loss, drawdown, order-count and consecutive-loss circuit breakers.
- A dedicated Kraken live database and capital allocation.

Kraken supports conditional secondary close orders and client order IDs, but
the exact Spot TP/SL coordination must be verified against the live API before
the first canary. The bot must not assume that two independent exit orders are
automatically OCO.

Exit gate: every tested failure leaves the position protected, safely closed,
or blocks all additional entries.

## Current validation gates

The automated chronological out-of-sample gate requires all of the following:

- at least 30 closed out-of-sample trades;
- profit factor of at least 1.20;
- positive expectancy after all modeled trading costs;
- maximum drawdown no greater than 10%.

A result that fails any gate is research output, not authorization for live
trading. Parameter selection must be performed only on the development period;
the later out-of-sample period remains untouched until final evaluation.

## Phase 4 — Forward paper observation

- Deploy the service with live Kraken market data and paper execution.
- Run continuously for at least 30 days.
- Record every signal, rejection, stale candle, API failure and restart.
- Reconcile state automatically after process and server restarts.
- Produce weekly performance and health reports.
- Require no unresolved orders or positions.

Kraken does not provide a full Spot execution simulator for this workflow, so
local paper execution and order-validation requests do not prove live fill
behavior.

Exit gate: at least 30 observed days, sufficient closed trades, acceptable
performance and no unresolved operational failures.

## Phase 5 — Live canary

- Allocate no more than EUR 100.
- Submit one EUR 5–10 order.
- Permit one open position only.
- Verify the entry fill and every protective order directly in Kraken Pro.
- Stop after the first completed trade and reconcile balances, fills and fees.
- Review each of the first 20–30 trades before increasing automation.

Exit gate: confirmed entry, protection and exit lifecycle with exact accounting
and no manual repair required.

## Phase 6 — Limited production

- Deploy on the Frankfurt crypto server described in
  [HOSTING_ARCHITECTURE.md](HOSTING_ARCHITECTURE.md).
- Restrict the API key to the server's static IP.
- Add external monitoring and alerts.
- Maintain a hard server-side allocation ceiling.
- Review performance and execution quality weekly.
- Increase capital only after several stable, profitable months.
- Keep a documented emergency-stop and recovery procedure.

## Sources

- [Kraken Spot API documentation](https://docs.kraken.com/)
- [Kraken API-key permissions and IP allowlist](https://docs.kraken.com/api/docs/rest-api/get-api-key-info)
- [Kraken client order identifiers](https://docs.kraken.com/api/blog/cl-ord-id/)
- [Kraken EEA MiCA availability](https://blog.kraken.com/news/all-30-eea-countries-mica)
