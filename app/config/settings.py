import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# =====================================
# Kraken Pro Spot API
# =====================================

# Kraken API credentials are a public key plus a base64-encoded private
# signing secret. The optional key-name guard prevents authenticating with a
# different Kraken key than the one dedicated to this bot.
KRAKEN_API_KEY = os.getenv("KRAKEN_API_KEY")
KRAKEN_API_SECRET = os.getenv("KRAKEN_API_SECRET")
KRAKEN_EXPECTED_KEY_NAME = os.getenv(
    "KRAKEN_EXPECTED_KEY_NAME",
    "",
).strip()

# =====================================
# Trading Mode
# =====================================

TRADING_MODE = os.getenv(
    "TRADING_MODE",
    "paper",
).strip().lower()

VALID_TRADING_MODES = {
    "paper",
    "live",
}

if TRADING_MODE not in VALID_TRADING_MODES:
    raise ValueError(
        "TRADING_MODE must be one of: paper, live."
    )

# Compatibility flag for the existing paper entry point.
PAPER_TRADING = TRADING_MODE == "paper"

# Live orders require both TRADING_MODE=live and this separate opt-in. Keeping
# the second switch off makes an accidental environment change fail closed.
LIVE_TRADING_ENABLED = (
    os.getenv("LIVE_TRADING_ENABLED", "false").strip().lower() == "true"
)

TEST_MODE = False


# =====================================
# Account
# =====================================

ACCOUNT_SIZE = float(os.getenv("ACCOUNT_SIZE", "1000.0"))

if ACCOUNT_SIZE <= 0:
    raise ValueError("ACCOUNT_SIZE must be greater than zero.")


# =====================================
# Scanner
# =====================================

QUOTE_CURRENCY = os.getenv(
    "QUOTE_CURRENCY",
    "USDC",
)

# Backtests may use a different quote market as a price-history proxy while
# all live and paper symbols remain denominated in QUOTE_CURRENCY.
BACKTEST_DATA_QUOTE_CURRENCY = os.getenv(
    "BACKTEST_DATA_QUOTE_CURRENCY",
    QUOTE_CURRENCY,
)

TOP_COINS = 5

# A fixed universe avoids selecting newly listed coins merely because they
# have a temporary volume spike. These are still crypto assets and can remain
# volatile; the intent is to prefer established, liquid markets.
CORE_SPOT_BASES = (
    "BTC",
    "ETH",
    "XRP",
    "SOL",
    "BNB",
)
SCAN_INTERVAL = 60
CANDLE_LIMIT = 200

# Live monitor observability. The webhook is optional and receives only
# operational status (never credentials or raw exchange responses).
LIVE_MONITOR_HEALTH_PATH = Path(
    os.getenv("LIVE_MONITOR_HEALTH_PATH", "logs/kraken-monitor-health.json")
)
LIVE_MONITOR_WEBHOOK_URL = os.getenv(
    "LIVE_MONITOR_WEBHOOK_URL",
    "",
).strip()
LIVE_MONITOR_WEBHOOK_TIMEOUT_SECONDS = float(
    os.getenv("LIVE_MONITOR_WEBHOOK_TIMEOUT_SECONDS", "5")
)
LIVE_MONITOR_ALERT_COOLDOWN_SECONDS = int(
    os.getenv("LIVE_MONITOR_ALERT_COOLDOWN_SECONDS", "900")
)


# =====================================
# Market Filter
# =====================================

MARKET_SYMBOL = f"BTC/{QUOTE_CURRENCY}"
MARKET_MIN_SCORE = 70


# =====================================
# Strategy
# =====================================

REGIME_TIMEFRAME = "1d"
TREND_TIMEFRAME = "4h"
CONFIRM_TIMEFRAME = "1h"
ENTRY_TIMEFRAME = "15m"

MIN_SCORE = 70

# Recovery-regime entries remain classified and reported, but are not enabled
# for trading until an independent sample demonstrates positive expectancy.
ALLOW_RECOVERY_TRADES = False


# =====================================
# Backtesting
# =====================================

# Roughly one year of evaluated candles plus enough earlier candles for
# the longest indicator to warm up on every timeframe.
BACKTEST_CANDLE_LIMITS = {
    "1d": 580,
    "4h": 2400,
    "1h": 8960,
    "15m": 35240,
}

# Exchanges can legitimately return slightly fewer candles because of gaps,
# listing schedules, or pagination boundaries. Require enough history for
# indicator warm-up and a useful evaluation period without demanding an exact
# response length.
BACKTEST_MIN_HISTORY_RATIO = 0.90

