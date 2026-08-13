import os

from dotenv import load_dotenv

load_dotenv()


# =====================================
# OKX API
# =====================================

OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_SECRET = os.getenv("OKX_SECRET")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE")


# =====================================
# Trading Mode
# =====================================

PAPER_TRADING = True
TEST_MODE = False


# =====================================
# Account
# =====================================

ACCOUNT_SIZE = 1000.0


# =====================================
# Scanner
# =====================================

QUOTE_CURRENCY = os.getenv(
    "QUOTE_CURRENCY",
    "USDC",
)

# OKX's USDC spot history starts much later than its USDT history. Backtests
# use the matching USDT market as a price-history proxy while all live/paper
# symbols remain denominated in QUOTE_CURRENCY.
BACKTEST_DATA_QUOTE_CURRENCY = os.getenv(
    "BACKTEST_DATA_QUOTE_CURRENCY",
    "USDT",
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
    "ADA",
)
SCAN_INTERVAL = 60
CANDLE_LIMIT = 200


# =====================================
# Market Filter
# =====================================

MARKET_SYMBOL = "BTC/USDC"
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
