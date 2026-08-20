from pathlib import Path

WORKFLOW = Path(".github/workflows/advisory-pages.yml")


def test_advisory_schedule_has_five_minute_redundancy():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'cron: "2,7,12,17,22,27,32,37,42,47,52,57 17-18 * * *"' in workflow
    assert 'timezone: "Europe/Athens"' in workflow
