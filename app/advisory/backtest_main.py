import argparse
from datetime import datetime, timedelta, timezone

from app.advisory.replay import AdvisoryReplayEngine
from app.exchange.binance_market_data_client import BinanceMarketDataClient

WARMUP = {
    "1d": timedelta(days=250),
    "4h": timedelta(days=40),
    "1h": timedelta(days=10),
    "15m": timedelta(days=4),
    "5m": timedelta(days=1),
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only Binance futures advisory replay"
    )
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    if args.days <= 0:
        parser.error("--days must be positive")

    client = BinanceMarketDataClient()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    candles = {}
    for timeframe, warmup in WARMUP.items():
        print(f"Loading {args.symbol} {timeframe} futures candles...", flush=True)
        candles[timeframe] = client.get_ohlcv_range(
            args.symbol,
            timeframe,
            int((start - warmup).timestamp() * 1000),
            int((end + timedelta(days=1)).timestamp() * 1000),
        )
    print("Loading historical funding rates...", flush=True)
    funding = client.get_funding_rates_range(
        args.symbol,
        int(start.timestamp() * 1000),
        int(end.timestamp() * 1000),
    )
    result = AdvisoryReplayEngine().run(args.symbol, candles, start, end, funding)

    print("=" * 64)
    print("ADVISORY FUTURES REPLAY - NO ORDERS SENT")
    print(f"Symbol:              {args.symbol}")
    print(f"Days:                {args.days}")
    print(f"Closed trades:       {len(result.trades)}")
    print(f"Wins / losses:       {result.wins} / {result.losses}")
    print(f"Win rate:            {result.win_rate:.2f}%")
    print(f"Average net return:  {result.average_return_pct:+.3f}%")
    print(f"Compounded return:   {result.compounded_return_pct:+.3f}%")
    print("Fees, slippage and historical funding are included.")


if __name__ == "__main__":
    main()
