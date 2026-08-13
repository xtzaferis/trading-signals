class TradingBotError(Exception):
    """Base exception for the trading bot."""


class MissingApiKeysError(TradingBotError):
    """Raised when API keys are required but not configured."""


class TradingModeError(TradingBotError):
    """Raised when an operation is not allowed in the configured mode."""


class LiveTradingDisabledError(TradingModeError):
    """Raised when live trading lacks the separate safety opt-in."""


class OrderValidationError(TradingBotError):
    """Raised before an unsafe or invalid order reaches the exchange."""
