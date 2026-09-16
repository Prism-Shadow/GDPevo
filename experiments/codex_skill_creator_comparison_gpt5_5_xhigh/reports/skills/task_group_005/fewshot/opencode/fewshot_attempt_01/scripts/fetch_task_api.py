#!/usr/bin/env python3
"""Fetch ERP task API records for batch reconciliation work.

This script intentionally performs retrieval only. It does not classify records
or embed answer values.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


def split_values(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                result.append(part)
    return result


def get_json(base_url: str, path: str, query: dict[str, str] | None = None):
    base = base_url.rstrip("/")
    url = base + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} fetching {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed fetching {url}: {exc}") from exc


def data_list(payload):
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    return payload


def first_or_none(payload):
    data = data_list(payload)
    if isinstance(data, list):
        return data[0] if data else None
    return data


def append_unique(target: list[str], value: str | None) -> None:
    if value and value not in target:
        target.append(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--claim-id", action="append", default=[])
    parser.add_argument("--business-id", action="append", default=[])
    parser.add_argument("--vendor-id", action="append", default=[])
    parser.add_argument("--prepaid-invoice-id", action="append", default=[])
    parser.add_argument("--period", action="append", default=[])
    parser.add_argument("--include-close-logs", action="store_true")
    args = parser.parse_args()

    claim_ids = split_values(args.claim_id)
    business_ids = split_values(args.business_id)
    vendor_ids = split_values(args.vendor_id)
    prepaid_invoice_ids = split_values(args.prepaid_invoice_id)
    periods = split_values(args.period)

    bundle = {
        "claims": {},
        "ap_bills_by_claim": {},
        "ap_payments_by_bill": {},
        "vendors": {},
        "compliance": {},
        "prepaid_invoices": {},
        "gl_balances_by_period": {},
        "close_logs": None,
    }

    for claim_id in claim_ids:
        claim_payload = get_json(args.base_url, "/api/claims", {"claim_id": claim_id})
        claim = first_or_none(claim_payload)
        bundle["claims"][claim_id] = claim
        if claim:
            append_unique(vendor_ids, claim.get("vendor_id"))

        bills_payload = get_json(args.base_url, "/api/ap/bills", {"claim_id": claim_id})
        bills = data_list(bills_payload)
        bundle["ap_bills_by_claim"][claim_id] = bills
        for bill in bills if isinstance(bills, list) else []:
            bill_id = bill.get("bill_id")
            append_unique(vendor_ids, bill.get("vendor_id"))
            if bill_id and bill_id not in bundle["ap_payments_by_bill"]:
                payment_payload = get_json(
                    args.base_url, "/api/ap/payments", {"bill_id": bill_id}
                )
                bundle["ap_payments_by_bill"][bill_id] = data_list(payment_payload)

    for business_id in business_ids:
        obj_payload = get_json(
            args.base_url, "/api/compliance/objects", {"business_id": business_id}
        )
        obj = first_or_none(obj_payload)
        ownership = get_json(args.base_url, f"/api/compliance/ownership/{business_id}")
        registry = get_json(args.base_url, f"/api/compliance/registry/{business_id}")
        screening = get_json(args.base_url, f"/api/compliance/screening/{business_id}")
        bank = get_json(args.base_url, f"/api/compliance/bank/{business_id}")
        bundle["compliance"][business_id] = {
            "object": obj,
            "ownership": ownership,
            "registry": registry,
            "screening": screening,
            "bank": bank,
        }
        if obj:
            append_unique(vendor_ids, obj.get("vendor_id"))

    for prepaid_invoice_id in prepaid_invoice_ids:
        payload = get_json(
            args.base_url,
            "/api/prepaids/invoices",
            {"prepaid_invoice_id": prepaid_invoice_id},
        )
        invoice = first_or_none(payload)
        bundle["prepaid_invoices"][prepaid_invoice_id] = invoice
        if invoice:
            append_unique(vendor_ids, invoice.get("vendor_id"))

    for period in periods:
        payload = get_json(args.base_url, "/api/prepaids/gl-balances", {"period": period})
        bundle["gl_balances_by_period"][period] = data_list(payload)

    for vendor_id in sorted(vendor_ids):
        payload = get_json(args.base_url, "/api/vendors", {"vendor_id": vendor_id})
        bundle["vendors"][vendor_id] = first_or_none(payload)

    if args.include_close_logs:
        payload = get_json(args.base_url, "/api/close/logs")
        bundle["close_logs"] = data_list(payload)

    json.dump(bundle, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
