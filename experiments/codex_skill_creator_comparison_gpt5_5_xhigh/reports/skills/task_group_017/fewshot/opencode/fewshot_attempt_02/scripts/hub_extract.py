#!/usr/bin/env python3
"""Extract a matter-scoped Investigation Review Hub bundle as JSON."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


TABLES = {
    "matters": "matter_id, name, agency, investigation_type, issued_date, hold_date, lead_partner, description, status",
    "subpoena_categories": "category_code",
    "production_stats": "category_code, batch_id",
    "custodian_sources": "source_id",
    "review_documents": "doc_id",
    "privilege_entries": "entry_id",
    "qc_findings": "finding_id",
    "retention_events": "event_id",
    "remediation_actions": "action_id",
}

LIST_FIELDS = {
    "affected_categories",
    "category_impacts",
    "issue_tags",
    "topic_tags",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Hub base URL, for example http://task-env:9017/")
    parser.add_argument("--matter-id", required=True, help="Matter ID to extract")
    parser.add_argument("--api-key", default=os.environ.get("REVIEW_HUB_API_KEY"), help="Optional X-API-Key for /api/query")
    parser.add_argument("--output", "-o", help="Write bundle to this file instead of stdout")
    parser.add_argument("--no-schema", action="store_true", help="Skip GET /api/schema")
    return parser.parse_args()


def request_json(url: str, *, method: str = "GET", body: dict[str, Any] | None = None, api_key: str | None = None) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if api_key:
        headers["X-API-Key"] = api_key

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc


def join_url(base_url: str, path: str) -> str:
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return sorted({str(item).strip() for item in value if str(item).strip()})
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return normalize_list(parsed)
        except json.JSONDecodeError:
            pass
    for delimiter in ("|", ";", ","):
        if delimiter in text:
            return sorted({part.strip() for part in text.split(delimiter) if part.strip()})
    return [text]


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    for field in LIST_FIELDS:
        if field in row:
            normalized[f"{field}_list"] = normalize_list(row[field])
    return normalized


def query_table(base_url: str, api_key: str, table: str, order_by: str, matter_id: str) -> list[dict[str, Any]]:
    sql = f"SELECT * FROM {table} WHERE matter_id = {sql_quote(matter_id)} ORDER BY {order_by}"
    result = request_json(join_url(base_url, "/api/query"), method="POST", body={"sql": sql}, api_key=api_key)
    return [normalize_row(row) for row in result.get("rows", [])]


def fetch_with_get(base_url: str, table: str, matter_id: str) -> list[dict[str, Any]]:
    endpoint_by_table = {
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
    query = urllib.parse.urlencode({"matter_id": matter_id})
    result = request_json(join_url(base_url, endpoint_by_table[table] + "?" + query))
    rows = result.get("rows", result if isinstance(result, list) else [])
    return [normalize_row(row) for row in rows]


def build_bundle(args: argparse.Namespace) -> dict[str, Any]:
    bundle: dict[str, Any] = {"matter_id": args.matter_id, "tables": {}}
    if not args.no_schema:
        bundle["schema"] = request_json(join_url(args.base_url, "/api/schema"))

    for table, order_by in TABLES.items():
        if args.api_key:
            try:
                rows = query_table(args.base_url, args.api_key, table, order_by, args.matter_id)
            except RuntimeError:
                rows = fetch_with_get(args.base_url, table, args.matter_id)
        else:
            rows = fetch_with_get(args.base_url, table, args.matter_id)
        bundle["tables"][table] = rows
    return bundle


def main() -> int:
    args = parse_args()
    bundle = build_bundle(args)
    text = json.dumps(bundle, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
