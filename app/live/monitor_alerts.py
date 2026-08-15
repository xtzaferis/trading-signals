from datetime import datetime, timezone

import requests

from app.core.logger import logger


class MonitorAlerts:
    """Optional webhook alerts with transition and cooldown deduplication."""

    def __init__(
        self,
        webhook_url: str = "",
        timeout: float = 5.0,
        cooldown_seconds: int = 900,
        sender=None,
        clock=None,
    ):
        self.webhook_url = webhook_url.strip()
        self.timeout = timeout
        self.cooldown_seconds = max(0, cooldown_seconds)
        self.sender = sender or requests.post
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._last_sent: dict[str, datetime] = {}

    def send(
        self,
        event: str,
        message: str,
        severity: str = "warning",
        details: dict | None = None,
        force: bool = False,
    ) -> bool:
        if not self.webhook_url:
            return False
        now = self.clock()
        previous = self._last_sent.get(event)
        if (
            not force
            and previous is not None
            and (now - previous).total_seconds() < self.cooldown_seconds
        ):
            return False
        payload = {
            "source": "kraken-live-monitor",
            "event": event,
            "severity": severity,
            "message": message,
            "timestamp": now.isoformat(),
            "details": details or {},
        }
        try:
            response = self.sender(
                self.webhook_url,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException:
            logger.exception("Kraken monitor webhook delivery failed.")
            return False
        self._last_sent[event] = now
        return True
