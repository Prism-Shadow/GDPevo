#!/usr/bin/env python3
"""Fetch a matter-scoped Investigation Review Hub snapshot via the public API."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


def request_json(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, body: dict | None = None) -> dict:
    data = None
    req_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} for {url}: {detail}") from exc


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch matter-scoped Hub rows for answer drafting.")
    parser.add_argument("--base-url", required=True, help="Investigation Review Hub base URL, for example http://task-env:9017")
    parser.add_argument("--matter-id", required=True, help="Matter ID to filter on.")
    parser.add_argument("--api-key", default=None, help="Optional X-API-Key value for POST /api/query.")
    parser.add_argument("--output", default="-", help="Output JSON path, or '-' for stdout.")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    headers = {}
    if args.api_key:
        headers["X-API-Key"] = args.api_key

    schema = request_json(f"{base_url}/api/schema")
    snapshot = {
        "matter_id": args.matter_id,
        "schema": schema,
        "tables": {},
    }

    for table_info in schema.get("tables", []):
        table = table_info.get("table")
        columns = [column.get("name") for column in table_info.get("columns", [])]
        if not table or "matter_id" not in columns:
            continue
        sql = f"select * from {table} where matter_id = {sql_literal(args.matter_id)}"
        result = request_json(
            f"{base_url}/api/query",
            method="POST",
            headers=headers,
            body={"sql": sql},
        )
        snapshot["tables"][table] = result.get("rows", [])

    text = json.dumps(snapshot, indent=2, sort_keys=True)
    if args.output == "-":
        print(text)
    else:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
