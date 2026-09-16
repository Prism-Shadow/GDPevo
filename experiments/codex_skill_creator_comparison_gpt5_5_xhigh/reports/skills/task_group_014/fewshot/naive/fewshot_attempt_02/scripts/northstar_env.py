#!/usr/bin/env python3
"""Small helper for Northstar payer-operations environment calls."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def normalize_base_url(value: str) -> str:
    if not value:
        raise SystemExit("base URL is required")
    return value.rstrip("/") + "/"


def request_json(base_url: str, path: str, token: str | None, payload: dict | None = None) -> object:
    url = urllib.parse.urljoin(normalize_base_url(base_url), path.lstrip("/"))
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method="POST" if payload else "GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"request failed: {exc}") from exc
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return body.decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="Call allowed Northstar environment endpoints.")
    parser.add_argument("--base-url", default=os.getenv("TASK_ENV_BASE_URL") or os.getenv("NORTHSTAR_BASE_URL"))
    parser.add_argument("--token", default=os.getenv("NORTHSTAR_SQL_TOKEN") or os.getenv("TASK_ENV_TOKEN"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    sql_parser = subparsers.add_parser("sql", help="POST SQL to /sql/query using {'sql': ...}.")
    sql_parser.add_argument("sql")

    get_parser = subparsers.add_parser("get", help="GET an allowed business endpoint path.")
    get_parser.add_argument("path")

    args = parser.parse_args()
    if args.command == "sql":
        result = request_json(args.base_url, "/sql/query", args.token, {"sql": args.sql})
    else:
        result = request_json(args.base_url, args.path, args.token)
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
