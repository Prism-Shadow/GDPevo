#!/usr/bin/env python3
"""Stdlib HTTP API for the task_group_018 clerk operations environment."""

from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "clerk_ops.json"
MANIFEST_FILE = BASE_DIR / "data" / "manifest.json"


def ensure_data() -> None:
    if DATA_FILE.exists() and MANIFEST_FILE.exists():
        return
    subprocess.run([sys.executable, str(BASE_DIR / "generate_data.py")], check=True)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_boolish(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.lower()
    if lowered in {"1", "true", "yes"}:
        return True
    if lowered in {"0", "false", "no"}:
        return False
    return None


def first(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    if not values:
        return None
    value = values[0].strip()
    return value or None


def matches(value: object, expected: str | None) -> bool:
    if expected is None:
        return True
    return str(value).lower() == expected.lower()


def contains_text(value: object, needle: str) -> bool:
    if value is None:
        return False
    if isinstance(value, (dict, list)):
        haystack = json.dumps(value, sort_keys=True).lower()
    else:
        haystack = str(value).lower()
    return needle.lower() in haystack


def date_active(row: dict, effective_on: str | None) -> bool:
    if not effective_on:
        return True
    start = row.get("effective_start")
    end = row.get("effective_end")
    if start and effective_on < start:
        return False
    if end and effective_on > end:
        return False
    return True


class ClerkOpsHandler(BaseHTTPRequestHandler):
    server_version = "ClerkOpsHTTP/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        try:
            if path == "/health":
                self.send_json(
                    {
                        "status": "ok",
                        "service": "clerk-operations",
                        "schema_version": self.server.dataset["meta"]["schema_version"],
                        "record_counts": self.server.manifest["record_counts"],
                    }
                )
            elif path == "/docs":
                self.send_docs()
            elif path == "/api/counties":
                self.send_json(
                    {"count": len(self.server.dataset["counties"]), "results": self.server.dataset["counties"]}
                )
            elif path == "/api/cases":
                self.handle_cases(query)
            elif path.startswith("/api/cases/"):
                self.handle_case_detail(path.rsplit("/", 1)[-1])
            elif path == "/api/citations":
                self.handle_citations(query)
            elif path.startswith("/api/citations/"):
                self.handle_citation_detail(path.rsplit("/", 1)[-1])
            elif path == "/api/hearings":
                self.handle_hearings(query)
            elif path == "/api/attorneys":
                self.handle_attorneys(query)
            elif path == "/api/fees":
                self.handle_fees(query)
            elif path == "/api/payment-policies":
                self.handle_payment_policies(query)
            elif path == "/api/financial-obligations":
                self.handle_financial_obligations(query)
            elif path == "/api/docket":
                self.handle_docket(query)
            elif path == "/api/stale-exports":
                self.handle_stale_exports(query)
            elif path == "/api/search":
                self.handle_search(query)
            else:
                self.send_error_json(HTTPStatus.NOT_FOUND, "endpoint not found")
        except BrokenPipeError:
            raise
        except Exception as exc:
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, f"internal error: {exc}")

    def handle_cases(self, query: dict[str, list[str]]) -> None:
        county = first(query, "county")
        matter_type = first(query, "matter_type")
        status = first(query, "status")
        defendant = first(query, "defendant_name")
        rows = []
        for row in self.server.dataset["cases"]:
            if not matches(row["county"], county):
                continue
            if not matches(row["matter_type"], matter_type):
                continue
            if not matches(row["status"], status):
                continue
            if defendant and defendant.lower() not in row["defendant_name"].lower():
                continue
            rows.append(row)
        self.send_list(rows, query)

    def handle_case_detail(self, case_number: str) -> None:
        for row in self.server.dataset["cases"]:
            if row["case_number"].lower() == case_number.lower():
                self.send_json(row)
                return
        self.send_error_json(HTTPStatus.NOT_FOUND, "case not found")

    def handle_citations(self, query: dict[str, list[str]]) -> None:
        county = first(query, "county")
        disposition = first(query, "disposition")
        violation_code = first(query, "violation_code")
        payment_plan = parse_boolish(first(query, "payment_plan_requested"))
        rows = []
        for row in self.server.dataset["citations"]:
            if not matches(row["county"], county):
                continue
            if not matches(row["disposition"], disposition):
                continue
            if not matches(row["violation_code"], violation_code):
                continue
            if payment_plan is not None and row["payment_plan_requested"] is not payment_plan:
                continue
            rows.append(row)
        self.send_list(rows, query)

    def handle_citation_detail(self, citation_number: str) -> None:
        for row in self.server.dataset["citations"]:
            if row["citation_number"].lower() == citation_number.lower():
                self.send_json(row)
                return
        self.send_error_json(HTTPStatus.NOT_FOUND, "citation not found")

    def handle_hearings(self, query: dict[str, list[str]]) -> None:
        county = first(query, "county")
        hearing_date = first(query, "date") or first(query, "hearing_date")
        matter = first(query, "matter")
        rows = []
        for row in self.server.dataset["hearings"]:
            if not matches(row["county"], county):
                continue
            if hearing_date and row["hearing_date"] != hearing_date:
                continue
            if matter and matter not in row["matters"]:
                continue
            rows.append(row)
        self.send_list(rows, query)

    def handle_attorneys(self, query: dict[str, list[str]]) -> None:
        county = first(query, "county")
        active = parse_boolish(first(query, "active"))
        rows = []
        for row in self.server.dataset["attorneys"]:
            if county and county not in row["counties"]:
                continue
            if active is not None and row["active"] is not active:
                continue
            rows.append(row)
        self.send_list(rows, query)

    def handle_fees(self, query: dict[str, list[str]]) -> None:
        county = first(query, "county")
        matter_type = first(query, "matter_type")
        effective_on = first(query, "effective_on")
        mandatory = parse_boolish(first(query, "mandatory"))
        rows = []
        for row in self.server.dataset["fee_schedules"]:
            if not matches(row["county"], county):
                continue
            if not matches(row["matter_type"], matter_type):
                continue
            if mandatory is not None and row["mandatory"] is not mandatory:
                continue
            if not date_active(row, effective_on):
                continue
            rows.append(row)
        self.send_list(rows, query)

    def handle_payment_policies(self, query: dict[str, list[str]]) -> None:
        county = first(query, "county")
        rows = [row for row in self.server.dataset["payment_policies"] if matches(row["county"], county)]
        self.send_list(rows, query)

    def handle_financial_obligations(self, query: dict[str, list[str]]) -> None:
        case_number = first(query, "case_number")
        county = first(query, "county")
        status = first(query, "status")
        rows = []
        for row in self.server.dataset["financial_obligations"]:
            if case_number and row["case_number"].lower() != case_number.lower():
                continue
            if not matches(row["county"], county):
                continue
            if not matches(row["status"], status):
                continue
            rows.append(row)
        self.send_list(rows, query)

    def handle_docket(self, query: dict[str, list[str]]) -> None:
        case_number = first(query, "case_number")
        event_type = first(query, "event_type")
        rows = self.server.dataset["docket_entries"]
        if case_number:
            rows = [row for row in rows if row["case_number"].lower() == case_number.lower()]
        if event_type:
            filtered = []
            for row in rows:
                entries = [entry for entry in row["entries"] if matches(entry["event_type"], event_type)]
                if entries:
                    filtered.append({"case_number": row["case_number"], "entries": entries})
            rows = filtered
        self.send_list(rows, query)

    def handle_stale_exports(self, query: dict[str, list[str]]) -> None:
        county = first(query, "county")
        name = first(query, "name")
        rows = []
        for row in self.server.dataset["stale_exports"]:
            if not matches(row["county"], county):
                continue
            if not matches(row["name"], name):
                continue
            rows.append(row)
        self.send_list(rows, query)

    def handle_search(self, query: dict[str, list[str]]) -> None:
        q = first(query, "q")
        if not q:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "query parameter q is required")
            return
        results = []
        for row in self.server.dataset["cases"]:
            if contains_text(row, q):
                results.append(
                    {
                        "record_type": "case",
                        "id": row["case_number"],
                        "county": row["county"],
                        "label": f"{row['case_number']} {row['defendant_name']}",
                    }
                )
        for row in self.server.dataset["citations"]:
            if contains_text(row, q):
                results.append(
                    {
                        "record_type": "citation",
                        "id": row["citation_number"],
                        "county": row["county"],
                        "label": f"{row['citation_number']} {row['defendant_name']}",
                    }
                )
        for row in self.server.dataset["attorneys"]:
            if contains_text(row, q):
                results.append(
                    {
                        "record_type": "attorney",
                        "id": row["attorney_id"],
                        "county": ",".join(row["counties"]),
                        "label": row["name"],
                    }
                )
        for row in self.server.dataset["hearings"]:
            if contains_text(row, q):
                results.append(
                    {
                        "record_type": "hearing",
                        "id": row["hearing_id"],
                        "county": row["county"],
                        "label": f"{row['hearing_date']} {row['judge']}",
                    }
                )
        self.send_list(results, query)

    def send_list(self, rows: list, query: dict[str, list[str]]) -> None:
        total = len(rows)
        limit = first(query, "limit")
        offset = first(query, "offset")
        try:
            limit_int = min(max(int(limit), 0), 500) if limit is not None else None
            offset_int = max(int(offset), 0) if offset is not None else 0
        except ValueError:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "limit and offset must be integers")
            return
        sliced = rows[offset_int : offset_int + limit_int] if limit_int is not None else rows[offset_int:]
        self.send_json({"count": total, "offset": offset_int, "returned": len(sliced), "results": sliced})

    def send_docs(self) -> None:
        manifest = self.server.manifest
        endpoint_items = "\n".join(f"<li><code>{html.escape(item)}</code></li>" for item in manifest["endpoints"])
        count_items = "\n".join(
            f"<li><code>{html.escape(key)}</code>: {value}</li>" for key, value in manifest["record_counts"].items()
        )
        body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Clerk Operations API</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.45; max-width: 920px; }}
    code {{ background: #f3f4f6; padding: 0.1rem 0.25rem; border-radius: 4px; }}
    h1, h2 {{ margin-top: 1.5rem; }}
  </style>
</head>
<body>
  <h1>Clerk Operations API</h1>
  <p>This local service exposes shared court clerk records, fee schedules, payment policies, docket entries, hearings, and stale exports.</p>
  <h2>Endpoints</h2>
  <ul>{endpoint_items}</ul>
  <h2>Generated Counts</h2>
  <ul>{count_items}</ul>
  <p>Use live endpoints and export dates to resolve conflicts. The service does not expose task IDs, answer keys, or scoring rubrics.</p>
</body>
</html>
"""
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = (json.dumps(payload, indent=2, sort_keys=False) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)

    def send_error_json(self, status: HTTPStatus, message: str) -> None:
        self.send_json({"error": message, "status": int(status)}, status=status)

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write(f"{self.address_string()} - - [{self.log_date_time_string()}] {format % args}\n")


def build_server(host: str, port: int) -> ThreadingHTTPServer:
    ensure_data()
    dataset = load_json(DATA_FILE)
    manifest = load_json(MANIFEST_FILE)
    server = ThreadingHTTPServer((host, port), ClerkOpsHandler)
    server.dataset = dataset
    server.manifest = manifest
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the clerk operations HTTP API.")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind. Default: 0.0.0.0")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind. Default: 8000")
    args = parser.parse_args()
    server = build_server(args.host, args.port)
    print(f"Clerk operations API listening on http://{args.host}:{args.port}", flush=True)
    print("Open /docs for endpoint documentation.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
