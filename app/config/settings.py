import os

from dotenv import load_dotenv

load_dotenv()

# ==========================
# OKX API
# ==========================
OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_SECRET = os.getenv("OKX_SECRET")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE")

# ==========================
# Trading Mode
# ==========================
PAPER_TRADING = True

# ==========================
# Timeframes
# ==========================
TREND_TIMEFRAME = "4h"
CONFIRM_TIMEFRAME = "1h"
ENTRY_TIMEFRAME = "15m"

# ==========================
# Scanner
# ==========================
QUOTE_CURRENCY = os.getenv("QUOTE_CURRENCY", "USDC")
TOP_COINS = 5
SCAN_INTERVAL = 60

# ==========================
# Market Analyzer
# ==========================
MARKET_SYMBOL = "BTC/USDC"
MARKET_MIN_SCORE = 75

# ==========================
# Candles
# ==========================
CANDLE_LIMIT = 200

# ==========================
# Strategy
# ==========================
MIN_SCORE = 90

# ==========================
# Risk Management
# ==========================

# Αρχικό κεφάλαιο (paper trading)
ACCOUNT_SIZE = 1000.0

# Ρίσκο ανά trade (1%)
RISK_PER_TRADE = 0.01

# Μέγιστες ανοιχτές θέσεις
MAX_OPEN_POSITIONS = 3

# ATR Stop Loss
ATR_MULTIPLIER = 2.0

# Risk / Reward
RISK_REWARD_RATIO = 2.0

# Μέγιστο ποσοστό κεφαλαίου ανά θέση
MAX_POSITION_SIZE = 0.20

# ==========================
# Paper Trading
# ==========================
PAPER_MONITOR_CONTINUOUS = False

# =====================================
# Test Mode
# =====================================

TEST_MODE = False