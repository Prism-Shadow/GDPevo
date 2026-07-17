#!/usr/bin/env python3
"""Standard-library JSON API for task_group_017 shared investigation data."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from judge_api import judge_answer_request


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "generated"
MANIFEST_PATH = BASE_DIR / "manifest.json"

COLLECTIONS = {
    "matters": "matters.json",
    "subpoena_categories": "subpoena_categories.json",
    "production_logs": "production_logs.json",
    "collection_events": "collection_events.json",
    "retention_rules": "retention_rules.json",
    "destruction_events": "destruction_events.json",
    "privilege_logs": "privilege_logs.json",
    "qc_events": "qc_events.json",
    "custodians": "custodians.json",
    "documents": "documents.json",
}

INDEX_TEXT = """task_group_017 shared legal investigation environment

JSON endpoints:
  /health
  /api/matters
  /api/matters/{matter_id}
  /api/subpoena_categories?matter_id=...
  /api/production_logs?matter_id=...
  /api/collection_events?matter_id=...
  /api/retention_rules?matter_id=...
  /api/destruction_events?matter_id=...
  /api/privilege_logs?matter_id=...
  /api/qc_events?matter_id=...
  /api/custodians?matter_id=...
  /api/documents?matter_id=...
  /api/search?matter_id=...&q=...
"""


def ensure_generated() -> None:
    missing = [name for name in COLLECTIONS.values() if not (DATA_DIR / name).exists()]
    if not missing and MANIFEST_PATH.exists():
        return
    subprocess.run([sys.executable, str(BASE_DIR / "generate_data.py")], check=True, cwd=str(BASE_DIR))


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def load_state() -> tuple[dict[str, list[dict]], dict]:
    ensure_generated()
    data = {name: read_json(DATA_DIR / filename) for name, filename in COLLECTIONS.items()}
    manifest = read_json(MANIFEST_PATH)
    return data, manifest


DATA, MANIFEST = load_state()


def first_value(query: dict[str, list[str]], key: str, default: str = "") -> str:
    values = query.get(key)
    if not values:
        return default
    return values[0]


def item_matches_filters(item: dict, query: dict[str, list[str]]) -> bool:
    for key in ("matter_id", "category_id", "custodian_id", "document_id", "event_id", "item_id"):
        expected = first_value(query, key)
        if not expected:
            continue
        value = item.get(key)
        if isinstance(value, list):
            if expected not in value:
                return False
        elif value != expected:
            return False
    return True


def filter_rows(rows: list[dict], query: dict[str, list[str]]) -> list[dict]:
    filtered = [row for row in rows if item_matches_filters(row, query)]
    status = first_value(query, "status")
    if status:
        filtered = [
            row
            for row in filtered
            if row.get("status") == status
            or row.get("review_status") == status
            or row.get("production_status") == status
            or row.get("issue_status") == status
        ]
    limit = first_value(query, "limit")
    if limit:
        try:
            max_rows = max(0, min(int(limit), 1000))
        except ValueError:
            max_rows = 1000
        filtered = filtered[:max_rows]
    return filtered


def text_blob(value: object) -> str:
    if isinstance(value, dict):
        return " ".join(text_blob(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(text_blob(v) for v in value)
    return str(value)


def search_records(query: dict[str, list[str]]) -> dict:
    q = first_value(query, "q").strip().lower()
    matter_id = first_value(query, "matter_id").strip()
    try:
        limit = max(1, min(int(first_value(query, "limit", "25")), 100))
    except ValueError:
        limit = 25

    results: dict[str, list[dict]] = {}
    total = 0
    if not q:
        return {"query": q, "matter_id": matter_id or None, "total": 0, "results": results}

    for collection, rows in DATA.items():
        matches = []
        for row in rows:
            if matter_id and row.get("matter_id") != matter_id:
                continue
            if q in text_blob(row).lower():
                matches.append(row)
            if len(matches) >= limit:
                break
        if matches:
            results[collection] = matches
            total += len(matches)
    return {
        "query": q,
        "matter_id": matter_id or None,
        "total": total,
        "limit_per_collection": limit,
        "results": results,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "TaskGroup017Env/1.0"

    def do_POST(self) -> None:
        if urlparse(self.path).path.rstrip("/") != "/api/judge":
            self.send_json(404, {"error": "endpoint not found", "path": self.path})
            return
        if os.environ.get("TASK_ENV_ENABLE_JUDGE") != "1":
            self.send_json(404, {"error": "endpoint not found", "path": self.path})
            return
        length = int(self.headers.get("Content-Length", "0"))
        status, payload = judge_answer_request(self.rfile.read(length))
        self.send_json(status, payload)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        if path == "/":
            self.send_text(200, INDEX_TEXT)
            return

        if path == "/health":
            self.send_json(
                200,
                {
                    "status": "ok",
                    "service": "task_group_017_env",
                    "random_seed": MANIFEST.get("random_seed"),
                    "record_counts": MANIFEST.get("record_counts", {}),
                },
            )
            return

        if path == "/api/matters":
            self.send_json(200, {"count": len(DATA["matters"]), "items": DATA["matters"]})
            return

        if path.startswith("/api/matters/"):
            matter_id = unquote(path.split("/", 3)[3])
            matter = next((row for row in DATA["matters"] if row["matter_id"] == matter_id), None)
            if matter is None:
                self.send_json(404, {"error": "matter not found", "matter_id": matter_id})
                return
            self.send_json(200, matter)
            return

        if path == "/api/search":
            self.send_json(200, search_records(query))
            return

        if path.startswith("/api/"):
            collection = path.split("/", 2)[2]
            if collection in COLLECTIONS:
                rows = filter_rows(DATA[collection], query)
                self.send_json(200, {"count": len(rows), "items": rows})
                return

        self.send_json(404, {"error": "endpoint not found", "path": parsed.path})

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write(f"{self.address_string()} - - [{self.log_date_time_string()}] {fmt % args}\n")

    def send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, status: int, payload: str) -> None:
        body = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    port = int(os.environ.get("TASK_ENV_PORT", os.environ.get("PORT", "9017")))
    host = os.environ.get("TASK_ENV_BIND", os.environ.get("TASK_ENV_HOST", "0.0.0.0"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"task_group_017 env listening on http://{host}:{port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
