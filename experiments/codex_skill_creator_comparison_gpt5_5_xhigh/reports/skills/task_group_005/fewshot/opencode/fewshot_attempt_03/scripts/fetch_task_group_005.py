#!/usr/bin/env python3
"""Fetch filtered task_group_005 ERP/compliance API snapshots.

The script is intentionally read-only and dependency-free. It writes one JSON
file containing only records requested by IDs or exact filters.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


FALLBACKS = {
    "endpoints": ["/endpoints"],
    "claims": ["/api/claims", "/claims"],
    "bills": ["/api/ap/bills", "/bills"],
    "payments": ["/api/ap/payments", "/payments"],
    "aging": ["/api/ap/aging"],
    "vendors": ["/api/vendors", "/vendors"],
    "close_logs": ["/api/close/logs", "/close/logs"],
    "compliance_objects": ["/api/compliance/objects", "/compliance/objects"],
    "prepaid_invoices": ["/api/prepaids/invoices", "/prepaids/invoices"],
    "gl_balances": ["/api/prepaids/gl-balances", "/gl/balances"],
}


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/"


def make_url(base_url: str, path: str, params: dict[str, Any] | None = None) -> str:
    url = urllib.parse.urljoin(base_url, path.lstrip("/"))
    if params:
        clean = {k: v for k, v in params.items() if v not in (None, "", [])}
        if clean:
            url += "?" + urllib.parse.urlencode(clean, doseq=True)
    return url


def fetch_json(base_url: str, path: str, params: dict[str, Any] | None = None) -> Any:
    url = make_url(base_url, path, params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_first(base_url: str, paths: list[str], params: dict[str, Any] | None = None) -> Any:
    last_error: Exception | None = None
    for path in paths:
        try:
            return fetch_json(base_url, path, params)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last_error = exc
    raise RuntimeError(f"all endpoint fallbacks failed: {paths}: {last_error}")


def fetch_paginated(
    base_url: str,
    paths: list[str],
    params: dict[str, Any] | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    total: int | None = None
    params = dict(params or {})

    while total is None or offset < total:
        page_params = dict(params)
        page_params.update({"limit": limit, "offset": offset})
        payload = fetch_first(base_url, paths, page_params)
        if not isinstance(payload, dict) or "data" not in payload:
            return payload if isinstance(payload, list) else [payload]
        data = payload.get("data", [])
        rows.extend(data)
        count = int(payload.get("count", len(data)))
        total = int(payload.get("total", len(rows)))
        if count == 0:
            break
        offset += count
    return rows


def add_list(values: list[str] | None) -> list[str]:
    return sorted(set(values or []))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--out", help="Write snapshot JSON to this path. Defaults to stdout.")
    parser.add_argument("--claim", action="append", help="Claim ID to fetch. Repeatable.")
    parser.add_argument("--business", action="append", help="Business ID to fetch. Repeatable.")
    parser.add_argument("--vendor", action="append", help="Vendor ID to fetch. Repeatable.")
    parser.add_argument("--prepaid", action="append", help="Prepaid invoice ID to fetch. Repeatable.")
    parser.add_argument("--account", action="append", help="GL account to fetch. Repeatable.")
    parser.add_argument("--period", help="GL/close period filter, such as YYYY-MM.")
    parser.add_argument("--entity", help="GL entity filter.")
    parser.add_argument("--skip-close-logs", action="store_true")
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    snapshot: dict[str, Any] = {"base_url": base_url}
    vendor_ids = set(add_list(args.vendor))

    try:
        snapshot["endpoints"] = fetch_first(base_url, FALLBACKS["endpoints"])
    except Exception as exc:
        snapshot["endpoints_error"] = str(exc)

    claims_by_id: dict[str, Any] = {}
    bills_by_claim: dict[str, Any] = {}
    aging_by_claim: dict[str, Any] = {}
    payments_by_bill: dict[str, Any] = {}

    for claim_id in add_list(args.claim):
        claims_by_id[claim_id] = fetch_paginated(base_url, FALLBACKS["claims"], {"claim_id": claim_id})
        bills = fetch_paginated(base_url, FALLBACKS["bills"], {"claim_id": claim_id})
        bills_by_claim[claim_id] = bills
        aging_by_claim[claim_id] = fetch_paginated(base_url, FALLBACKS["aging"], {"claim_id": claim_id})
        for row in claims_by_id[claim_id]:
            if row.get("vendor_id"):
                vendor_ids.add(row["vendor_id"])
        for bill in bills:
            if bill.get("vendor_id"):
                vendor_ids.add(bill["vendor_id"])
            bill_id = bill.get("bill_id")
            if bill_id and bill_id not in payments_by_bill:
                payments_by_bill[bill_id] = fetch_paginated(base_url, FALLBACKS["payments"], {"bill_id": bill_id})

    if claims_by_id:
        snapshot["claims_by_id"] = claims_by_id
        snapshot["ap_bills_by_claim"] = bills_by_claim
        snapshot["ap_aging_by_claim"] = aging_by_claim
        snapshot["payments_by_bill"] = payments_by_bill

    compliance_by_business: dict[str, Any] = {}
    for business_id in add_list(args.business):
        obj = fetch_paginated(base_url, FALLBACKS["compliance_objects"], {"business_id": business_id})
        compliance_by_business[business_id] = {"object": obj}
        if obj and obj[0].get("vendor_id"):
            vendor_ids.add(obj[0]["vendor_id"])
        for label, path in {
            "ownership": f"/api/compliance/ownership/{business_id}",
            "registry": f"/api/compliance/registry/{business_id}",
            "screening": f"/api/compliance/screening/{business_id}",
            "bank": f"/api/compliance/bank/{business_id}",
        }.items():
            try:
                compliance_by_business[business_id][label] = fetch_json(base_url, path)
            except Exception as exc:
                compliance_by_business[business_id][label + "_error"] = str(exc)
    if compliance_by_business:
        snapshot["compliance_by_business"] = compliance_by_business

    prepaid_by_id: dict[str, Any] = {}
    for prepaid_id in add_list(args.prepaid):
        prepaid_by_id[prepaid_id] = fetch_paginated(
            base_url,
            FALLBACKS["prepaid_invoices"],
            {"prepaid_invoice_id": prepaid_id},
        )
    if prepaid_by_id:
        snapshot["prepaid_invoices_by_id"] = prepaid_by_id

    gl_balances: list[dict[str, Any]] = []
    for account in add_list(args.account):
        params = {"account": account, "period": args.period, "entity": args.entity}
        gl_balances.extend(fetch_paginated(base_url, FALLBACKS["gl_balances"], params))
    if gl_balances:
        snapshot["gl_balances"] = gl_balances

    vendors_by_id: dict[str, Any] = {}
    for vendor_id in sorted(vendor_ids):
        vendors_by_id[vendor_id] = fetch_paginated(base_url, FALLBACKS["vendors"], {"vendor_id": vendor_id})
    if vendors_by_id:
        snapshot["vendors_by_id"] = vendors_by_id

    if not args.skip_close_logs:
        close_params = {"period": args.period} if args.period else {}
        snapshot["close_logs"] = fetch_paginated(base_url, FALLBACKS["close_logs"], close_params)

    text = json.dumps(snapshot, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
