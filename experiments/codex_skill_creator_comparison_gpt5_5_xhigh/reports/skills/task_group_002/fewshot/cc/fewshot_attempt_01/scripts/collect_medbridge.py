#!/usr/bin/env python3
"""Collect linked MedBridge Sales Ops records and generic derived checks.

This helper intentionally contains no task-specific record values. It fetches
API records, links them from prompt-provided IDs, and prints a compact JSON
bundle a solver can use while filling the task's answer_template.json.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from typing import Any


COLLECTIONS = [
    "customers",
    "products",
    "rfqs",
    "quotes",
    "freight-quotes",
    "policies",
    "opportunities",
    "invoices",
    "payments",
    "revenue-journals",
    "events",
    "vouchers",
]


def fetch_json(base_url: str, path: str) -> Any:
    url = base_url.rstrip("/") + path
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code} for {url}: {exc.read().decode('utf-8', 'replace')}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach {url}: {exc}")


def load_collections(base_url: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for collection in COLLECTIONS:
        data = fetch_json(base_url, f"/api/{collection}")
        if isinstance(data, dict) and isinstance(data.get("records"), list):
            out[collection] = data["records"]
        elif isinstance(data, list):
            out[collection] = data
        else:
            out[collection] = []
    return out


def index_records(records: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, dict[str, Any]]]:
    indexes: dict[str, dict[str, dict[str, Any]]] = {}
    for collection, rows in records.items():
        idx: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = row.get("id") or row.get("code")
            if key:
                idx[str(key)] = row
        indexes[collection] = idx
    return indexes


def read_prompt(path: str | None) -> str:
    if not path:
        return ""
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def detect_ids(prompt: str, records: dict[str, list[dict[str, Any]]]) -> dict[str, set[str]]:
    detected: dict[str, set[str]] = defaultdict(set)
    patterns = {
        "quotes": r"\bQ-[A-Z0-9]+(?:-[A-Z0-9]+)*\b",
        "rfqs": r"\bRFQ-[A-Z0-9]+(?:-[A-Z0-9]+)*\b",
        "opportunities": r"\bOPP-[A-Z0-9]+(?:-[A-Z0-9]+)*\b",
        "customers": r"\bCUST-[A-Z0-9]+(?:-[A-Z0-9]+)*\b",
        "events": r"\bEVT-[A-Z0-9]+(?:-[A-Z0-9]+)*\b",
    }
    for collection, pattern in patterns.items():
        detected[collection].update(re.findall(pattern, prompt))

    for product in records.get("products", []):
        code = str(product.get("code", ""))
        if code and re.search(rf"(?<![A-Z0-9-]){re.escape(code)}(?![A-Z0-9-])", prompt):
            detected["products"].add(code)

    for voucher in records.get("vouchers", []):
        code = str(voucher.get("code", ""))
        if code and re.search(rf"(?<![A-Z0-9-]){re.escape(code)}(?![A-Z0-9-])", prompt):
            detected["vouchers"].add(code)

    return detected


def add_arg_ids(detected: dict[str, set[str]], args: argparse.Namespace) -> None:
    mapping = {
        "quotes": args.quote_id,
        "rfqs": args.rfq_id,
        "opportunities": args.opportunity_id,
        "customers": args.customer_id,
        "events": args.event_id,
        "vouchers": args.voucher_code,
        "products": args.product_code,
    }
    for collection, values in mapping.items():
        for value in values or []:
            detected[collection].add(value)


def select_linked(
    detected: dict[str, set[str]],
    records: dict[str, list[dict[str, Any]]],
    indexes: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    selected_ids: dict[str, set[str]] = defaultdict(set)
    for collection, ids in detected.items():
        selected_ids[collection].update(ids)

    changed = True
    while changed:
        changed = False

        for quote_id in list(selected_ids["quotes"]):
            quote = indexes["quotes"].get(quote_id)
            if not quote:
                continue
            changed |= add_if_new(selected_ids, "customers", quote.get("customer_id"))
            changed |= add_if_new(selected_ids, "products", quote.get("primary_product_code"))
            for line in quote.get("line_items", []) or []:
                changed |= add_if_new(selected_ids, "products", line.get("product_code"))
            for freight in records.get("freight-quotes", []):
                if freight.get("quote_id") == quote_id:
                    changed |= add_if_new(selected_ids, "freight-quotes", freight.get("id"))

        for rfq_id in list(selected_ids["rfqs"]):
            rfq = indexes["rfqs"].get(rfq_id)
            if not rfq:
                continue
            changed |= add_if_new(selected_ids, "customers", rfq.get("customer_id"))
            for line in rfq.get("requested_modules", []) or []:
                changed |= add_if_new(selected_ids, "products", line.get("product_code"))

        for opp_id in list(selected_ids["opportunities"]):
            opp = indexes["opportunities"].get(opp_id)
            if not opp:
                continue
            changed |= add_if_new(selected_ids, "customers", opp.get("customer_id"))
            for phase in opp.get("phases", []) or []:
                changed |= add_if_new(selected_ids, "invoices", phase.get("invoice_id"))
            for collection in ["invoices", "payments", "revenue-journals", "events", "vouchers"]:
                for row in records.get(collection, []):
                    if row.get("opportunity_id") == opp_id:
                        changed |= add_if_new(selected_ids, collection, row.get("id") or row.get("code"))

        for event_id in list(selected_ids["events"]):
            event = indexes["events"].get(event_id)
            if not event:
                continue
            changed |= add_if_new(selected_ids, "customers", event.get("customer_id"))
            changed |= add_if_new(selected_ids, "opportunities", event.get("opportunity_id"))
            changed |= add_if_new(selected_ids, "vouchers", event.get("voucher_code"))

        for voucher_code in list(selected_ids["vouchers"]):
            voucher = indexes["vouchers"].get(voucher_code)
            if not voucher:
                continue
            changed |= add_if_new(selected_ids, "customers", voucher.get("customer_id"))
            changed |= add_if_new(selected_ids, "opportunities", voucher.get("opportunity_id"))
            changed |= add_if_new(selected_ids, "events", voucher.get("event_id"))

    selected: dict[str, list[dict[str, Any]]] = {}
    for collection in COLLECTIONS:
        if collection == "policies":
            selected[collection] = sorted(records.get(collection, []), key=lambda r: str(r.get("id", "")))
            continue
        rows = []
        for key in sorted(selected_ids.get(collection, set())):
            row = indexes.get(collection, {}).get(key)
            if row:
                rows.append(row)
        selected[collection] = rows
    return selected


def add_if_new(selected_ids: dict[str, set[str]], collection: str, value: Any) -> bool:
    if value is None or value == "":
        return False
    value = str(value)
    before = len(selected_ids[collection])
    selected_ids[collection].add(value)
    return len(selected_ids[collection]) != before


def money(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return round(number + 1e-9, 2)


def parse_iso(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def select_tier(product: dict[str, Any] | None, quantity: Any) -> dict[str, Any] | None:
    if not product:
        return None
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        return None
    for tier in sorted(product.get("price_tiers", []) or [], key=lambda item: float(item.get("min_qty") or 0)):
        min_qty = float(tier.get("min_qty") or 0)
        raw_max = tier.get("max_qty")
        max_qty = math.inf if raw_max in (None, "") else float(raw_max)
        if min_qty <= qty <= max_qty:
            return tier
    return None


def derive_quote_pricing(selected: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    products = {row.get("code"): row for row in selected.get("products", [])}
    summaries = []
    for quote in selected.get("quotes", []):
        lines = []
        exw_total = 0.0
        for line in quote.get("line_items", []) or []:
            code = line.get("product_code")
            qty = line.get("confirmed_quantity", quote.get("confirmed_quantity"))
            if qty is None:
                qty = line.get("requested_quantity")
            product = products.get(code)
            tier = select_tier(product, qty)
            unit_price = money((tier or {}).get("unit_price_usd"))
            line_total = money(float(qty or 0) * unit_price)
            exw_total = money(exw_total + line_total)
            lines.append(
                {
                    "product_code": code,
                    "quantity": qty,
                    "selected_tier": tier,
                    "article_number": (product or {}).get("article_number"),
                    "shelf_life_months": (product or {}).get("shelf_life_months"),
                    "unit_price_usd": unit_price,
                    "line_total_usd": line_total,
                }
            )
        summaries.append({"quote_id": quote.get("id"), "quote_date": quote.get("quote_date"), "lines": lines, "exw_total_usd": exw_total})
    return summaries


def derive_rfq_pricing(selected: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    products = {row.get("code"): row for row in selected.get("products", [])}
    summaries = []
    for rfq in selected.get("rfqs", []):
        lines = []
        total = 0.0
        for line in rfq.get("requested_modules", []) or []:
            code = line.get("product_code")
            qty = line.get("quantity")
            product = products.get(code)
            tier = select_tier(product, qty)
            unit_price = money((tier or {}).get("unit_price_usd"))
            line_total = money(float(qty or 0) * unit_price)
            total = money(total + line_total)
            lines.append(
                {
                    "product_code": code,
                    "quantity": qty,
                    "article_number": (product or {}).get("article_number"),
                    "selected_tier": tier,
                    "shelf_life_months": (product or {}).get("shelf_life_months"),
                    "unit_price_usd": unit_price,
                    "line_total_usd": line_total,
                }
            )
        summaries.append({"rfq_id": rfq.get("id"), "quote_date": rfq.get("quote_date"), "currency": rfq.get("currency"), "lines": lines, "grand_total_usd": total})
    return summaries


def derive_freight(selected: dict[str, list[dict[str, Any]]], quote_pricing: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    exw_by_quote = {item.get("quote_id"): item.get("exw_total_usd") for item in quote_pricing}
    quote_date_by_id = {row.get("id"): row.get("quote_date") for row in selected.get("quotes", [])}
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for freight in selected.get("freight-quotes", []):
        quote_id = freight.get("quote_id")
        quote_date = parse_iso(quote_date_by_id.get(quote_id) or freight.get("quote_date"))
        valid_until = parse_iso(freight.get("valid_until"))
        status = str(freight.get("status") or "").lower()
        valid_on_quote_date = bool(valid_until and quote_date and valid_until >= quote_date and status in {"active", "valid"})
        source_is_stale = (status in {"stale", "expired", "mismatch"}) or bool(valid_until and quote_date and valid_until < quote_date)
        exw = exw_by_quote.get(quote_id)
        cost = money(freight.get("cost_usd"))
        out[str(quote_id)].append(
            {
                "freight_id": freight.get("id"),
                "mode": str(freight.get("mode") or "").upper(),
                "cost_usd": cost,
                "transit_days_text": freight.get("transit_days_text"),
                "transit_days_range": format_transit_range(freight),
                "valid_until": freight.get("valid_until"),
                "status": freight.get("status"),
                "valid_on_quote_date": valid_on_quote_date,
                "source_is_stale": source_is_stale,
                "route_risk": str(freight.get("route_risk") or "").upper(),
                "risk_notes": freight.get("risk_notes"),
                "grand_total_usd": money(float(exw) + cost) if exw is not None else None,
                "distractor_hint": is_distractor_freight(freight),
            }
        )
    return dict(out)


def format_transit_range(freight: dict[str, Any]) -> str | None:
    lo = freight.get("transit_days_min")
    hi = freight.get("transit_days_max")
    if lo is None or hi is None:
        return None
    return f"{lo}-{hi}"


def is_distractor_freight(freight: dict[str, Any]) -> bool:
    text = " ".join(str(freight.get(key, "")) for key in ["id", "destination", "risk_notes", "status"]).lower()
    return any(token in text for token in ["-dis-", "distractor", "wrong shipment", "benchmark", "mismatch"])


def derive_opportunities(selected: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    invoices = selected.get("invoices", [])
    payments = selected.get("payments", [])
    journals = selected.get("revenue-journals", [])
    out = []
    for opp in selected.get("opportunities", []):
        phases = opp.get("phases", []) or []
        milestones = []
        total_phase_amount = 0.0
        total_paid = 0.0
        total_outstanding = 0.0
        recognized_amount = 0.0
        missing_paid = []
        recognized = []
        for index, phase in enumerate(phases, start=1):
            alias = f"MS{index}"
            phase_id = phase.get("phase_id")
            invoice = find_invoice(invoices, opp.get("id"), phase)
            paid = money((invoice or {}).get("paid_amount_usd"))
            amount = money((invoice or {}).get("amount_usd", phase.get("amount_usd")))
            outstanding = money((invoice or {}).get("outstanding_amount_usd", max(amount - paid, 0.0)))
            phase_journals = [
                journal
                for journal in journals
                if journal.get("opportunity_id") == opp.get("id")
                and (journal.get("phase_id") == phase_id or (invoice and journal.get("invoice_id") == invoice.get("id")))
                and str(journal.get("status", "")).lower() == "posted"
            ]
            journal_amount = money(sum(float(j.get("amount_usd") or 0) for j in phase_journals))
            payment_state = payment_state_for(amount, paid)
            recognition_status = recognition_state(payment_state, phase_journals)
            if recognition_status == "RECOGNIZED":
                recognized.append(alias)
                recognized_amount = money(recognized_amount + journal_amount)
            elif recognition_status == "MISSING_REVENUE_JOURNAL":
                missing_paid.append(alias)
            total_phase_amount = money(total_phase_amount + money(phase.get("amount_usd")))
            total_paid = money(total_paid + paid)
            total_outstanding = money(total_outstanding + outstanding)
            milestones.append(
                {
                    "milestone_id": alias,
                    "api_phase_id": phase_id,
                    "invoice_id": (invoice or {}).get("id"),
                    "amount_usd": amount,
                    "invoice_state": invoice_state_for((invoice or {}).get("status"), outstanding),
                    "payment_state": payment_state,
                    "paid_amount_usd": paid,
                    "outstanding_amount_usd": outstanding,
                    "due_date_if_unpaid": None if payment_state == "PAID" else (invoice or {}).get("due_date"),
                    "recognition_status": recognition_status,
                    "posted_revenue_journals": [journal.get("id") for journal in phase_journals],
                }
            )
        out.append(
            {
                "opportunity_id": opp.get("id"),
                "customer_id": opp.get("customer_id"),
                "stage_normalized": normalize_stage(opp.get("stage")),
                "won_amount_usd": money(opp.get("won_amount_usd")),
                "phase_total_amount_usd": total_phase_amount,
                "opportunity_matches_phase_total": money(opp.get("won_amount_usd")) == total_phase_amount,
                "total_paid_amount_usd": total_paid,
                "outstanding_balance_usd": total_outstanding,
                "recognized_milestones": recognized,
                "missing_required_milestones": missing_paid,
                "recognized_amount_usd": recognized_amount,
                "milestones": milestones,
                "payment_records": [p.get("id") for p in payments if p.get("opportunity_id") == opp.get("id")],
            }
        )
    return out


def find_invoice(invoices: list[dict[str, Any]], opp_id: Any, phase: dict[str, Any]) -> dict[str, Any] | None:
    invoice_id = phase.get("invoice_id")
    phase_id = phase.get("phase_id")
    for invoice in invoices:
        if invoice.get("id") == invoice_id:
            return invoice
    for invoice in invoices:
        if invoice.get("opportunity_id") == opp_id and invoice.get("phase_id") == phase_id:
            return invoice
    return None


def payment_state_for(amount: float, paid: float) -> str:
    if paid >= amount and amount > 0:
        return "PAID"
    if paid > 0:
        return "PARTIAL"
    return "UNPAID"


def invoice_state_for(status: Any, outstanding: float) -> str:
    normalized = str(status or "").lower()
    if normalized in {"paid", "settled"} or outstanding == 0:
        return "PAID"
    if normalized in {"void", "cancelled", "canceled"}:
        return "VOID"
    if normalized in {"open", "unpaid", "overdue", "issued", "draft"} or outstanding > 0:
        return "OPEN"
    return "UNKNOWN"


def recognition_state(payment_state: str, journals: list[dict[str, Any]]) -> str:
    if payment_state == "PAID":
        return "RECOGNIZED" if journals else "MISSING_REVENUE_JOURNAL"
    return "NOT_REQUIRED_UNPAID"


def normalize_stage(stage: Any) -> str:
    normalized = str(stage or "").lower()
    if "won" in normalized:
        return "WON"
    if "lost" in normalized:
        return "LOST"
    if normalized:
        return "OPEN"
    return "UNKNOWN"


def build_output(args: argparse.Namespace) -> dict[str, Any]:
    base_url = args.base_url.rstrip("/")
    prompt = read_prompt(args.prompt_file)
    records = load_collections(base_url)
    indexes = index_records(records)
    detected = detect_ids(prompt, records)
    add_arg_ids(detected, args)
    selected = select_linked(detected, records, indexes)
    quote_pricing = derive_quote_pricing(selected)
    rfq_pricing = derive_rfq_pricing(selected)
    return {
        "base_url": base_url,
        "detected_ids": {key: sorted(value) for key, value in sorted(detected.items()) if value},
        "selected_records": selected,
        "derived": {
            "quote_pricing": quote_pricing,
            "rfq_pricing": rfq_pricing,
            "freight_by_quote": derive_freight(selected, quote_pricing),
            "opportunity_reconciliation": derive_opportunities(selected),
        },
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="MedBridge task environment base URL")
    parser.add_argument("--prompt-file", help="Prompt file to scan for IDs")
    parser.add_argument("--quote-id", action="append", default=[])
    parser.add_argument("--rfq-id", action="append", default=[])
    parser.add_argument("--opportunity-id", action="append", default=[])
    parser.add_argument("--customer-id", action="append", default=[])
    parser.add_argument("--event-id", action="append", default=[])
    parser.add_argument("--voucher-code", action="append", default=[])
    parser.add_argument("--product-code", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    print(json.dumps(build_output(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
