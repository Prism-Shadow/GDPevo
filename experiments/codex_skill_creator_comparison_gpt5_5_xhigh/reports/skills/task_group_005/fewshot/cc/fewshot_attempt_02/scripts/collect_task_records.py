#!/usr/bin/env python3
"""Collect scoped task_group ERP/compliance API records.

This helper intentionally fetches only caller-supplied IDs. It does not solve a
task by itself; use it to gather current records before applying SKILL.md rules.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request


def get_json(base_url: str, path: str, params: dict[str, str] | None = None) -> object:
    url = base_url.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.load(response)


def collection_data(payload: object) -> list[dict]:
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    if isinstance(payload, list):
        return payload
    return []


def fetch_collection_all(base_url: str, path: str, params: dict[str, str] | None = None) -> list[dict]:
    params = dict(params or {})
    params.setdefault("limit", "100")
    offset = int(params.get("offset", "0"))
    rows: list[dict] = []
    while True:
        params["offset"] = str(offset)
        payload = get_json(base_url, path, params)
        page = collection_data(payload)
        rows.extend(page)
        if not isinstance(payload, dict):
            break
        total = payload.get("total")
        count = payload.get("count", len(page))
        if total is None or offset + int(count) >= int(total) or not page:
            break
        offset += int(count)
    return rows


def fetch_claims(base_url: str, claim_ids: list[str]) -> dict[str, object]:
    claims: dict[str, object] = {}
    bills: dict[str, list[dict]] = {}
    payments: dict[str, list[dict]] = {}
    for claim_id in claim_ids:
        try:
            claims[claim_id] = get_json(base_url, f"/api/claims/{urllib.parse.quote(claim_id)}")
        except Exception:
            rows = fetch_collection_all(base_url, "/api/claims", {"claim_id": claim_id})
            claims[claim_id] = rows[0] if rows else None
        bills[claim_id] = fetch_collection_all(base_url, "/api/ap/bills", {"claim_id": claim_id})
        for bill in bills[claim_id]:
            bill_id = str(bill.get("bill_id", ""))
            if bill_id:
                payments[bill_id] = fetch_collection_all(base_url, "/api/ap/payments", {"bill_id": bill_id})
    return {"claims": claims, "bills_by_claim": bills, "payments_by_bill": payments}


def fetch_businesses(base_url: str, business_ids: list[str]) -> dict[str, object]:
    result: dict[str, object] = {}
    for business_id in business_ids:
        objects = fetch_collection_all(base_url, "/api/compliance/objects", {"business_id": business_id})
        obj = objects[0] if objects else {}
        vendor_id = obj.get("vendor_id") if isinstance(obj, dict) else None
        vendors = fetch_collection_all(base_url, "/api/vendors", {"vendor_id": str(vendor_id)}) if vendor_id else []
        result[business_id] = {
            "compliance_object": obj,
            "ownership": get_json(base_url, f"/api/compliance/ownership/{urllib.parse.quote(business_id)}"),
            "registry": get_json(base_url, f"/api/compliance/registry/{urllib.parse.quote(business_id)}"),
            "screening": get_json(base_url, f"/api/compliance/screening/{urllib.parse.quote(business_id)}"),
            "bank": get_json(base_url, f"/api/compliance/bank/{urllib.parse.quote(business_id)}"),
            "vendor": vendors[0] if vendors else None,
        }
    return {"businesses": result}


def fetch_prepaids(base_url: str, invoice_ids: list[str], entity: str | None, period: str | None) -> dict[str, object]:
    invoices: dict[str, object] = {}
    for invoice_id in invoice_ids:
        rows = fetch_collection_all(base_url, "/api/prepaids/invoices", {"prepaid_invoice_id": invoice_id})
        invoices[invoice_id] = rows[0] if rows else None
    params: dict[str, str] = {}
    if entity:
        params["entity"] = entity
    if period:
        params["period"] = period
    gl_rows = fetch_collection_all(base_url, "/api/prepaids/gl-balances", params)
    return {"invoices": invoices, "gl_balances": gl_rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    claims = subparsers.add_parser("claims")
    claims.add_argument("claim_ids", nargs="+")

    businesses = subparsers.add_parser("businesses")
    businesses.add_argument("business_ids", nargs="+")

    prepaids = subparsers.add_parser("prepaids")
    prepaids.add_argument("invoice_ids", nargs="+")
    prepaids.add_argument("--entity")
    prepaids.add_argument("--period")

    args = parser.parse_args()
    if args.mode == "claims":
        output = fetch_claims(args.base_url, args.claim_ids)
    elif args.mode == "businesses":
        output = fetch_businesses(args.base_url, args.business_ids)
    elif args.mode == "prepaids":
        output = fetch_prepaids(args.base_url, args.invoice_ids, args.entity, args.period)
    else:
        parser.error("unknown mode")
    json.dump(output, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
