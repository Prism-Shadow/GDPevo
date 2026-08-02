#!/usr/bin/env python3
"""Pull every workbench record for one deal into a single JSON bundle.

    fetch_deal.py <base_url> <deal_id> [out_dir]

Routes are discovered from the deal record's own `links` map rather than assumed, so
this keeps working if the collection routes differ. The governing playbook or policy
named on the deal record is fetched too.

Writes <out_dir>/bundle.json and prints a summary of row counts.
"""
import json
import sys
import urllib.error
import urllib.request


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"_error": f"HTTP {e.code}", "_url": url}
    except Exception as e:  # noqa: BLE001 - surface anything else as data
        return {"_error": str(e), "_url": url}


def unwrap(payload):
    """Workbench collections come back as {"<name>": [...]} - return the payload."""
    if isinstance(payload, dict) and "_error" not in payload:
        lists = [v for v in payload.values() if isinstance(v, list)]
        if len(lists) == 1 and len(payload) <= 2:
            return lists[0]
    return payload


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    base = sys.argv[1].rstrip("/")
    deal_id = sys.argv[2]
    out_dir = sys.argv[3] if len(sys.argv) > 3 else "."

    root = get(f"{base}/api/deals/{deal_id}")
    deal = root.get("deal", root) if isinstance(root, dict) else root
    bundle = {"deal": deal}

    for name, path in (root.get("links") or {}).items():
        bundle[name] = unwrap(get(f"{base}{path}"))

    if isinstance(deal, dict):
        if deal.get("playbook_id"):
            bundle["playbook_rules"] = unwrap(
                get(f"{base}/api/playbooks/{deal['playbook_id']}/rules"))
        if deal.get("policy_id"):
            bundle["policy_thresholds"] = unwrap(
                get(f"{base}/api/policies/{deal['policy_id']}/thresholds"))

    path = f"{out_dir.rstrip('/')}/bundle.json"
    with open(path, "w") as fh:
        json.dump(bundle, fh, indent=1, sort_keys=True)

    print(f"wrote {path}")
    for key, val in sorted(bundle.items()):
        if isinstance(val, list):
            print(f"  {key:24} {len(val)} rows")
        elif isinstance(val, dict) and "_error" in val:
            print(f"  {key:24} ERROR {val['_error']}")
        else:
            print(f"  {key:24} object")

    # Stale draft terms are distractors - call them out rather than silently keeping them.
    terms = bundle.get("terms") or bundle.get("draft_terms") or []
    if isinstance(terms, list):
        stale = [t.get("term_id") for t in terms
                 if isinstance(t, dict) and t.get("staleness_flag") != "current"]
        if stale:
            print(f"\n  NOTE: non-current draft terms (exclude these): {', '.join(stale)}")
        wrong = [t.get("term_id") for t in terms
                 if isinstance(t, dict) and t.get("deal_id") not in (None, deal_id)]
        if wrong:
            print(f"  WARNING: rows for another deal_id leaked in: {', '.join(wrong)}")


if __name__ == "__main__":
    main()
