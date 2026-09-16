#!/usr/bin/env python3
"""Collect scoped records from the finance task API."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request


def api_get(base_url: str, path: str, **params):
    base = base_url.rstrip("/")
    query = {k: v for k, v in params.items() if v is not None}
    url = base + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.load(response)


def data_list(payload):
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    if isinstance(payload, list):
        return payload
    return [payload]


def first_or_none(payload):
    values = data_list(payload)
    return values[0] if values else None


def collect_claim(base_url: str, claim_id: str):
    claim_path = "/api/claims/" + urllib.parse.quote(claim_id, safe="")
    claim = api_get(base_url, claim_path)
    bills = data_list(api_get(base_url, "/api/ap/bills", claim_id=claim_id, limit=200))
    payments = {}
    for bill in bills:
        bill_id = bill.get("bill_id")
        if bill_id:
            payments[bill_id] = data_list(
                api_get(base_url, "/api/ap/payments", bill_id=bill_id, limit=200)
            )
    aging = data_list(api_get(base_url, "/api/ap/aging", claim_id=claim_id, limit=200))
    return {"claim": claim, "bills": bills, "payments_by_bill": payments, "aging": aging}


def collect_business(base_url: str, business_id: str):
    encoded = urllib.parse.quote(business_id, safe="")
    obj = first_or_none(
        api_get(base_url, "/api/compliance/objects", business_id=business_id, limit=20)
    )
    result = {
        "compliance_object": obj,
        "ownership": api_get(base_url, f"/api/compliance/ownership/{encoded}"),
        "registry": api_get(base_url, f"/api/compliance/registry/{encoded}"),
        "screening": api_get(base_url, f"/api/compliance/screening/{encoded}"),
        "bank": api_get(base_url, f"/api/compliance/bank/{encoded}"),
        "vendor": None,
    }
    vendor_id = obj.get("vendor_id") if isinstance(obj, dict) else None
    if vendor_id:
        result["vendor"] = first_or_none(
            api_get(base_url, "/api/vendors", vendor_id=vendor_id, limit=20)
        )
    return result


def collect_prepaid(base_url: str, invoice_id: str):
    return first_or_none(
        api_get(
            base_url,
            "/api/prepaids/invoices",
            prepaid_invoice_id=invoice_id,
            limit=20,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url")
    parser.add_argument("--claims", nargs="*", default=[])
    parser.add_argument("--businesses", nargs="*", default=[])
    parser.add_argument("--prepaids", nargs="*", default=[])
    parser.add_argument("--entity")
    parser.add_argument("--period")
    parser.add_argument("--accounts", nargs="*", default=[])
    parser.add_argument("--close-logs", action="store_true")
    args = parser.parse_args()

    out = {"claims": {}, "businesses": {}, "prepaids": {}, "gl_balances": {}, "close_logs": []}

    for claim_id in args.claims:
        out["claims"][claim_id] = collect_claim(args.base_url, claim_id)

    for business_id in args.businesses:
        out["businesses"][business_id] = collect_business(args.base_url, business_id)

    for invoice_id in args.prepaids:
        out["prepaids"][invoice_id] = collect_prepaid(args.base_url, invoice_id)

    if args.entity and args.period:
        for account in args.accounts:
            key = f"{args.entity}|{args.period}|{account}"
            out["gl_balances"][key] = first_or_none(
                api_get(
                    args.base_url,
                    "/api/prepaids/gl-balances",
                    entity=args.entity,
                    period=args.period,
                    account=account,
                    limit=20,
                )
            )

    if args.close_logs:
        out["close_logs"] = data_list(api_get(args.base_url, "/api/close/logs", limit=200))

    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
