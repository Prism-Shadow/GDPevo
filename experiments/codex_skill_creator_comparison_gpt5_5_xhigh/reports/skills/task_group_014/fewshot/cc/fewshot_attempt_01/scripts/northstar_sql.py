#!/usr/bin/env python3
"""Run a targeted SQL query against the Northstar task environment."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def run_sql(base_url: str, token: str, sql: str) -> dict:
    if not sql.strip():
        raise ValueError("SQL must be non-empty")

    body = json.dumps({"sql": sql}).encode("utf-8")
    request = urllib.request.Request(
        normalize_base_url(base_url) + "/sql/query",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run SQL against the Northstar task environment and print JSON."
    )
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument(
        "--token",
        default="pa-review-token-014",
        help="Bearer token for POST /sql/query",
    )
    parser.add_argument("--sql", help="SQL string. If omitted, read SQL from stdin.")
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON instead of pretty JSON.",
    )
    args = parser.parse_args()

    sql = args.sql if args.sql is not None else sys.stdin.read()

    try:
        result = run_sql(args.base_url, args.token, sql)
    except (ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"northstar_sql: {exc}", file=sys.stderr)
        return 1

    if args.compact:
        print(json.dumps(result, separators=(",", ":")))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
