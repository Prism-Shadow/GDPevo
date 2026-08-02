#!/usr/bin/env python3
"""Pull the complete M&A deal-workbench record bundle for one deal.

Fetches every per-deal endpoint plus the playbook / policy the deal points at,
so the whole evidence base for an answer lands in one place.

Usage:
    python3 fetch_deal.py PRJ_EXAMPLE                     # full JSON bundle
    python3 fetch_deal.py PRJ_EXAMPLE --summary           # compact triage view
    python3 fetch_deal.py PRJ_EXAMPLE --out bundle.json
    python3 fetch_deal.py PRJ_EXAMPLE --base-url http://host:9020/

Base URL resolution order: --base-url, $TASK_ENV_BASE_URL, $GDPEVO_ENV_BASE_URL,
then http://task-env:9020/.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = "http://task-env:9020/"

# endpoint suffix -> key that holds the list/object in the response envelope
DEAL_ENDPOINTS = {
    "terms": "draft_terms",
    "benchmarks": "benchmarks",
    "risk-estimates": "risk_estimates",
    "cap-table": "cap_table",
    "consents": "consents",
    "employees": "employees",
    "material-contracts": "material_contracts",
    "regulatory": "regulatory",
    "diligence-findings": "diligence_findings",
    "notes": "deal_notes",
    "documents": "documents",
}


def resolve_base(explicit):
    base = (
        explicit
        or os.environ.get("TASK_ENV_BASE_URL")
        or os.environ.get("GDPEVO_ENV_BASE_URL")
        or DEFAULT_BASE
    )
    return base.rstrip("/")


def get(base, path, timeout=30):
    url = base + path
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"_error": f"HTTP {exc.code} for {path}"}
    except Exception as exc:  # noqa: BLE001 - surface transport errors inline
        return {"_error": f"{type(exc).__name__}: {exc} for {path}"}


def unwrap(payload, key):
    """Return the payload's meaningful body, tolerating envelope drift."""
    if isinstance(payload, dict):
        if "_error" in payload:
            return payload
        if key in payload:
            return payload[key]
        # fall back to the single non-metadata value
        candidates = [v for k, v in payload.items() if k not in ("deal_id", "links", "count")]
        if len(candidates) == 1:
            return candidates[0]
    return payload


def fetch_bundle(base, deal_id):
    bundle = {"deal_id": deal_id, "base_url": base}

    deal_payload = get(base, f"/api/deals/{deal_id}")
    deal = unwrap(deal_payload, "deal")
    bundle["deal"] = deal

    for suffix, key in DEAL_ENDPOINTS.items():
        bundle[key] = unwrap(get(base, f"/api/deals/{deal_id}/{suffix}"), key)

    playbook_id = deal.get("playbook_id") if isinstance(deal, dict) else None
    policy_id = deal.get("policy_id") if isinstance(deal, dict) else None
    bundle["playbook_id"] = playbook_id
    bundle["policy_id"] = policy_id
    bundle["playbook_rules"] = (
        unwrap(get(base, f"/api/playbooks/{playbook_id}/rules"), "rules") if playbook_id else []
    )
    bundle["policy_thresholds"] = (
        unwrap(get(base, f"/api/policies/{policy_id}/thresholds"), "thresholds")
        if policy_id
        else []
    )
    return bundle


def split_terms(terms):
    current, stale = [], []
    for t in terms or []:
        if not isinstance(t, dict):
            continue
        (current if str(t.get("staleness_flag", "")).lower() == "current" else stale).append(t)
    return current, stale


def money(v):
    return f"{v:,}" if isinstance(v, (int, float)) else str(v)


