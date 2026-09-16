#!/usr/bin/env python3
"""Fetch a ProcureOps read-only API snapshot for reconciliation tasks."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


ENDPOINTS = [
    "manifest",
    "suppliers",
    "items",
    "programs",
    "contracts",
    "purchase_requisitions",
    "purchase_orders",
    "receipts",
    "ap/invoices",
    "ap/payments",
    "approvals",
    "budget_snapshots",
    "vendor_risk_events",
]


def fetch_json(base_url: str, endpoint: str, timeout: float) -> object:
    url = f"{base_url.rstrip('/')}/{endpoint}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed to fetch {url}: {exc}") from exc
    return json.loads(payload)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch all allowed ProcureOps read-only endpoints into one JSON file."
    )
    parser.add_argument("--base-url", required=True, help="ProcureOps API base URL.")
    parser.add_argument("--out", help="Output JSON path. Defaults to stdout.")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    snapshot = {}
    for endpoint in ENDPOINTS:
        key = endpoint.replace("/", "_")
        snapshot[key] = fetch_json(args.base_url, endpoint, args.timeout)

    output = json.dumps(snapshot, indent=2, sort_keys=True)
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output + "\n", encoding="utf-8")
    else:
        sys.stdout.write(output + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
