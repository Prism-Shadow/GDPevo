#!/usr/bin/env python3
"""Read-only helper for task-environment JSON APIs."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


def get_json(base_url: str, endpoint: str, params: dict[str, str] | None = None) -> Any:
    endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    url = urljoin(base_url.rstrip("/") + "/", endpoint.lstrip("/"))
    if params:
        url = f"{url}?{urlencode(params)}"
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def collect_pages(base_url: str, endpoint: str, params: dict[str, str]) -> Any:
    limit = int(params.get("limit", "100"))
    offset = int(params.get("offset", "0"))
    all_rows: list[Any] = []
    first: dict[str, Any] | None = None

    while True:
        page_params = dict(params)
        page_params["limit"] = str(limit)
        page_params["offset"] = str(offset)
        payload = get_json(base_url, endpoint, page_params)
        if not isinstance(payload, dict) or "data" not in payload:
            return payload
        if first is None:
            first = dict(payload)
        rows = payload.get("data") or []
        all_rows.extend(rows)
        total = int(payload.get("total", len(all_rows)))
        offset += limit
        if len(all_rows) >= total or not rows:
            first["data"] = all_rows
            first["count"] = len(all_rows)
            first["offset"] = 0
            first["limit"] = len(all_rows)
            return first


def parse_filters(values: list[str]) -> dict[str, str]:
    filters: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"Filter must be key=value: {value}")
        key, raw = value.split("=", 1)
        filters[key] = raw
    return filters


def command_get(args: argparse.Namespace) -> Any:
    params = parse_filters(args.filter)
    if args.all_pages:
        return collect_pages(args.base_url, args.endpoint, params)
    return get_json(args.base_url, args.endpoint, params)


def command_batch(args: argparse.Namespace) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item_id in args.ids:
        params = {args.id_field: item_id}
        result[item_id] = collect_pages(args.base_url, args.endpoint, params)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task API base URL")
    subparsers = parser.add_subparsers(dest="command", required=True)

    get_parser = subparsers.add_parser("get", help="GET one endpoint")
    get_parser.add_argument("endpoint")
    get_parser.add_argument("--filter", action="append", default=[], help="Exact filter key=value")
    get_parser.add_argument("--all-pages", action="store_true")
    get_parser.set_defaults(func=command_get)

    batch_parser = subparsers.add_parser("batch", help="Fetch one collection once per ID")
    batch_parser.add_argument("endpoint")
    batch_parser.add_argument("id_field")
    batch_parser.add_argument("ids", nargs="+")
    batch_parser.set_defaults(func=command_batch)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    payload = args.func(args)
    json.dump(payload, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
