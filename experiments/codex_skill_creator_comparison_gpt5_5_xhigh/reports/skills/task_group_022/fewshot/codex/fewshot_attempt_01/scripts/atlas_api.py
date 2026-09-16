#!/usr/bin/env python3
"""Small CLI for the Atlas Commerce Operations task API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_BASE_URL = "http://task-env:9022/"


def normalize_base_url(value: str | None) -> str:
    base = value or os.environ.get("TASK_ENV_BASE_URL") or DEFAULT_BASE_URL
    return base if base.endswith("/") else base + "/"


def read_text_arg(value: str | None, file_value: str | None) -> str:
    if value is not None:
        return value
    if file_value:
        return Path(file_value).read_text()
    data = sys.stdin.read()
    if not data.strip():
        raise SystemExit("expected SQL or JSON on stdin, or pass --sql/--file")
    return data


def request_json(method: str, base_url: str, path: str, token: str | None, body=None):
    url = base_url.rstrip("/") + path
    headers = {"Accept": "application/json"}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        print(raw or f"HTTP {exc.code}", file=sys.stderr)
        raise SystemExit(1) from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"request failed: {exc}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        print(raw, file=sys.stderr)
        raise SystemExit(f"response was not JSON: {exc}") from exc


def sql_rows_as_dicts(payload):
    columns = payload.get("columns")
    rows = payload.get("rows")
    if not isinstance(columns, list) or not isinstance(rows, list):
        raise SystemExit("SQL response does not contain columns and rows")
    converted = [dict(zip(columns, row)) for row in rows]
    result = dict(payload)
    result["rows"] = converted
    return result


def emit(payload, output: str | None):
    text = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    if output:
        Path(output).write_text(text)
    else:
        sys.stdout.write(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Override TASK_ENV_BASE_URL")
    parser.add_argument("--token-env", default="TASK_ENV_API_TOKEN")
    parser.add_argument("--no-auth", action="store_true", help="Send no bearer token")
    parser.add_argument("--output", help="Write response JSON to this file")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("schema", help="GET /api/schema")
    subparsers.add_parser("dictionary", help="GET /api/data-dictionary")
    subparsers.add_parser("audit", help="GET /api/correction-audit")

    sql_parser = subparsers.add_parser("sql", help="POST /api/sql")
    sql_parser.add_argument("--sql", help="SQL text to execute")
    sql_parser.add_argument("--file", help="Read SQL text from a file")
    sql_parser.add_argument("--dicts", action="store_true", help="Convert row arrays to objects")

    tx_parser = subparsers.add_parser("transaction", help="POST /api/sql/transaction")
    tx_parser.add_argument("--json", help="Transaction JSON body")
    tx_parser.add_argument("--file", help="Read transaction JSON body from a file")

    args = parser.parse_args()
    base_url = normalize_base_url(args.base_url)
    token = None if args.no_auth else os.environ.get(args.token_env)
    if not args.no_auth and not token:
        raise SystemExit(f"missing bearer token env var: {args.token_env}")

    if args.command == "schema":
        payload = request_json("GET", base_url, "/api/schema", token)
    elif args.command == "dictionary":
        payload = request_json("GET", base_url, "/api/data-dictionary", token)
    elif args.command == "audit":
        payload = request_json("GET", base_url, "/api/correction-audit", token)
    elif args.command == "sql":
        sql = read_text_arg(args.sql, args.file)
        payload = request_json("POST", base_url, "/api/sql", token, {"sql": sql})
        if args.dicts:
            payload = sql_rows_as_dicts(payload)
    elif args.command == "transaction":
        raw = read_text_arg(args.json, args.file)
        try:
            body = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"transaction body is not valid JSON: {exc}") from exc
        payload = request_json("POST", base_url, "/api/sql/transaction", token, body)
    else:
        raise SystemExit(f"unknown command: {args.command}")

    emit(payload, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
