#!/usr/bin/env python3
"""Gather scoped ERP finance evidence from the shared task API.

The script emits evidence and reusable draft calculations. It does not produce
the final answer JSON because each task template controls exact fields.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any


ID_PATTERNS = {
    "claim_ids": re.compile(r"CLM-[A-Z0-9-]+"),
    "business_ids": re.compile(r"BUS-\d{4}-\d{4}"),
    "vendor_ids": re.compile(r"VEN-\d{4}"),
    "prepaid_invoice_ids": re.compile(r"PPD-[A-Z0-9-]+"),
}


def api_get(base_url: str, path: str, params: dict[str, Any] | None = None) -> Any:
    base = base_url.rstrip("/")
    url = base + path
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        if clean:
            url += "?" + urllib.parse.urlencode(clean)
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.load(response)


def api_data(base_url: str, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    params = dict(params or {})
    rows: list[dict[str, Any]] = []
    limit = int(params.pop("limit", 100))
    offset = int(params.pop("offset", 0))
    while True:
        page_params = dict(params)
        page_params.update({"limit": limit, "offset": offset})
        payload = api_get(base_url, path, page_params)
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            page = payload["data"]
            rows.extend(page)
            total = payload.get("total")
            if total is None or offset + len(page) >= int(total) or not page:
                break
            offset += len(page)
            continue
        if isinstance(payload, list):
            rows.extend(payload)
        elif isinstance(payload, dict):
            rows.append(payload)
        break
    return rows


def resolve_input_dir(task_dir: Path) -> Path:
    candidates = [task_dir, task_dir / "input"]
    for candidate in candidates:
        if (candidate / "prompt.txt").exists() or (candidate / "payloads").exists():
            return candidate
    return task_dir


def read_local(input_dir: Path) -> dict[str, Any]:
    prompt_path = input_dir / "prompt.txt"
    prompt = prompt_path.read_text() if prompt_path.exists() else ""
    payload_dir = input_dir / "payloads"
    payloads: dict[str, Any] = {}
    payload_text = ""

    if payload_dir.exists():
        for path in sorted(payload_dir.iterdir()):
            if not path.is_file():
                continue
            text = path.read_text()
            payload_text += "\n" + text
            if path.suffix.lower() == ".json":
                payloads[path.name] = json.loads(text)
            elif path.suffix.lower() == ".csv":
                with path.open(newline="") as handle:
                    payloads[path.name] = list(csv.DictReader(handle))
            else:
                payloads[path.name] = text

    combined = prompt + "\n" + payload_text
    ids = {name: sorted(set(pattern.findall(combined))) for name, pattern in ID_PATTERNS.items()}
    account_candidates = set(re.findall(r"\b(?:1[0-9]{3}|2[0-9]{3}|6[0-9]{3})\b", combined))
    accounts = sorted(value for value in account_candidates if not re.match(r"^20\d{2}$", value))
    periods = sorted(set(re.findall(r"\b20\d{2}-[01]\d\b", combined)))
    dates = sorted(set(re.findall(r"\b20\d{2}-[01]\d-[0-3]\d\b", combined)))

    return {
        "input_dir": str(input_dir),
        "prompt_present": prompt_path.exists(),
        "payload_names": sorted(payloads),
        "payloads": payloads,
        "ids": ids,
        "accounts": accounts,
        "periods": periods,
        "dates": dates,
    }


def money(value: Any) -> float:
    return round(float(value or 0), 2)


def same_money(a: Any, b: Any, tolerance: float = 0.005) -> bool:
    return abs(float(a or 0) - float(b or 0)) <= tolerance


def vendor_matches(claim: dict[str, Any], bill: dict[str, Any]) -> bool:
    claim_vendor = claim.get("vendor_id")
    bill_vendor = bill.get("vendor_id")
    if claim_vendor is None:
        return bill_vendor is None
    return claim_vendor == bill_vendor


def claim_derived(
    claim: dict[str, Any] | None,
    bills: list[dict[str, Any]],
    payments_by_bill: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    if not claim:
        return {"flags": ["claim_missing"], "open_balance": 0.0}

    flags: list[str] = []
    if claim.get("status") not in {"approved", "paid"}:
        flags.append("claim_not_approved_or_paid")
    if claim.get("receipt_status") not in {None, "", "attached"}:
        flags.append("receipt_or_support_not_fully_attached")

    usable_bills = []
    matched_bills = []
    settled_bills = []
    open_balance = 0.0

    for bill in bills:
        status = bill.get("status")
        bill_id = bill.get("bill_id")
        bill_payments = payments_by_bill.get(bill_id, [])
        cleared_total = sum(money(p.get("amount")) for p in bill_payments if p.get("status") == "cleared")
        bill_info = {
            "bill_id": bill_id,
            "status": status,
            "amount_matches_claim": same_money(bill.get("amount"), claim.get("amount")),
            "vendor_matches_claim": vendor_matches(claim, bill),
            "cleared_payment_total": money(cleared_total),
            "uncleared_payment_statuses": sorted(
                {str(p.get("status")) for p in bill_payments if p.get("status") != "cleared"}
            ),
        }
        if status in {"void", "draft"}:
            flags.append(f"bill_{status}")
        else:
            usable_bills.append(bill_info)
            if bill_info["amount_matches_claim"] and bill_info["vendor_matches_claim"]:
                matched_bills.append(bill_info)
                if status == "paid" and same_money(cleared_total, claim.get("amount")):
                    settled_bills.append(bill_info)
                else:
                    open_balance += max(0.0, money(bill.get("amount")) - money(cleared_total))

    if not bills:
        flags.append("no_ap_bill")
    elif not matched_bills:
        flags.append("no_amount_vendor_matched_bill")
    if settled_bills:
        flags.append("settled_by_cleared_payment")
    elif matched_bills and claim.get("status") == "approved":
        flags.append("open_payable")

    return {
        "flags": sorted(set(flags)),
        "usable_bills": usable_bills,
        "matched_bills": matched_bills,
        "settled_bills": settled_bills,
        "open_balance": money(open_balance),
    }


def gather_claims(base_url: str, claim_ids: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for claim_id in claim_ids:
        claims = api_data(base_url, "/api/claims", {"claim_id": claim_id})
        claim = claims[0] if claims else None
        bills = api_data(base_url, "/api/ap/bills", {"claim_id": claim_id})
        payments_by_bill = {
            bill["bill_id"]: api_data(base_url, "/api/ap/payments", {"bill_id": bill["bill_id"]})
            for bill in bills
            if bill.get("bill_id")
        }
        aging_by_bill = {
            bill["bill_id"]: api_data(base_url, "/api/ap/aging", {"bill_id": bill["bill_id"]})
            for bill in bills
            if bill.get("bill_id")
        }
        result[claim_id] = {
            "claim": claim,
            "bills": bills,
            "payments_by_bill": payments_by_bill,
            "aging_by_bill": aging_by_bill,
            "derived": claim_derived(claim, bills, payments_by_bill),
        }
    return result


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def business_derived(
    compliance: dict[str, Any] | None,
    vendor: dict[str, Any] | None,
    review_date: date | None,
) -> dict[str, Any]:
    compliance = compliance or {}
    vendor = vendor or {}
    flags: list[str] = []

    bank_status = compliance.get("bank_account_status")
    if bank_status == "name_mismatch":
        flags.append("bank_name_mismatch")
    if bank_status == "closed":
        flags.append("bank_closed")
    if compliance.get("pep_status") == "confirmed_pep":
        flags.append("confirmed_pep")
    if compliance.get("sanctions_check_status") in {"confirmed", "match", "sanctions_confirmed"}:
        flags.append("sanctions_confirmed")
    if compliance.get("pep_status") == "not_run" or compliance.get("sanctions_check_status") == "not_run":
        flags.append("screening_not_run")
    if compliance.get("shell_company_suspected"):
        flags.append("shell_company_suspected")
    if compliance.get("missing_fields"):
        flags.append("missing_required_documents")
    if vendor.get("status") == "on_hold":
        flags.append("vendor_on_hold")

    license_expiry = parse_date(compliance.get("license_expiry"))
    expired_license = bool(review_date and license_expiry and license_expiry < review_date)
    if expired_license:
        flags.append("expired_license")

    compliance_tax = compliance.get("tax_id")
    vendor_tax = vendor.get("tax_id")
    invalid_tax = bool(compliance_tax and vendor_tax and compliance_tax != vendor_tax)
    risk_score = compliance.get("risk_score")
    risk_score_override = isinstance(risk_score, (int, float)) and risk_score >= 70

    owners = compliance.get("ubo_list") or []
    reportable_names = sorted({o.get("name") for o in owners if float(o.get("ownership_pct") or 0) >= 25 and o.get("name")})

    return {
        "hard_stop_flags": sorted(set(flags)),
        "reportable_ubo_count": len(reportable_names),
        "reportable_ubo_names": reportable_names,
        "invalid_tax": invalid_tax,
        "expired_license": expired_license,
        "risk_score_override": risk_score_override,
    }


def gather_businesses(base_url: str, business_ids: list[str], local: dict[str, Any]) -> dict[str, Any]:
    review_date = None
    for value in local.get("dates", []):
        parsed = parse_date(value)
        if parsed and (review_date is None or parsed > review_date):
            review_date = parsed

    result: dict[str, Any] = {}
    for business_id in business_ids:
        local_records = find_dicts_with_value(local.get("payloads", {}), "business_id", business_id)
        objects = api_data(base_url, "/api/compliance/objects", {"business_id": business_id})
        compliance = objects[0] if objects else None
        vendor_id = compliance.get("vendor_id") if compliance else None
        if not vendor_id:
            for record in local_records:
                if record.get("vendor_id"):
                    vendor_id = record["vendor_id"]
                    break
        vendor = None
        if vendor_id:
            vendors = api_data(base_url, "/api/vendors", {"vendor_id": vendor_id})
            vendor = vendors[0] if vendors else None

        detail_paths = {
            "ownership": f"/api/compliance/ownership/{business_id}",
            "registry": f"/api/compliance/registry/{business_id}",
            "screening": f"/api/compliance/screening/{business_id}",
            "bank": f"/api/compliance/bank/{business_id}",
        }
        details = {}
        for key, path in detail_paths.items():
            try:
                details[key] = api_get(base_url, path)
            except Exception as exc:  # keep evidence collection best-effort
                details[key] = {"error": str(exc)}

        result[business_id] = {
            "local_records": local_records,
            "compliance_object": compliance,
            "vendor": vendor,
            "details": details,
            "derived": business_derived(compliance, vendor, review_date),
        }
    return result


def find_dicts_with_value(obj: Any, key: str, value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        if obj.get(key) == value:
            found.append(obj)
        for child in obj.values():
            found.extend(find_dicts_with_value(child, key, value))
    elif isinstance(obj, list):
        for child in obj:
            found.extend(find_dicts_with_value(child, key, value))
    return found


def month_index(period: str) -> int:
    year, month = period.split("-")
    return int(year) * 12 + int(month)


def invoice_calc(invoice: dict[str, Any], period: str) -> dict[str, Any]:
    start = invoice.get("service_start", "")[:7]
    end = invoice.get("service_end", "")[:7]
    close_i = month_index(period)
    start_i = month_index(start) if re.match(r"^\d{4}-\d{2}$", start) else None
    end_i = month_index(end) if re.match(r"^\d{4}-\d{2}$", end) else None
    monthly = money(invoice.get("monthly_amortization"))
    original = money(invoice.get("original_amount"))

    active = bool(start_i is not None and end_i is not None and start_i <= close_i <= end_i)
    period_amortization = monthly if active else 0.0
    if start_i is None or end_i is None or close_i < start_i:
        months = 0
    else:
        months = max(0, min(close_i, end_i) - start_i + 1)
    cumulative = min(original, money(monthly * months))
    ending = money(original - cumulative)
    flags = invoice.get("data_quality_flags") or []
    default_missing = any("missing" in str(flag) or "default" in str(flag) for flag in flags)

    return {
        "period_amortization": money(period_amortization),
        "cumulative_amortization_through_period": money(cumulative),
        "ending_balance": ending,
        "default_missing_term_flag": default_missing,
        "exception_flag": bool(flags),
        "data_quality_flags": flags,
    }


def gather_prepaids(base_url: str, local: dict[str, Any]) -> dict[str, Any]:
    scope = {}
    for payload in local.get("payloads", {}).values():
        if isinstance(payload, dict) and "selected_prepaid_invoice_ids" in payload:
            scope = payload
            break
    invoice_ids = scope.get("selected_prepaid_invoice_ids") or local["ids"].get("prepaid_invoice_ids", [])
    period = scope.get("close_period") or (local.get("periods") or [None])[-1]
    accounts = scope.get("accounts") or local.get("accounts", [])
    threshold = float(scope.get("variance_threshold_abs", 0) or 0)

    invoices = {}
    calcs = {}
    for invoice_id in invoice_ids:
        rows = api_data(base_url, "/api/prepaids/invoices", {"prepaid_invoice_id": invoice_id})
        if rows:
            invoices[invoice_id] = rows[0]
            if period:
                calcs[invoice_id] = invoice_calc(rows[0], period)

    gl_balances = {}
    for account in accounts:
        rows = api_data(base_url, "/api/prepaids/gl-balances", {"period": period, "account": account})
        gl_balances[account] = rows[0] if rows else None

    rollup = {}
    if period:
        grouped: dict[str, list[str]] = defaultdict(list)
        for invoice_id, invoice in invoices.items():
            grouped[str(invoice.get("account"))].append(invoice_id)
        for account, ids in grouped.items():
            gl = gl_balances.get(account) or {}
            schedule = sum(calcs[i]["ending_balance"] for i in ids)
            variance = money(schedule - money(gl.get("ending_balance")))
            rollup[account] = {
                "selected_invoice_count": len(ids),
                "original_amount_total": money(sum(money(invoices[i].get("original_amount")) for i in ids)),
                "period_amortization_total": money(sum(calcs[i]["period_amortization"] for i in ids)),
                "cumulative_amortization_through_period": money(
                    sum(calcs[i]["cumulative_amortization_through_period"] for i in ids)
                ),
                "schedule_ending_balance": money(schedule),
                "gl_ending_balance": money(gl.get("ending_balance")),
                "variance_amount": variance,
                "variance_flag": abs(variance) > threshold if threshold else abs(variance) > 0,
                "has_default_missing_term_flag": any(calcs[i]["default_missing_term_flag"] for i in ids),
            }

    return {
        "scope": scope,
        "invoices": invoices,
        "invoice_calcs": calcs,
        "gl_balances": gl_balances,
        "account_rollup_draft": rollup,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task API base URL")
    parser.add_argument("--task-dir", default=".", help="Task root or input directory")
    args = parser.parse_args()

    input_dir = resolve_input_dir(Path(args.task_dir).resolve())
    local = read_local(input_dir)
    base_url = args.base_url

    evidence: dict[str, Any] = {
        "local": {
            "input_dir": local["input_dir"],
            "prompt_present": local["prompt_present"],
            "payload_names": local["payload_names"],
            "payloads": local["payloads"],
            "ids": local["ids"],
            "accounts": local["accounts"],
            "periods": local["periods"],
            "dates": local["dates"],
        }
    }

    try:
        evidence["api_endpoints"] = api_get(base_url, "/endpoints")
    except Exception as exc:
        evidence["api_endpoints_error"] = str(exc)

    if local["ids"].get("claim_ids"):
        evidence["claims"] = gather_claims(base_url, local["ids"]["claim_ids"])
        try:
            evidence["close_logs"] = api_data(base_url, "/api/close/logs")
        except Exception as exc:
            evidence["close_logs_error"] = str(exc)

    if local["ids"].get("business_ids"):
        evidence["businesses"] = gather_businesses(base_url, local["ids"]["business_ids"], local)

    if local["ids"].get("prepaid_invoice_ids") or any(
        isinstance(payload, dict) and "selected_prepaid_invoice_ids" in payload
        for payload in local.get("payloads", {}).values()
    ):
        evidence["prepaids"] = gather_prepaids(base_url, local)

    json.dump(evidence, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
