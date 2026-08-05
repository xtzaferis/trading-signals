from app.market.market_analyzer import MarketAnalyzer
from app.services.screener_service import ScreenerService


def main():

    print("=" * 50)
    print("OKX Trading Bot")
    print("=" * 50)

    # ----------------------------------
    # Market Analysis
    # ----------------------------------

    analyzer = MarketAnalyzer()

    market = analyzer.analyze()

    print("\nMarket Analysis")
    print("-" * 50)

    print(f"Score : {market.score}")
    print(f"Bullish : {market.bullish}")

    for reason in market.reasons:
        print(f"  ✓ {reason}")

    # Αν η αγορά είναι bearish,
    # σταματάμε εδώ.
    if not market.bullish:

        print("\nMarket is bearish.")
        print("Skipping scan.\n")

        return

    print("\nMarket is bullish.")
    print("Starting screener...\n")

    # ----------------------------------
    # Screener
    # ----------------------------------

    service = ScreenerService()

    results = service.run()

    print("\nTop Trading Signals\n")

    for signal in results[:10]:

        print(
            f"{signal.symbol:<15}"
            f" Score: {signal.score:<3}"
            f" Action: {signal.action}"
        )

        for reason in signal.reasons:
            print(f"   - {reason}")

        print()


if __name__ == "__main__":
    main()