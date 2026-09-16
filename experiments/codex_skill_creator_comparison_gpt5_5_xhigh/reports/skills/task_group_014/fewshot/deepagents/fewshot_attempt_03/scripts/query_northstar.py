#!/usr/bin/env python3
"""Run SQL against a Northstar task environment.

This helper uses only Python's standard library. It sends {"sql": "..."} to
the environment SQL endpoint and prints the JSON response.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute a SQL query against a Northstar task environment."
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TASK_ENV_BASE_URL"),
        help="Environment base URL, for example http://task-env:9014",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("NORTHSTAR_SQL_TOKEN"),
        help="Bearer token for POST /sql/query. Defaults to NORTHSTAR_SQL_TOKEN.",
    )
    parser.add_argument(
        "--sql",
        help="SQL string. If omitted, SQL is read from standard input.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON response.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.base_url:
        print("error: --base-url or TASK_ENV_BASE_URL is required", file=sys.stderr)
        return 2

    sql = args.sql if args.sql is not None else sys.stdin.read()
    if not sql or not sql.strip():
        print("error: SQL must be a non-empty string", file=sys.stderr)
        return 2

    endpoint = args.base_url.rstrip("/") + "/sql/query"
    headers = {"Content-Type": "application/json"}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"sql": sql}).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(body or f"HTTP {exc.code}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"request failed: {exc}", file=sys.stderr)
        return 1

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        print(raw)
        return 0

    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
