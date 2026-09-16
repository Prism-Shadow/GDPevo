#!/usr/bin/env python3
"""Fetch and summarize task-group ERP finance API evidence."""

import argparse
import csv
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path


API_PATHS = {
    "claims": ["/api/claims", "/claims"],
    "bills": ["/api/ap/bills", "/bills"],
    "payments": ["/api/ap/payments", "/payments"],
    "vendors": ["/api/vendors", "/vendors"],
    "compliance": ["/api/compliance/objects", "/compliance/objects"],
    "prepaids": ["/api/prepaids/invoices", "/prepaids/invoices"],
    "gl": ["/api/prepaids/gl-balances", "/gl/balances"],
    "logs": ["/api/close/logs", "/close/logs"],
}


def money(value):
    return round(float(value or 0), 2)


def parse_date(value):
    if not value:
        return None
    return date.fromisoformat(value[:10])


def active_months_through(start, end, period):
    start_d = parse_date(start)
    end_d = parse_date(end)
    period_d = parse_date(period + "-01")
    if not start_d or not end_d or not period_d:
        return 0
    if period_d < date(start_d.year, start_d.month, 1):
        return 0
    last = min(date(period_d.year, period_d.month, 1), date(end_d.year, end_d.month, 1))
    if last < date(start_d.year, start_d.month, 1):
        return 0
    return (last.year - start_d.year) * 12 + last.month - start_d.month + 1


def period_is_active(start, end, period):
    return active_months_through(start, end, period) > active_months_through(start, end, previous_month(period))


def previous_month(period):
    year, month = [int(part) for part in period.split("-")]
    if month == 1:
        return f"{year - 1}-12"
    return f"{year}-{month - 1:02d}"


