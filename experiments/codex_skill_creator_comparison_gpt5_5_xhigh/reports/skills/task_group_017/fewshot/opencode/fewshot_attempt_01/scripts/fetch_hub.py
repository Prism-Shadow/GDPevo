#!/usr/bin/env python3
"""Collect Investigation Review Hub evidence for one matter.

The script uses only documented hub endpoints. It prefers POST /api/query when
available, then records GET endpoint responses as fallback context.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


GET_ENDPOINTS = {
    "matters": "/api/matters",
    "subpoena_categories": "/api/subpoena-categories",
    "productions": "/api/productions",
    "custodian_sources": "/api/custodian-sources",
    "documents": "/api/documents/search",
    "privilege_log": "/api/privilege-log",
    "qc_findings": "/api/qc-findings",
    "retention_events": "/api/retention-events",
    "remediation_actions": "/api/remediation-actions",
}


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(2)


def normalize_base_url(raw: str) -> str:
    if not raw:
        fail("base URL is required")
    return raw.rstrip("/") + "/"


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    url = urllib.parse.urljoin(base_url, path.lstrip("/"))
    data = None
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = resp.read().decode("utf-8")
    if not payload.strip():
        return None
    return json.loads(payload)


def safe_matter_id(matter_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.:-]+", matter_id):
        fail("matter_id contains characters that are unsafe for SQL helper use")
    return matter_id


def rows_from_query_response(response: Any) -> list[dict[str, Any]]:
    if response is None:
        return []
    if isinstance(response, list):
        return [row for row in response if isinstance(row, dict)]
    if not isinstance(response, dict):
        return []
    for key in ("rows", "results", "data"):
        rows = response.get(key)
        if isinstance(rows, list):
            if rows and isinstance(rows[0], dict):
                return rows
            columns = response.get("columns")
            if isinstance(columns, list):
                return [dict(zip(columns, row)) for row in rows if isinstance(row, list)]
            return []
    return []


def query_error(response: Any) -> str | None:
    if isinstance(response, dict):
        for key in ("error", "errors", "message"):
            value = response.get(key)
            if value:
                return str(value)
    return None


def query_table(
    base_url: str,
    table: str,
    matter_id: str,
    api_key: str | None,
) -> tuple[list[dict[str, Any]], str | None]:
    sql = f"SELECT * FROM {table} WHERE matter_id = '{matter_id}'"
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    errors: list[str] = []
    for key in ("sql", "query"):
        try:
            response = request_json(
                base_url,
                "/api/query",
                method="POST",
                body={key: sql},
                headers=headers,
            )
            error = query_error(response)
            if error:
                errors.append(f"{key}: {error}")
                continue
            return rows_from_query_response(response), None
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append(f"{key}: {exc}")
    return [], "; ".join(errors)


def fetch_endpoint(base_url: str, path: str, matter_id: str) -> tuple[Any, str | None]:
    query = urllib.parse.urlencode({"matter_id": matter_id})
    try:
        return request_json(base_url, f"{path}?{query}"), None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        return None, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Task environment base URL")
    parser.add_argument("matter_id", help="Matter ID to collect")
    parser.add_argument("--out", default="-", help="Output JSON path, or '-' for stdout")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("REVIEW_API_KEY", "review-key-017"),
        help="X-API-Key value for POST /api/query; use an empty string to omit",
    )
    parser.add_argument("--no-sql", action="store_true", help="Skip POST /api/query")
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    matter_id = safe_matter_id(args.matter_id)
    api_key = args.api_key or None

    warnings: list[str] = []
    try:
        schema = request_json(base_url, "/api/schema")
    except Exception as exc:  # noqa: BLE001 - command-line diagnostic
        schema = None
        warnings.append(f"/api/schema failed: {exc}")

    tables: dict[str, list[dict[str, Any]]] = {}
    if not args.no_sql and isinstance(schema, dict):
        for table_info in schema.get("tables", []):
            table = table_info.get("table") if isinstance(table_info, dict) else None
            if not table:
                continue
            rows, error = query_table(base_url, table, matter_id, api_key)
            tables[table] = rows
            if error:
                warnings.append(f"POST /api/query for {table} failed: {error}")

    endpoints: dict[str, Any] = {}
    for name, path in GET_ENDPOINTS.items():
        payload, error = fetch_endpoint(base_url, path, matter_id)
        endpoints[name] = payload
        if error:
            warnings.append(f"GET {path} failed: {error}")

    output = {
        "matter_id": matter_id,
        "schema": schema,
        "tables": tables,
        "endpoints": endpoints,
        "warnings": warnings,
    }

    text = json.dumps(output, indent=2, sort_keys=True)
    if args.out == "-":
        print(text)
    else:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.write("\n")
        print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
