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
