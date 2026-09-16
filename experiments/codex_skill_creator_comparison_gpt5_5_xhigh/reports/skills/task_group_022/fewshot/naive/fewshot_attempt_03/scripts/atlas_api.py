#!/usr/bin/env python3
"""Small Atlas Commerce Operations API helper using only the Python standard library."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def read_payload(value: str | None, file_path: str | None) -> object:
    if file_path:
        with open(file_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    if value:
        return json.loads(value)
    return json.load(sys.stdin)


def read_sql(sql: str | None, file_path: str | None) -> str:
    if file_path:
        with open(file_path, "r", encoding="utf-8") as handle:
            return handle.read()
    if sql:
        return sql
    return sys.stdin.read()


def bearer(token: str) -> str:
    return token if token.lower().startswith("bearer ") else f"Bearer {token}"


def call_api(base_url: str, token: str, method: str, path: str, payload: object | None = None) -> object:
    url = base_url.rstrip("/") + path
    headers = {"Authorization": bearer(token)}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} {exc.reason}: {detail}") from exc
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="Call the Atlas Commerce Operations task API.")
    parser.add_argument("--base-url", default=os.getenv("TASK_ENV_BASE_URL") or os.getenv("ATLAS_BASE_URL"))
    parser.add_argument(
        "--token",
        default=os.getenv("ATLAS_API_TOKEN")
        or os.getenv("TASK_ENV_API_TOKEN")
        or os.getenv("BUSINESS_API_TOKEN"),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health")
    subparsers.add_parser("schema")
    subparsers.add_parser("dictionary")
    subparsers.add_parser("audit")

    sql_parser = subparsers.add_parser("sql")
    sql_parser.add_argument("sql", nargs="?")
    sql_parser.add_argument("--file")

    post_parser = subparsers.add_parser("post")
    post_parser.add_argument("path")
    post_parser.add_argument("json_payload", nargs="?")
    post_parser.add_argument("--file")

    args = parser.parse_args()
    if not args.base_url:
        raise SystemExit("Missing --base-url or TASK_ENV_BASE_URL/ATLAS_BASE_URL")
    if not args.token:
        raise SystemExit("Missing --token or ATLAS_API_TOKEN/TASK_ENV_API_TOKEN/BUSINESS_API_TOKEN")

    if args.command == "health":
        result = call_api(args.base_url, args.token, "GET", "/health")
    elif args.command == "schema":
        result = call_api(args.base_url, args.token, "GET", "/api/schema")
    elif args.command == "dictionary":
        result = call_api(args.base_url, args.token, "GET", "/api/data-dictionary")
    elif args.command == "audit":
        result = call_api(args.base_url, args.token, "GET", "/api/correction-audit")
    elif args.command == "sql":
        result = call_api(args.base_url, args.token, "POST", "/api/sql", {"sql": read_sql(args.sql, args.file)})
    elif args.command == "post":
        path = args.path if args.path.startswith("/") else "/" + args.path
        result = call_api(args.base_url, args.token, "POST", path, read_payload(args.json_payload, args.file))
    else:
        parser.error(f"unknown command: {args.command}")

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
