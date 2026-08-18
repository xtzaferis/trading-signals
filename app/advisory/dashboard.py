import argparse
import json
import threading
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import monotonic
from urllib.parse import urlparse

from app.advisory.service import AdvisoryReport, EntryAdvisoryService

HTML_PATH = Path(__file__).with_name("dashboard.html")


class ScanInProgressError(RuntimeError):
    pass


def report_to_dict(report: AdvisoryReport, duration_seconds: float) -> dict:
    shortlisted = {item.symbol for item in report.shortlist}
    candidates = []
    for candidate in report.candidates:
        trade = asdict(candidate.trade) if candidate.trade else None
        derivatives = asdict(candidate.derivatives) if candidate.derivatives else None
        if derivatives is not None:
            derivatives["label"] = candidate.derivatives.label
        candidates.append(
            {
                "symbol": candidate.symbol,
                "status": candidate.status,
                "risk": candidate.risk,
                "score": candidate.score,
                "price": candidate.price,
                "trade": trade,
                "reasons": list(candidate.reasons),
                "derivatives": derivatives,
                "shortlisted": candidate.symbol in shortlisted,
            }
        )
    return {
        "generated_at": report.generated_at.isoformat(),
        "window_open": report.window_open,
        "forced": report.forced,
        "duration_seconds": round(duration_seconds, 1),
        "candidates": candidates,
        "errors": list(report.errors),
        "summary": {
            "long": sum(item.status == "LONG" for item in report.candidates),
            "short": sum(item.status == "SHORT" for item in report.candidates),
            "wait": sum(item.status == "WAIT" for item in report.candidates),
            "shortlisted": len(report.shortlist),
        },
    }


class DashboardApplication:
    def __init__(self, service_factory=EntryAdvisoryService):
        self.service_factory = service_factory
        self._scan_lock = threading.Lock()

    def scan(self, force: bool = False) -> dict:
        if not self._scan_lock.acquire(blocking=False):
            raise ScanInProgressError("A market scan is already running.")
        started = monotonic()
        try:
            report = self.service_factory().scan(force=force)
            return report_to_dict(report, monotonic() - started)
        finally:
            self._scan_lock.release()


def make_handler(application: DashboardApplication):
    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "CryptoAdvisoryDashboard/1.0"

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/":
                self._send_bytes(
                    HTTPStatus.OK,
                    HTML_PATH.read_bytes(),
                    "text/html; charset=utf-8",
                )
                return
            if path == "/api/health":
                self._send_json(HTTPStatus.OK, {"status": "ok", "read_only": True})
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

        def do_POST(self):
            if urlparse(self.path).path != "/api/signals":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
                return
            try:
                length = min(int(self.headers.get("Content-Length", "0")), 4096)
                body = json.loads(self.rfile.read(length) or b"{}")
                result = application.scan(force=body.get("force") is True)
                self._send_json(HTTPStatus.OK, result)
            except ScanInProgressError as error:
                self._send_json(HTTPStatus.CONFLICT, {"error": str(error)})
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            except Exception:
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "The scan failed. Check the terminal for details."},
                )
                raise

        def log_message(self, format_string, *args):
            print(f"Dashboard | {self.address_string()} | {format_string % args}")

        def _send_json(self, status: HTTPStatus, payload: dict):
            self._send_bytes(
                status,
                json.dumps(payload, allow_nan=False).encode("utf-8"),
                "application/json; charset=utf-8",
            )

        def _send_bytes(self, status: HTTPStatus, body: bytes, content_type: str):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'",
            )
            self.end_headers()
            self.wfile.write(body)

    return DashboardHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Local read-only advisory dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(
        (args.host, args.port),
        make_handler(DashboardApplication()),
    )
    print("=" * 64)
    print("READ-ONLY ADVISORY DASHBOARD")
    print(f"Open http://{args.host}:{args.port} in your browser")
    print("Press Ctrl+C to stop. No order execution is available.")
    print("=" * 64)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
