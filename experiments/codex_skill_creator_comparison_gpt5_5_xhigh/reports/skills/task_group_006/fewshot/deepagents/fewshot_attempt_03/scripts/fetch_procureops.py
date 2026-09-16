#!/usr/bin/env python3
"""Fetch allowed ProcureOps endpoints into one normalized JSON snapshot."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request


ENDPOINTS = [
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


def endpoint_key(endpoint: str) -> str:
    return endpoint.strip("/").replace("/", "_") or "manifest"


def fetch_json(base_url: str, endpoint: str) -> object:
    url = base_url.rstrip("/") + endpoint
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def normalize(payload: object) -> object:
    if isinstance(payload, dict) and "results" in payload:
        return payload["results"]
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cache ProcureOps API records from the allowed endpoints."
    )
    parser.add_argument(
        "base_url",
        nargs="?",
        default=os.environ.get("TASK_ENV_BASE_URL"),
        help="ProcureOps base URL. Defaults to TASK_ENV_BASE_URL.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="procureops_snapshot.json",
        help="Path for the normalized JSON snapshot.",
    )
    args = parser.parse_args(argv)

    if not args.base_url:
        parser.error("base_url is required or TASK_ENV_BASE_URL must be set")

    snapshot = {}
    for endpoint in ENDPOINTS:
        payload = fetch_json(args.base_url, endpoint)
        snapshot[endpoint_key(endpoint)] = normalize(payload)

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, sort_keys=True)
        handle.write("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
