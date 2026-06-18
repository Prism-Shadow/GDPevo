#!/usr/bin/env python3
"""Helpers for the shared ERP finance JSON API.

Set the base URL via the ERP_BASE env var (read it from your environment access notes; do NOT
trust a base URL printed inside a task prompt). Defaults to the common local value.

Usage examples:
    ERP_BASE=http://127.0.0.1:8029 python scripts/fetch.py bills        # dump all AP bills
    python scripts/fetch.py claim CLM-2025-OPS-017                      # one claim
    python scripts/fetch.py compliance BUS-2025-0009                   # all 6 compliance facets

Or import the helpers:
    from fetch import get_all, get_one, claim_picture, open_balance
"""
import json
import os
import sys
import urllib.request
from collections import defaultdict

BASE = os.environ.get("ERP_BASE", "http://127.0.0.1:8029").rstrip("/")


def _get(path):
    with urllib.request.urlopen(BASE + path) as r:
        return json.load(r)


def get_all(resource, **filters):
    """Page through a list endpoint and return every row in `data`.

    resource: e.g. 'api/claims', 'api/ap/bills', 'api/ap/payments', 'api/vendors',
              'api/prepaids/invoices', 'api/prepaids/gl-balances', 'api/close/logs'
    filters:  exact-match query params (status='paid', account='1250', ...)
    """
    rows, offset = [], 0
    qbase = "&".join(f"{k}={v}" for k, v in filters.items())
    while True:
        q = f"limit=500&offset={offset}" + (("&" + qbase) if qbase else "")
        page = _get(f"/{resource}?{q}")
        rows.extend(page["data"])
        offset += len(page["data"])
        if offset >= page.get("total", len(rows)) or not page["data"]:
            break
    return rows


def get_one(path):
    """GET a single-object endpoint, e.g. 'api/claims/CLM-...' or
    'api/compliance/profile/BUS-...'. Returns None on 404."""
    try:
        return _get("/" + path.lstrip("/"))
    except Exception:
        return None


def compliance(business_id):
    """All six compliance facets for one business, keyed by facet name."""
    return {
        f: get_one(f"api/compliance/{f}/{business_id}")
        for f in ("profile", "ownership", "registry", "screening", "bank", "risk")
    }


def cleared_total_by_bill():
    """Sum of CLEARED-only payments per bill_id (the business 'paid' definition)."""
    out = defaultdict(float)
    for p in get_all("api/ap/payments"):
        if p.get("status") == "cleared":
            out[p["bill_id"]] += p["amount"]
    return out


def matched_bill(claim, bills):
    """Return the bill that validly matches a claim (claim_id + amount + vendor, not void),
    or None. Handles duplicate bill_id rows by checking every field."""
    for b in bills:
        if (
            b.get("claim_id") == claim["claim_id"]
            and abs(b.get("amount", 0) - claim.get("amount", 0)) < 0.005
            and b.get("vendor_id") == claim.get("vendor_id")
            and claim.get("vendor_id") is not None
            and b.get("status") != "void"
        ):
            return b
    return None


def open_balance(bill, cleared):
    """Open AP balance = bill amount minus CLEARED payments (not scheduled/processing)."""
    return round(bill["amount"] - cleared.get(bill["bill_id"], 0.0), 2)


def claim_picture(claim_id):
    """Convenience: print claim + its bills + cleared totals for manual triage."""
    c = get_one(f"api/claims/{claim_id}")
    bills = [b for b in get_all("api/ap/bills") if b.get("claim_id") == claim_id]
    cleared = cleared_total_by_bill()
    print(json.dumps({"claim": c}, indent=2))
    for b in bills:
        print(
            f"  bill {b['bill_id']} status={b['status']} amt={b['amount']} "
            f"vendor={b['vendor_id']} cleared={cleared.get(b['bill_id'],0.0)} "
            f"open={open_balance(b, cleared)}"
        )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "claim" and len(sys.argv) > 2:
        claim_picture(sys.argv[2])
    elif cmd == "compliance" and len(sys.argv) > 2:
        print(json.dumps(compliance(sys.argv[2]), indent=2))
    else:
        alias = {
            "claims": "api/claims",
            "bills": "api/ap/bills",
            "payments": "api/ap/payments",
            "vendors": "api/vendors",
            "invoices": "api/prepaids/invoices",
            "gl": "api/prepaids/gl-balances",
            "logs": "api/close/logs",
        }.get(cmd, cmd)
        print(json.dumps(get_all(alias), indent=2))
