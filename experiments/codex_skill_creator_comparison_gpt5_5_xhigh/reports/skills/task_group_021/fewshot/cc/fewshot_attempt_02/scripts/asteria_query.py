#!/usr/bin/env python3
"""Small stdlib client for Asteria Fleet Data Quality Hub tasks."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def parse_access(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("- ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    if "base_url" not in values:
        raise SystemExit(f"base_url not found in {path}")
    return values


def parse_headers(items: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for item in items:
        if ":" not in item:
            raise SystemExit(f"header must be 'Name: value': {item}")
        name, value = item.split(":", 1)
        headers[name.strip()] = value.strip()
    return headers


def request_json(base_url: str, path: str, *, method: str = "GET",
                 payload: dict | None = None,
                 params: dict[str, str] | None = None,
                 headers: dict[str, str] | None = None) -> object:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    body = None
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, method=method, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"request failed for {url}: {exc}") from exc
    return json.loads(data)


def print_json(obj: object) -> None:
    print(json.dumps(obj, indent=2, sort_keys=False, ensure_ascii=False))


def base_and_headers(args: argparse.Namespace) -> tuple[str, dict[str, str]]:
    access = parse_access(args.access)
    headers = parse_headers(args.header or [])
    if getattr(args, "bearer", None):
        headers["Authorization"] = f"Bearer {args.bearer}"
    return access["base_url"], headers


def cmd_catalog(args: argparse.Namespace) -> None:
    base_url, headers = base_and_headers(args)
    print_json(request_json(base_url, "/api/catalog/collections", headers=headers))


def cmd_schema(args: argparse.Namespace) -> None:
    base_url, headers = base_and_headers(args)
    print_json(request_json(base_url, "/api/catalog/schema", headers=headers))


def cmd_get(args: argparse.Namespace) -> None:
    base_url, headers = base_and_headers(args)
    params: dict[str, str] = {}
    for item in args.param or []:
        if "=" not in item:
            raise SystemExit(f"param must be key=value: {item}")
        key, value = item.split("=", 1)
        params[key] = value
    print_json(request_json(base_url, args.path, params=params, headers=headers))


def cmd_query(args: argparse.Namespace) -> None:
    base_url, headers = base_and_headers(args)
    sql = args.sql
    if args.sql_file:
        sql = Path(args.sql_file).read_text(encoding="utf-8")
    if not sql:
        sql = sys.stdin.read()
    payload: dict[str, object] = {"sql": sql}
    print_json(request_json(base_url, "/api/query", method="POST", payload=payload, headers=headers))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--access", default="environment_access.md",
                        help="Path to environment_access.md")
    parser.add_argument("--header", action="append", default=[],
                        help="Extra HTTP header, e.g. 'X-Query-Token: value'")
    parser.add_argument("--bearer", help="Bearer token for Authorization header")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_late_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--access", default=argparse.SUPPRESS,
                       help="Path to environment_access.md")
        p.add_argument("--header", action="append", default=argparse.SUPPRESS,
                       help="Extra HTTP header, e.g. 'X-Query-Token: value'")
        p.add_argument("--bearer", default=argparse.SUPPRESS,
                       help="Bearer token for Authorization header")

    catalog = sub.add_parser("catalog", help="Fetch /api/catalog/collections")
    add_late_common(catalog)
    catalog.set_defaults(func=cmd_catalog)

    schema = sub.add_parser("schema", help="Fetch /api/catalog/schema")
    add_late_common(schema)
    schema.set_defaults(func=cmd_schema)

    get = sub.add_parser("get", help="GET an allowed API path")
    add_late_common(get)
    get.add_argument("path", help="Path such as /api/source-snapshots")
    get.add_argument("--param", action="append", default=[],
                     help="Query parameter as key=value")
    get.set_defaults(func=cmd_get)

    query = sub.add_parser("query", help="POST SQL to /api/query")
    add_late_common(query)
    query.add_argument("--sql", help="SQL string; stdin is used if omitted")
    query.add_argument("--sql-file", help="Read SQL from a file")
    query.set_defaults(func=cmd_query)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
