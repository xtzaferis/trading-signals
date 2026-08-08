from app.exchange.okx_client import OKXClient


class LiveMarketService:

    def __init__(self):

        self.client = OKXClient()

    def get_snapshot(
        self,
        symbol: str,
        trend_timeframe: str,
        confirm_timeframe: str,
        entry_timeframe: str,
        limit: int = 200,
    ) -> dict:

        return {

            "trend": {
                "candles": (
                    self.client.get_ohlcv(
                        symbol,
                        timeframe=trend_timeframe,
                        limit=limit,
                    )
                ),
            },

            "confirm": {
                "candles": (
                    self.client.get_ohlcv(
                        symbol,
                        timeframe=confirm_timeframe,
                        limit=limit,
                    )
                ),
            },

            "entry": {
                "candles": (
                    self.client.get_ohlcv(
                        symbol,
                        timeframe=entry_timeframe,
                        limit=limit,
                    )
                ),
            },
        }