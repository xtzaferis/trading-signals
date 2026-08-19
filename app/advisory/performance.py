from app.storage.advisory_signal_repository import AdvisorySignalRepository


def main() -> None:
    repository = AdvisorySignalRepository()
    statistics = repository.statistics()
    print("=" * 64)
    print("FORWARD ADVISORY PERFORMANCE - SHORTLISTED SETUPS")
    print(f"Resolved:           {statistics['resolved']}")
    print(f"Targets:            {statistics['targets']}")
    print(f"Stops:              {statistics['stops']}")
    print(f"Timeouts:           {statistics['timeouts']}")
    print(f"Average net return: {statistics['average_return_pct']:+.3f}%")
    print(f"Sum of returns:     {statistics['total_return_pct']:+.3f}%")
    calibration = repository.calibration()
    overall = calibration["overall"]
    print(f"Target rate:        {overall['target_rate_pct']:.2f}%")
    print(
        "95% interval:       "
        f"{overall['target_rate_95pct_interval'][0]:.2f}% to "
        f"{overall['target_rate_95pct_interval'][1]:.2f}%"
    )
    print(
        "Calibration:        "
        + ("usable" if overall["reliable"] else "preliminary (fewer than 30)")
    )
    for direction, result in calibration["by_direction"].items():
        print(
            f"  {direction:<5}: sample={result['sample']}, "
            f"target={result['target_rate_pct']:.2f}%, "
            f"avg={result['average_net_return_pct']:+.3f}%"
        )
    diagnostics = repository.outcome_diagnostics()
    if diagnostics["resolved"]:
        print("Outcome diagnostics:")
        print(f"  Average MFE:      {diagnostics['average_mfe_pct']:+.3f}%")
        print(f"  Average MAE:      {diagnostics['average_mae_pct']:+.3f}%")
        print(
            "  Average exit time: "
            f"{diagnostics['average_time_to_exit_minutes']:.1f} minutes"
        )
        print(
            "  Actual funding:    "
            f"{diagnostics['average_actual_funding_rate']:+.6f} average rate"
        )
    if statistics["resolved"] == 0:
        print("No resolved observations yet. Run the scanner on multiple days.")


if __name__ == "__main__":
    main()
