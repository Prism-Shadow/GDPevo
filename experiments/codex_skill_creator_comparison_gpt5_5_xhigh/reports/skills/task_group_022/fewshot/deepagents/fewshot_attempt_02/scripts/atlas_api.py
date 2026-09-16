#!/usr/bin/env python3
"""Small CLI for the Atlas Commerce Operations task API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://task-env:9022/"


def _read_text_arg(value: str | None) -> str:
    if value is None or value == "-":
        return sys.stdin.read()
    path = Path(value)
    if path.exists():
        return path.read_text()
    return value


def _base_url(args: argparse.Namespace) -> str:
    return args.base_url or os.environ.get("TASK_ENV_BASE_URL") or DEFAULT_BASE_URL


def _request(
    method: str,
    base_url: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    headers = {"Accept": "application/json"}
    data = None

    token = os.environ.get("TASK_ENV_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(body or str(exc), file=sys.stderr)
        raise SystemExit(exc.code)
    except urllib.error.URLError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)

    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body


def _print_json(value: Any) -> None:
    if isinstance(value, str):
        print(value)
    else:
        print(json.dumps(value, indent=2, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Task environment base URL.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("schema", help="Fetch /api/schema.")
    subparsers.add_parser("dictionary", help="Fetch /api/data-dictionary.")
    subparsers.add_parser("audit", help="Fetch /api/correction-audit.")

    sql_parser = subparsers.add_parser("sql", help="POST SQL to /api/sql.")
    sql_parser.add_argument("sql", nargs="?", help="SQL text, SQL file path, or stdin.")

    tx_parser = subparsers.add_parser(
        "transaction",
        help="POST a JSON transaction payload to /api/sql/transaction.",
    )
    tx_parser.add_argument(
        "payload",
        nargs="?",
        help="JSON text, JSON file path, or stdin. The payload is sent unchanged.",
    )

    args = parser.parse_args()
    base_url = _base_url(args)

    if args.command == "schema":
        result = _request("GET", base_url, "/api/schema")
    elif args.command == "dictionary":
        result = _request("GET", base_url, "/api/data-dictionary")
    elif args.command == "audit":
        result = _request("GET", base_url, "/api/correction-audit")
    elif args.command == "sql":
        sql = _read_text_arg(args.sql).strip()
        if not sql:
            print("SQL is empty", file=sys.stderr)
            return 2
        result = _request("POST", base_url, "/api/sql", {"sql": sql})
    elif args.command == "transaction":
        raw_payload = _read_text_arg(args.payload).strip()
        if not raw_payload:
            print("transaction payload is empty", file=sys.stderr)
            return 2
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            print(f"invalid transaction JSON: {exc}", file=sys.stderr)
            return 2
        result = _request("POST", base_url, "/api/sql/transaction", payload)
    else:
        parser.error("unknown command")

    _print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
