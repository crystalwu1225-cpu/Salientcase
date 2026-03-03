from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bug_bucket_classifier import classify_bug_buckets

DB_PATH = Path(__file__).with_name("form_responses.db")
INDEX_PATH = Path(__file__).with_name("index.html")

STATUS_FLOW = ["New", "In Review", "Routed", "Resolved"]
ALLOWED_STATUSES = set(STATUS_FLOW)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bug_report TEXT NOT NULL,
  customer TEXT NOT NULL,
  caller_id TEXT,
  start_date_time TEXT,
  impact_scope TEXT NOT NULL,
  reported_by TEXT NOT NULL,
  bucket TEXT NOT NULL,
  severity TEXT NOT NULL,
  status TEXT NOT NULL,
  submitted_at TEXT NOT NULL
);
"""


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db_connection() as conn:
        conn.execute(SCHEMA_SQL)
        conn.commit()


def estimate_severity(impact_scope: str) -> str:
    normalized = (impact_scope or "").strip().lower()
    if normalized == "outage":
        return "Sev1"
    if normalized == "many":
        return "Sev2"
    return "Sev3"


def compute_bucket(bug_report: str) -> str:
    classification = classify_bug_buckets(bug_report)
    return classification.primary or "Unclassified"


class AppHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict | list, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        return json.loads(raw.decode("utf-8"))

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path in {"/", "/index.html"}:
            self._send_html(INDEX_PATH.read_text(encoding="utf-8"))
            return

        if parsed.path == "/api/submissions":
            filters = parse_qs(parsed.query)
            where = []
            values: list[str] = []

            for key, column in (
                ("bucket", "bucket"),
                ("severity", "severity"),
                ("customer", "customer"),
                ("status", "status"),
            ):
                value = (filters.get(key) or [""])[0].strip()
                if value:
                    where.append(f"{column} = ?")
                    values.append(value)

            query = "SELECT * FROM submissions"
            if where:
                query += " WHERE " + " AND ".join(where)
            query += " ORDER BY datetime(submitted_at) DESC"

            with get_db_connection() as conn:
                rows = [dict(row) for row in conn.execute(query, values).fetchall()]

            self._send_json({"submissions": rows, "statuses": STATUS_FLOW})
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/submissions":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        payload = self._read_json()
        required = ["bugReport", "customer", "impactScope", "reportedBy"]
        missing = [field for field in required if not str(payload.get(field, "")).strip()]

        if missing:
            self._send_json(
                {"error": f"Missing required fields: {', '.join(missing)}"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        submitted_at = datetime.now(timezone.utc).isoformat()
        bug_report = payload["bugReport"].strip()
        record = {
            "bug_report": bug_report,
            "customer": payload["customer"].strip(),
            "caller_id": str(payload.get("callerId", "")).strip(),
            "start_date_time": str(payload.get("startDateTime", "")).strip(),
            "impact_scope": payload["impactScope"].strip(),
            "reported_by": payload["reportedBy"].strip(),
            "bucket": compute_bucket(bug_report),
            "severity": estimate_severity(payload["impactScope"]),
            "status": "New",
            "submitted_at": submitted_at,
        }

        with get_db_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO submissions (
                  bug_report, customer, caller_id, start_date_time, impact_scope,
                  reported_by, bucket, severity, status, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["bug_report"],
                    record["customer"],
                    record["caller_id"],
                    record["start_date_time"],
                    record["impact_scope"],
                    record["reported_by"],
                    record["bucket"],
                    record["severity"],
                    record["status"],
                    record["submitted_at"],
                ),
            )
            conn.commit()
            record["id"] = cur.lastrowid

        self._send_json(record, status=HTTPStatus.CREATED)

    def do_PATCH(self) -> None:  # noqa: N802
        if not self.path.startswith("/api/submissions/") or not self.path.endswith("/status"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            submission_id = int(self.path.split("/")[3])
        except (IndexError, ValueError):
            self._send_json({"error": "Invalid submission id"}, status=HTTPStatus.BAD_REQUEST)
            return

        payload = self._read_json()
        new_status = str(payload.get("status", "")).strip()
        if new_status not in ALLOWED_STATUSES:
            self._send_json({"error": "Invalid status"}, status=HTTPStatus.BAD_REQUEST)
            return

        with get_db_connection() as conn:
            cur = conn.execute("UPDATE submissions SET status = ? WHERE id = ?", (new_status, submission_id))
            conn.commit()

        if cur.rowcount == 0:
            self._send_json({"error": "Submission not found"}, status=HTTPStatus.NOT_FOUND)
            return

        self._send_json({"id": submission_id, "status": new_status})


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer(("0.0.0.0", 8000), AppHandler)
    print("Serving on http://0.0.0.0:8000")
    server.serve_forever()