def summarize(bundle):
    out = []
    deal = bundle.get("deal") or {}
    add = out.append

    add("=" * 72)
    add(f"DEAL {bundle['deal_id']}  ({deal.get('project_name')})")
    add("=" * 72)
    for f in (
        "client_name",
        "client_side",
        "counterparty_name",
        "target_name",
        "transaction_type",
        "status",
        "industry",
        "signing_date",
        "meeting_date",
        "playbook_id",
        "policy_id",
    ):
        add(f"  {f:22} {deal.get(f)}")
    add("  -- value base --")
    for f in ("currency", "headline_value", "upfront_cash", "stock_value", "milestone_value"):
        add(f"  {f:22} {money(deal.get(f))}")
    ctx = deal.get("strategic_context")
    if ctx:
        add(f"  strategic_context      {ctx}")

    current, stale = split_terms(bundle.get("draft_terms"))
    add("")
    add(f"DRAFT TERMS - CURRENT ({len(current)})   << analyze these")
    for t in current:
        add(
            f"  {t.get('term_id')}  {t.get('category')}  "
            f"[{t.get('numeric_value')} {t.get('unit')}] basis={t.get('basis')} "
            f"clause={t.get('clause_ref')}"
        )
        add(f"      draft: {t.get('draft_value')}")
        if t.get("counterparty_rationale"):
            add(f"      rationale: {t.get('counterparty_rationale')}")
    add(f"DRAFT TERMS - STALE ({len(stale)})   << EXCLUDE from analysis")
    for t in stale:
        add(f"  {t.get('term_id')}  {t.get('category')}  [{t.get('numeric_value')} {t.get('unit')}]")

    rules = bundle.get("playbook_rules") or []
    if rules:
        add("")
        add(f"PLAYBOOK {bundle.get('playbook_id')} ({len(rules)} rules)")
        for r in rules:
            add(
                f"  {r.get('category')}  limit={r.get('limit_value')} {r.get('limit_unit')}  "
                f"risk_default={r.get('risk_default')}  basis={r.get('basis')}"
            )
            add(f"      preferred: {r.get('preferred_position')}")
            add(f"      fallback : {r.get('fallback_position')}")
            if r.get("required_action"):
                add(f"      action   : {r.get('required_action')}")

    thresholds = bundle.get("policy_thresholds") or []
    if thresholds:
        add("")
        add(f"POLICY {bundle.get('policy_id')} ({len(thresholds)} thresholds)")
        for p in thresholds:
            add(
                f"  {p.get('category')}  threshold={p.get('threshold_value')} "
                f"{p.get('threshold_unit')}  restricted={p.get('restricted_flag')}  "
                f"approval={p.get('approval_required')}  basis={p.get('basis')}"
            )
            add(f"      standard: {p.get('policy_standard')}")

    cons = bundle.get("consents") or []
    if cons:
        add("")
        add("CONSENTS")
        req_total = 0
        for c in cons:
            flag = str(c.get("required_for_closing", "")).lower()
            mark = "REQUIRED" if flag == "yes" else "notice/non-blocking"
            if flag == "yes":
                req_total += c.get("amount_at_risk") or 0
            add(
                f"  {c.get('consent_id')}  {mark}  risk={c.get('risk_rating')}  "
                f"at_risk={money(c.get('amount_at_risk'))}  {c.get('contract_name')} "
                f"/ {c.get('counterparty')}  ({c.get('consent_type')})"
            )
        add(f"  >> required-for-closing amount_at_risk total = {money(req_total)}")

    mats = bundle.get("material_contracts") or []
    if mats:
        add("")
        add("MATERIAL CONTRACTS")
        rev_total = 0
        for m in mats:
            cr = str(m.get("consent_required", "")).lower()
            if cr == "yes":
                rev_total += m.get("annual_revenue") or 0
            add(
                f"  {m.get('contract_id')}  consent_required={m.get('consent_required')}  "
                f"coc={m.get('change_of_control')}  anti_assign={m.get('anti_assignment')}  "
                f"rev={money(m.get('annual_revenue'))}  {m.get('contract_name')} "
                f"({m.get('contract_type')})"
            )
        add(f"  >> consent_required=yes annual_revenue total = {money(rev_total)}")

    emps = bundle.get("employees") or []
    if emps:
        add("")
        add("EMPLOYEES")
        head = pto = 0
        for e in emps:
            head += e.get("count") or 0
            pto += e.get("pto_liability") or 0
            add(
                f"  {e.get('employee_id')}  {e.get('employee_group')}  count={e.get('count')}  "
                f"pto={money(e.get('pto_liability'))}  service_credit={e.get('service_credit_required')}  "
                f"warn={e.get('warn_risk')}"
            )
            add(f"      draft: {e.get('draft_treatment')}")
            add(f"      playbook: {e.get('playbook_requirement')}")
        add(f"  >> total headcount = {head}   total pto_liability = {money(pto)}")

    risks = bundle.get("risk_estimates") or []
    if risks:
        add("")
        add("RISK ESTIMATES")
        lo = hi = 0
        for r in risks:
            lo += r.get("exposure_low") or 0
            hi += r.get("exposure_high") or 0
            add(
                f"  {r.get('estimate_id')}  {r.get('category')}  "
                f"low={money(r.get('exposure_low'))}  high={money(r.get('exposure_high'))}  "
                f"conf={r.get('confidence')}"
            )
        add(f"  >> ALL-category totals: low = {money(lo)}   high = {money(hi)}")

    finds = bundle.get("diligence_findings") or []
    if finds:
        add("")
        add("DILIGENCE FINDINGS")
        for f in finds:
            add(
                f"  {f.get('finding_id')}  {f.get('topic')}  sev={f.get('severity')}  "
                f"amount={money(f.get('amount'))}  ({f.get('source')})"
            )
            add(f"      {f.get('notes')}")

    bms = bundle.get("benchmarks") or []
    if bms:
        add("")
        add("BENCHMARKS")
        for b in bms:
            add(
                f"  {b.get('benchmark_id')}  {b.get('category')}  metric={b.get('metric')}  "
                f"n={b.get('sample_size')}  median={b.get('median_value')}  "
                f"mean={b.get('mean_value')}  UQ={b.get('upper_quartile')}"
            )

    reg = bundle.get("regulatory")
    if isinstance(reg, dict) and reg:
        add("")
        add("REGULATORY")
        for k, v in reg.items():
            if k != "deal_id":
                add(f"  {k:32} {v}")

    docs = bundle.get("documents") or []
    if docs:
        add("")
        add("DOCUMENTS")
        for d in docs:
            add(
                f"  {d.get('document_id')}  {d.get('document_type')}  {d.get('version')}  "
                f"{d.get('effective_date')}  {d.get('title')}"
            )

    notes = bundle.get("deal_notes") or []
    if notes:
        add("")
        add("NOTES")
        for n in notes:
            add(f"  {n.get('note_id')}  {n.get('topic')} ({n.get('note_date')}, {n.get('author')})")
            add(f"      {n.get('content')}")

    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deal_id")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--summary", action="store_true", help="compact triage view instead of raw JSON")
    ap.add_argument("--out", default=None, help="also write the raw JSON bundle to this path")
    args = ap.parse_args()

    base = resolve_base(args.base_url)
    bundle = fetch_bundle(base, args.deal_id)

    deal = bundle.get("deal")
    if not isinstance(deal, dict) or deal.get("_error") or not deal.get("deal_id"):
        print(f"ERROR: could not load deal {args.deal_id} from {base}", file=sys.stderr)
        print(json.dumps(deal, indent=2)[:800], file=sys.stderr)
        return 2

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(bundle, fh, indent=2, sort_keys=True)
        print(f"wrote {args.out}", file=sys.stderr)

    print(summarize(bundle) if args.summary else json.dumps(bundle, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
