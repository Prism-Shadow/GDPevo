#!/usr/bin/env python3
"""Pull every workbench record for one deal and print a digest for analysis.

Usage:
    python3 pull_deal.py <base_url> <deal_id> [--json] [--sql-token TOKEN]

<base_url> and any SQL token come from the task prompt; nothing is hardcoded here.

The digest highlights the fields that decide the answer: current-vs-stale draft terms, the
applicable playbook/policy limits, and the filtered aggregates (closing consents, consent-gated
contract revenue, PTO, modeled exposure) that summary blocks are built from.
"""

import argparse
import json
import sys
import urllib.request

TIMEOUT = 30
# Per-deal record sets; the deal record's own "links" object is authoritative and is
# used to extend this list at runtime.
SUBRESOURCES = [
    "terms", "cap-table", "consents", "employees", "material-contracts",
    "regulatory", "diligence-findings", "benchmarks", "risk-estimates",
    "notes", "documents",
]


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode())
    except Exception as exc:                                  # noqa: BLE001
        return {"_error": f"{type(exc).__name__}: {exc}"}


def unwrap(payload):
    """API responses wrap their payload in a single descriptive key."""
    if not isinstance(payload, dict) or "_error" in payload:
        return payload
    for value in payload.values():
        if isinstance(value, (list, dict)):
            return value
    return payload


def money(rows, field, where=None):
    total = 0
    for row in rows or []:
        if where and not where(row):
            continue
        total += int(row.get(field) or 0)
    return total


def fetch(base, deal_id):
    base = base.rstrip("/")
    bundle = {}
    deal_doc = get(f"{base}/api/deals/{deal_id}")
    bundle["deal"] = (deal_doc or {}).get("deal", deal_doc)

    names = list(SUBRESOURCES)
    for route in ((deal_doc or {}).get("links") or {}).values():
        leaf = str(route).rstrip("/").rsplit("/", 1)[-1]
        if leaf and leaf not in names:
            names.append(leaf)

    for name in names:
        bundle[name.replace("-", "_")] = unwrap(get(f"{base}/api/deals/{deal_id}/{name}"))

    deal = bundle.get("deal") or {}
    if deal.get("playbook_id"):
        bundle["playbook_rules"] = unwrap(
            get(f"{base}/api/playbooks/{deal['playbook_id']}/rules"))
    if deal.get("policy_id"):
        bundle["policy_thresholds"] = unwrap(
            get(f"{base}/api/policies/{deal['policy_id']}/thresholds"))
    return bundle


