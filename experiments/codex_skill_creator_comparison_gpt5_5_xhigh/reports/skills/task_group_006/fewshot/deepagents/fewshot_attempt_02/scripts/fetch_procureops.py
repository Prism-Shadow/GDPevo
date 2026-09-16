#!/usr/bin/env python3
"""Fetch standard ProcureOps API collections into one JSON file.

The script uses only the Python standard library. It does not compute answers;
it gives a solver a stable local snapshot to inspect with jq or Python.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


DEFAULT_ENDPOINTS = [
    "/manifest",
    "/suppliers",
    "/items",
    "/programs",
    "/contracts",
    "/purchase_requisitions",
    "/purchase_orders",
    "/receipts",
    "/ap/invoices",
    "/ap/payments",
    "/approvals",
    "/budget_snapshots",
    "/vendor_risk_events",
]


def endpoint_key(path: str) -> str:
    return path.strip("/").replace("/", "_") or "root"


def fetch_json(base_url: str, path: str) -> object:
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Task environment base URL")
    parser.add_argument(
        "--endpoint",
        action="append",
        dest="endpoints",
        help="Endpoint path to fetch. Repeat to limit the default endpoint list.",
    )
    parser.add_argument(
        "--out",
        default="-",
        help="Output JSON path, or '-' for stdout. Default: stdout.",
    )
    args = parser.parse_args()

    endpoints = args.endpoints or DEFAULT_ENDPOINTS
    output = {"base_url": args.base_url.rstrip("/"), "endpoints": {}, "collections": {}}

    try:
        for path in endpoints:
            data = fetch_json(args.base_url, path)
            key = endpoint_key(path)
            output["endpoints"][key] = data
            if isinstance(data, dict) and isinstance(data.get("results"), list):
                output["collections"][key] = data["results"]
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"fetch_procureops.py: {exc}", file=sys.stderr)
        return 1

    text = json.dumps(output, indent=2, sort_keys=True)
    if args.out == "-":
        print(text)
    else:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
