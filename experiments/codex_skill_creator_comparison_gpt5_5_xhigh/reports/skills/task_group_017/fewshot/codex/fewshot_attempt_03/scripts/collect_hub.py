#!/usr/bin/env python3
"""Collect matter-filtered Investigation Review Hub records.

This script uses only the public hub API. It prefers POST /api/query so document
search caps do not hide relevant rows, then falls back to GET endpoints.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


TABLES = {
    "matters": "matter_id",
    "subpoena_categories": "category_code",
    "production_stats": "category_code, batch_id",
    "custodian_sources": "source_id",
    "review_documents": "doc_id",
    "privilege_entries": "entry_id",
    "qc_findings": "finding_id",
    "retention_events": "event_id",
    "remediation_actions": "action_id",
}

GET_ENDPOINTS = {
    "matters": "/api/matters",
    "subpoena_categories": "/api/subpoena-categories",
    "production_stats": "/api/productions",
    "custodian_sources": "/api/custodian-sources",
    "review_documents": "/api/documents/search",
    "privilege_entries": "/api/privilege-log",
    "qc_findings": "/api/qc-findings",
    "retention_events": "/api/retention-events",
    "remediation_actions": "/api/remediation-actions",
}


def request_json(method: str, url: str, headers: dict[str, str], body: dict | None = None) -> dict:
    data = None
    req_headers = dict(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc


def join_url(base_url: str, path: str) -> str:
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "matter"


def query_table(base_url: str, headers: dict[str, str], table: str, matter_id: str) -> list[dict]:
    order_by = TABLES[table]
    sql = (
        f"SELECT * FROM {table} "
        f"WHERE matter_id = {sql_literal(matter_id)} "
        f"ORDER BY {order_by}"
    )
    payload = request_json("POST", join_url(base_url, "/api/query"), headers, {"sql": sql})
    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        raise RuntimeError(f"Unexpected query response for {table}: rows is not a list")
    return rows


def get_table(base_url: str, headers: dict[str, str], table: str, matter_id: str) -> list[dict]:
    query = urllib.parse.urlencode({"matter_id": matter_id})
    payload = request_json("GET", join_url(base_url, f"{GET_ENDPOINTS[table]}?{query}"), headers)
    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        raise RuntimeError(f"Unexpected GET response for {table}: rows is not a list")
    return [row for row in rows if row.get("matter_id") == matter_id]


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Investigation Review Hub base URL")
    parser.add_argument("--matter-id", required=True, help="Matter ID to collect")
    parser.add_argument("--out", default=None, help="Output directory; defaults to hub_dump_<matter-id>")
    parser.add_argument("--api-key-header", default="X-API-Key", help="Header name for POST /api/query")
    parser.add_argument("--api-key", default="", help="Header value for POST /api/query when required")
    parser.add_argument("--prefer-get", action="store_true", help="Use GET endpoints before SQL query")
    args = parser.parse_args()

    headers = {}
    if args.api_key:
        headers[args.api_key_header] = args.api_key

    output_dir = Path(args.out or f"hub_dump_{safe_name(args.matter_id)}").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    schema = request_json("GET", join_url(args.base_url, "/api/schema"), headers)
    write_json(output_dir / "schema.json", schema)

    summary = {"matter_id": args.matter_id, "tables": {}}
    for table in TABLES:
        rows = None
        errors = []
        methods = ("get", "query") if args.prefer_get else ("query", "get")
        for method in methods:
            try:
                rows = (
                    get_table(args.base_url, headers, table, args.matter_id)
                    if method == "get"
                    else query_table(args.base_url, headers, table, args.matter_id)
                )
                break
            except Exception as exc:  # noqa: BLE001 - report both API fallbacks.
                errors.append(f"{method}: {exc}")
        if rows is None:
            print(f"[ERROR] {table}: {'; '.join(errors)}", file=sys.stderr)
            return 1
        write_json(output_dir / f"{table}.json", rows)
        summary["tables"][table] = {"row_count": len(rows), "file": f"{table}.json"}

    write_json(output_dir / "_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
