#!/usr/bin/env python3
"""Small CLI for the Atlas Commerce Operations HTTP API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def first_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def base_url(value: str | None) -> str:
    value = value or first_env("GDPEVO_ENV_BASE_URL", "TASK_ENV_BASE_URL", "ATLAS_BASE_URL")
    if not value:
        raise SystemExit("Set GDPEVO_ENV_BASE_URL, TASK_ENV_BASE_URL, or ATLAS_BASE_URL.")
    return value.rstrip("/")


def auth_token(value: str | None) -> str:
    value = value or first_env("ATLAS_AUTH_TOKEN", "GDPEVO_AUTH_TOKEN", "TASK_ENV_AUTH_TOKEN")
    if not value:
        raise SystemExit("Set ATLAS_AUTH_TOKEN, GDPEVO_AUTH_TOKEN, or TASK_ENV_AUTH_TOKEN.")
    return value


def call_api(args: argparse.Namespace, method: str, path: str, body: object | None = None) -> object:
    url = base_url(args.base_url) + path
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Authorization": f"Bearer {auth_token(args.token)}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {url}: {detail}") from exc
    return json.loads(raw) if raw else None


def read_text_arg(value: str | None, file_path: str | None) -> str:
    if value is not None:
        return value
    if file_path:
        with open(file_path, "r", encoding="utf-8") as handle:
            return handle.read()
    return sys.stdin.read()


def print_json(value: object, raw: bool = False) -> None:
    if raw:
        print(json.dumps(value, separators=(",", ":")))
    else:
        print(json.dumps(value, indent=2, sort_keys=False))


def cmd_schema(args: argparse.Namespace) -> None:
    print_json(call_api(args, "GET", "/api/schema"), args.raw)


def cmd_dictionary(args: argparse.Namespace) -> None:
    print_json(call_api(args, "GET", "/api/data-dictionary"), args.raw)


def cmd_audit(args: argparse.Namespace) -> None:
    query = {}
    for key in ("entity_type", "entity_id", "source_row_id", "limit"):
        value = getattr(args, key)
        if value is not None:
            query[key] = value
    path = "/api/correction-audit"
    if query:
        path += "?" + urllib.parse.urlencode(query)
    print_json(call_api(args, "GET", path), args.raw)


def cmd_sql(args: argparse.Namespace) -> None:
    sql = read_text_arg(args.sql, args.file).strip()
    params = json.loads(args.params) if args.params else []
    print_json(call_api(args, "POST", "/api/sql", {"sql": sql, "params": params}), args.raw)


def cmd_transaction(args: argparse.Namespace) -> None:
    payload = json.loads(read_text_arg(None, args.file))
    print_json(call_api(args, "POST", "/api/sql/transaction", payload), args.raw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url")
    parser.add_argument("--token")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--raw", action="store_true", help="Print compact JSON.")
    subparsers = parser.add_subparsers(required=True)

    schema = subparsers.add_parser("schema")
    schema.set_defaults(func=cmd_schema)

    dictionary = subparsers.add_parser("dictionary")
    dictionary.set_defaults(func=cmd_dictionary)

    audit = subparsers.add_parser("audit")
    audit.add_argument("--entity-type")
    audit.add_argument("--entity-id")
    audit.add_argument("--source-row-id")
    audit.add_argument("--limit", type=int)
    audit.set_defaults(func=cmd_audit)

    sql = subparsers.add_parser("sql")
    sql.add_argument("--sql", help="SQL string. If omitted, read SQL from stdin.")
    sql.add_argument("--file", help="File containing SQL. Ignored when --sql is set.")
    sql.add_argument("--params", help="JSON array of SQL parameters.")
    sql.set_defaults(func=cmd_sql)

    transaction = subparsers.add_parser("transaction")
    transaction.add_argument("--file", help="JSON transaction payload. If omitted, read stdin.")
    transaction.set_defaults(func=cmd_transaction)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
