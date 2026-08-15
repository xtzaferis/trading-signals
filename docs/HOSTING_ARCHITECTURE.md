# Hosting Architecture

## Decision

The source code will live in one private GitHub repository. Runtime services
will be separated by asset class so a crypto failure cannot interfere with a
stock account, and vice versa.

| Component | Location | Purpose |
| --- | --- | --- |
| Source code | Private GitHub repository | Version control and CI tests |
| Crypto runtime | AWS Lightsail, Frankfurt | Continuous Kraken monitoring and execution |
| Crypto database | Encrypted server disk plus backups | Orders, positions, decisions and reconciliation |
| Stock runtime | Separate GUI-capable machine or Windows VPS | IB Gateway and the stock bot |
| Secrets | Runtime machines only | API credentials must never enter Git or CI |

## Source repository

- Rename the repository to a future-proof name such as
  `algorithmic-trading-platform`.
- Keep the repository private.
- Use protected branches and pull requests for production changes.
- Run unit tests, linting and security checks in GitHub Actions.
- Never execute live trading or store API credentials in GitHub Actions.

## Crypto server

The initial recommendation is an Ubuntu AWS Lightsail instance in Frankfurt
with 2 GB RAM and a static public IPv4 address. At the time this decision was
recorded, the corresponding Linux bundle was approximately USD 12 per month.
Confirm pricing before provisioning.

The static address will be added to the Kraken API-key allowlist. Kraken's key
information endpoint reports both permissions and allowed IP addresses.

Required server controls:

- Run one trading process under `systemd` or Docker Compose.
- Permit SSH only from trusted addresses.
- Disable password-based SSH access.
- Enable automatic security updates and time synchronization.
- Store secrets in a root-owned environment file with mode `600` or an
  equivalent managed secret store.
- Keep `LIVE_TRADING_ENABLED=false` until the live-canary gate is approved.
- Add uptime, stale-data, API-error, daily-loss and unprotected-position alerts.
- Back up the trading database daily and test restoration.
- Pin Python dependencies and deploy immutable releases.

### Monitor operations

The live monitor writes `logs/kraken-monitor-health.json` atomically. An
external uptime check should treat a stale `checked_at`, `status=error`, or
`safe=false` as an incident. Each open position includes current price, SL,
TP, unrealized P&L, and percentage distance to both exits.

Set `LIVE_MONITOR_WEBHOOK_URL` to an HTTPS endpoint that accepts JSON to
receive deduplicated alerts for unsafe reconciliation, monitor-cycle failure,
recovery, and position closure. The payload contains operational metadata
only; it does not contain API credentials or raw exchange responses.

On Linux, install `deploy/systemd/kraken-monitor.service`, adjust its paths and
user, then enable it with `systemctl enable --now kraken-monitor`. `systemd`
restarts the process after a crash and at boot. For local development only,
`python -m app.live.supervisor` provides restart-on-crash behavior. Never run
the supervisor and a separate monitor simultaneously.

## Stock server

IBKR must not share a process, database or capital allocation with Kraken.
The official TWS API requires a running TWS or IB Gateway session. IBKR does
not officially support a completely headless GUI-less session, and manual
weekly authentication is normally required.

Use either:

1. A dedicated Windows VPS with remote desktop access, or
2. A dedicated mini-PC with a UPS and secure remote access.

IB Gateway and the stock bot should run on the same machine and communicate
over localhost. A separate IBKR username should be used so logging into another
IBKR application does not interrupt the bot session.

## Sources

- [Kraken API key information, permissions and IP allowlists](https://docs.kraken.com/api/docs/rest-api/get-api-key-info)
- [AWS Lightsail instance bundles](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html)
- [AWS Lightsail European regions](https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-regions-and-availability-zones-in-amazon-lightsail.html)
- [IBKR TWS API requirements](https://ibkrcampus.com/campus/ibkr-api-page/twsapi-doc/)
- [IBKR session and restart limitations](https://ibkrcampus.com/docs/third-party-integrations/general-third-party-frequently-asked-questions)
