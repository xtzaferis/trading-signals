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
altcoins. Daily and 4-hour candles provide market
context, while aligned 1-hour, 15-minute and 5-minute candles trigger a
`LONG`, `SHORT`, or `WAIT` result. It also displays a derivatives-pressure
proxy built from funding, 5-minute open-interest change, account long/short
ratio and taker buy/sell flow. It never creates, sizes, or submits a futures
order. By default it only scans from 18:00
inclusive until 21:00 exclusive in the `Europe/Athens` timezone:

```powershell
.\.venv\Scripts\python.exe -m app.advisory.main
```

For maintenance or testing outside that window, use `--force`. This bypasses
only the clock restriction and does not enable exchange execution:

```powershell
.\.venv\Scripts\python.exe -m app.advisory.main --force
```

For the local graphical dashboard, start the read-only web server:

```powershell
.\.venv\Scripts\python.exe -m app.advisory.dashboard
```

Then open `http://127.0.0.1:8000`. Press **Get signals** to run the scan. The
server binds only to the local computer by default and contains no order route.

A `LONG` or `SHORT` row has passed its short-term directional gates and a conservative
fee-aware net reward/risk check. A `WAIT` row is informational and is not an
instruction to force a trade. The levels use spot USDT candles as the market
signal; confirm that the corresponding futures contract exists and verify its
mark price, funding, spread, leverage and order details manually. The pressure
reading is not a true liquidation heatmap and must be treated only as supporting
context; exact liquidation clusters generally require continuously collected
liquidation events or a specialist data provider.

Each row is classified `LOW`, `MEDIUM`, or `HIGH` risk from its 15-minute ATR
percentage. At most two qualifying entries are repeated under `TOP ACTIONABLE
SETUPS`; the section can legitimately be empty when no setup passes every gate.

Optional `.env` settings:

```dotenv
ADVISORY_TOP_COINS=20
ADVISORY_MAX_SIGNALS=2
ADVISORY_DATA_SOURCE=binance
ADVISORY_QUOTE_CURRENCY=USDT
ADVISORY_TIMEZONE=Europe/Athens
ADVISORY_START_HOUR=18
ADVISORY_END_HOUR=21
ADVISORY_FUTURES_FEE=0.0005
ADVISORY_FUTURES_SLIPPAGE=0.0005
```
