from app.storage.advisory_signal_repository import AdvisorySignalRepository


def main() -> None:
    statistics = AdvisorySignalRepository().statistics()
    print("=" * 64)
    print("FORWARD ADVISORY PERFORMANCE - SHORTLISTED SETUPS")
    print(f"Resolved:           {statistics['resolved']}")
    print(f"Targets:            {statistics['targets']}")
    print(f"Stops:              {statistics['stops']}")
    print(f"Timeouts:           {statistics['timeouts']}")
    print(f"Average net return: {statistics['average_return_pct']:+.3f}%")
    print(f"Sum of returns:     {statistics['total_return_pct']:+.3f}%")
    if statistics["resolved"] == 0:
        print("No resolved observations yet. Run the scanner on multiple days.")


if __name__ == "__main__":
    main()
