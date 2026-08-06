#!/usr/bin/env python3
"""Pull one deal's complete record bundle from the M&A workbench.

Usage:
    python3 fetch_deal.py PRJ_XXXX [--base URL] [--out bundle.json] [--quiet]

Base URL resolution: --base, else $GDPEVO_ENV_BASE_URL, else $TASK_ENV_BASE_URL.
Both are documented in environment_access.md.

Writes a single JSON bundle and prints a summary that highlights the things most
often gotten wrong: the bound playbook/policy, stale draft terms, and near-miss
decoy deals sharing a similar project name.
"""

import argparse
import difflib
import json
import os
import sys
import urllib.error
import urllib.request

SUB_ENDPOINTS = {
    "terms": "draft_terms",
    "documents": "documents",
    "benchmarks": "benchmarks",
    "risk-estimates": "risk_estimates",
    "cap-table": "cap_table",
    "consents": "consents",
    "employees": "employees",
    "material-contracts": "material_contracts",
    "regulatory": "regulatory",
    "diligence-findings": "diligence_findings",
    "notes": "deal_notes",
}


def resolve_base(explicit=None):
    base = explicit or os.environ.get("GDPEVO_ENV_BASE_URL") or os.environ.get("TASK_ENV_BASE_URL")
    if not base:
        sys.exit("No base URL. Pass --base or set GDPEVO_ENV_BASE_URL (see environment_access.md).")
    return base.rstrip("/")


def get(base, path, timeout=30):
    url = f"{base}{path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"_error": f"HTTP {exc.code}", "_url": url}
    except Exception as exc:  # noqa: BLE001 - report and continue
        return {"_error": str(exc), "_url": url}


def similar(name, other):
    """Near-miss check on project names, ignoring the 'Project ' prefix.

    Decoys differ by a syllable (Lyra/Lyric, Orion/Oriel, Juniper/Junia) or add a
    suffix (Meridian/Meridian North), so match on a shared 3-char prefix or a high
    overall similarity ratio.
    """
    a = name.replace("Project ", "").strip().lower()
    b = other.replace("Project ", "").strip().lower()
    if not a or not b:
        return False
    if a == b or a.startswith(b) or b.startswith(a):
        return True
    if a[:3] == b[:3]:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deal_id")
    ap.add_argument("--base")
    ap.add_argument("--out")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    base = resolve_base(args.base)
    deal_id = args.deal_id

    detail = get(base, f"/api/deals/{deal_id}")
    if "_error" in detail or "deal" not in detail:
        sys.exit(f"Could not load {deal_id}: {detail}")
    deal = detail["deal"]

    bundle = {"base_url": base, "deal_id": deal_id, "deal": deal}

    for path, key in SUB_ENDPOINTS.items():
        payload = get(base, f"/api/deals/{deal_id}/{path}")
        value = payload.get(key, payload) if isinstance(payload, dict) else payload
        # Defensive: never let another deal's row into the bundle.
        if isinstance(value, list):
            value = [r for r in value if not isinstance(r, dict) or r.get("deal_id", deal_id) == deal_id]
        bundle[key] = value

    pb = deal.get("playbook_id")
    pol = deal.get("policy_id")
    bundle["playbook_rules"] = get(base, f"/api/playbooks/{pb}/rules").get("rules", []) if pb else []
    bundle["policy_thresholds"] = (
        get(base, f"/api/policies/{pol}/thresholds").get("thresholds", []) if pol else []
    )

    all_deals = get(base, "/api/deals").get("deals", [])
    bundle["decoys"] = [
        {k: d.get(k) for k in ("deal_id", "project_name", "target_name", "client_side", "playbook_id", "policy_id")}
        for d in all_deals
        if d.get("deal_id") != deal_id and similar(deal.get("project_name", ""), d.get("project_name", ""))
    ]

    out = args.out or f"{deal_id}_bundle.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, indent=2, sort_keys=True)

    if args.quiet:
        print(out)
        return

    terms = bundle.get("draft_terms") or []
    current = [t for t in terms if t.get("staleness_flag") == "current"]
    stale = [t for t in terms if t.get("staleness_flag") != "current"]

    print(f"bundle -> {out}")
    print(f"\n{deal_id}  {deal.get('project_name')}  ({deal.get('transaction_type')})")
    print(f"  client       : {deal.get('client_name')} as {deal.get('client_side')}")
    print(f"  counterparty : {deal.get('counterparty_name')}   target: {deal.get('target_name')}")
    print(f"  standard     : playbook={pb}  policy={pol}")
    print(
        "  values       : headline={headline_value} upfront={upfront_cash} "
        "stock={stock_value} milestone={milestone_value} {currency}".format(**deal)
    )
    print(f"  dates        : signing={deal.get('signing_date')} meeting={deal.get('meeting_date')}"
          f"  status={deal.get('status')}")

    print(f"\ncurrent draft terms ({len(current)}):")
    for t in current:
        print(f"  {t['term_id']:<26} {t['category']:<28} {t.get('numeric_value')} {t.get('unit')}"
              f"  basis={t.get('basis')}")
    if stale:
        print(f"\nSTALE terms ({len(stale)}) - exclude from the register, list them if the template asks:")
        for t in stale:
            print(f"  {t['term_id']:<26} {t['category']:<28} {t.get('numeric_value')} {t.get('unit')}")

    rules = bundle["playbook_rules"] or bundle["policy_thresholds"]
    if rules:
        rule_cats = {r["category"] for r in rules}
        draft_cats = {t["category"] for t in current}
        missing = sorted(rule_cats - draft_cats)
        if missing:
            print(f"\nstandard categories with NO current term (missing_required_term candidates):")
            for c in missing:
                print(f"  {c}")

    for key in ("consents", "material_contracts", "employees", "diligence_findings", "risk_estimates"):
        rows = bundle.get(key) or []
        print(f"\n{key} ({len(rows)}):")
        for r in rows:
            ident = next((r[k] for k in r if k.endswith("_id") and k != "deal_id"), "?")
            rest = {k: v for k, v in r.items() if k not in ("deal_id", "notes") and not k.endswith("_id")}
            print(f"  {ident:<26} {json.dumps(rest)[:150]}")

    if bundle["decoys"]:
        print(f"\nNEAR-MISS DECOY DEALS ({len(bundle['decoys'])}) - do not read records from these:")
        for d in bundle["decoys"]:
            print(f"  {d['deal_id']:<12} {d['project_name']:<28} side={d['client_side']}"
                  f" pb={d['playbook_id']} pol={d['policy_id']}")


if __name__ == "__main__":
    main()
