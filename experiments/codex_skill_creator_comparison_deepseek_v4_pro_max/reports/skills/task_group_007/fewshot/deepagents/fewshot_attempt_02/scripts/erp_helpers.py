#!/usr/bin/env python3
"""
Core ERP helpers for the Northwind Components API.

Load this module with curl/wget data already fetched and held in memory
or use the provided convenience wrappers to fetch from the API base URL.
"""

import json
import urllib.request
from datetime import date, datetime
from typing import Any, Optional


def effective_available(inv_record: dict) -> int:
    """Return on_hand minus quarantined and reserved."""
    return inv_record.get("on_hand", 0) - inv_record.get("quarantined", 0) - inv_record.get("reserved", 0)


def fetch_all(base_url: str, endpoint: str, params: Optional[dict] = None) -> list[dict]:
    """Fetch a list endpoint, optionally with query params."""
    url = f"{base_url}{endpoint}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        url = f"{url}?{qs}"
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read())


def fetch_one(base_url: str, endpoint: str, id_val: str) -> Optional[dict]:
    """Try single-resource GET; return None on 404."""
    url = f"{base_url}{endpoint}/{id_val}"
    try:
        with urllib.request.urlopen(url) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def filter_by(items: list[dict], key: str, value: Any) -> list[dict]:
    """Client-side filter on a dict field."""
    return [item for item in items if item.get(key) == value]


def lookup(items: list[dict], key: str, value: Any) -> Optional[dict]:
    """Return the first item matching key=value, or None."""
    for item in items:
        if item.get(key) == value:
            return item
    return None


def index_by(items: list[dict], key: str) -> dict[str, dict]:
    """Build a dict keyed by the given field."""
    return {item[key]: item for item in items if key in item}


def parse_date(d: str) -> date:
    """Parse YYYY-MM-DD string to date."""
    return datetime.strptime(d, "%Y-%m-%d").date()


def shipping_weight(lines: list[dict], products: dict[str, dict]) -> float:
    """Compute total weight for a set of order/BOM lines using product weight_lb."""
    total = 0.0
    for line in lines:
        sku = line.get("sku", "")
        qty = line.get("quantity", 0)
        prod = products.get(sku, {})
        total += prod.get("weight_lb", 0) * qty
    return total


def round2(val: float) -> float:
    """Round to 2 decimal places (currency)."""
    return round(val, 2)


def round1(val: float) -> float:
    """Round to 1 decimal place (percentages)."""
    return round(val, 1)


def sorted_str_ids(ids: list[str]) -> list[str]:
    """Return sorted, unique string IDs."""
    return sorted(set(ids))
