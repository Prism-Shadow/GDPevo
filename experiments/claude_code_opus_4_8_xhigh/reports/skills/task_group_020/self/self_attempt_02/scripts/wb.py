#!/usr/bin/env python3
"""Client for the M&A deal workbench.

Base URL and SQL token come from environment_access.md. Override with the
GDPEVO_ENV_BASE_URL / WB_TOKEN environment variables or the --base / --token
flags.

    wb.py bundle PRJ_XXXX [--out DIR]   every table for one deal
    wb.py deals [--grep TEXT]           list deals (id, name, side, playbook)
    wb.py get /api/deals/PRJ_XXXX       raw endpoint, pretty-printed
    wb.py sql "SELECT ..."              read-only SQL, table or --json
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = os.environ.get("GDPEVO_ENV_BASE_URL", "http://task-env:9020/")
DEFAULT_TOKEN = os.environ.get("WB_TOKEN", "deal-workbench-readonly")
TIMEOUT = 30

# (url suffix, wrapper key in the response)
DEAL_RESOURCES = [
    ("", "deal"),
    ("/terms", "draft_terms"),
    ("/cap-table", "cap_table"),
    ("/consents", "consents"),
    ("/employees", "employees"),
    ("/material-contracts", "material_contracts"),
    ("/regulatory", "regulatory"),
    ("/diligence-findings", "diligence_findings"),
    ("/benchmarks", "benchmarks"),
    ("/risk-estimates", "risk_estimates"),
    ("/notes", "deal_notes"),
    ("/documents", "documents"),
]


def _url(base, path):
    return base.rstrip("/") + "/" + path.lstrip("/")


def get(base, path):
    req = urllib.request.Request(_url(base, path), headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())


def sql(base, token, statement):
    body = json.dumps({"token": token, "sql": statement}).encode()
    req = urllib.request.Request(
        _url(base, "/api/query"), data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())


def unwrap(payload, key):
    """Return the wrapped collection, tolerating wrapper-key drift."""
    if not isinstance(payload, dict):
        return payload
    if key in payload:
        return payload[key]
    # endpoints wrap the collection alongside scalar metadata (e.g.
    # {"playbook_id": ..., "rules": [...]}); prefer the sole list value
    lists = [k for k, v in payload.items() if isinstance(v, list)]
    if len(lists) == 1:
        return payload[lists[0]]
    candidates = [k for k in payload if k not in ("count", "links", "query")]
    if len(candidates) == 1:
        return payload[candidates[0]]
    return payload


def cmd_bundle(args):
    bundle, missing = {}, []
    for suffix, key in DEAL_RESOURCES:
        path = "/api/deals/{}{}".format(args.deal_id, suffix)
        try:
            bundle[key] = unwrap(get(args.base, path), key)
        except urllib.error.HTTPError as e:
            missing.append("{} -> HTTP {}".format(path, e.code))
        except Exception as e:  # noqa: BLE001 - report and continue
            missing.append("{} -> {}".format(path, e))

    deal = bundle.get("deal") or {}
    for id_key, path_tmpl, label in (
        ("playbook_id", "/api/playbooks/{}/rules", "playbook_rules"),
        ("policy_id", "/api/policies/{}/thresholds", "policy_thresholds"),
    ):
        ident = deal.get(id_key)
        if ident:
            try:
                bundle[label] = unwrap(get(args.base, path_tmpl.format(ident)), label)
            except Exception as e:  # noqa: BLE001
                missing.append("{} -> {}".format(label, e))

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        dest = os.path.join(args.out, "{}_bundle.json".format(args.deal_id))
        with open(dest, "w") as fh:
            json.dump(bundle, fh, indent=1, sort_keys=True)
        print("wrote {}".format(dest), file=sys.stderr)

    print(json.dumps(bundle, indent=1, sort_keys=True))

    terms = bundle.get("draft_terms") or []
    if isinstance(terms, list):
        stale = [t.get("category") for t in terms if t.get("staleness_flag") == "stale"]
        cur = {t.get("category") for t in terms if t.get("staleness_flag") == "current"}
        silent = sorted({c for c in stale if c not in cur})
        print("\n-- {} terms: {} current, {} stale".format(
            args.deal_id, len(cur), len(stale)), file=sys.stderr)
        if silent:
            print("-- draft is SILENT on (stale-only): {}".format(", ".join(silent)),
                  file=sys.stderr)
    if missing:
        print("-- unavailable: {}".format("; ".join(missing)), file=sys.stderr)


def cmd_deals(args):
    rows = unwrap(get(args.base, "/api/deals"), "deals")
    for d in rows:
        line = "{:<14} {:<26} {:<7} pb={:<12} pol={:<14} {}".format(
            d.get("deal_id", ""), d.get("project_name", ""), d.get("client_side", ""),
            str(d.get("playbook_id")), str(d.get("policy_id")),
            d.get("transaction_type", ""))
        if not args.grep or args.grep.lower() in line.lower():
            print(line)


def cmd_get(args):
    print(json.dumps(get(args.base, args.path), indent=1, sort_keys=True))


def cmd_sql(args):
    res = sql(args.base, args.token, args.statement)
    if args.json:
        print(json.dumps(res, indent=1))
        return
    cols = res.get("columns", [])
    rows = res.get("rows", [])
    widths = [len(str(c)) for c in cols]
    for r in rows:
        for i, v in enumerate(r):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(v)))
    fmt = "  ".join("{{:<{}}}".format(w) for w in widths)
    if cols:
        print(fmt.format(*[str(c) for c in cols]))
        print("  ".join("-" * w for w in widths))
    for r in rows:
        print(fmt.format(*[str(v) for v in r]))
    print("\n({} rows)".format(res.get("row_count", len(rows))), file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", default=DEFAULT_BASE)
    p.add_argument("--token", default=DEFAULT_TOKEN)
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("bundle", help="fetch every table for one deal")
    b.add_argument("deal_id")
    b.add_argument("--out", help="also write <deal>_bundle.json into this directory")
    b.set_defaults(func=cmd_bundle)

    d = sub.add_parser("deals", help="list deals")
    d.add_argument("--grep")
    d.set_defaults(func=cmd_deals)

    g = sub.add_parser("get", help="fetch a raw endpoint")
    g.add_argument("path")
    g.set_defaults(func=cmd_get)

    s = sub.add_parser("sql", help="run read-only SQL")
    s.add_argument("statement")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_sql)

    args = p.parse_args()
    try:
        args.func(args)
    except urllib.error.URLError as e:
        print("workbench unreachable at {}: {}".format(args.base, e), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
