#!/usr/bin/env python3
"""Fetch a ProcureOps API snapshot using only the public read endpoints."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


ENDPOINTS = [
    ("manifest", "/manifest"),
    ("suppliers", "/suppliers"),
    ("items", "/items"),
    ("programs", "/programs"),
    ("contracts", "/contracts"),
    ("purchase_requisitions", "/purchase_requisitions"),
    ("purchase_orders", "/purchase_orders"),
    ("receipts", "/receipts"),
    ("ap_invoices", "/ap/invoices"),
    ("ap_payments", "/ap/payments"),
    ("approvals", "/approvals"),
    ("budget_snapshots", "/budget_snapshots"),
    ("vendor_risk_events", "/vendor_risk_events"),
]


def urljoin(base_url: str, path: str) -> str:
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def fetch_json(url: str, timeout: float) -> object:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="ProcureOps API base URL, for example http://task-env:9006/")
    parser.add_argument(
        "output",
        nargs="?",
        help="Path to write the snapshot JSON. Omit to print to stdout.",
    )
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout in seconds")
    args = parser.parse_args()

    snapshot: dict[str, object] = {"base_url": args.base_url, "endpoints": {}}
    errors: dict[str, str] = {}

    for key, path in ENDPOINTS:
        url = urljoin(args.base_url, path)
        try:
            snapshot["endpoints"][key] = fetch_json(url, args.timeout)  # type: ignore[index]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            errors[key] = f"{type(exc).__name__}: {exc}"

    if errors:
        snapshot["errors"] = errors

    encoded = json.dumps(snapshot, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.write("\n")
    else:
        print(encoded)

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
