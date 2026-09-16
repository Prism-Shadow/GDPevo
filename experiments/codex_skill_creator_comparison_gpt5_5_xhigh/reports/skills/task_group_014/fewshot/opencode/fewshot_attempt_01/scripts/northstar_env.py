#!/usr/bin/env python3
"""Small HTTP helper for Northstar task environments."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


def emit(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def request_json(base_url: str, path: str, *, method: str = "GET", token: str | None = None, body: Any = None) -> Any:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} for {url}: {detail}") from exc
    except URLError as exc:
        raise SystemExit(f"Request failed for {url}: {exc.reason}") from exc

    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Query a Northstar payer-operations task environment.")
    parser.add_argument("--base-url", default=os.environ.get("TASK_ENV_BASE_URL"), help="Environment base URL.")
    parser.add_argument("--token", default=os.environ.get("SQL_BEARER_TOKEN"), help="Bearer token for SQL queries.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("tables", help="GET /api/tables.")

    get_parser = sub.add_parser("get", help="GET an API path such as /api/cases/CASE-ID.")
    get_parser.add_argument("path")

    sql_parser = sub.add_parser("sql", help="POST a SQL query to /sql/query.")
    sql_parser.add_argument("query")

    args = parser.parse_args()
    if not args.base_url:
        parser.error("--base-url or TASK_ENV_BASE_URL is required")

    if args.command == "tables":
        emit(request_json(args.base_url, "/api/tables"))
    elif args.command == "get":
        emit(request_json(args.base_url, args.path))
    elif args.command == "sql":
        if not args.token:
            parser.error("--token or SQL_BEARER_TOKEN is required for sql")
        emit(request_json(args.base_url, "/sql/query", method="POST", token=args.token, body={"query": args.query}))
    else:
        parser.error(f"unknown command {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
