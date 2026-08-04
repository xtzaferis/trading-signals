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
# Risk
# ==========================
RISK_PER_TRADE = 0.01
MAX_OPEN_POSITIONS = 3

# ==========================
# Scanner
# ==========================
TOP_COINS = 5

# ==========================
# Quote Currency
# ==========================
QUOTE_CURRENCY = os.getenv("QUOTE_CURRENCY", "USDC")

# ==========================
# Candles
# ==========================
CANDLE_LIMIT = 200

# ==========================
# Scanner
# ==========================
SCAN_INTERVAL = 60  # δευτερόλεπτα

# ==========================
# Strategy
# ==========================
MIN_SCORE = 90
