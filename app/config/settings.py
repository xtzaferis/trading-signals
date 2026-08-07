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

MARKET_MIN_SCORE = 75

# =====================================
# Strategy
# =====================================

TREND_TIMEFRAME = "4h"

CONFIRM_TIMEFRAME = "1h"

ENTRY_TIMEFRAME = "15m"

MIN_SCORE = 90

# =====================================
# Risk Management
# =====================================

RISK_PER_TRADE = 0.01

MAX_OPEN_POSITIONS = 3

MAX_POSITION_SIZE = 0.20

ATR_MULTIPLIER = 2.0

RISK_REWARD_RATIO = 2.0

# =====================================
# Trade Management
# =====================================

BREAK_EVEN_ENABLED = True

BREAK_EVEN_R = 1.0

TRAILING_STOP_ENABLED = True

# =====================================
# Paper Trading
# =====================================

PAPER_MONITOR_CONTINUOUS = False