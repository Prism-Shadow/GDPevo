#!/usr/bin/env python3
"""
ProcureOps API client for the shared task environment.

Usage:
    python3 procureops_client.py <base_url> <endpoint> [--ids <id1,id2,...>]

Prints the full endpoint result or filters by matching IDs.

Examples:
    python3 procureops_client.py http://task-env:9006 programs
    python3 procureops_client.py http://task-env:9006 purchase_orders --ids PO-AX17-4481,PO-AX17-4519
    python3 procureops_client.py http://task-env:9006 receipts --ids RCV-BLUE-14
"""

import json
import sys
import urllib.request
from typing import Optional

ENDPOINTS = [
    "manifest", "suppliers", "items", "programs", "contracts",
    "purchase_requisitions", "purchase_orders", "receipts",
    "ap/invoices", "ap/payments", "approvals", "budget_snapshots",
    "vendor_risk_events",
]


def fetch_endpoint(base_url: str, endpoint: str) -> dict:
    url = f"{base_url.rstrip('/')}/{endpoint}"
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode())


def filter_by_ids(data: dict, id_field: str, ids: set) -> dict:
    results = data.get("results", [])
    filtered = [r for r in results if r.get(id_field) in ids]
    return {"count": len(filtered), "results": filtered}


def id_field_for_endpoint(endpoint: str) -> str:
    mapping = {
        "suppliers": "supplier_id",
        "items": "sku",
        "programs": "program_id",
        "contracts": "contract_id",
        "purchase_requisitions": "requisition_id",
        "purchase_orders": "po_id",
        "receipts": "receipt_id",
        "ap/invoices": "invoice_id",
        "ap/payments": "payment_id",
        "approvals": "event_id",
        "budget_snapshots": "snapshot_id",
        "vendor_risk_events": "event_id",
    }
    return mapping.get(endpoint, "")


def find_by_foreign_key(data: dict, field: str, value: str) -> list:
   """Return all results where field matches value."""
   results = data.get("results", [])
   return [r for r in results if str(r.get(field, "")) == value]


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ProcureOps API client")
    parser.add_argument("base_url", help="Base URL, e.g. http://task-env:9006")
    parser.add_argument("endpoint", help=f"Endpoint: {', '.join(ENDPOINTS)}")
    parser.add_argument("--ids", help="Comma-separated IDs to filter by primary key")
    parser.add_argument("--by-field", nargs=2, metavar=("FIELD", "VALUE"),
                        help="Filter by any field, e.g. --by-field program_id PRG-AX17")
    parser.add_argument("--raw", action="store_true", help="Print raw JSON without formatting")
    args = parser.parse_args()

    data = fetch_endpoint(args.base_url, args.endpoint)

    if args.ids:
        id_set = set(args.ids.split(","))
        id_field = id_field_for_endpoint(args.endpoint)
        if id_field:
            data = filter_by_ids(data, id_field, id_set)
        else:
            print(f"Warning: no primary-key mapping for endpoint '{args.endpoint}'", file=sys.stderr)

    if args.by_field:
        field, value = args.by_field
        results = find_by_foreign_key(data, field, value)
        data = {"count": len(results), "results": results}

    indent = None if args.raw else 2
    print(json.dumps(data, indent=indent))


if __name__ == "__main__":
    main()
