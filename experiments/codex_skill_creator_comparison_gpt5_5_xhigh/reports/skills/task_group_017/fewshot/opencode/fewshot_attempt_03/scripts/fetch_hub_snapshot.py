#!/usr/bin/env python3
"""Fetch a matter-scoped Investigation Review Hub snapshot via /api/query."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


PREFERRED_ORDER = {
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

LISTISH_FIELDS = {
    "topic_tags",
    "category_impacts",
    "issue_tags",
    "affected_categories",
}


def request_json(url: str, method: str = "GET", body: dict[str, Any] | None = None, api_key: str | None = None) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach {url}: {exc.reason}") from exc


def split_listish(value: Any) -> Any:
    if value is None or isinstance(value, list):
        return value
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return []
    if stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
    return [part.strip() for part in stripped.split(",") if part.strip()]


def parsed_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for key in LISTISH_FIELDS:
        if key in row:
            out[f"{key}_parsed"] = split_listish(row[key])
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Investigation Review Hub base URL")
    parser.add_argument("--matter-id", required=True, help="Matter ID to fetch")
    parser.add_argument("--api-key", default=os.environ.get("HUB_API_KEY") or os.environ.get("REVIEW_HUB_API_KEY"))
    parser.add_argument("--out", default="hub_snapshot.json", help="Output JSON path")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/") + "/"
    schema = request_json(urllib.parse.urljoin(base_url, "api/schema"), api_key=args.api_key)

    tables: dict[str, Any] = {}
    for table in schema.get("tables", []):
        table_name = table.get("table")
        columns = [col.get("name") for col in table.get("columns", [])]
        if not table_name or "matter_id" not in columns:
            continue
        order_by = PREFERRED_ORDER.get(table_name, "matter_id")
        sql = f"select * from {table_name} where matter_id = :matter_id order by {order_by}"
        result = request_json(
            urllib.parse.urljoin(base_url, "api/query"),
            method="POST",
            body={"sql": sql, "params": {"matter_id": args.matter_id}},
            api_key=args.api_key,
        )
        rows = result.get("rows", [])
        tables[table_name] = {
            "columns": result.get("columns", columns),
            "row_count": result.get("row_count", len(rows)),
            "truncated": result.get("truncated", False),
            "rows": rows,
            "parsed_rows": [parsed_row(row) for row in rows],
        }

    snapshot = {
        "matter_id": args.matter_id,
        "base_url": base_url,
        "schema": schema,
        "tables": tables,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
