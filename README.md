# Spot Trading Bot

Algorithmic spot trading bot with paper trading and a fail-closed Kraken Pro
Spot integration path.

## Features

- Kraken Pro Spot read-only preflight
- Market Scanner
- Technical Indicators
- Signal Engine (in progress)
- Paper Trading (planned)
- Risk Management (planned)

## Tech Stack

- Python
- CCXT
- Pandas
- TA
- FastAPI

## Kraken Pro setup

Kraken live execution is disabled by default. Create a dedicated Spot API key
for the bot with these permissions:

- Query Funds
- Query Open Orders & Trades
- Query Closed Orders & Trades
- Create & Modify Orders
- Cancel & Close Orders

Do not enable deposit, withdrawal, withdrawal-address, Earn or other funding
permissions.

Set these values in `.env` without committing the file:

```dotenv
TRADING_MODE=live
LIVE_TRADING_ENABLED=false
QUOTE_CURRENCY=EUR
KRAKEN_API_KEY=YOUR_KRAKEN_API_KEY
KRAKEN_API_SECRET=YOUR_KRAKEN_PRIVATE_SIGNING_SECRET
KRAKEN_EXPECTED_KEY_NAME=trading-bot
```

Run the authenticated, read-only check:

```powershell
.\.venv\Scripts\python.exe -m app.live.preflight
```

The preflight verifies every required query and trading permission, rejects
funding permissions, checks the dedicated key name and Spot market, reports
the IP allowlist, EUR balance and open-order count, and never previews or
submits an order.

The Kraken live broker remains deliberately unconnected until the read-only
preflight passes and the protective-order lifecycle is fully covered by tests.
Do not set `LIVE_TRADING_ENABLED=true` yet.

## Read-only futures entry advisory

The advisory command uses Binance's unauthenticated public APIs and ranks up
to twenty liquid USDT coins, including a broader group of more volatile
altcoins. Spot volume selects the liquid universe; all indicators and planned
levels use completed Binance USD-M futures candles and the current mark price.
Daily and 4-hour candles provide market
context, while aligned 1-hour, 15-minute and 5-minute candles trigger a
`LONG`, `SHORT`, or `WAIT` result. It also displays a derivatives-pressure
proxy built from funding, 5-minute open-interest change, account long/short
ratio and taker buy/sell flow. It never creates, sizes, or submits a futures
order. By default it only scans from 17:00
inclusive until 19:00 exclusive in the `Europe/Athens` timezone:

```powershell
.\.venv\Scripts\python.exe -m app.advisory.main
```

For maintenance or testing outside that window, use `--force`. This bypasses
only the clock restriction and does not enable exchange execution:

```powershell
.\.venv\Scripts\python.exe -m app.advisory.main --force
```

Outside-session forced scans are diagnostic only and are not written to the
forward-performance journal.

For the local graphical dashboard, start the read-only web server:

```powershell
.\.venv\Scripts\python.exe -m app.advisory.dashboard
```

Then open `http://127.0.0.1:8000`. Press **Get signals** to run the scan. The
server binds only to the local computer by default and contains no order route.

### Free GitHub Pages publication

The `advisory-pages.yml` GitHub Actions workflow runs at 17:00 in the
`Europe/Athens` timezone and deploys a static, read-only copy of the dashboard.
In the GitHub repository, open **Settings → Pages** and select **GitHub Actions**
as the deployment source. The public dashboard URL is normally:

```text
https://<github-user>.github.io/<repository>/
```

The workflow restores the previously published observation history, resolves
older entries, performs the current scan, and republishes both the dashboard
and public signal history. It never uploads `.env`, `data/trading.db`, or API
credentials. Manual workflow runs outside the configured session preserve the
last genuine signal publication.

A `LONG` or `SHORT` row has passed its short-term directional gates and a conservative
fee-aware net reward/risk check. A `WAIT` row is informational and is not an
instruction to force a trade. Confirm the futures contract, spread, leverage
and order details manually. The pressure
reading is not a true liquidation heatmap and must be treated only as supporting
context; exact liquidation clusters generally require continuously collected
liquidation events or a specialist data provider.

Each row is classified `LOW`, `MEDIUM`, or `HIGH` risk from its 15-minute ATR
percentage. At most two qualifying entries are repeated under `TOP ACTIONABLE
SETUPS`; the section can legitimately be empty when no setup passes every gate.
The second setup is skipped when its last 96 hourly returns imply at least 0.80
effective correlation with the first setup in the proposed trade directions.

Every scan is journaled locally in `data/trading.db`. On later scans, completed
five-minute futures candles resolve open observations as `TARGET`, `STOP`, or
`TIMEOUT`; same-candle stop/target ambiguity is conservatively counted as a
stop. View forward results with:

```powershell
.\.venv\Scripts\python.exe -m app.advisory.performance
```

Run a candle replay for an individual USD-M futures symbol with:

```powershell
.\.venv\Scripts\python.exe -m app.advisory.backtest_main --symbol BTC/USDT --days 30
```

The replay uses the same candle signal and level planner, includes fees,
slippage and historical funding, and never sends orders. Historical
long/short-account and taker-flow snapshots are not available for the entire
replay range, so the replay deliberately excludes the live positioning score
adjustment.

Optional `.env` settings:

```dotenv
ADVISORY_TOP_COINS=20
ADVISORY_MAX_SIGNALS=2
ADVISORY_MAX_CORRELATION=0.80
ADVISORY_DATA_SOURCE=binance
ADVISORY_QUOTE_CURRENCY=USDT
ADVISORY_TIMEZONE=Europe/Athens
ADVISORY_START_HOUR=17
ADVISORY_END_HOUR=19
ADVISORY_FUTURES_FEE=0.0005
ADVISORY_FUTURES_SLIPPAGE=0.0005
```
