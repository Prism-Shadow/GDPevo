#!/usr/bin/env python3
"""Fetch matter-scoped Investigation Review Hub evidence.

This helper intentionally performs collection only. The solver still decides
materiality, classification, metrics, and final JSON assembly from the task's
answer template.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


TABLES = {
    "matters": "matter_id",
    "subpoena_categories": "category_code",
    "production_stats": "batch_id",
    "custodian_sources": "source_id",
    "review_documents": "doc_id",
    "privilege_entries": "entry_id",
    "qc_findings": "finding_id",
    "retention_events": "event_id",
    "remediation_actions": "action_id",
}

REST_ENDPOINTS = {
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

LIST_FIELDS = {
    "affected_categories",
    "category_impacts",
    "issue_tags",
    "topic_tags",
}


def request_json(url: str, *, headers: dict[str, str] | None = None, body: dict[str, Any] | None = None) -> Any:
    data = None
    req_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=req_headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def split_list(value: Any) -> Any:
    if isinstance(value, str):
        if not value:
            return []
        return [part.strip() for part in value.split(",") if part.strip()]
    return value


def normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        item = dict(row)
        for field in LIST_FIELDS:
            if field in item:
                item[field] = split_list(item[field])
        normalized.append(item)
    return normalized


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def fetch_schema(base_url: str) -> Any:
    return request_json(urllib.parse.urljoin(base_url, "/api/schema"))


def fetch_sql(base_url: str, api_key: str | None, matter_id: str, table: str, order_key: str) -> dict[str, Any]:
    url = urllib.parse.urljoin(base_url, "/api/query")
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    sql = (
        f"select * from {table} "
        f"where matter_id = {sql_literal(matter_id)} "
        f"order by {order_key}"
    )
    payload = request_json(url, headers=headers, body={"sql": sql})
    rows = normalize_rows(payload.get("rows", []))
    return {
        "source": "sql",
        "row_count": payload.get("row_count", len(rows)),
        "truncated": payload.get("truncated", False),
        "rows": rows,
    }


def fetch_rest(base_url: str, matter_id: str, table: str) -> dict[str, Any]:
    endpoint = REST_ENDPOINTS[table]
    url = urllib.parse.urljoin(base_url, endpoint)
    sep = "&" if "?" in url else "?"
    if table != "matters":
        url = f"{url}{sep}{urllib.parse.urlencode({'matter_id': matter_id})}"
    payload = request_json(url)
    rows = payload.get("rows", [])
    if table == "matters":
        rows = [row for row in rows if row.get("matter_id") == matter_id]
    rows = normalize_rows(rows)
    return {
        "source": "rest",
        "row_count": len(rows),
        "truncated": payload.get("count", len(rows)) > len(rows),
        "rows": rows,
    }


def collect(base_url: str, matter_id: str, api_key: str | None, rest_only: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "matter_id": matter_id,
        "base_url": base_url,
        "fetched_at_utc": _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "schema": None,
        "tables": {},
        "errors": {},
    }
    try:
        result["schema"] = fetch_schema(base_url)
    except Exception as exc:  # pragma: no cover - diagnostic path
        result["errors"]["schema"] = str(exc)

    for table, order_key in TABLES.items():
        try:
            if rest_only:
                raise RuntimeError("rest-only mode")
            result["tables"][table] = fetch_sql(base_url, api_key, matter_id, table, order_key)
        except Exception as sql_exc:
            try:
                result["tables"][table] = fetch_rest(base_url, matter_id, table)
                result["tables"][table]["sql_error"] = str(sql_exc)
            except Exception as rest_exc:  # pragma: no cover - diagnostic path
                result["errors"][table] = {
                    "sql_error": str(sql_exc),
                    "rest_error": str(rest_exc),
                }
                result["tables"][table] = {"source": "none", "row_count": 0, "truncated": False, "rows": []}
    return result


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matter_id", help="Matter ID from the task prompt")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TASK_ENV_BASE_URL", "http://task-env:9017/"),
        help="Investigation Review Hub base URL",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("REVIEW_HUB_API_KEY", ""),
        help="X-API-Key for POST /api/query; omit with --api-key '' if unavailable",
    )
    parser.add_argument("--out", default=None, help="Output JSON path")
    parser.add_argument("--rest-only", action="store_true", help="Skip POST /api/query and use REST endpoints")
    args = parser.parse_args(argv)

    base_url = args.base_url if args.base_url.endswith("/") else args.base_url + "/"
    api_key = args.api_key or None
    evidence = collect(base_url, args.matter_id, api_key, args.rest_only)

    out_path = args.out or f"hub_evidence_{args.matter_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"wrote {out_path}")
    for table, payload in evidence["tables"].items():
        print(f"{table}: {payload.get('row_count', 0)} rows via {payload.get('source')}")
    if evidence["errors"]:
        print("errors:", json.dumps(evidence["errors"], sort_keys=True), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