# Fresh completed candles are fetched for every backtest by default. Set this
# to true only when faster, repeatable development runs are preferred over the
# newest available exchange history.
BACKTEST_USE_CACHE = (
    os.getenv("BACKTEST_USE_CACHE", "false").strip().lower() == "true"
)
BACKTEST_CACHE_TTL_SECONDS = 6 * 60 * 60


# =====================================
# Risk Management
# =====================================

RISK_PER_TRADE = 0.005
MAX_OPEN_POSITIONS = 2
MAX_POSITION_SIZE = 0.50

ATR_MULTIPLIER = 2.0
RISK_REWARD_RATIO = 3.0
MIN_STOP_DISTANCE_PCT = 0.0075

MAX_DRAWDOWN_PCT = 0.15

# Persistent execution circuit breakers. They block new entries only; exits
# and exchange-native protection are always allowed to proceed.
MAX_DAILY_LOSS_PCT = float(os.getenv("MAX_DAILY_LOSS_PCT", "0.02"))
MAX_CONSECUTIVE_LOSSES = int(os.getenv("MAX_CONSECUTIVE_LOSSES", "3"))
MAX_EXCHANGE_ORDERS_PER_DAY = int(
    os.getenv("MAX_EXCHANGE_ORDERS_PER_DAY", "4")
)
EMERGENCY_STOP = (
    os.getenv("EMERGENCY_STOP", "false").strip().lower() == "true"
)

# Absolute safety ceiling for a single exchange order. Risk sizing may choose
# a smaller value, but exchange execution must never exceed this amount.
MAX_EXCHANGE_ORDER_VALUE = float(
    os.getenv("MAX_EXCHANGE_ORDER_VALUE", "10.0")
)

# Real-money canary execution has its own explicit opt-in and remains capped
# independently of the wider exchange gateway configuration.
LIVE_CANARY_ENABLED = (
    os.getenv("LIVE_CANARY_ENABLED", "false").strip().lower() == "true"
)
LIVE_CANARY_CONFIRMATION = os.getenv(
    "LIVE_CANARY_CONFIRMATION",
    "",
).strip()
LIVE_CANARY_SYMBOL = os.getenv(
    "LIVE_CANARY_SYMBOL",
    MARKET_SYMBOL,
).strip().upper()
LIVE_CANARY_ORDER_VALUE = float(
    os.getenv("LIVE_CANARY_ORDER_VALUE", "10.0")
)
LIVE_CANARY_MAX_ALLOCATION = 20.0
LIVE_ACCOUNT_SIZE = float(os.getenv("LIVE_ACCOUNT_SIZE", "20.0"))
LIVE_CANARY_STOP_LOSS_PCT = 0.02
LIVE_CANARY_TAKE_PROFIT_PCT = 0.04

if not 0 < LIVE_ACCOUNT_SIZE <= LIVE_CANARY_MAX_ALLOCATION:
    raise ValueError(
        f"LIVE_ACCOUNT_SIZE must be between 0 and "
        f"{LIVE_CANARY_MAX_ALLOCATION:g} {QUOTE_CURRENCY}."
    )
if not 0 < LIVE_CANARY_ORDER_VALUE <= LIVE_ACCOUNT_SIZE:
    raise ValueError(
        "LIVE_CANARY_ORDER_VALUE must be positive and no greater than "
        "LIVE_ACCOUNT_SIZE."
    )


# =====================================
# Trade Management
# =====================================

BREAK_EVEN_ENABLED = True
BREAK_EVEN_R = 1.0

TRAILING_STOP_ENABLED = True
TRAILING_START_R = 1.5

MAX_POSITION_HOLD_HOURS = 24


# =====================================
# Trade Protection
# =====================================

MIN_BARS_BETWEEN_TRADES = 4
MIN_BARS_AFTER_STOP_LOSS = 96


# =====================================
# Trading Costs
# =====================================

TRADING_FEE = 0.001
SLIPPAGE = 0.0005


# =====================================
# Paper Trading
# =====================================

PAPER_MONITOR_CONTINUOUS = False

# Records experimental recovery signals and their hypothetical TP/SL outcomes.
# Shadow trades never reach a broker or reserve portfolio cash.
SHADOW_RECOVERY_ENABLED = True
SHADOW_MIN_CLOSED_TRADES = 30
SHADOW_MIN_PROFIT_FACTOR = 1.20

PAPER_STATE_PERSISTENCE_ENABLED = True
MAX_ENTRY_CANDLE_AGE_SECONDS = 45 * 60
PAPER_HEALTH_STALE_SECONDS = max(5 * 60, SCAN_INTERVAL * 3)
