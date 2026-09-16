#!/usr/bin/env python3
"""Small Atlas Commerce API helper for skill users."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def base_url() -> str:
    return os.environ.get("TASK_ENV_BASE_URL", "http://task-env:9022").rstrip("/")


def token() -> str:
    value = os.environ.get("TASK_ENV_API_TOKEN")
    if not value:
        raise SystemExit("TASK_ENV_API_TOKEN is not set")
    return value


def request_json(path: str, payload: object | None = None) -> object:
    data = None
    headers = {"Authorization": f"Bearer {token()}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(base_url() + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {body}") from exc


def print_json(obj: object) -> None:
    print(json.dumps(obj, indent=2, sort_keys=False))


def read_text_arg(value: str | None, file_path: str | None) -> str:
    if value and file_path:
        raise SystemExit("Use either --sql/--json or --file, not both")
    if file_path:
        with open(file_path, "r", encoding="utf-8") as handle:
            return handle.read()
    if value:
        return value
    return sys.stdin.read()


def command_schema(_: argparse.Namespace) -> None:
    print_json(request_json("/api/schema"))


def command_dictionary(_: argparse.Namespace) -> None:
    print_json(request_json("/api/data-dictionary"))


def command_audit(_: argparse.Namespace) -> None:
    print_json(request_json("/api/correction-audit"))


def command_sql(args: argparse.Namespace) -> None:
    sql = read_text_arg(args.sql, args.file).strip()
    if not sql:
        raise SystemExit("No SQL supplied")
    print_json(request_json("/api/sql", {"sql": sql}))


def command_transaction(args: argparse.Namespace) -> None:
    text = read_text_arg(args.json, args.file).strip()
    if not text:
        raise SystemExit("No transaction JSON supplied")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid transaction JSON: {exc}") from exc
    print_json(request_json("/api/sql/transaction", payload))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("schema", help="GET /api/schema")
    p.set_defaults(func=command_schema)

    p = sub.add_parser("dictionary", help="GET /api/data-dictionary")
    p.set_defaults(func=command_dictionary)

    p = sub.add_parser("audit", help="GET /api/correction-audit")
    p.set_defaults(func=command_audit)

    p = sub.add_parser("sql", help="POST read-only SQL to /api/sql")
    p.add_argument("--sql", help="SQL string; defaults to stdin")
    p.add_argument("--file", help="File containing SQL")
    p.set_defaults(func=command_sql)

    p = sub.add_parser("transaction", help="POST raw JSON to /api/sql/transaction")
    p.add_argument("--json", help="Transaction JSON string; defaults to stdin")
    p.add_argument("--file", help="File containing transaction JSON")
    p.set_defaults(func=command_transaction)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
