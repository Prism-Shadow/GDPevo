#!/usr/bin/env python3
"""Fetch all standard Investigation Review Hub rows for one matter."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


TABLES = [
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


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def post_query(
    base_url: str, sql: str, api_key: str | None, api_key_header: str
) -> dict:
    url = base_url.rstrip("/") + "/api/query"
    payload = json.dumps({"sql": sql}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers[api_key_header] = api_key
    request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"query failed for SQL {sql!r}: {exc.code} {body}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--matter-id", required=True)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--api-key-header", default="X-API-Key")
    args = parser.parse_args()

    matter = sql_quote(args.matter_id)
    output: dict[str, object] = {"matter_id": args.matter_id, "tables": {}}
    for table in TABLES:
        sql = f"SELECT * FROM {table} WHERE matter_id = {matter} ORDER BY 1"
        result = post_query(args.base_url, sql, args.api_key, args.api_key_header)
        if "error" in result:
            raise RuntimeError(f"{table}: {result['error']}")
        output["tables"][table] = result.get("rows", [])

    json.dump(output, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