def digest(b):
    deal = b.get("deal") or {}
    out = ["=" * 78, f"DEAL {deal.get('deal_id')} — {deal.get('project_name')}", "=" * 78]
    for k in ("client_name", "client_side", "counterparty_name", "target_name",
              "transaction_type", "status", "signing_date", "meeting_date",
              "headline_value", "upfront_cash", "stock_value", "milestone_value",
              "playbook_id", "policy_id"):
        out.append(f"  {k:<20} {deal.get(k)}")

    terms = b.get("terms") or []
    current = [t for t in terms if t.get("staleness_flag") == "current"]
    stale = [t for t in terms if t.get("staleness_flag") != "current"]
    out += ["", f"-- CURRENT DRAFT TERMS ({len(current)}) --"]
    for t in current:
        out.append(f"  {t.get('term_id')}  {t.get('category')}  "
                   f"{t.get('numeric_value')} {t.get('unit')}  basis={t.get('basis')}  "
                   f"[{t.get('clause_ref')}]")
        out.append(f"      {t.get('draft_value')}")
    if stale:
        out.append(f"-- STALE / EXCLUDE ({len(stale)}) --")
        for t in stale:
            out.append(f"  {t.get('term_id')}  {t.get('category')}  "
                       f"{t.get('numeric_value')} {t.get('unit')}  <-- distractor")

    for key, label in (("playbook_rules", "PLAYBOOK RULES"),
                       ("policy_thresholds", "POLICY THRESHOLDS")):
        if b.get(key):
            out += ["", f"-- {label} --"]
            for r in b[key]:
                if key == "playbook_rules":
                    out.append(f"  {r.get('category')}: limit={r.get('limit_value')} "
                               f"{r.get('limit_unit')} basis={r.get('basis')} "
                               f"risk={r.get('risk_default')}")
                    out.append(f"      preferred: {r.get('preferred_position')}")
                    out.append(f"      fallback : {r.get('fallback_position')}")
                    out.append(f"      action   : {r.get('required_action')}")
                else:
                    out.append(f"  {r.get('category')}: threshold={r.get('threshold_value')} "
                               f"{r.get('threshold_unit')} restricted={r.get('restricted_flag')} "
                               f"approval={r.get('approval_required')}")
                    out.append(f"      standard : {r.get('policy_standard')}")

    cons = b.get("consents") or []
    mats = b.get("material_contracts") or []
    emps = b.get("employees") or []
    risks = b.get("risk_estimates") or []

    out += ["", "-- CONSENTS --"]
    for c in cons:
        out.append(f"  {c.get('consent_id')}  closing={c.get('required_for_closing')}  "
                   f"risk={c.get('risk_rating')}  at_risk={c.get('amount_at_risk')}  "
                   f"{c.get('contract_name')} / {c.get('counterparty')}")
    out += ["-- MATERIAL CONTRACTS --"]
    for m in mats:
        out.append(f"  {m.get('contract_id')}  consent={m.get('consent_required')}  "
                   f"rev={m.get('annual_revenue')}  coc={m.get('change_of_control')}  "
                   f"{m.get('contract_name')}")
    out += ["-- EMPLOYEES --"]
    for e in emps:
        out.append(f"  {e.get('employee_id')}  {e.get('employee_group')}  n={e.get('count')}  "
                   f"pto={e.get('pto_liability')}  credit={e.get('service_credit_required')}  "
                   f"warn={e.get('warn_risk')}")
        out.append(f"      draft: {e.get('draft_treatment')}")
        out.append(f"      req  : {e.get('playbook_requirement')}")
    out += ["-- RISK ESTIMATES --"]
    for r in risks:
        out.append(f"  {r.get('estimate_id')}  {r.get('category')}  "
                   f"low={r.get('exposure_low')}  high={r.get('exposure_high')}")

    reg = b.get("regulatory") or {}
    if reg:
        out += ["-- REGULATORY --",
                f"  hsr={reg.get('hsr_required')}  basis={reg.get('threshold_basis')}  "
                f"approval={reg.get('regulatory_approval')}  "
                f"hohw={reg.get('hell_or_high_water_required')}"]

    for f in b.get("diligence_findings") or []:
        out.append(f"  FINDING {f.get('finding_id')}  {f.get('topic')}  "
                   f"{f.get('severity')}  {f.get('amount')}")

    hv = int(deal.get("headline_value") or 0)
    out += ["", "-- DERIVED AGGREGATES (verify before use) --",
            f"  headline_value                     {hv}",
            f"  closing_consent_amount_at_risk     "
            f"{money(cons, 'amount_at_risk', lambda c: c.get('required_for_closing') == 'yes')}",
            f"  all_consent_amount_at_risk         {money(cons, 'amount_at_risk')}",
            f"  contract_revenue_consent_required  "
            f"{money(mats, 'annual_revenue', lambda m: m.get('consent_required') == 'yes')}",
            f"  total_employee_count               {money(emps, 'count')}",
            f"  total_pto_liability                {money(emps, 'pto_liability')}",
            f"  modeled_exposure_low / high        "
            f"{money(risks, 'exposure_low')} / {money(risks, 'exposure_high')}"]
    out.append("  percent-of-headline reference (recompute against the term's own basis):")
    for pct in (1, 2.5, 5, 7.5, 10, 15, 20):
        out.append(f"      {pct:>5}% -> {round(hv * pct / 100)}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base_url")
    ap.add_argument("deal_id")
    ap.add_argument("--json", action="store_true", help="dump the raw bundle instead")
    ap.add_argument("--sql-token", help="token for the read-only SQL endpoint")
    ap.add_argument("--sql", help="run one read-only query and print the rows")
    args = ap.parse_args()

    if args.sql:
        if not args.sql_token:
            sys.exit("--sql requires --sql-token")
        req = urllib.request.Request(
            args.base_url.rstrip("/") + "/api/query",
            data=json.dumps({"token": args.sql_token, "sql": args.sql}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            print(r.read().decode())
        return

    bundle = fetch(args.base_url, args.deal_id)
    print(json.dumps(bundle, indent=1) if args.json else digest(bundle))


if __name__ == "__main__":
    main()
