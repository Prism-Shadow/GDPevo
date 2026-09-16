#!/usr/bin/env python3
"""Bulk-fetch all ProcureOps endpoints into a single JSON file.

Usage:
  python3 fetch_data.py <BASE_URL> [--out data.json]

The output file contains one key per endpoint, each holding the full results
list from that endpoint. Load this file and filter in-process rather than
making repeated HTTP calls.
"""

import json
import sys
import urllib.request

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


def fetch_all(base_url: str) -> dict:
    """Fetch every endpoint and return a dict keyed by endpoint name."""
    base = base_url.rstrip("/")
    data = {}
    for ep in ENDPOINTS:
        url = f"{base}/{ep}"
        with urllib.request.urlopen(url) as resp:
            payload = json.loads(resp.read())
        # Normalize key: replace slash with underscore
        key = ep.replace("/", "_")
        data[key] = payload.get("results", [])
    return data


def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_data.py <BASE_URL> [--out data.json]")
        sys.exit(1)

    base_url = sys.argv[1]
    out_path = "procureops_data.json"

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--out" and i + 1 < len(args):
            out_path = args[i + 1]
            i += 2
        else:
            i += 1

    data = fetch_all(base_url)
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(data)} endpoint results to {out_path}")


if __name__ == "__main__":
    main()
