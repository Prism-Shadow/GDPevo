#!/usr/bin/env python3
"""Fetch task API endpoints with exact-match params and pagination."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


def parse_params(items: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--param must be key=value, got: {item}")
        key, value = item.split("=", 1)
        if not key:
            raise SystemExit(f"--param has an empty key: {item}")
        params[key] = value
    return params


def request_json(base_url: str, endpoint: str, params: dict[str, Any]) -> Any:
    base = base_url.rstrip("/") + "/"
    path = endpoint.lstrip("/")
    url = urljoin(base, path)
    if params:
        url = f"{url}?{urlencode(params)}"
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_all(base_url: str, endpoint: str, params: dict[str, str], page_size: int) -> Any:
    first_params: dict[str, Any] = dict(params)
    first_params.setdefault("limit", page_size)
    first_params.setdefault("offset", 0)
    first = request_json(base_url, endpoint, first_params)
    if not isinstance(first, dict) or "data" not in first:
        return first
    if not isinstance(first.get("data"), list):
        return first

    rows = list(first["data"])
    total = first.get("total")
    limit = int(first.get("limit") or page_size)
    offset = int(first.get("offset") or 0)

    while isinstance(total, int) and len(rows) < total:
        offset += limit
        page_params: dict[str, Any] = dict(params)
        page_params["limit"] = limit
        page_params["offset"] = offset
        page = request_json(base_url, endpoint, page_params)
        page_rows = page.get("data", []) if isinstance(page, dict) else []
        if not page_rows:
            break
        rows.extend(page_rows)

    result = dict(first)
    result["data"] = rows
    result["count"] = len(rows)
    result["offset"] = 0
    result["limit"] = len(rows)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("TASK_ENV_BASE_URL"))
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--param", action="append", default=[], help="Exact-match key=value filter")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--output", help="Write JSON to this file instead of stdout")
    args = parser.parse_args()

    if not args.base_url:
        raise SystemExit("Provide --base-url or set TASK_ENV_BASE_URL")

    data = fetch_all(args.base_url, args.endpoint, parse_params(args.param), args.page_size)
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
