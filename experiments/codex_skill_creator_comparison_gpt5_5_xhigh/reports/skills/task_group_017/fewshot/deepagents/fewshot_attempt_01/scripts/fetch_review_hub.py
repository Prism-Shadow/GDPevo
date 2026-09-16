#!/usr/bin/env python3
"""Fetch and matter-filter Investigation Review Hub endpoint data.

The script uses only the public Review Hub HTTP endpoints. It does not inspect
local environment files or databases. When an API key is provided, it prefers
the read-only SQL endpoint to avoid capped GET responses.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


ENDPOINTS = {
    "matters": "/api/matters",
    "subpoena_categories": "/api/subpoena-categories",
    "productions": "/api/productions",
    "custodian_sources": "/api/custodian-sources",
    "review_documents": "/api/documents/search",
    "privilege_log": "/api/privilege-log",
    "qc_findings": "/api/qc-findings",
    "retention_events": "/api/retention-events",
    "remediation_actions": "/api/remediation-actions",
}

SQL_TABLES = {
    "matters": "matters",
    "subpoena_categories": "subpoena_categories",
    "productions": "production_stats",
    "custodian_sources": "custodian_sources",
    "review_documents": "review_documents",
    "privilege_log": "privilege_entries",
    "qc_findings": "qc_findings",
    "retention_events": "retention_events",
    "remediation_actions": "remediation_actions",
}


def build_url(base_url: str, path: str, matter_id: str | None = None) -> str:
    base = base_url.rstrip("/") + "/"
    url = urllib.parse.urljoin(base, path.lstrip("/"))
    if matter_id:
        return f"{url}?{urllib.parse.urlencode({'matter_id': matter_id})}"
    return url


def request_json(url: str, headers: dict[str, str], timeout: float) -> Any:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def post_json(
    url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float
) -> Any:
    body = json.dumps(payload).encode("utf-8")
    request_headers = dict(headers)
    request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=request_headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def rows_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return [row for row in payload["rows"] if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def filter_rows(rows: list[dict[str, Any]], matter_id: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("matter_id") == matter_id]


def fetch_sql_table(
    base_url: str,
    table: str,
    matter_id: str,
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    payload = {
        "sql": f"select * from {table} where matter_id = ?",
        "params": [matter_id],
    }
    result = post_json(build_url(base_url, "/api/query"), payload, headers, timeout)
    rows = rows_from_payload(result)
    return {
        "source": "sql",
        "table": table,
        "matter_row_count": len(rows),
        "rows": rows,
    }


def fetch_endpoint(
    base_url: str,
    path: str,
    matter_id: str,
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    errors: list[str] = []
    for use_query in (True, False):
        url = build_url(base_url, path, matter_id if use_query else None)
        try:
            payload = request_json(url, headers, timeout)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append(f"{url}: {exc}")
            continue

        rows = filter_rows(rows_from_payload(payload), matter_id)
        if rows or not use_query:
            return {
                "endpoint": path,
                "source_row_count": len(rows_from_payload(payload)),
                "matter_row_count": len(rows),
                "rows": rows,
            }

    return {"endpoint": path, "error": "; ".join(errors), "rows": []}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch Review Hub data filtered to one matter ID."
    )
    parser.add_argument("base_url", help="Review Hub base URL")
    parser.add_argument("matter_id", help="Matter ID to filter")
    parser.add_argument(
        "--api-key",
        help="Optional value for the X-API-Key header when the task provides one",
    )
    parser.add_argument(
        "--no-sql",
        action="store_true",
        help="Do not use POST /api/query even when an API key is supplied",
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    headers = {"Accept": "application/json"}
    if args.api_key:
        headers["X-API-Key"] = args.api_key

    output: dict[str, Any] = {"matter_id": args.matter_id, "tables": {}}

    try:
        output["schema"] = request_json(
            build_url(args.base_url, "/api/schema"), headers, args.timeout
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        output["schema_error"] = str(exc)

    use_sql = bool(args.api_key) and not args.no_sql
    for name, path in ENDPOINTS.items():
        if use_sql:
            try:
                output["tables"][name] = fetch_sql_table(
                    args.base_url,
                    SQL_TABLES[name],
                    args.matter_id,
                    headers,
                    args.timeout,
                )
                continue
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                output.setdefault("sql_errors", {})[name] = str(exc)

        output["tables"][name] = fetch_endpoint(
            args.base_url, path, args.matter_id, headers, args.timeout
        )

    json.dump(output, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
