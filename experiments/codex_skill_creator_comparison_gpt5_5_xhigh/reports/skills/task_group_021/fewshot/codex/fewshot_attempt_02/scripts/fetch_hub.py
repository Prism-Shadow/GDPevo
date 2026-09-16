#!/usr/bin/env python3
"""Fetch all pages from an Asteria Data Quality Hub REST endpoint."""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def read_base_url(env_path):
    text = Path(env_path).read_text()
    for line in text.splitlines():
        if line.strip().startswith("base_url:"):
            return line.split(":", 1)[1].strip().rstrip("/")
    raise ValueError(f"base_url not found in {env_path}")


def parse_params(raw_params):
    params = {}
    for raw in raw_params:
        if "=" not in raw:
            raise ValueError(f"Invalid --param {raw!r}; expected key=value")
        key, value = raw.split("=", 1)
        params[key] = value
    return params


def fetch_pages(base_url, endpoint, params, page_limit):
    endpoint = "/" + endpoint.lstrip("/")
    offset = 0
    items = []
    while True:
        query = dict(params)
        query["limit"] = str(page_limit)
        query["offset"] = str(offset)
        url = f"{base_url}{endpoint}?{urllib.parse.urlencode(query)}"
        with urllib.request.urlopen(url) as response:
            payload = json.load(response)
        if "error" in payload:
            raise RuntimeError(f"{url}: {payload['error']}")
        page_items = payload.get("items")
        if not isinstance(page_items, list):
            raise RuntimeError(f"{url}: response did not contain an items list")
        items.extend(page_items)
        limit = int(payload.get("limit", page_limit))
        total = int(payload.get("total", len(items)))
        offset += limit
        if offset >= total:
            return {"items": items, "total": total}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default="environment_access.md", help="Path to environment_access.md")
    parser.add_argument("--endpoint", required=True, help="REST endpoint, for example /api/contacts")
    parser.add_argument("--param", action="append", default=[], help="Query parameter as key=value")
    parser.add_argument("--limit", type=int, default=100, help="Page limit to request")
    parser.add_argument("--out", help="Write JSON to this path instead of stdout")
    args = parser.parse_args()

    try:
        base_url = read_base_url(args.env)
        params = parse_params(args.param)
        payload = fetch_pages(base_url, args.endpoint, params, args.limit)
    except Exception as exc:
        print(f"fetch_hub.py: {exc}", file=sys.stderr)
        return 1

    output = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(output + "\n")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
