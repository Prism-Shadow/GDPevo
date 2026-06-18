#!/usr/bin/env python3
"""ProcureOps API probe helper.

A thin, dependency-free client over the read-only ProcureOps ERP API. Use it to
pull the records a task needs and to do the common rollups (collect a record by
id, list a collection with filters, gather all child records for a parent id).

Why this exists: every ProcureOps task starts the same way -- resolve a handful
of ids against the live API, then walk PO -> receipts / invoices / payments and
supplier -> risk events. Doing that by hand with curl is slow and error prone.
This script gives you stable JSON you can pipe into your own arithmetic.

Usage (always pass the base URL your task prompt names; default 8056):

  python3 scripts/probe.py get <collection> <id> [--base URL]
  python3 scripts/probe.py list <collection> [k=v ...] [--start D --end D] [--base URL]
  python3 scripts/probe.py bundle <po_id> [--base URL]      # PO + its receipts/invoices
  python3 scripts/probe.py supplier <supplier_id> [--base URL]  # supplier + risk events

<collection> is one of: programs suppliers items contracts purchase_requisitions
purchase_orders receipts ap/invoices ap/payments approval_events
budget_snapshots vendor_risk_events

The API never invents task ids or answer keys; it is operational source data
only. It is the source of truth -- when a local memo/export disagrees with a
record you can fetch from the API, trust the API.
"""
import json
import sys
import urllib.parse
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8056"


def _get(base, path):
    url = base.rstrip("/") + path
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def get_one(base, collection, rec_id):
    return _get(base, f"/{collection}/{urllib.parse.quote(rec_id)}")


def list_recs(base, collection, filters=None, start=None, end=None):
    params = dict(filters or {})
    if start:
        params["start"] = start
    if end:
        params["end"] = end
    q = ("?" + urllib.parse.urlencode(params)) if params else ""
    return _get(base, f"/{collection}{q}")


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    opts = {}
    i = 0
    while i < len(argv):
        if argv[i].startswith("--"):
            opts[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            i += 1
    base = opts.get("base", DEFAULT_BASE)
    if not args:
        print(__doc__)
        return 1
    cmd = args[0]

    if cmd == "get":
        print(json.dumps(get_one(base, args[1], args[2]), indent=2, sort_keys=True))
    elif cmd == "list":
        filters = {}
        for kv in args[2:]:
            if "=" in kv:
                k, v = kv.split("=", 1)
                filters[k] = v
        print(json.dumps(
            list_recs(base, args[1], filters, opts.get("start"), opts.get("end")),
            indent=2, sort_keys=True))
    elif cmd == "bundle":
        po_id = args[1]
        out = {
            "purchase_order": get_one(base, "purchase_orders", po_id),
            "receipts": list_recs(base, "receipts", {"po_id": po_id})["results"],
            "invoices": list_recs(base, "ap/invoices", {"po_id": po_id})["results"],
        }
        print(json.dumps(out, indent=2, sort_keys=True))
    elif cmd == "supplier":
        sid = args[1]
        out = {
            "supplier": get_one(base, "suppliers", sid),
            "risk_events": list_recs(base, "vendor_risk_events", {"supplier_id": sid})["results"],
        }
        print(json.dumps(out, indent=2, sort_keys=True))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
