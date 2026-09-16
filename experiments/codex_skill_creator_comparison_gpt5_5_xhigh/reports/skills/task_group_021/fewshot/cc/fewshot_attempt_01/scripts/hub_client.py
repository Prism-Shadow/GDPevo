#!/usr/bin/env python3
"""Small generic client for Asteria Hub GET pagination and query calls."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


COMMON_ITEM_KEYS = (
    "data",
    "items",
    "results",
    "records",
    "rows",
    "transactions",
    "contacts",
    "events",
    "charges",
)


def parse_kv(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"Expected key=value, got {value!r}")
        key, item = value.split("=", 1)
        parsed[key] = item
    return parsed


def make_url(base_url: str, path_or_url: str, params: dict[str, Any] | None = None) -> str:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        url = path_or_url
    else:
        url = base_url.rstrip("/") + "/" + path_or_url.lstrip("/")
    if params:
        separator = "&" if urllib.parse.urlparse(url).query else "?"
        url = url + separator + urllib.parse.urlencode(params)
    return url


def request_json(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: Any | None = None,
) -> Any:
    data = None
    req_headers = dict(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} for {url}: {detail}") from exc
    if not body.strip():
        return None
    return json.loads(body)


def item_list(response: Any, key: str | None = None) -> list[Any]:
    if isinstance(response, list):
        return response
    if not isinstance(response, dict):
        return []
    if key:
        value = response.get(key)
        return value if isinstance(value, list) else []
    for candidate in COMMON_ITEM_KEYS:
        value = response.get(candidate)
        if isinstance(value, list):
            return value
    return []


def next_url(response: Any) -> str | None:
    if not isinstance(response, dict):
        return None
    for key in ("next", "next_url"):
        value = response.get(key)
        if isinstance(value, str) and value:
            return value
    links = response.get("links")
    if isinstance(links, dict):
        value = links.get("next")
        if isinstance(value, str) and value:
            return value
    return None


def paged_get(args: argparse.Namespace, headers: dict[str, str]) -> Any:
    params = parse_kv(args.param)
    if not args.paginate:
        return request_json("GET", make_url(args.base_url, args.path, params), headers)

    all_items: list[Any] = []
    offset = int(params.get(args.offset_param, "0"))
    limit = int(params.get(args.limit_param, str(args.limit)))
    seen_urls: set[str] = set()
    current_url = make_url(
        args.base_url,
        args.path,
        {**params, args.offset_param: offset, args.limit_param: limit},
    )

    while current_url and current_url not in seen_urls:
        seen_urls.add(current_url)
        response = request_json("GET", current_url, headers)
        batch = item_list(response, args.items_key)
        if batch:
            all_items.extend(batch)
        follow = next_url(response)
        if follow:
            current_url = make_url(args.base_url, follow)
            continue
        if not batch or len(batch) < limit:
            break
        offset += limit
        current_url = make_url(
            args.base_url,
            args.path,
            {**params, args.offset_param: offset, args.limit_param: limit},
        )
    return all_items


def run_query(args: argparse.Namespace, headers: dict[str, str]) -> Any:
    sql = args.sql
    if args.sql_file:
        with open(args.sql_file, "r", encoding="utf-8") as handle:
            sql = handle.read()
    if not sql:
        raise SystemExit("Provide --sql or --sql-file")
    payload_key = args.payload_key
    return request_json(
        "POST",
        make_url(args.base_url, args.path),
        headers,
        {payload_key: sql},
    )


def write_output(data: Any, out_path: str | None) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    else:
        print(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", help="Bearer token, if the environment_access file supplies one.")
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        help="Extra HTTP header as Name=Value. Use this for API-key style auth.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    get_parser = subparsers.add_parser("get", help="GET an endpoint, optionally with pagination.")
    get_parser.add_argument("path")
    get_parser.add_argument("--param", action="append", default=[], help="Query parameter as key=value.")
    get_parser.add_argument("--paginate", action="store_true")
    get_parser.add_argument("--limit", type=int, default=500)
    get_parser.add_argument("--limit-param", default="limit")
    get_parser.add_argument("--offset-param", default="offset")
    get_parser.add_argument("--items-key", help="Response key containing item list.")
    get_parser.add_argument("--out")

    query_parser = subparsers.add_parser("query", help="POST SQL to the Hub query endpoint.")
    query_parser.add_argument("--path", default="/api/query")
    query_parser.add_argument("--sql")
    query_parser.add_argument("--sql-file")
    query_parser.add_argument("--payload-key", default="query")
    query_parser.add_argument("--out")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    headers = parse_kv(args.header)
    if args.token:
        headers.setdefault("Authorization", f"Bearer {args.token}")

    if args.command == "get":
        result = paged_get(args, headers)
        write_output(result, args.out)
    elif args.command == "query":
        result = run_query(args, headers)
        write_output(result, args.out)
    else:
        parser.error("unknown command")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
