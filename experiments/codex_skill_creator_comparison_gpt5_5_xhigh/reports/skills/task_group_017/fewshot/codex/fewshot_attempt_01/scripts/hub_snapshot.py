#!/usr/bin/env python3
"""Collect matter-scoped Investigation Review Hub rows through the query API."""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urljoin


TABLE_ORDER = [
    "matters",
    "subpoena_categories",
    "production_stats",
    "custodian_sources",
    "review_documents",
    "privilege_entries",
    "qc_findings",
    "retention_events",
    "remediation_actions",
]

ORDER_COLUMNS = {
    "matters": ["matter_id"],
    "subpoena_categories": ["category_code"],
    "production_stats": ["category_code", "batch_id"],
    "custodian_sources": ["source_id"],
    "review_documents": ["doc_id"],
    "privilege_entries": ["entry_id"],
    "qc_findings": ["finding_id"],
    "retention_events": ["event_id"],
    "remediation_actions": ["action_id"],
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Dump Investigation Review Hub rows for one matter as JSON.",
    )
    parser.add_argument("--base-url", required=True, help="Hub base URL")
    parser.add_argument("--matter-id", required=True, help="Matter ID to filter")
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional X-API-Key value for POST /api/query",
    )
    parser.add_argument(
        "--include-schema",
        action="store_true",
        help="Include GET /api/schema output in the snapshot",
    )
    return parser.parse_args()


def request_json(method, url, payload=None, api_key=None):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if api_key:
        headers["X-API-Key"] = api_key

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc


def sql_literal(value):
    if not re.fullmatch(r"[A-Za-z0-9_.:-]+", value):
        raise ValueError("matter-id contains characters outside the expected safe set")
    return "'" + value.replace("'", "''") + "'"


def query_table(base_url, table, matter_id, api_key):
    order_by = ", ".join(ORDER_COLUMNS.get(table, ["matter_id"]))
    sql = (
        f"select * from {table} "
        f"where matter_id = {sql_literal(matter_id)} "
        f"order by {order_by}"
    )
    result = request_json(
        "POST",
        urljoin(base_url, "/api/query"),
        {"sql": sql},
        api_key=api_key,
    )
    return {
        "columns": result.get("columns", []),
        "row_count": result.get("row_count", len(result.get("rows", []))),
        "rows": result.get("rows", []),
        "truncated": result.get("truncated", False),
    }


def main():
    args = parse_args()
    base_url = args.base_url.rstrip("/") + "/"

    snapshot = {
        "matter_id": args.matter_id,
        "source": "Investigation Review Hub POST /api/query",
        "tables": {},
    }

    if args.include_schema:
        snapshot["schema"] = request_json("GET", urljoin(base_url, "/api/schema"))

    for table in TABLE_ORDER:
        snapshot["tables"][table] = query_table(
            base_url,
            table,
            args.matter_id,
            args.api_key,
        )

    json.dump(snapshot, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
