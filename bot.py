from app.services.screener_service import ScreenerService


def main():

    print("=" * 50)
    print("OKX Trading Bot")
    print("=" * 50)

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