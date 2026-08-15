import os
import subprocess
import sys
import time
from pathlib import Path

from app.config.settings import (
    LIVE_MONITOR_ALERT_COOLDOWN_SECONDS,
    LIVE_MONITOR_WEBHOOK_TIMEOUT_SECONDS,
    LIVE_MONITOR_WEBHOOK_URL,
)
from app.core.logger import logger
from app.live.monitor_alerts import MonitorAlerts

LOCK_PATH = Path("logs/kraken-monitor-supervisor.pid")


def _acquire_lock(path: Path = LOCK_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = path.open("x", encoding="utf-8")
    except FileExistsError as error:
        raise RuntimeError(
            f"A Kraken monitor supervisor lock already exists at {path}."
        ) from error
    with descriptor:
        descriptor.write(str(os.getpid()))


def run(restart_delay: int = 10) -> None:
    _acquire_lock()
    alerts = MonitorAlerts(
        LIVE_MONITOR_WEBHOOK_URL,
        LIVE_MONITOR_WEBHOOK_TIMEOUT_SECONDS,
        LIVE_MONITOR_ALERT_COOLDOWN_SECONDS,
    )
    try:
        while True:
            logger.info("Starting Kraken live monitor child process.")
            completed = subprocess.run(
                [sys.executable, "-m", "app.live.monitor", "--wait"],
                check=False,
            )
            logger.error(
                "Kraken monitor exited with code %s; restarting in %s seconds.",
                completed.returncode,
                restart_delay,
            )
            alerts.send(
                "monitor-process-exited",
                "Kraken monitor process exited and will be restarted.",
                severity="critical",
                details={"exit_code": completed.returncode},
            )
            time.sleep(max(1, restart_delay))
    finally:
        LOCK_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    run()
