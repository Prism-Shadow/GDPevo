#!/usr/bin/env python3
"""Pull every workbench record for one deal into a single JSON bundle.

Usage:
    python3 fetch_deal.py PRJ_XXXX [--base-url URL] [--out bundle.json] [--quiet]

Writes the raw bundle to --out (default deal_<id>.json) and prints a digest:
deal economics, playbook/policy limits with parsed preferred/fallback numbers,
and the roll-up totals that answer templates ask for repeatedly.

Every printed aggregate is also stored in the bundle under "derived", so you can
re-read it without refetching. Treat parsed prose numbers as hints and confirm
them against the quoted source text that accompanies each one.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

TOKEN = "deal-workbench-readonly"

SUBRESOURCES = [
    "terms", "documents", "benchmarks", "risk-estimates", "cap-table",
    "consents", "employees", "material-contracts", "regulatory",
    "diligence-findings", "notes",
]

# JSON key that holds the list inside each sub-resource response
LIST_KEY = {
    "terms": "draft_terms",
    "documents": "documents",
    "benchmarks": "benchmarks",
    "risk-estimates": "risk_estimates",
    "cap-table": "cap_table",
    "consents": "consents",
    "employees": "employees",
    "material-contracts": "material_contracts",
    "diligence-findings": "diligence_findings",
    "notes": "deal_notes",
}


def discover_base_url(explicit=None):
    if explicit:
        return explicit.rstrip("/")
    env = os.environ.get("GDPEVO_ENV_BASE_URL")
    if env:
        return env.rstrip("/")
    for path in ("environment_access.md", "../environment_access.md",
                 "/work/environment_access.md"):
        if os.path.exists(path):
            with open(path) as fh:
                m = re.search(r"BASE_URL\s*=\s*(\S+)", fh.read())
            if m:
                return m.group(1).rstrip("/")
    sys.exit("No base URL: pass --base-url or set GDPEVO_ENV_BASE_URL.")


def get(base, path):
    try:
        with urllib.request.urlopen(base + path, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return {"_error": f"HTTP {exc.code} for {path}"}
    except Exception as exc:  # noqa: BLE001 - surface, don't abort the bundle
        return {"_error": f"{type(exc).__name__} for {path}: {exc}"}


def sql(base, statement):
    body = json.dumps({"token": TOKEN, "sql": statement}).encode()
    req = urllib.request.Request(
        base + "/api/query", data=body,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:  # noqa: BLE001
        return {"_error": str(exc)}


def numbers_in(text):
    """Pull percent / month / day / contract-count figures out of prose."""
    text = text or ""
    return {
        "percents": [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*%", text)],
        "months": [int(x) for x in re.findall(r"(\d+)\s*month", text, re.I)],
        "days": [int(x) for x in re.findall(r"(\d+)\s*day", text, re.I)],
        "millions": [float(x) for x in re.findall(
            r"(\d+(?:\.\d+)?)\s*million", text, re.I)],
        "counts": [int(x) for x in re.findall(
            r"top\s+(\w+)\s+", text, re.I) if x.isdigit()],
    }


def dollars(pct, base_amount):
    """Percent points -> integer dollars, half-up."""
    if pct is None or base_amount is None:
        return None
    return int(pct * base_amount / 100 + 0.5)


def yes(value):
    return str(value).strip().lower() in ("yes", "true", "1")


def build_derived(deal, records, rules, thresholds):
    base_amount = deal.get("headline_value")
    consents = records.get("consents", [])
    contracts = records.get("material-contracts", [])
    employees = records.get("employees", [])
    risks = records.get("risk-estimates", [])
    terms = records.get("terms", [])

    closing = [c for c in consents if yes(c.get("required_for_closing"))]
    non_closing = [c for c in consents if not yes(c.get("required_for_closing"))]
    consent_contracts = [c for c in contracts if yes(c.get("consent_required"))]
    notice_contracts = [c for c in contracts
                        if not yes(c.get("consent_required"))]

    risk_by_cat = {}
    for r in risks:
        risk_by_cat[r.get("category")] = {
            "estimate_id": r.get("estimate_id"),
            "low": r.get("exposure_low"),
            "high": r.get("exposure_high"),
        }

    derived = {
        "economics": {
            "headline_value": base_amount,
            "upfront_cash": deal.get("upfront_cash"),
            "stock_value": deal.get("stock_value"),
            "milestone_value": deal.get("milestone_value"),
            "client_side": deal.get("client_side"),
            "playbook_id": deal.get("playbook_id"),
            "policy_id": deal.get("policy_id"),
            "transaction_type": deal.get("transaction_type"),
            "signing_date": deal.get("signing_date"),
            "meeting_date": deal.get("meeting_date"),
        },
        "terms_current": [t.get("term_id") for t in terms
                          if t.get("staleness_flag") == "current"],
        "terms_stale": [t.get("term_id") for t in terms
                        if t.get("staleness_flag") != "current"],
        "consents": {
            "required_for_closing_ids": [c.get("consent_id") for c in closing],
            "required_for_closing_count": len(closing),
            "required_for_closing_amount": sum(
                c.get("amount_at_risk") or 0 for c in closing),
            "not_required_ids": [c.get("consent_id") for c in non_closing],
            "not_required_amount": sum(
                c.get("amount_at_risk") or 0 for c in non_closing),
        },
        "material_contracts": {
            "consent_required_ids": [c.get("contract_id")
                                     for c in consent_contracts],
            "consent_required_revenue": sum(
                c.get("annual_revenue") or 0 for c in consent_contracts),
            "notice_only_ids": [c.get("contract_id") for c in notice_contracts],
            "top_annual_revenue": max(
                (c.get("annual_revenue") or 0 for c in contracts), default=0),
        },
        "employees": {
            "total_count": sum(e.get("count") or 0 for e in employees),
            "total_pto_liability": sum(
                e.get("pto_liability") or 0 for e in employees),
            "service_credit_ids": [e.get("employee_id") for e in employees
                                   if yes(e.get("service_credit_required"))],
            "warn_risk_ids": [
                e.get("employee_id") for e in employees
                if str(e.get("warn_risk", "")).lower() in ("medium", "high")],
            "by_group": [
                {"employee_id": e.get("employee_id"),
                 "group": e.get("employee_group"),
                 "count": e.get("count"),
                 "pto_liability": e.get("pto_liability"),
                 "warn_risk": e.get("warn_risk"),
                 "draft_treatment": e.get("draft_treatment")}
                for e in employees],
        },
        "risk_estimates": {
            "by_category": risk_by_cat,
            "total_low_all": sum(r.get("exposure_low") or 0 for r in risks),
            "total_high_all": sum(r.get("exposure_high") or 0 for r in risks),
        },
        "playbook_limits": [],
        "policy_limits": [],
        "term_amounts": [],
    }

    for rule in rules:
        derived["playbook_limits"].append({
            "category": rule.get("category"),
            "basis": rule.get("basis"),
            "limit_value": rule.get("limit_value"),
            "limit_unit": rule.get("limit_unit"),
            "risk_default": rule.get("risk_default"),
            "preferred_text": rule.get("preferred_position"),
            "preferred_parsed": numbers_in(rule.get("preferred_position")),
            "fallback_text": rule.get("fallback_position"),
            "fallback_parsed": numbers_in(rule.get("fallback_position")),
        })

    for th in thresholds:
        derived["policy_limits"].append({
            "category": th.get("category"),
            "basis": th.get("basis"),
            "threshold_value": th.get("threshold_value"),
            "threshold_unit": th.get("threshold_unit"),
            "restricted_flag": th.get("restricted_flag"),
            "approval_required": th.get("approval_required"),
            "policy_standard": th.get("policy_standard"),
            "threshold_amount_on_headline": dollars(
                th.get("threshold_value"), base_amount)
            if th.get("threshold_unit") == "percent_points" else None,
        })

    for t in terms:
        entry = {
            "term_id": t.get("term_id"),
            "category": t.get("category"),
            "staleness_flag": t.get("staleness_flag"),
            "basis": t.get("basis"),
            "unit": t.get("unit"),
            "numeric_value": t.get("numeric_value"),
            "draft_value": t.get("draft_value"),
            "prose_numbers": numbers_in(t.get("draft_value")),
        }
        if t.get("unit") == "percent_points" and t.get("numeric_value") is not None:
            entry["amount_on_headline"] = dollars(t["numeric_value"], base_amount)
        derived["term_amounts"].append(entry)

    return derived


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deal_id")
    ap.add_argument("--base-url")
    ap.add_argument("--out")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    base = discover_base_url(args.base_url)
    did = args.deal_id

    root = get(base, f"/api/deals/{did}")
    if "_error" in root or "deal" not in root:
        sys.exit(f"Could not load deal {did}: {root}")
    deal = root["deal"]

    records = {}
    for sub in SUBRESOURCES:
        payload = get(base, f"/api/deals/{did}/{sub}")
        if sub == "regulatory":
            records[sub] = payload.get("regulatory", payload)
        else:
            records[sub] = payload.get(LIST_KEY[sub], [])

    rules = []
    if deal.get("playbook_id"):
        rules = get(base, f"/api/playbooks/{deal['playbook_id']}/rules").get(
            "rules", [])
    thresholds = []
    if deal.get("policy_id"):
        thresholds = get(
            base, f"/api/policies/{deal['policy_id']}/thresholds").get(
                "thresholds", [])

    bundle = {
        "deal_id": did,
        "base_url": base,
        "deal": deal,
        "records": records,
        "playbook_rules": rules,
        "policy_thresholds": thresholds,
    }
    bundle["derived"] = build_derived(deal, records, rules, thresholds)

    out = args.out or f"deal_{did}.json"
    with open(out, "w") as fh:
        json.dump(bundle, fh, indent=1, sort_keys=True)

    if args.quiet:
        print(out)
        return

    d = bundle["derived"]
    print(f"# {did} -> {out}")
    print(json.dumps(d["economics"], indent=1))
    print(f"current terms: {d['terms_current']}")
    print(f"STALE terms (exclude unless asked): {d['terms_stale']}")
    print(json.dumps({k: d[k] for k in
                      ("consents", "material_contracts", "employees",
                       "risk_estimates")}, indent=1))
    print("## playbook limits")
    for r in d["playbook_limits"]:
        print(f"  {r['category']}: limit={r['limit_value']} {r['limit_unit']}"
              f" | risk_default={r['risk_default']}")
        print(f"    preferred: {r['preferred_text']}")
        print(f"    fallback : {r['fallback_text']}")
    print("## policy limits")
    for r in d["policy_limits"]:
        print(f"  {r['category']}: {r['threshold_value']} {r['threshold_unit']}"
              f" | restricted={r['restricted_flag']}"
              f" | approval={r['approval_required']}")
    print("## draft terms")
    for t in d["term_amounts"]:
        print(f"  {t['term_id']} [{t['staleness_flag']}] {t['category']}"
              f" = {t['numeric_value']} {t['unit']} (basis: {t['basis']})"
              f" -> {t.get('amount_on_headline')}")
        print(f"    {t['draft_value']}")


if __name__ == "__main__":
    main()
