#!/usr/bin/env python3
"""Minimal read-only client for the ProcureOps ERP API.

Usage as a library:
    from procureops import API
    api = API()                      # defaults to http://127.0.0.1:8056
    po  = api.get("purchase_orders", "PO-AX17-4481")
    inv = api.list("ap/invoices", supplier_id="SUP-LUMA")   # -> list of dicts
    rcv = api.receipts_for_po("PO-AX17-4481")

Usage from the shell:
    python procureops.py get purchase_orders PO-AX17-4481
    python procureops.py list ap/invoices supplier_id=SUP-LUMA
    python procureops.py health

The API is read-only (GET only); this client never mutates anything.
All money should be rounded to cents by the caller (see round_cents).
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from datetime import date

DEFAULT_BASE = "http://127.0.0.1:8056"
MIRROR_BASE = "http://127.0.0.1:8006"


class API:
    def __init__(self, base: str = DEFAULT_BASE, timeout: float = 15.0):
        self.base = base.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: dict | None = None):
        url = f"{self.base}/{path.lstrip('/')}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=self.timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    # ---- generic ----
    def health(self):
        return self._get("health")

    def manifest(self):
        return self._get("manifest")

    def get(self, collection: str, record_id: str):
        """Fetch one record by id. collection e.g. 'purchase_orders', 'ap/invoices'."""
        return self._get(f"{collection}/{record_id}")

    def list(self, collection: str, **filters) -> list:
        """List with exact-match filters. Returns the results list (not the wrapper)."""
        resp = self._get(collection, filters or None)
        return resp.get("results", resp) if isinstance(resp, dict) else resp

    # ---- common joins ----
    def receipts_for_po(self, po_id: str) -> list:
        return self.list("receipts", po_id=po_id)

    def invoices_for_po(self, po_id: str) -> list:
        return self.list("ap/invoices", po_id=po_id)

    def invoices_for_supplier(self, supplier_id: str) -> list:
        return self.list("ap/invoices", supplier_id=supplier_id)

    def payments_for_invoice(self, invoice_id: str) -> list:
        return self.list("ap/payments", invoice_id=invoice_id)

    def payments_for_supplier(self, supplier_id: str) -> list:
        return self.list("ap/payments", supplier_id=supplier_id)

    def risk_events_for_supplier(self, supplier_id: str) -> list:
        return self.list("vendor_risk_events", supplier_id=supplier_id)

    def approvals_for_object(self, object_id: str) -> list:
        return self.list("approval_events", object_id=object_id)

    def pos_for_contract(self, contract_id: str) -> list:
        return self.list("purchase_orders", contract_id=contract_id)

    def budget_snapshot(self, program_id: str) -> dict | None:
        rows = self.list("budget_snapshots", program_id=program_id)
        return rows[0] if rows else None


# ---------- helper rules (codify the verified business logic) ----------

def round_cents(x: float) -> float:
    return round(float(x) + 0.0, 2)


def on_or_before(d: str, as_of: str) -> bool:
    """Inclusive date scoping: record dated exactly on as_of is in scope."""
    return date.fromisoformat(d) <= date.fromisoformat(as_of)


def open_risk_events(events: list, as_of: str) -> list:
    """Open/monitoring vendor-risk events as of a date (excludes closed)."""
    return [
        e for e in events
        if str(e.get("status", "")).lower() in {"open", "monitoring"}
        and on_or_before(e["event_date"], as_of)
    ]


def severe_open_risk_event_ids(events: list, as_of: str) -> list:
    return sorted(
        e["event_id"] for e in open_risk_events(events, as_of)
        if str(e.get("severity", "")).lower() in {"high", "critical"}
    )


def latest_approval(events: list) -> dict | None:
    return max(events, key=lambda e: e["event_date"]) if events else None


def noncancelled_subtotal(pos: list) -> float:
    return round_cents(sum(
        p.get("subtotal", 0) for p in pos
        if str(p.get("status", "")).lower() != "cancelled"
    ))


def line_qty(record: dict, field: str) -> int:
    """Sum a quantity field across a record's lines (e.g. 'quantity_received')."""
    return sum(l.get(field, 0) for l in record.get("lines", []))


def severe_unmatched(ordered: int, received: int, pct_threshold: float = 0.10) -> bool:
    """Material receiving shortfall => 'Severe Unmatched Quantity' (accompanies
    'Underage Quantity'). Verified: 10% and 34% short both qualify; 0% short does
    not. A pure over-bill with received==ordered is AP Quantity Variance, not this."""
    if received >= ordered:
        return False
    return (ordered - received) / ordered >= pct_threshold


def _main(argv: list) -> int:
    api = API()
    if not argv or argv[0] == "health":
        print(json.dumps(api.health(), indent=2)); return 0
    cmd = argv[0]
    if cmd == "manifest":
        print(json.dumps(api.manifest(), indent=2)); return 0
    if cmd == "get" and len(argv) >= 3:
        print(json.dumps(api.get(argv[1], argv[2]), indent=2)); return 0
    if cmd == "list" and len(argv) >= 2:
        filters = dict(kv.split("=", 1) for kv in argv[2:] if "=" in kv)
        print(json.dumps(api.list(argv[1], **filters), indent=2)); return 0
    print(__doc__); return 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
