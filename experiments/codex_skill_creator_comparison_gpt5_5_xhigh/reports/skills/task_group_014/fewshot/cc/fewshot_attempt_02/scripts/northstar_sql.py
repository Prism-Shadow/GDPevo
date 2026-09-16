#!/usr/bin/env python3
"""Small SQL/API helper for Northstar payer-operations tasks."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def normalize_base_url(base_url: str) -> str:
    base_url = base_url.strip()
    if not base_url:
        raise ValueError("base URL is required")
    return base_url if base_url.endswith("/") else base_url + "/"


def request_json(url: str, method: str = "GET", token: str | None = None, body: dict | None = None) -> dict:
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the Northstar task environment.")
    parser.add_argument("--base-url", default=os.environ.get("TASK_ENV_BASE_URL") or os.environ.get("NORTHSTAR_BASE_URL"))
    parser.add_argument("--token", default=os.environ.get("SQL_BEARER_TOKEN") or os.environ.get("NORTHSTAR_SQL_TOKEN"))
    parser.add_argument("--raw", action="store_true", help="print compact JSON instead of indented JSON")

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--sql", help="SQL string to submit to POST /sql/query")
    source.add_argument("--file", type=Path, help="file containing SQL to submit")
    source.add_argument("--tables", action="store_true", help="GET /api/tables")

    args = parser.parse_args()
    if not args.base_url:
        parser.error("--base-url or TASK_ENV_BASE_URL is required")

    base_url = normalize_base_url(args.base_url)
    if args.tables:
        result = request_json(base_url + "api/tables")
    else:
        if not args.token:
            parser.error("--token or SQL_BEARER_TOKEN is required for SQL")
        sql = args.sql if args.sql is not None else args.file.read_text(encoding="utf-8")
        if not sql.strip():
            parser.error("SQL must be non-empty")
        result = request_json(base_url + "sql/query", method="POST", token=args.token, body={"sql": sql})

    if args.raw:
        print(json.dumps(result, separators=(",", ":")))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"northstar_sql.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
