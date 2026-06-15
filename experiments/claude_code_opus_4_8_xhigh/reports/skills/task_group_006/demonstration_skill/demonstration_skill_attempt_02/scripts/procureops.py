#!/usr/bin/env python3
"""Tiny read-only client + helpers for the ProcureOps ERP API.

Use this to avoid re-writing a GET client and the rounding/set conventions in
every ProcureOps answer task. Import it, or copy the bits you need.

The ProcureOps API is the system of record. List endpoints return
{"count": n, "results": [...]}; single-record endpoints return the bare object.
Filters match a field exactly (case-insensitive); start=/end= filter the
collection's primary date field.

Example:
    from procureops import Client, money, as_set
    api = Client("http://127.0.0.1:8006")
    po  = api.get("/purchase_orders/PO-AX17-4481")
    inv = api.get_list("/ap/invoices", supplier_id="SUP-LUMA",
                       start="2026-01-01", end="2026-06-01")  # invoice_date scoped
    total = money(po["subtotal"] + po["tax"])
    ids   = as_set([r["invoice_id"] for r in inv])            # deduped + sorted asc
"""
from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request


class Client:
    def __init__(self, base_url: str = "http://127.0.0.1:8006", timeout: float = 15.0):
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    def _fetch(self, path: str, params: dict | None = None):
        url = self.base + path
        if params:
            # drop None-valued filters
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                url += "?" + urllib.parse.urlencode(clean)
        with urllib.request.urlopen(url, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get(self, path: str, **params):
        """GET a single record by id path, e.g. get('/programs/PRG-AX17')."""
        return self._fetch(path, params or None)

    def get_list(self, path: str, **filters) -> list:
        """GET a collection and return the results list (handles {count,results})."""
        data = self._fetch(path, filters or None)
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        return data


def money(x) -> float:
    """Round a USD amount to cents (2 dp)."""
    return round(float(x) + 0.0, 2)


def ratio(x, places: int = 4) -> float:
    """Round a ratio/percentage to the given precision."""
    return round(float(x) + 0.0, places)


def as_set(ids) -> list:
    """Dedupe and sort ascending — the default convention for id list fields."""
    return sorted({i for i in ids if i is not None})


def max_qty_within_budget(remaining: float, unit_price: float, tax_rate: float) -> int:
    """Largest integer quantity whose tax-loaded subtotal fits the remaining budget."""
    per_unit = unit_price * (1.0 + tax_rate)
    if per_unit <= 0:
        return 0
    return int(math.floor(remaining / per_unit))


def on_or_before(date_str: str | None, cutoff: str | None) -> bool:
    """True if an ISO date (YYYY-MM-DD) is on/before the cutoff. Used for as_of scoping.
    Records with no date, or after the cutoff, are excluded (returns False/True as
    appropriate). ISO date strings compare correctly lexicographically."""
    if not date_str:
        return False
    if not cutoff:
        return True
    return date_str <= cutoff


if __name__ == "__main__":  # smoke test
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8006"
    api = Client(base)
    print("health:", api.get("/health"))
    print("manifest counts:", api.get("/manifest").get("record_counts"))
