#!/usr/bin/env python3
"""Small CLI for the Atlas Commerce workplace API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Optional


DEFAULT_BASE_URL = "http://task-env:9022/"


def normalize_base_url(value: Optional[str]) -> str:
    base = (value or os.environ.get("TASK_ENV_BASE_URL") or DEFAULT_BASE_URL).strip()
    if not base:
        raise SystemExit("No base URL supplied. Set TASK_ENV_BASE_URL or pass --base-url.")
    return base.rstrip("/")


def request_json(base_url: str, method: str, path: str, payload: Optional[object] = None) -> object:
    token = os.environ.get("TASK_ENV_API_TOKEN")
    if not token:
        raise SystemExit("TASK_ENV_API_TOKEN is not set")

    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Request failed: {exc}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def read_text_arg_or_stdin(value: Optional[str]) -> str:
    if value:
        return value
    return sys.stdin.read()


def read_json_file_or_stdin(path: Optional[str]) -> object:
    if path and path != "-":
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.load(sys.stdin)


def emit(value: object, compact: bool) -> None:
    if compact:
        print(json.dumps(value, separators=(",", ":"), ensure_ascii=False))
    else:
        print(json.dumps(value, indent=2, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Atlas task environment base URL")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("schema", help="GET /api/schema")
    sub.add_parser("dictionary", help="GET /api/data-dictionary")
    sub.add_parser("audit", help="GET /api/correction-audit")

    sql_parser = sub.add_parser("sql", help="POST /api/sql with {'sql': ...}")
    sql_parser.add_argument("sql", nargs="?", help="SQL string; stdin is used if omitted")

    txn_parser = sub.add_parser("transaction", help="POST raw JSON to /api/sql/transaction")
    txn_parser.add_argument("json_file", nargs="?", help="Transaction JSON file; stdin if omitted or '-'")

    args = parser.parse_args()
    base_url = normalize_base_url(args.base_url)

    if args.command == "schema":
        result = request_json(base_url, "GET", "/api/schema")
    elif args.command == "dictionary":
        result = request_json(base_url, "GET", "/api/data-dictionary")
    elif args.command == "audit":
        result = request_json(base_url, "GET", "/api/correction-audit")
    elif args.command == "sql":
        sql = read_text_arg_or_stdin(args.sql).strip()
        if not sql:
            raise SystemExit("SQL is empty")
        result = request_json(base_url, "POST", "/api/sql", {"sql": sql})
    elif args.command == "transaction":
        payload = read_json_file_or_stdin(args.json_file)
        result = request_json(base_url, "POST", "/api/sql/transaction", payload)
    else:
        raise SystemExit(f"Unhandled command: {args.command}")

    emit(result, args.compact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
