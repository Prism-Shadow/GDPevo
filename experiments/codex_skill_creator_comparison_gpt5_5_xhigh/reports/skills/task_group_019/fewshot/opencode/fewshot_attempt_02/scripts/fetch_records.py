#!/usr/bin/env python3
"""Fetch JSON records from the licensing task API."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, List
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


def parse_params(items: List[str]) -> Dict[str, str]:
    params: Dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"invalid --param {item!r}; use key=value")
        key, value = item.split("=", 1)
        if not key:
            raise SystemExit(f"invalid --param {item!r}; empty key")
        params[key] = value
    return params


def endpoint_url(base_url: str, endpoint: str, params: Dict[str, str]) -> str:
    base = base_url.rstrip("/") + "/"
    path = endpoint.lstrip("/")
    url = urljoin(base, path)
    if params:
        url += "?" + urlencode(params)
    return url


def fetch_json(url: str):
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        payload = response.read().decode("utf-8")
        return json.loads(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("endpoints", nargs="+", help="GET endpoints such as /api/policies")
    parser.add_argument("--base-url", required=True, help="Task environment base URL")
    parser.add_argument("--limit", default=None, help="Add limit=N unless a limit param is already supplied")
    parser.add_argument("--param", action="append", default=[], help="Query parameter applied to all endpoints, as key=value")
    args = parser.parse_args()

    params = parse_params(args.param)
    if args.limit is not None and "limit" not in params:
        params["limit"] = args.limit

    responses = {}
    errors = {}
    for endpoint in args.endpoints:
        url = endpoint_url(args.base_url, endpoint, params)
        try:
            data = fetch_json(url)
            responses[endpoint] = {"url": url, "data": data}
        except Exception as exc:  # pragma: no cover - diagnostic path
            errors[endpoint] = {"url": url, "error": str(exc)}

    result = {"base_url": args.base_url, "responses": responses}
    if errors:
        result["errors"] = errors
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
