#!/usr/bin/env python3
"""Fetch and optionally search the read-only ProcureOps API."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import urlopen


ENDPOINTS = {
    "manifest": "/manifest",
    "suppliers": "/suppliers",
    "items": "/items",
    "programs": "/programs",
    "contracts": "/contracts",
    "purchase_requisitions": "/purchase_requisitions",
    "purchase_orders": "/purchase_orders",
    "receipts": "/receipts",
    "ap_invoices": "/ap/invoices",
    "ap_payments": "/ap/payments",
    "approvals": "/approvals",
    "budget_snapshots": "/budget_snapshots",
    "vendor_risk_events": "/vendor_risk_events",
}

ID_FIELDS = {
    "supplier_id",
    "sku",
    "program_id",
    "contract_id",
    "requisition_id",
    "po_id",
    "receipt_id",
    "invoice_id",
    "payment_id",
    "event_id",
    "snapshot_id",
    "object_id",
    "related_object_id",
}


def fetch_json(base_url: str, path: str) -> Any:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    try:
        with urlopen(url, timeout=20) as response:
            return json.load(response)
    except HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code} fetching {url}: {exc.reason}") from exc
    except URLError as exc:
        raise SystemExit(f"Error fetching {url}: {exc.reason}") from exc


def fetch_all(base_url: str) -> dict[str, Any]:
    data: dict[str, Any] = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "endpoints": {},
    }
    for name, path in ENDPOINTS.items():
        payload = fetch_json(base_url, path)
        if isinstance(payload, dict) and isinstance(payload.get("results"), list):
            data["endpoints"][name] = payload["results"]
        else:
            data["endpoints"][name] = payload
    return data


def contains_id(value: Any, wanted: set[str]) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in ID_FIELDS and isinstance(nested, str) and nested in wanted:
                return True
            if contains_id(nested, wanted):
                return True
        return False
    if isinstance(value, list):
        return any(contains_id(item, wanted) for item in value)
    return isinstance(value, str) and value in wanted


def find_matches(data: dict[str, Any], ids: list[str]) -> dict[str, list[Any]]:
    wanted = set(ids)
    matches: dict[str, list[Any]] = {}
    for endpoint, records in data["endpoints"].items():
        if not isinstance(records, list):
            continue
        selected = [record for record in records if contains_id(record, wanted)]
        if selected:
            matches[endpoint] = selected
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Task ProcureOps base URL, for example http://host:9006/")
    parser.add_argument("--out", help="Write the full fetched data to this JSON path")
    parser.add_argument(
        "--id",
        action="append",
        default=[],
        help="Record ID to search for after fetching all endpoints. Repeat as needed.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Print the full fetched data to stdout instead of only ID matches or a summary.",
    )
    args = parser.parse_args()

    data = fetch_all(args.base_url)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")

    if args.full:
        json.dump(data, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    if args.id:
        json.dump(find_matches(data, args.id), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    summary = {
        endpoint: len(records) if isinstance(records, list) else "object"
        for endpoint, records in data["endpoints"].items()
    }
    json.dump({"record_counts": summary}, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
