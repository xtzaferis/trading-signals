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

The advisory command uses Kraken Futures' unauthenticated public APIs and
ranks up to fifteen liquid USD perpetuals, including a broader group of more
volatile altcoins. Futures quote volume, spread, and contract age select the
tradeable universe; all indicators and planned levels use completed Kraken
trade candles and the current mark price.
Daily and 4-hour candles provide market
context, while aligned 1-hour, 15-minute and 5-minute candles trigger a
`LONG`, `SHORT`, or `WAIT` result. It also displays a derivatives-pressure
proxy built from funding, account long/short ratio, and 5-minute, 15-minute,
and 1-hour open-interest and taker-flow windows. It never creates, sizes, or
submits a futures
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

The `advisory-pages.yml` workflow requests a scan every five minutes from
17:02 through 18:57 in the `Europe/Athens` timezone. The redundant cadence
reduces the effect of delayed or dropped GitHub schedule events. Under
**Settings → Pages**,
set the source to **GitHub Actions**, then manually rerun the workflow once.
No deployment token or API key is required. The dashboard URL is:

```text
https://xtzaferis.github.io/trading-signals/
```

The workflow restores the previously published observation history, resolves
older entries, performs the current scan, and republishes both the dashboard
and public signal history. It never uploads `.env`, `data/trading.db`, or API
credentials. Manual workflow runs outside the configured session preserve the
last genuine signal publication. An open hosted dashboard checks for a newer
published snapshot once per minute; it does not itself trigger scans.

GitHub's native `schedule` trigger is best effort and can delay or drop runs.
For dependable five-minute dispatches, deploy the optional Cloudflare Cron
Worker in `deploy/cloudflare-advisory-scheduler`. It calls only the existing
read-only `workflow_dispatch` endpoint during 17:00–19:00 Europe/Athens and
keeps its restricted GitHub token in Cloudflare Secrets. The native GitHub
schedule remains enabled as a fallback. See the deployment directory README
for the one-time setup.

A `LONG` or `SHORT` row has passed its short-term directional gates and a conservative
fee-aware net reward/risk check. A `WAIT` row is informational and is not an
instruction to force a trade. Confirm the futures contract, spread, leverage
and order details manually. The pressure
reading is not a true liquidation heatmap and must be treated only as supporting
context; exact liquidation clusters generally require continuously collected
liquidation events or a specialist data provider.

Actionable signals require the 5-minute direction to persist across two closed
candles. A current order-book snapshot vetoes unusually wide spreads, shallow
depth, or strong opposing imbalance. The mark price must also remain within
half an ATR of the completed 15-minute setup candle. Published signals expire
after ten minutes and the dashboard automatically removes expired cards; run a
fresh scan instead of entering from an old snapshot.

Each row is classified `LOW`, `MEDIUM`, or `HIGH` risk from its 15-minute ATR
percentage. At most two qualifying entries are repeated under `TOP ACTIONABLE
SETUPS`; the section can legitimately be empty when no setup passes every gate.
The second setup is skipped when its last 96 hourly returns imply at least 0.80
effective correlation with the first setup in the proposed trade directions.

Every scan is journaled locally in `data/trading-advisory-kraken.db`. On later
scans, completed
five-minute futures candles resolve open observations as `TARGET`, `STOP`, or
`TIMEOUT`; same-candle stop/target ambiguity is conservatively counted as a
stop. View forward results with:

```powershell
.\.venv\Scripts\python.exe -m app.advisory.performance
```

The performance report calibrates the nominal signal score against resolved
forward outcomes by direction, score band, and 4-hour market regime. Results
remain explicitly preliminary until a group contains at least 30 resolved
shortlisted setups; the displayed 95% interval communicates small-sample
uncertainty.
It also records realized funding, maximum favorable and adverse excursion,
time to exit, and available 15-minute, 1-hour, 4-hour, and 24-hour directional
returns.

Run a candle replay for an individual Kraken USD perpetual with:

```powershell
.\.venv\Scripts\python.exe -m app.advisory.backtest_main --symbol BTC/USD --days 90 --validation-windows 3
```

The replay uses the same candle signal and level planner, includes fees,
slippage and historical funding, and never sends orders. It reports separate
chronological windows with frozen rules so that one favorable period cannot
hide instability in another. Within each day it evaluates every completed
15-minute decision point from 17:00 through 18:45, permits at most one entry per
symbol, and prevents overlapping positions. Historical
long/short-account and taker-flow snapshots are not available for the entire
replay range, so the replay deliberately excludes the live positioning score
adjustment.

Optional `.env` settings:

```dotenv
ADVISORY_TOP_COINS=15
ADVISORY_MAX_SIGNALS=2
ADVISORY_MAX_CORRELATION=0.80
ADVISORY_DATA_SOURCE=kraken
ADVISORY_QUOTE_CURRENCY=USD
ADVISORY_TIMEZONE=Europe/Athens
ADVISORY_START_HOUR=17
ADVISORY_END_HOUR=19
ADVISORY_FUTURES_FEE=0.0005
ADVISORY_FUTURES_SLIPPAGE=0.0005
ADVISORY_MIN_FUTURES_QUOTE_VOLUME=1000000
ADVISORY_MAX_FUTURES_SPREAD_BPS=10
ADVISORY_MIN_CONTRACT_AGE_DAYS=30
ADVISORY_SIGNAL_TTL_MINUTES=10
ADVISORY_MAX_ENTRY_DEVIATION_ATR=0.50
ADVISORY_ORDER_BOOK_LEVELS=20
ADVISORY_MIN_BOOK_DEPTH_USDT=100000
ADVISORY_MAX_BOOK_SPREAD_BPS=8
ADVISORY_MAX_OPPOSING_BOOK_IMBALANCE=0.35
```
