#!/usr/bin/env python3
"""Small Atlas workplace API helper using only the Python standard library."""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


def _base_url() -> str:
    base = os.environ.get("TASK_ENV_BASE_URL", "http://task-env:9022/")
    return base if base.endswith("/") else base + "/"


def _read_text_arg(value: str) -> str:
    if value == "-":
        return sys.stdin.read()
    path = Path(value)
    if path.exists():
        return path.read_text()
    return value


def _request(method: str, path: str, body=None):
    data = None
    headers = {}
    token = os.environ.get("TASK_ENV_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    url = urljoin(_base_url(), path.lstrip("/"))
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req) as resp:
            payload = resp.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code} from {url}: {detail}", file=sys.stderr)
        raise SystemExit(1) from exc
    except URLError as exc:
        print(f"Request failed for {url}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return payload


def _print_json(value) -> None:
    if isinstance(value, str):
        print(value)
    else:
        print(json.dumps(value, indent=2, sort_keys=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Call the Atlas workplace API.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("schema", help="GET /api/schema")
    sub.add_parser("dictionary", help="GET /api/data-dictionary")
    sub.add_parser("audit", help="GET /api/correction-audit")

    sql_parser = sub.add_parser("sql", help="POST a read-only SQL query")
    sql_parser.add_argument("query", help="SQL text, a SQL file, or '-' for stdin")

    post_parser = sub.add_parser("post", help="POST an explicit JSON body")
    post_parser.add_argument("endpoint", help="Endpoint path such as /api/sql/transaction")
    post_parser.add_argument("body", help="JSON text, a JSON file, or '-' for stdin")

    args = parser.parse_args()

    if args.command == "schema":
        _print_json(_request("GET", "/api/schema"))
    elif args.command == "dictionary":
        _print_json(_request("GET", "/api/data-dictionary"))
    elif args.command == "audit":
        _print_json(_request("GET", "/api/correction-audit"))
    elif args.command == "sql":
        sql = _read_text_arg(args.query)
        _print_json(_request("POST", "/api/sql", {"sql": sql}))
    elif args.command == "post":
        raw = _read_text_arg(args.body)
        try:
            body = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"Invalid JSON body: {exc}", file=sys.stderr)
            return 2
        _print_json(_request("POST", args.endpoint, body))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
