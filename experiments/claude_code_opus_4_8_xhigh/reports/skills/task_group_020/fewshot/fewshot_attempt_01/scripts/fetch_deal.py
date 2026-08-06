#!/usr/bin/env python3
"""Pull every workbench record for one deal into a single JSON bundle.

The workbench holds ~85 deals, many with near-identical project/target names.
Every fetch here is keyed on the exact deal_id, so the bundle can never mix in a
neighbouring deal's rows.

Usage:
    python3 fetch_deal.py PRJ_EXAMPLE                     # bundle to stdout
    python3 fetch_deal.py PRJ_EXAMPLE -o bundle.json      # bundle to file
    python3 fetch_deal.py PRJ_EXAMPLE --triage            # + reviewer triage report
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = os.environ.get("GDPEVO_ENV_BASE_URL", "http://task-env:9020/")
DEFAULT_TOKEN = "deal-workbench-readonly"

# Per-deal sub-resources. Key = bundle key, value = URL suffix.
DEAL_SECTIONS = {
    "terms": "terms",
    "documents": "documents",
    "benchmarks": "benchmarks",
    "risk_estimates": "risk-estimates",
    "cap_table": "cap-table",
    "consents": "consents",
    "employees": "employees",
    "material_contracts": "material-contracts",
    "regulatory": "regulatory",
    "diligence_findings": "diligence-findings",
    "notes": "notes",
}


def get_json(url, timeout=30):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_json(url, payload, timeout=30):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def unwrap(payload, prefer=None):
    """Endpoints wrap their payload in a single key.

    Shapes seen: {"consents": [...]}, {"regulatory": {...}} (a bare object, not a
    list) and {"deal": {...}, "links": {...}}. Prefer an explicitly named key,
    otherwise take the sole list/dict value and drop navigation keys like "links".
    """
    if not isinstance(payload, dict):
        return payload
    if prefer and prefer in payload:
        return payload[prefer]
    payload = {k: v for k, v in payload.items()
               if k not in ("links", "count") and isinstance(v, (list, dict))}
    if len(payload) == 1:
        return next(iter(payload.values()))
    return payload


def fetch_bundle(base, deal_id, token):
    base = base.rstrip("/")
    bundle = {"deal_id": deal_id, "_source": base}
    errors = {}

    try:
        bundle["deal"] = unwrap(get_json(f"{base}/api/deals/{deal_id}"), prefer="deal")
    except urllib.error.HTTPError as exc:
        sys.exit(f"ERROR: deal {deal_id} not reachable ({exc.code}). Check the deal_id.")

    deal = bundle["deal"]
    if isinstance(deal, list):
        deal = deal[0] if deal else {}
        bundle["deal"] = deal

    for key, suffix in DEAL_SECTIONS.items():
        try:
            bundle[key] = unwrap(get_json(f"{base}/api/deals/{deal_id}/{suffix}"))
        except Exception as exc:  # endpoint may not exist for every deal
            bundle[key] = []
            errors[key] = str(exc)

    # Governing standard: a deal carries a playbook_id, a policy_id, or both.
    playbook_id = deal.get("playbook_id")
    if playbook_id:
        try:
            bundle["playbook_rules"] = unwrap(
                get_json(f"{base}/api/playbooks/{playbook_id}/rules")
            )
            bundle["playbook_id"] = playbook_id
        except Exception as exc:
            errors["playbook_rules"] = str(exc)

    policy_id = deal.get("policy_id")
    if policy_id:
        try:
            bundle["policy_thresholds"] = unwrap(
                get_json(f"{base}/api/policies/{policy_id}/thresholds")
            )
            bundle["policy_id"] = policy_id
        except Exception as exc:
            errors["policy_thresholds"] = str(exc)

    if errors:
        bundle["_fetch_errors"] = errors
    return bundle


def rows(bundle, key):
    """Section rows as a list. Single-object sections (regulatory) become [obj]."""
    val = bundle.get(key)
    if isinstance(val, list):
        return val
    if isinstance(val, dict):
        return [val]
    return []


def triage(bundle):
    """Print the checks a reviewer must make before drafting the answer."""
    out = []
    deal = bundle.get("deal", {})
    add = out.append

    add("=" * 68)
    add(f"TRIAGE  {bundle['deal_id']}  ({deal.get('project_name')})")
    add("=" * 68)
    add(f"  client_side      : {deal.get('client_side')}")
    add(f"  transaction_type : {deal.get('transaction_type')}")
    add(f"  headline_value   : {deal.get('headline_value')}")
    add(f"  upfront_cash     : {deal.get('upfront_cash')}")
    add(f"  stock_value      : {deal.get('stock_value')}")
    add(f"  milestone_value  : {deal.get('milestone_value')}")
    add(f"  playbook_id      : {deal.get('playbook_id')}")
    add(f"  policy_id        : {deal.get('policy_id')}")
    add(f"  signing_date     : {deal.get('signing_date')}")
    add(f"  meeting_date     : {deal.get('meeting_date')}")

    # 1. Stale terms are the single most common trap.
    add("")
    add("-- DRAFT TERMS (exclude anything not 'current') " + "-" * 20)
    for t in rows(bundle, "terms"):
        flag = str(t.get("staleness_flag", "?"))
        mark = "  " if flag == "current" else "!!"
        add(f"{mark} {t.get('term_id')}  [{flag}]  {t.get('category')}"
            f"  = {t.get('numeric_value')} {t.get('unit')}  ({t.get('clause_ref')})")
        add(f"     draft: {t.get('draft_value')}")
    stale = [t.get("term_id") for t in rows(bundle, "terms")
             if t.get("staleness_flag") != "current"]
    if stale:
        add(f"  ** EXCLUDE stale term ids: {stale}")

    # 2. Playbook / policy positions live in prose, not only in limit_value.
    if bundle.get("playbook_rules"):
        add("")
        add("-- PLAYBOOK RULES (read the prose for preferred vs fallback) " + "-" * 6)
        for r in bundle["playbook_rules"]:
            add(f"   {r.get('category')}  limit={r.get('limit_value')} "
                f"{r.get('limit_unit')}  risk_default={r.get('risk_default')}")
            add(f"     preferred: {r.get('preferred_position')}")
            add(f"     fallback : {r.get('fallback_position')}")
    if bundle.get("policy_thresholds"):
        add("")
        add("-- POLICY THRESHOLDS (escalate restricted_flag=yes only) " + "-" * 9)
        for p in bundle["policy_thresholds"]:
            mark = "  " if str(p.get("restricted_flag")).lower() == "yes" else ".."
            add(f"{mark} {p.get('category')}  threshold={p.get('threshold_value')} "
                f"{p.get('threshold_unit')}  basis={p.get('basis')}  "
                f"approval={p.get('approval_required')}  "
                f"restricted={p.get('restricted_flag')}")

    # 3. Consents split on required_for_closing.
    add("")
    add("-- CONSENTS " + "-" * 54)
    closing_total = 0
    for c in rows(bundle, "consents"):
        req = str(c.get("required_for_closing", "")).lower()
        amt = c.get("amount_at_risk") or 0
        if req == "yes":
            closing_total += amt
        add(f"   {c.get('consent_id')}  closing={req:<4} risk={c.get('risk_rating')}"
            f"  at_risk={amt}  {c.get('contract_name')}")
    add(f"   => closing-required amount_at_risk total = {closing_total}")

    # 4. Material contracts split on consent_required (yes vs 'notice only').
    add("")
    add("-- MATERIAL CONTRACTS " + "-" * 45)
    consent_rev = 0
    for m in rows(bundle, "material_contracts"):
        cr = str(m.get("consent_required", "")).lower()
        rev = m.get("annual_revenue") or 0
        if cr == "yes":
            consent_rev += rev
        add(f"   {m.get('contract_id')}  consent={cr:<12} type={m.get('contract_type')}"
            f"  revenue={rev}")
    add(f"   => consent-required annual revenue total = {consent_rev}")

    # 5. Employees: per-group and deal totals both get asked for.
    add("")
    add("-- EMPLOYEES " + "-" * 53)
    head = pto = 0
    for e in rows(bundle, "employees"):
        head += e.get("count") or 0
        pto += e.get("pto_liability") or 0
        add(f"   {e.get('employee_id')}  {e.get('employee_group')}: "
            f"count={e.get('count')} pto={e.get('pto_liability')} "
            f"service_credit={e.get('service_credit_required')} "
            f"warn={e.get('warn_risk')}")
        add(f"     draft: {e.get('draft_treatment')}")
        add(f"     req  : {e.get('playbook_requirement')}")
    add(f"   => TOTAL headcount = {head}   TOTAL pto_liability = {pto}")

    # 6. Risk estimates: copy verbatim, never round.
    add("")
    add("-- RISK ESTIMATES (use exact values; some end in odd digits) " + "-" * 6)
    lo = hi = 0
    for r in rows(bundle, "risk_estimates"):
        lo += r.get("exposure_low") or 0
        hi += r.get("exposure_high") or 0
        add(f"   {r.get('estimate_id')}  {r.get('category')}: "
            f"low={r.get('exposure_low')} high={r.get('exposure_high')}")
    add(f"   => ALL-category sum: low = {lo}   high = {hi}")

    add("")
    add("-- BENCHMARKS " + "-" * 52)
    for b in rows(bundle, "benchmarks"):
        add(f"   {b.get('benchmark_id')}  {b.get('metric')}: n={b.get('sample_size')} "
            f"median={b.get('median_value')} upper_quartile={b.get('upper_quartile')}")

    add("")
    add("-- REGULATORY " + "-" * 52)
    for r in rows(bundle, "regulatory"):
        add(f"   hsr_required={r.get('hsr_required')} basis={r.get('threshold_basis')} "
            f"approval={r.get('regulatory_approval')} "
            f"hell_or_high_water={r.get('hell_or_high_water_required')}")

    add("")
    add("-- DILIGENCE FINDINGS " + "-" * 44)
    for f in rows(bundle, "diligence_findings"):
        add(f"   {f.get('finding_id')}  {f.get('topic')} [{f.get('severity')}] "
            f"amount={f.get('amount')}")

    add("")
    add("-- DOCUMENTS / NOTES " + "-" * 45)
    for d in rows(bundle, "documents"):
        add(f"   {d.get('document_id')}  {d.get('document_type')} "
            f"v{d.get('version')}  {d.get('title')}")
    for n in rows(bundle, "notes"):
        snippet = str(n.get("content") or n.get("note") or n.get("summary") or "")[:110]
        add(f"   {n.get('note_id', '')}  [{n.get('topic', '')}] {snippet}")

    hv = deal.get("headline_value")
    if isinstance(hv, (int, float)) and hv:
        add("")
        add("-- PERCENT-OF-HEADLINE READY RECKONER " + "-" * 28)
        add(f"   basis = {int(hv)}")
        for pct in (2.5, 5.0, 6.0, 8.0, 10.0, 12.0, 12.5, 15.0, 18.0, 20.0):
            add(f"     {pct:>5}% = {int(round(hv * pct / 100.0))}")

    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deal_id")
    ap.add_argument("--base-url", default=DEFAULT_BASE)
    ap.add_argument("--token", default=DEFAULT_TOKEN)
    ap.add_argument("-o", "--out", help="write bundle JSON here")
    ap.add_argument("--triage", action="store_true",
                    help="print the reviewer triage report to stderr")
    args = ap.parse_args()

    bundle = fetch_bundle(args.base_url, args.deal_id, args.token)

    if args.out:
        with open(args.out, "w") as fh:
            json.dump(bundle, fh, indent=2, sort_keys=True)
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(json.dumps(bundle, indent=2, sort_keys=True))

    if args.triage:
        print(triage(bundle), file=sys.stderr)


if __name__ == "__main__":
    main()
