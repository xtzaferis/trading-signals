import json
import shutil
from pathlib import Path
from time import monotonic

from app.advisory.dashboard import HTML_PATH, report_to_dict
from app.advisory.service import EntryAdvisoryService
from app.config.settings import ADVISORY_DATA_SOURCE
from app.storage.advisory_signal_repository import AdvisorySignalRepository

SITE_DIR = Path("site")


def publish(
    site_dir: Path = SITE_DIR,
    repository: AdvisorySignalRepository | None = None,
    service=None,
) -> bool:
    site_dir.mkdir(parents=True, exist_ok=True)
    history_path = site_dir / f"advisory-history-{ADVISORY_DATA_SOURCE}.json"
    repository = repository or AdvisorySignalRepository()
    repository.import_public_history(history_path)
    service = service or EntryAdvisoryService(journal=repository)
    started = monotonic()
    report = service.scan()
    duration = monotonic() - started

    shutil.copyfile(HTML_PATH, site_dir / "index.html")
    repository.export_public_history(history_path)
    # Preserve the last useful snapshot outside the configured window. During
    # the session, publish empty/error reports so the dashboard never mistakes
    # a failed market scan for a stale successful deployment.
    if not report.window_open and not report.forced:
        return False
    payload = report_to_dict(report, duration)
    payload["performance"] = repository.statistics()
    (site_dir / "signals.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    return True


def main() -> None:
    published = publish()
    if published:
        print("Published the latest in-session advisory snapshot.")
    else:
        print("No in-session snapshot generated; preserved the previous signals file.")


if __name__ == "__main__":
    main()
