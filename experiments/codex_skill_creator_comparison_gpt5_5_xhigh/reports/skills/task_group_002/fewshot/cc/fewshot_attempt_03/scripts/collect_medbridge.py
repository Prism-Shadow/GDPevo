#!/usr/bin/env python3
"""Collect MedBridge Sales Ops API evidence for a strict-JSON task.

This script intentionally does not generate the final answer. It fetches records
linked to IDs in the prompt, adds narrow search results, and writes a compact
evidence bundle with derived checks the solver can use while filling the task's
answer template.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any


ID_PATTERNS = {
    "customers": r"\bCUST-[A-Z0-9][A-Z0-9-]*\b",
    "quotes": r"\bQ-[A-Z0-9][A-Z0-9-]*\b",
    "rfqs": r"\bRFQ-[A-Z0-9][A-Z0-9-]*\b",
    "opportunities": r"\bOPP-[A-Z0-9][A-Z0-9-]*\b",
    "freight-quotes": r"\bFR-[A-Z0-9][A-Z0-9-]*\b",
    "invoices": r"\bINV-[A-Z0-9][A-Z0-9-]*\b",
    "payments": r"\bPAY-[A-Z0-9][A-Z0-9-]*\b",
    "revenue-journals": r"\bRJ-[A-Z0-9][A-Z0-9-]*\b",
    "events": r"\bEVT-[A-Z0-9][A-Z0-9-]*\b",
}

DIRECT_FETCH_COLLECTIONS = {"customers", "products", "rfqs", "quotes", "opportunities"}
PRODUCT_RE = re.compile(r"(?<![A-Z0-9-])[A-Z]{2,}[A-Z0-9]*(?:-[A-Z0-9]+)+(?![A-Z0-9-])")


def fetch_json(base_url: str, path: str) -> tuple[Any | None, str | None]:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return json.loads(response.read().decode("utf-8")), None
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = str(exc)
        return None, f"HTTP {exc.code}: {body}"
    except Exception as exc:
        return None, str(exc)


def add_id(ids: dict[str, set[str]], collection: str, value: Any) -> None:
    if isinstance(value, str) and value:
        ids[collection].add(value)


def extract_prompt_ids(prompt_text: str) -> dict[str, set[str]]:
    ids: dict[str, set[str]] = defaultdict(set)
    for collection, pattern in ID_PATTERNS.items():
        for match in re.findall(pattern, prompt_text):
            ids[collection].add(match)

    known = {value for values in ids.values() for value in values}
    for token in PRODUCT_RE.findall(prompt_text):
        if token not in known and not token.startswith(("POL-", "EVT-", "INV-", "PAY-", "RJ-")):
            ids["products"].add(token)

    for token in re.findall(r"`([A-Z][A-Z0-9]{4,})`", prompt_text):
        if token not in known:
            ids["vouchers"].add(token)

    return ids


def extract_prompt_dates(prompt_text: str) -> list[str]:
    return sorted(set(re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", prompt_text)))


def get_record(records: dict[str, dict[str, Any]], collection: str, record_id: str) -> Any | None:
    return records.get(collection, {}).get(record_id)


def derive_related_ids(ids: dict[str, set[str]], records: dict[str, dict[str, Any]]) -> bool:
    changed = False

    def remember(collection: str, value: Any) -> None:
        nonlocal changed
        before = len(ids[collection])
        add_id(ids, collection, value)
        changed = changed or len(ids[collection]) > before

    for quote in records.get("quotes", {}).values():
        remember("customers", quote.get("customer_id"))
        remember("products", quote.get("primary_product_code"))
        for line in quote.get("line_items", []) or []:
            remember("products", line.get("product_code"))

    for rfq in records.get("rfqs", {}).values():
        remember("customers", rfq.get("customer_id"))
        for module in rfq.get("requested_modules", []) or []:
            remember("products", module.get("product_code"))

    for opp in records.get("opportunities", {}).values():
        remember("customers", opp.get("customer_id"))
        for phase in opp.get("phases", []) or []:
            remember("invoices", phase.get("invoice_id"))

    for invoice in records.get("invoices", {}).values():
        remember("customers", invoice.get("customer_id"))
        remember("opportunities", invoice.get("opportunity_id"))

    for event in records.get("events", {}).values():
        remember("customers", event.get("customer_id"))
        remember("opportunities", event.get("opportunity_id"))
        remember("vouchers", event.get("voucher_code"))

    for voucher in records.get("vouchers", {}).values():
        remember("customers", voucher.get("customer_id"))
        remember("opportunities", voucher.get("opportunity_id"))
        remember("events", voucher.get("event_id"))

    return changed


def selected_tier(product: dict[str, Any], quantity: float | int | None) -> dict[str, Any] | None:
    if quantity is None:
        return None
    for tier in product.get("price_tiers", []) or []:
        min_qty = tier.get("min_qty", 0)
        max_qty = tier.get("max_qty")
        if quantity >= min_qty and (max_qty is None or quantity <= max_qty):
            return tier
    return None


def parse_iso(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def compact_transit(record: dict[str, Any]) -> str | None:
    lo = record.get("transit_days_min")
    hi = record.get("transit_days_max")
    if lo is not None and hi is not None:
        return f"{lo}-{hi}"
    return record.get("transit_days_text")


def freight_is_distractor(record: dict[str, Any]) -> bool:
    text = " ".join(
        str(record.get(key, ""))
        for key in ("id", "destination", "risk_notes", "forwarder")
    ).lower()
    return any(marker in text for marker in ("distractor", "benchmark", "wrong shipment", "wrong-size"))


def derive_quote_summary(records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    freight_records = list(records.get("freight-quotes", {}).values())
    products = records.get("products", {})

    for quote_id, quote in records.get("quotes", {}).items():
        quote_date = parse_iso(quote.get("quote_date"))
        lines = []
        exw_total = 0.0
        for line in quote.get("line_items", []) or []:
            code = line.get("product_code")
            quantity = line.get("confirmed_quantity") or quote.get("confirmed_quantity")
            product = products.get(code) if code else None
            tier = selected_tier(product or {}, quantity)
            unit_price = tier.get("unit_price_usd") if tier else None
            line_total = round(quantity * unit_price, 2) if quantity is not None and unit_price is not None else None
            if line_total is not None:
                exw_total += line_total
            lines.append(
                {
                    "line_id": line.get("line_id"),
                    "product_code": code,
                    "quantity": quantity,
                    "selected_tier": tier,
                    "article_number": product.get("article_number") if product else None,
                    "shelf_life_months": product.get("shelf_life_months") if product else None,
                    "line_total": line_total,
                }
            )

        freight = []
        for record in freight_records:
            if record.get("quote_id") != quote_id:
                continue
            valid_until = parse_iso(record.get("valid_until"))
            status = str(record.get("status", "")).lower()
            valid = status == "active" and quote_date is not None and valid_until is not None and valid_until >= quote_date
            stale = status == "stale" or (quote_date is not None and valid_until is not None and valid_until < quote_date)
            freight.append(
                {
                    "id": record.get("id"),
                    "mode": str(record.get("mode", "")).upper(),
                    "cost_usd": record.get("cost_usd"),
                    "transit_days_text": record.get("transit_days_text"),
                    "transit_days_compact": compact_transit(record),
                    "valid_until": record.get("valid_until"),
                    "status": record.get("status"),
                    "valid_on_quote_date": valid,
                    "source_is_stale": stale,
                    "route_risk": str(record.get("route_risk", "")).upper(),
                    "customs_or_border_note": "customs" in str(record.get("risk_notes", "")).lower()
                    or "border" in str(record.get("risk_notes", "")).lower(),
                    "candidate_current_route": not freight_is_distractor(record),
                    "grand_total_if_used": round(exw_total + record.get("cost_usd", 0), 2),
                }
            )

        summaries[quote_id] = {
            "quote_date": quote.get("quote_date"),
            "customer_id": quote.get("customer_id"),
            "confirmed_quantity": quote.get("confirmed_quantity"),
            "lines": lines,
            "exw_total": round(exw_total, 2),
            "freight": freight,
        }

    return summaries


def derive_rfq_summary(records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    products = records.get("products", {})

    for rfq_id, rfq in records.get("rfqs", {}).items():
        lines = []
        total = 0.0
        for module in rfq.get("requested_modules", []) or []:
            code = module.get("product_code")
            quantity = module.get("quantity")
            product = products.get(code) if code else None
            tier = selected_tier(product or {}, quantity)
            unit_price = tier.get("unit_price_usd") if tier else None
            line_total = round(quantity * unit_price, 2) if quantity is not None and unit_price is not None else None
            if line_total is not None:
                total += line_total
            lines.append(
                {
                    "product_code": code,
                    "quantity": quantity,
                    "selected_tier": tier,
                    "article_number": product.get("article_number") if product else None,
                    "shelf_life_months": product.get("shelf_life_months") if product else None,
                    "line_total": line_total,
                }
            )
        summaries[rfq_id] = {
            "quote_date": rfq.get("quote_date"),
            "customer_id": rfq.get("customer_id"),
            "requested_modules_only": lines,
            "exw_total": round(total, 2),
        }

    return summaries


def payment_state(invoice: dict[str, Any]) -> str:
    amount = float(invoice.get("amount_usd") or 0)
    paid = float(invoice.get("paid_amount_usd") or 0)
    if paid >= amount and amount > 0:
        return "PAID"
    if paid > 0:
        return "PARTIAL"
    return "UNPAID"


def derive_opportunity_summary(records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    invoices = records.get("invoices", {})
    journals = list(records.get("revenue-journals", {}).values())

    for opp_id, opp in records.get("opportunities", {}).items():
        milestones = []
        phase_total = 0.0
        total_paid = 0.0
        outstanding = 0.0
        recognized_amount = 0.0
        recognized = []
        missing = []

        for idx, phase in enumerate(opp.get("phases", []) or [], start=1):
            label = f"MS{idx}"
            invoice = invoices.get(phase.get("invoice_id"), {})
            amount = float(phase.get("amount_usd") or invoice.get("amount_usd") or 0)
            paid = float(invoice.get("paid_amount_usd") or 0)
            unpaid = float(invoice.get("outstanding_amount_usd") or max(amount - paid, 0))
            phase_total += amount
            total_paid += paid
            outstanding += unpaid
            state = payment_state(invoice)
            matched_journals = [
                journal
                for journal in journals
                if journal.get("opportunity_id") == opp_id
                and journal.get("status") == "posted"
                and (
                    journal.get("invoice_id") == invoice.get("id")
                    or journal.get("phase_id") == phase.get("phase_id")
                )
            ]
            if state == "PAID" and matched_journals:
                recognition_status = "RECOGNIZED"
                recognized.append(label)
                recognized_amount += sum(float(journal.get("amount_usd") or 0) for journal in matched_journals)
            elif state == "PAID":
                recognition_status = "MISSING_REVENUE_JOURNAL"
                missing.append(label)
            else:
                recognition_status = "NOT_REQUIRED_UNPAID"
            milestones.append(
                {
                    "normalized_milestone_id": label,
                    "phase_number": idx,
                    "api_phase_id": phase.get("phase_id"),
                    "invoice_id": invoice.get("id") or phase.get("invoice_id"),
                    "amount": round(amount, 2),
                    "invoice_status": invoice.get("status"),
                    "payment_state": state,
                    "paid_amount": round(paid, 2),
                    "unpaid_amount": round(unpaid, 2),
                    "due_date": None if state == "PAID" else invoice.get("due_date"),
                    "revenue_recognition_status": recognition_status,
                }
            )

        summaries[opp_id] = {
            "customer_id": opp.get("customer_id"),
            "contact": opp.get("contact"),
            "stage": opp.get("stage"),
            "won_amount": opp.get("won_amount_usd"),
            "phase_total": round(phase_total, 2),
            "matches_won_amount": round(phase_total, 2) == round(float(opp.get("won_amount_usd") or 0), 2),
            "total_paid": round(total_paid, 2),
            "outstanding_balance": round(outstanding, 2),
            "milestones": milestones,
            "recognized_milestones": recognized,
            "missing_required_milestones": missing,
            "recognized_amount": round(recognized_amount, 2),
        }

    return summaries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--template")
    parser.add_argument("--out", required=True)
    parser.add_argument("--no-search", action="store_true")
    args = parser.parse_args()

    prompt_text = Path(args.prompt).read_text(encoding="utf-8")
    template = None
    if args.template:
        template = json.loads(Path(args.template).read_text(encoding="utf-8"))

    ids = extract_prompt_ids(prompt_text)
    records: dict[str, dict[str, Any]] = defaultdict(dict)
    errors: list[dict[str, str]] = []
    searches: list[dict[str, Any]] = []

    api_info, error = fetch_json(args.base_url, "/api")
    if error:
        errors.append({"path": "/api", "error": error})

    policies, error = fetch_json(args.base_url, "/api/policies")
    if error:
        errors.append({"path": "/api/policies", "error": error})
    elif isinstance(policies, dict):
        for policy in policies.get("records", []) or []:
            add_id(ids, "policies", policy.get("id"))
            records["policies"][policy.get("id")] = policy

    fetched = set()
    for _ in range(4):
        for collection in sorted(DIRECT_FETCH_COLLECTIONS):
            for record_id in sorted(ids.get(collection, set())):
                key = (collection, record_id)
                if key in fetched:
                    continue
                fetched.add(key)
                if collection == "policies" and record_id in records["policies"]:
                    continue
                data, error = fetch_json(args.base_url, f"/api/{collection}/{urllib.parse.quote(record_id)}")
                if error:
                    errors.append({"path": f"/api/{collection}/{record_id}", "error": error})
                    continue
                if isinstance(data, dict) and "error" not in data:
                    records[collection][record_id] = data
        if not derive_related_ids(ids, records):
            break

    search_terms = set()
    for collection in (
        "quotes",
        "rfqs",
        "opportunities",
        "freight-quotes",
        "invoices",
        "payments",
        "revenue-journals",
        "events",
        "vouchers",
    ):
        search_terms.update(ids.get(collection, set()))
    if not args.no_search:
        for term in sorted(search_terms):
            data, error = fetch_json(args.base_url, f"/api/search?q={urllib.parse.quote(term)}")
            if error:
                errors.append({"path": f"/api/search?q={term}", "error": error})
                continue
            if isinstance(data, dict):
                searches.append({"q": term, "count": data.get("count"), "results": data.get("results", [])})
                for result in data.get("results", []) or []:
                    collection = result.get("collection")
                    record_id = result.get("id")
                    record = result.get("record")
                    if collection and record_id and isinstance(record, dict):
                        records[collection][record_id] = record

    derive_related_ids(ids, records)

    output = {
        "api": api_info,
        "prompt_dates": extract_prompt_dates(prompt_text),
        "found_ids": {collection: sorted(values) for collection, values in sorted(ids.items()) if values},
        "template_top_level_keys": list(template.keys()) if isinstance(template, dict) else None,
        "records": {collection: dict(sorted(items.items())) for collection, items in sorted(records.items())},
        "searches": searches,
        "derived": {
            "quotes": derive_quote_summary(records),
            "rfqs": derive_rfq_summary(records),
            "opportunities": derive_opportunity_summary(records),
        },
        "errors": errors,
    }

    Path(args.out).write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
