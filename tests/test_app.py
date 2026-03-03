from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "http://127.0.0.1:8000"
DB_PATH = Path(__file__).resolve().parents[1] / "form_responses.db"


def request_json(path: str, method: str = "GET", data: dict | None = None):
    payload = None
    headers = {}
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(f"{BASE_URL}{path}", method=method, data=payload, headers=headers)
    with urlopen(req, timeout=3) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def wait_for_server():
    for _ in range(30):
        try:
            request_json("/api/submissions")
            return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("server did not start")


def test_submission_lifecycle():
    if DB_PATH.exists():
        DB_PATH.unlink()

    proc = subprocess.Popen(["python", "app.py"], cwd=Path(__file__).resolve().parents[1], env={**os.environ})
    try:
        wait_for_server()

        status, created = request_json(
            "/api/submissions",
            method="POST",
            data={
                "bugReport": "Webhook failed for all calls",
                "customer": "Acme",
                "callerId": "123",
                "startDateTime": "2026-01-02T10:11",
                "impactScope": "outage",
                "reportedBy": "qa@example.com",
            },
        )
        assert status == 201
        assert created["status"] == "New"
        assert created["severity"] == "Sev1"

        _, listing = request_json("/api/submissions")
        assert len(listing["submissions"]) >= 1

        query = urlencode({"customer": "Acme", "status": "New"})
        _, filtered = request_json(f"/api/submissions?{query}")
        assert all(row["customer"] == "Acme" for row in filtered["submissions"])
        assert all(row["status"] == "New" for row in filtered["submissions"])

        row_id = created["id"]
        status, patched = request_json(
            f"/api/submissions/{row_id}/status",
            method="PATCH",
            data={"status": "Resolved"},
        )
        assert status == 200
        assert patched["status"] == "Resolved"

    finally:
        proc.terminate()
        proc.wait(timeout=5)
        if DB_PATH.exists():
            DB_PATH.unlink()


def test_rejects_invalid_status():
    if DB_PATH.exists():
        DB_PATH.unlink()

    proc = subprocess.Popen(["python", "app.py"], cwd=Path(__file__).resolve().parents[1], env={**os.environ})
    try:
        wait_for_server()

        _, created = request_json(
            "/api/submissions",
            method="POST",
            data={
                "bugReport": "transcript does not match",
                "customer": "Beta",
                "impactScope": "single",
                "reportedBy": "qa@example.com",
            },
        )

        req = Request(
            f"{BASE_URL}/api/submissions/{created['id']}/status",
            method="PATCH",
            data=json.dumps({"status": "Done"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        try:
            urlopen(req, timeout=3)
            assert False, "Expected HTTPError"
        except HTTPError as err:
            assert err.code == 400

    finally:
        proc.terminate()
        proc.wait(timeout=5)
        if DB_PATH.exists():
            DB_PATH.unlink()
