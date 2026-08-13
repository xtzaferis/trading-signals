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

TOP_COINS = 5
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

TREND_TIMEFRAME = "4h"
CONFIRM_TIMEFRAME = "1h"
ENTRY_TIMEFRAME = "15m"

MIN_SCORE = 70


# =====================================
# Backtesting
# =====================================

# Roughly one month of evaluated candles plus enough earlier candles for
# the longest (EMA 200) indicator to warm up on every timeframe.
BACKTEST_CANDLE_LIMITS = {
    "4h": 1280,
    "1h": 4520,
    "15m": 17480,
}


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


# =====================================
# Trading Costs
# =====================================

TRADING_FEE = 0.001
SLIPPAGE = 0.0005


# =====================================
# Paper Trading
# =====================================

PAPER_MONITOR_CONTINUOUS = False
