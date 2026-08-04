class TradingBotError(Exception):
    """Base exception for the trading bot."""


class MissingApiKeysError(TradingBotError):
    """Raised when API keys are required but not configured."""