class Api:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def get(self, path, params=None):
        query = urllib.parse.urlencode(params or {})
        url = self.base_url + path + (("?" + query) if query else "")
        with urllib.request.urlopen(url, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_collection(self, key, params=None):
        last_error = None
        for path in API_PATHS[key]:
            try:
                return self._paged(path, params or {})
            except Exception as exc:  # try documented fallback path
                last_error = exc
        raise RuntimeError(f"Could not fetch {key}: {last_error}")

    def _paged(self, path, params):
        limit = int(params.get("limit", 100))
        offset = int(params.get("offset", 0))
        out = []
        while True:
            page_params = dict(params, limit=limit, offset=offset)
            payload = self.get(path, page_params)
            data = payload.get("data", payload if isinstance(payload, list) else [])
            out.extend(data)
            total = payload.get("total", len(out)) if isinstance(payload, dict) else len(out)
            if len(out) >= total or not data:
                return out
            offset += limit


def first(items):
    return items[0] if items else None


def parse_ids(raw):
    ids = []
    for item in raw or []:
        ids.extend(part.strip() for part in item.split(",") if part.strip())
    return ids


def valid_bill_for_claim(bill, claim):
    if bill.get("status") == "void":
        return False
    if money(bill.get("amount")) != money(claim.get("amount")):
        return False
    claim_vendor = claim.get("vendor_id")
    bill_vendor = bill.get("vendor_id")
    return not (claim_vendor and bill_vendor and claim_vendor != bill_vendor)


def summarize_claims(args):
    api = Api(args.base_url)
    claim_ids = sorted(parse_ids(args.claim_ids))
    payment_cache = {}
    per_claim = []
    for claim_id in claim_ids:
        claim = first(api.get_collection("claims", {"claim_id": claim_id}))
        bills = api.get_collection("bills", {"claim_id": claim_id})
        valid_bills = []
        invalid_bills = []
        for bill in bills:
            payments = api.get_collection("payments", {"bill_id": bill.get("bill_id")})
            payment_cache[bill.get("bill_id")] = payments
            bill_summary = {
                "bill_id": bill.get("bill_id"),
                "status": bill.get("status"),
                "amount": money(bill.get("amount")),
                "vendor_id": bill.get("vendor_id"),
                "cleared_payments": money(sum(p.get("amount", 0) for p in payments if p.get("status") == "cleared")),
                "in_flight_payments": [p.get("payment_id") for p in payments if p.get("status") in {"scheduled", "processing"}],
            }
            if claim and valid_bill_for_claim(bill, claim):
                valid_bills.append(bill_summary)
            else:
                invalid_bills.append(bill_summary)
        open_balance = money(sum(max(0.0, b["amount"] - b["cleared_payments"]) for b in valid_bills))
        paid = any(b["status"] == "paid" and b["cleared_payments"] >= b["amount"] for b in valid_bills)
        ready_claim = claim and claim.get("status") in {"approved", "paid"}
        attached = claim and claim.get("receipt_status") == "attached"
        payable = bool(ready_claim and attached and valid_bills and open_balance > 0 and not paid)
        reasons = []
        if not claim:
            reasons.append("missing_claim")
        elif claim.get("status") not in {"approved", "paid"}:
            reasons.append("claim_not_approved_or_paid")
        if claim and claim.get("status") != "paid" and claim.get("receipt_status") != "attached":
            reasons.append("receipt_support_not_attached")
        if not valid_bills:
            reasons.append("no_valid_ap_bill")
        if invalid_bills:
            reasons.append("ap_amount_or_vendor_mismatch_or_void")
        classification = "paid" if paid else "payable" if payable else "blocked"
        per_claim.append({
            "claim_id": claim_id,
            "classification": classification,
            "claim": claim,
            "valid_bills": valid_bills,
            "invalid_bills": invalid_bills,
            "open_balance": open_balance,
            "block_reasons": reasons if classification == "blocked" else [],
            "stale_snapshot_correction": stale_correction(claim, valid_bills, invalid_bills, paid),
        })
    logs = api.get_collection("logs")
    close_log_candidates = [
        log for log in logs
        if log.get("area") == "AP" and log.get("status") == "closed"
        and "Manual journal" in log.get("message", "")
    ]
    print_json({
        "per_claim": per_claim,
        "paid_claim_ids": sorted(x["claim_id"] for x in per_claim if x["classification"] == "paid"),
        "payable_claim_ids": sorted(x["claim_id"] for x in per_claim if x["classification"] == "payable"),
        "blocked_claim_ids": sorted(x["claim_id"] for x in per_claim if x["classification"] == "blocked"),
        "open_balance_total": money(sum(x["open_balance"] for x in per_claim if x["classification"] == "payable")),
        "ap_close_log_refresh_candidates": sorted(log.get("log_id") for log in close_log_candidates),
    })


def stale_correction(claim, valid_bills, invalid_bills, paid):
    if claim and claim.get("status") not in {"approved", "paid"}:
        return "block_unapproved_claim"
    if paid:
        return "replace_with_matched_paid_bill"
    if valid_bills and any(b["in_flight_payments"] or b["status"] == "scheduled" for b in valid_bills):
        return "mark_in_flight_payment"
    if invalid_bills and any(b["status"] == "void" for b in invalid_bills):
        return "ignore_void_bill"
    if invalid_bills:
        return "exclude_amount_or_vendor_mismatch"
    return "current_snapshot_ok"


def hard_stop_flags(comp, vendor, as_of):
    flags = []
    bank_status = comp.get("bank_account_status")
    if bank_status == "closed":
        flags.append("bank_closed")
    if bank_status == "name_mismatch":
        flags.append("bank_name_mismatch")
    if comp.get("pep_status") == "confirmed_pep":
        flags.append("confirmed_pep")
    missing = set(comp.get("missing_fields") or [])
    expiry = parse_date(comp.get("license_expiry"))
    as_of_month_start = date(as_of.year, as_of.month, 1)
    if expiry and expiry < as_of_month_start and "license" not in missing:
        flags.append("expired_license")
    if comp.get("missing_fields"):
        flags.append("missing_required_documents")
    sanctions = comp.get("sanctions_check_status")
    if sanctions in {"confirmed", "confirmed_match", "match", "sanctions_confirmed"}:
        flags.append("sanctions_confirmed")
    if comp.get("pep_status") == "not_run" or sanctions == "not_run":
        flags.append("screening_not_run")
    if comp.get("shell_company_suspected"):
        flags.append("shell_company_suspected")
    if vendor and vendor.get("status") == "on_hold":
        flags.append("vendor_on_hold")
    return sorted(set(flags))


def onboarding_decision(flags):
    if not flags:
        return "approve"
    info_only = {"missing_required_documents", "screening_not_run"}
    if set(flags).issubset(info_only):
        return "awaiting_information"
    return "escalate"


def tax_invalid(comp, vendor):
    tax = comp.get("tax_id") or ""
    if not re.fullmatch(r"TIN[0-9]{6}", tax):
        return True
    return bool(vendor and vendor.get("tax_id") and vendor.get("tax_id") != tax)


def summarize_compliance(args):
    api = Api(args.base_url)
    as_of = parse_date(args.as_of_date)
    events = {}
    if args.account_change_json:
        payload = json.loads(Path(args.account_change_json).read_text())
        events = {event["business_id"]: event for event in payload.get("account_change_events", [])}
    per_business = []
    for business_id in sorted(parse_ids(args.business_ids)):
        comp = first(api.get_collection("compliance", {"business_id": business_id})) or {}
        vendor = first(api.get_collection("vendors", {"vendor_id": comp.get("vendor_id")})) if comp.get("vendor_id") else None
        flags = hard_stop_flags(comp, vendor, as_of)
        owner_names = {
            owner.get("name")
            for owner in comp.get("ubo_list", [])
            if owner.get("name") and float(owner.get("ownership_pct", 0)) >= 25
        }
        invalid_tax = tax_invalid(comp, vendor)
        event = events.get(business_id, {})
        requested_last4 = event.get("requested_bank_last4")
        vendor_last4 = vendor.get("bank_account_last4") if vendor else None
        release_blockers = account_change_blockers(comp, vendor, as_of, requested_last4, invalid_tax)
        expired_license = bool(
            parse_date(comp.get("license_expiry"))
            and parse_date(comp.get("license_expiry")) < as_of
            and "license" not in set(comp.get("missing_fields") or [])
        )
        per_business.append({
            "business_id": business_id,
            "vendor_id": comp.get("vendor_id"),
            "reportable_ubo_count": len(owner_names),
            "hard_stop_flags": flags,
            "onboarding_decision": onboarding_decision(flags),
            "invalid_tax": invalid_tax,
            "expired_license": expired_license,
            "bank_name_mismatch": comp.get("bank_account_status") == "name_mismatch",
            "requested_bank_last4_matches_vendor": None if not requested_last4 else requested_last4 == vendor_last4,
            "risk_score_override": float(comp.get("risk_score", 0)) >= 70,
            "account_change_blockers": release_blockers,
            "account_change_decision": account_change_decision(release_blockers),
            "compliance": comp,
            "vendor": vendor,
        })
    print_json({
        "per_business": per_business,
        "reportable_ubo_counts": {x["business_id"]: x["reportable_ubo_count"] for x in per_business},
        "hard_stop_flags": {x["business_id"]: x["hard_stop_flags"] for x in per_business},
        "follow_up_business_ids": [x["business_id"] for x in per_business if x["onboarding_decision"] != "approve"],
        "overall_release_ready": all(x["onboarding_decision"] == "approve" for x in per_business),
        "bank_mismatch_ids": [x["business_id"] for x in per_business if x["bank_name_mismatch"]],
        "invalid_tax_ids": [x["business_id"] for x in per_business if x["invalid_tax"]],
        "expired_license_ids": [x["business_id"] for x in per_business if x["expired_license"]],
        "review_queue_ids": [x["business_id"] for x in per_business if x["account_change_decision"] != "release"],
        "risk_score_override_flags": [x["business_id"] for x in per_business if x["risk_score_override"]],
        "account_change_decisions": {x["business_id"]: x["account_change_decision"] for x in per_business},
    })


def account_change_blockers(comp, vendor, as_of, requested_last4, invalid_tax):
    blockers = []
    if not vendor or vendor.get("status") != "active":
        blockers.append("vendor_on_hold")
    if requested_last4 and vendor and requested_last4 != vendor.get("bank_account_last4"):
        blockers.append("requested_bank_mismatch")
    if comp.get("bank_account_status") in {"closed", "name_mismatch"}:
        blockers.append("bank_" + comp.get("bank_account_status"))
    if invalid_tax:
        blockers.append("invalid_tax")
    missing = set(comp.get("missing_fields") or [])
    expiry = parse_date(comp.get("license_expiry"))
    if expiry and expiry < as_of and "license" not in missing:
        blockers.append("expired_license")
    if comp.get("missing_fields"):
        blockers.append("missing_required_documents")
    sanctions = comp.get("sanctions_check_status")
    if comp.get("pep_status") == "not_run" or sanctions == "not_run":
        blockers.append("screening_not_run")
    if comp.get("pep_status") == "confirmed_pep":
        blockers.append("confirmed_pep")
    if sanctions in {"confirmed", "confirmed_match", "match", "sanctions_confirmed"}:
        blockers.append("sanctions_confirmed")
    if comp.get("shell_company_suspected"):
        blockers.append("shell_company_suspected")
    if float(comp.get("risk_score", 0)) >= 70:
        blockers.append("risk_score_override")
    return sorted(set(blockers))


def account_change_decision(blockers):
    escalatory = {"confirmed_pep", "sanctions_confirmed", "shell_company_suspected", "vendor_on_hold", "invalid_tax"}
    if escalatory.intersection(blockers):
        return "escalate"
    if blockers:
        return "hold"
    return "release"


def summarize_prepaids(args):
    api = Api(args.base_url)
    scope = json.loads(Path(args.scope_json).read_text())
    period = scope["close_period"]
    entity = scope.get("entity")
    accounts = set(scope.get("accounts", []))
    threshold = float(scope.get("variance_threshold_abs", 0))
    selected_ids = scope.get("selected_prepaid_invoice_ids", [])
    gl_rows = api.get_collection("gl", {"period": period})
    gl_by_account = {
        row["account"]: row for row in gl_rows
        if (not entity or row.get("entity") == entity) and (not accounts or row.get("account") in accounts)
    }
    invoice_results = []
    rollup = {}
    default_missing_ids = []
    exception_ids = []
    for invoice_id in selected_ids:
        invoice = first(api.get_collection("prepaids", {"prepaid_invoice_id": invoice_id}))
        if not invoice:
            continue
        account = invoice.get("account")
        flags = invoice.get("data_quality_flags") or []
        months = active_months_through(invoice.get("service_start"), invoice.get("service_end"), period)
        monthly = money(invoice.get("monthly_amortization"))
        cumulative = min(money(invoice.get("original_amount")), money(monthly * months))
        period_amortization = monthly if period_is_active(invoice.get("service_start"), invoice.get("service_end"), period) else 0.0
        ending = max(0.0, money(invoice.get("original_amount")) - cumulative)
        default_missing = any(flag in {"missing_contract_dates", "default_term", "missing_term"} for flag in flags)
        exception = bool(flags) or invoice.get("recognition_method") != "straight_line" or not invoice.get("service_start") or not invoice.get("service_end")
        if default_missing:
            default_missing_ids.append(invoice_id)
        if exception:
            exception_ids.append(invoice_id)
        invoice_results.append({
            "prepaid_invoice_id": invoice_id,
            "account": account,
            "march_amortization": money(period_amortization),
            "cumulative_amortization_through_march": money(cumulative),
            "ending_balance": money(ending),
            "default_missing_term_flag": default_missing,
            "exception_flag": exception,
        })
        bucket = rollup.setdefault(account, {
            "account_name": gl_by_account.get(account, {}).get("account_name", ""),
            "selected_invoice_count": 0,
            "original_amount_total": 0.0,
            "march_amortization_total": 0.0,
            "cumulative_amortization_through_march": 0.0,
            "schedule_ending_balance": 0.0,
            "has_default_missing_term_flag": False,
            "_has_exception": False,
        })
        bucket["selected_invoice_count"] += 1
        bucket["original_amount_total"] += money(invoice.get("original_amount"))
        bucket["march_amortization_total"] += money(period_amortization)
        bucket["cumulative_amortization_through_march"] += money(cumulative)
        bucket["schedule_ending_balance"] += money(ending)
        bucket["has_default_missing_term_flag"] = bucket["has_default_missing_term_flag"] or default_missing
        bucket["_has_exception"] = bucket["_has_exception"] or exception
    for account, bucket in rollup.items():
        for key in ("original_amount_total", "march_amortization_total", "cumulative_amortization_through_march", "schedule_ending_balance"):
            bucket[key] = money(bucket[key])
        bucket["gl_ending_balance"] = money(gl_by_account.get(account, {}).get("ending_balance", 0))
        bucket["variance_amount"] = money(bucket["schedule_ending_balance"] - bucket["gl_ending_balance"])
        bucket["variance_flag"] = abs(bucket["variance_amount"]) > threshold
        if bucket["variance_flag"] or bucket["has_default_missing_term_flag"]:
            bucket["account_status"] = "requires_reconciliation"
        elif bucket.pop("_has_exception"):
            bucket["account_status"] = "variance_review"
        else:
            bucket["account_status"] = "reconciled"
        bucket.pop("_has_exception", None)
    print_json({
        "period": period,
        "entity": entity,
        "selected_invoice_ids": selected_ids,
        "account_rollup": {account: rollup[account] for account in sorted(rollup)},
        "invoice_results": invoice_results,
        "default_missing_term_invoice_ids": sorted(default_missing_ids),
        "exception_invoice_ids": sorted(exception_ids),
    })


def print_json(payload):
    json.dump(payload, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    claims = sub.add_parser("claims")
    claims.add_argument("--base-url", required=True)
    claims.add_argument("--claim-ids", action="append", required=True)
    claims.set_defaults(func=summarize_claims)
    compliance = sub.add_parser("compliance")
    compliance.add_argument("--base-url", required=True)
    compliance.add_argument("--business-ids", action="append", required=True)
    compliance.add_argument("--as-of-date", required=True)
    compliance.add_argument("--account-change-json")
    compliance.set_defaults(func=summarize_compliance)
    prepaids = sub.add_parser("prepaids")
    prepaids.add_argument("--base-url", required=True)
    prepaids.add_argument("--scope-json", required=True)
    prepaids.set_defaults(func=summarize_prepaids)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
