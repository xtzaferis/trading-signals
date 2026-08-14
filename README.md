# Spot Trading Bot

Algorithmic spot trading bot with paper trading and a fail-closed Coinbase
Advanced integration path.

## Features

- Coinbase Advanced Trade read-only preflight
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

## Coinbase Advanced setup

Coinbase live execution is disabled by default. Create a dedicated Coinbase
Advanced portfolio for the bot, then create a CDP API key scoped to that
portfolio with only **View** and **Trade** permissions. Never enable
**Transfer**.

Set these values in `.env` without committing the file:

```dotenv
TRADING_MODE=live
LIVE_TRADING_ENABLED=false
QUOTE_CURRENCY=EUR
COINBASE_API_KEY=organizations/YOUR_ORG_ID/apiKeys/YOUR_KEY_ID
COINBASE_API_SECRET="-----BEGIN EC PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END EC PRIVATE KEY-----\n"
COINBASE_EXPECTED_PORTFOLIO_ID=YOUR_DEDICATED_PORTFOLIO_UUID
```

Run the authenticated, read-only check:

```powershell
.\.venv\Scripts\python.exe -m app.live.preflight
```

The preflight verifies View/Trade permissions, rejects Transfer permission,
checks the configured spot market and portfolio, reports the EUR balance and
open-order count, and never previews or submits an order. Coinbase's public
sandbox returns static mocked responses, so it is not used as evidence that a
real trading workflow works.

The Coinbase live broker remains deliberately unconnected until the read-only
preflight passes and the protective bracket-order lifecycle is fully covered
by tests. Do not set `LIVE_TRADING_ENABLED=true` yet.
