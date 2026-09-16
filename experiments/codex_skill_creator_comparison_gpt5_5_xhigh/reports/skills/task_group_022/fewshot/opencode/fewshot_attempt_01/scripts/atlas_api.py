#!/usr/bin/env python3
"""Small stdlib client for the Atlas task environment."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request


DEFAULT_BASE_URL = "http://task-env:9022"


def base_url() -> str:
    return os.environ.get("TASK_ENV_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def token() -> str:
    value = os.environ.get("TASK_ENV_API_TOKEN")
    if not value:
        raise SystemExit("TASK_ENV_API_TOKEN is not set")
    return value


def request(method: str, path: str, body: object | None = None) -> object:
    url = path if path.startswith("http://") or path.startswith("https://") else base_url() + path
    data = None
    headers = {
        "Authorization": f"Bearer {token()}",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {raw}") from exc
    return json.loads(raw)


def print_json(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the Atlas task environment")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("schema")
    sub.add_parser("dictionary")
    sub.add_parser("audit")

    sql_parser = sub.add_parser("sql")
    sql_parser.add_argument("sql")

    sql_file_parser = sub.add_parser("sql-file")
    sql_file_parser.add_argument("path")

    post_parser = sub.add_parser("post")
    post_parser.add_argument("path", help="API path such as /api/sql/transaction")
    post_parser.add_argument("json_file", help="JSON body to post")

    args = parser.parse_args()

    if args.command == "schema":
        print_json(request("GET", "/api/schema"))
    elif args.command == "dictionary":
        print_json(request("GET", "/api/data-dictionary"))
    elif args.command == "audit":
        print_json(request("GET", "/api/correction-audit"))
    elif args.command == "sql":
        print_json(request("POST", "/api/sql", {"sql": args.sql}))
    elif args.command == "sql-file":
        with open(args.path, "r", encoding="utf-8") as handle:
            sql = handle.read()
        print_json(request("POST", "/api/sql", {"sql": sql}))
    elif args.command == "post":
        with open(args.json_file, "r", encoding="utf-8") as handle:
            body = json.load(handle)
        print_json(request("POST", args.path, body))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
