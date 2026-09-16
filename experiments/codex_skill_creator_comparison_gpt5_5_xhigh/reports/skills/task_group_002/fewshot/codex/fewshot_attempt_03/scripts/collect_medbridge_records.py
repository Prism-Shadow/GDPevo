#!/usr/bin/env python3
"""Collect related MedBridge Sales Ops API records for a task.

The script is intentionally read-only. It prints source records and simple
annotations so the agent can apply the task's answer template and decision
rules without retyping repeated API lookup code.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


COLLECTIONS = {
    "customers",
    "events",
    "freight-quotes",
    "invoices",
    "opportunities",
    "payments",
    "policies",
    "products",
    "quotes",
    "revenue-journals",
    "rfqs",
    "vouchers",
}


def api_get(base_url: str, path: str) -> Any:
    base = base_url.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    url = base + path
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return [record for record in payload["records"] if isinstance(record, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("record"), dict):
        return [payload["record"]]
    if isinstance(payload, dict):
        return [payload]
    return []


def by_id(items: list[dict[str, Any]], wanted: str | None, key: str = "id") -> dict[str, Any] | None:
    if not wanted:
        return None
    for item in items:
        if str(item.get(key, "")).lower() == wanted.lower():
            return item
    return None


def load_collection(base_url: str, name: str, warnings: list[str]) -> list[dict[str, Any]]:
    try:
        return records(api_get(base_url, f"/api/{name}"))
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        warnings.append(f"could not load {name}: {exc}")
        return []


def freight_annotation(record: dict[str, Any], quote_date: str | None) -> dict[str, Any]:
    status = str(record.get("status", "")).lower()
    valid_until = record.get("valid_until")
    is_expired = bool(quote_date and valid_until and str(valid_until) < str(quote_date))
    destination = str(record.get("destination", "")).lower()
    record_id = str(record.get("id", "")).upper()
    notes = str(record.get("risk_notes", "")).lower()
    likely_distractor = (
        record_id.startswith("FR-DIS-")
        or "distractor" in destination
        or status == "mismatch"
        or "wrong shipment" in notes
        or "old route benchmark" in notes
    )
    return {
        "id": record.get("id"),
        "mode": str(record.get("mode", "")).upper(),
        "validity_status": "STALE" if status == "stale" or is_expired else ("MISMATCH" if status == "mismatch" else "VALID"),
        "source_is_stale": bool(status == "stale" or is_expired),
        "likely_current_option": not likely_distractor,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect related MedBridge Sales Ops API records.")
    parser.add_argument("--base-url", required=True, help="Task API base URL, for example http://task-env:9002/")
    parser.add_argument("--quote-id", action="append", default=[], help="Quote ID to collect")
    parser.add_argument("--rfq-id", action="append", default=[], help="RFQ ID to collect")
    parser.add_argument("--opportunity-id", action="append", default=[], help="Opportunity ID to collect")
    parser.add_argument("--customer-id", action="append", default=[], help="Customer ID to include")
    parser.add_argument("--product-code", action="append", default=[], help="Product code to include")
    parser.add_argument("--event-id", action="append", default=[], help="Event ID to include")
    parser.add_argument("--voucher-code", action="append", default=[], help="Voucher code to include")
    parser.add_argument("--search", action="append", default=[], help="Optional search text")
    args = parser.parse_args()

    warnings: list[str] = []
    data = {name: load_collection(args.base_url, name, warnings) for name in sorted(COLLECTIONS)}

    quote_ids = set(args.quote_id)
    rfq_ids = set(args.rfq_id)
    opportunity_ids = set(args.opportunity_id)
    customer_ids = set(args.customer_id)
    product_codes = set(args.product_code)
    event_ids = set(args.event_id)
    voucher_codes = set(args.voucher_code)

    selected_quotes = [item for item in data["quotes"] if item.get("id") in quote_ids]
    selected_rfqs = [item for item in data["rfqs"] if item.get("id") in rfq_ids]
    selected_opportunities = [item for item in data["opportunities"] if item.get("id") in opportunity_ids]

    for quote in selected_quotes:
        customer_ids.add(str(quote.get("customer_id", "")))
        if quote.get("primary_product_code"):
            product_codes.add(str(quote["primary_product_code"]))
        for line in quote.get("line_items", []):
            if isinstance(line, dict) and line.get("product_code"):
                product_codes.add(str(line["product_code"]))

    for rfq in selected_rfqs:
        customer_ids.add(str(rfq.get("customer_id", "")))
        for line in rfq.get("requested_modules", []):
            if isinstance(line, dict) and line.get("product_code"):
                product_codes.add(str(line["product_code"]))

    for opportunity in selected_opportunities:
        customer_ids.add(str(opportunity.get("customer_id", "")))
        for phase in opportunity.get("phases", []):
            if isinstance(phase, dict) and phase.get("invoice_id"):
                pass

    collect_finance = bool(opportunity_ids)
    linked_invoices = []
    linked_payments = []
    linked_revenue = []
    if collect_finance:
        linked_invoices = [
            item for item in data["invoices"]
            if item.get("opportunity_id") in opportunity_ids
        ]
        linked_payments = [
            item for item in data["payments"]
            if item.get("opportunity_id") in opportunity_ids
            or item.get("invoice_id") in {invoice.get("id") for invoice in linked_invoices}
        ]
        linked_revenue = [
            item for item in data["revenue-journals"]
            if item.get("opportunity_id") in opportunity_ids
            or item.get("invoice_id") in {invoice.get("id") for invoice in linked_invoices}
        ]

    linked_events = [
        item for item in data["events"]
        if item.get("id") in event_ids
        or item.get("opportunity_id") in opportunity_ids
    ]
    for event in linked_events:
        if event.get("voucher_code"):
            voucher_codes.add(str(event["voucher_code"]))

    linked_vouchers = [
        item for item in data["vouchers"]
        if item.get("code") in voucher_codes
        or item.get("event_id") in {event.get("id") for event in linked_events}
        or item.get("opportunity_id") in opportunity_ids
    ]

    linked_freight = [item for item in data["freight-quotes"] if item.get("quote_id") in quote_ids]
    quote_dates = {quote.get("id"): quote.get("quote_date") for quote in selected_quotes}
    freight_annotations = [
        freight_annotation(item, quote_dates.get(item.get("quote_id"))) for item in linked_freight
    ]

    search_results = []
    for query in args.search:
        path = "/api/search?q=" + urllib.parse.quote(query)
        try:
            search_results.append(api_get(args.base_url, path))
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            warnings.append(f"could not search {query!r}: {exc}")

    output = {
        "requested": {
            "quote_ids": sorted(quote_ids),
            "rfq_ids": sorted(rfq_ids),
            "opportunity_ids": sorted(opportunity_ids),
            "customer_ids": sorted(customer_ids),
            "product_codes": sorted(product_codes),
            "event_ids": sorted(event_ids),
            "voucher_codes": sorted(voucher_codes),
        },
        "records": {
            "quotes": selected_quotes,
            "rfqs": selected_rfqs,
            "customers": [item for item in data["customers"] if item.get("id") in customer_ids],
            "products": [item for item in data["products"] if item.get("code") in product_codes],
            "freight_quotes_linked": linked_freight,
            "freight_annotations": freight_annotations,
            "policies": data["policies"],
            "opportunities": selected_opportunities,
            "invoices": linked_invoices,
            "payments": linked_payments,
            "revenue_journals": linked_revenue,
            "events": linked_events,
            "vouchers": linked_vouchers,
        },
        "search_results": search_results,
        "warnings": warnings,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not warnings else 2


if __name__ == "__main__":
    sys.exit(main())
