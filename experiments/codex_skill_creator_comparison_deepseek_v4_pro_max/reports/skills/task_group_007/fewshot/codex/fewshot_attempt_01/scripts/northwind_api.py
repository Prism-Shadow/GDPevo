#!/usr/bin/env python3
"""
Northwind ERP API Helper — deterministic, importable utility module.

Use this module inside the solving agent's Python environment to avoid
re-writing fetch, arithmetic, and classification logic for every task.
All functions are pure helpers; no side effects beyond HTTP reads.

Typical import:
    from northwind_api import get_json, effective_available, classify_customer, classify_inventory_status, get_shipping_quote

The task runner supplies the API base URL as the environment variable
TASK_ENV_BASE_URL or as a prompt variable <TASK_ENV_BASE_URL>.
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.parse
from datetime import date, datetime
from typing import Any, Optional

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _base_url() -> str:
    """Return the ERP API base URL from the environment or a sensible default."""
    return os.environ.get("TASK_ENV_BASE_URL", "http://task-env:9007")


def get_json(path: str, base_url: str | None = None, **params: str) -> Any:
    """GET *path* (e.g. '/orders') with optional query *params* and return parsed JSON."""
    url = f"{base_url or _base_url()}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode())


def fetch_index(endpoint: str, base_url: str | None = None) -> list[dict]:
    """Return the full list from a collection endpoint (e.g. 'orders', 'products')."""
    return get_json(f"/{endpoint}", base_url=base_url)


def fetch_one(endpoint: str, key: str, base_url: str | None = None) -> dict | None:
    """Return a single record (e.g. '/orders/SO-NNNNN') or None on 404."""
    try:
        return get_json(f"/{endpoint}/{key}", base_url=base_url)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def index_by(items: list[dict], key: str) -> dict[str, dict]:
    """Build a lookup dict keyed on *key* (must be a string field)."""
    return {item[key]: item for item in items if key in item}


# ---------------------------------------------------------------------------
# Inventory calculus
# ---------------------------------------------------------------------------

def effective_available(inv: dict) -> int:
    """on_hand - reserved - quarantined (units available for new allocations)."""
    return int(inv.get("on_hand", 0)) - int(inv.get("reserved", 0)) - int(inv.get("quarantined", 0))


def usable_for_transfer(inv: dict, safety_stock: int) -> int:
    """Units that can leave a warehouse without dipping below *safety_stock*."""
    ea = effective_available(inv)
    return max(0, ea - safety_stock)


def inventory_lookup(inventory_list: list[dict]) -> dict[tuple[str, str], dict]:
    """Return {(sku, warehouse_id): record} for fast cross-warehouse lookups."""
    return {(r["sku"], r["warehouse_id"]): r for r in inventory_list}


def warehouse_effective_availabilities(
    inventory_list: list[dict], sku: str
) -> dict[str, int]:
    """Return {warehouse_id: effective_available} for *sku* across all warehouses."""
    return {
        r["warehouse_id"]: effective_available(r)
        for r in inventory_list
        if r["sku"] == sku
    }


# ---------------------------------------------------------------------------
# Product helpers
# ---------------------------------------------------------------------------

def product_weight(products_index: dict[str, dict], sku: str) -> float:
    """Return weight_lb for a SKU; 0.0 if unknown."""
    p = products_index.get(sku, {})
    return float(p.get("weight_lb", 0.0))


def order_total_weight(order: dict, products_index: dict[str, dict]) -> float:
    """Sum (line quantity × product weight_lb) for all lines of an order."""
    total = 0.0
    for line in order.get("lines", []):
        total += line.get("quantity", 0) * product_weight(products_index, line.get("sku", ""))
    return total


# ---------------------------------------------------------------------------
# Customer classification (reusable across expedite & allocation tasks)
# ---------------------------------------------------------------------------

def classify_customer(customer: dict) -> str:
    """Map account_status / risk_flag to a standard exception code.

    Returns one of: none, review_required, account_blocked, fraud_watch, credit_watch
    """
    status = customer.get("account_status", "")
    risk = customer.get("risk_flag", "")

    if status == "blocked":
        return "account_blocked"
    if status == "review_required":
        return "review_required"
    if risk == "fraud_watch":
        return "fraud_watch"
    if risk == "credit_watch":
        return "credit_watch"
    return "none"


# ---------------------------------------------------------------------------
# Inventory status classification (expedite tasks)
# ---------------------------------------------------------------------------

def classify_inventory_status(
    order: dict,
    products_index: dict[str, dict],
    inv_lookup: dict[tuple[str, str], dict],
) -> str:
    """Classify an order's inventory readiness.

    Returns one of: ready, low_stock, shortage, inactive_sku, inactive_and_shortage
    """
    warehouse = order.get("warehouse_id", "")
    has_shortage = False
    has_low_stock = False
    has_inactive = False

    for line in order.get("lines", []):
        sku = line.get("sku", "")
        qty = line.get("quantity", 0)
        product = products_index.get(sku, {})
        inv = inv_lookup.get((sku, warehouse), {})
        ea = effective_available(inv)

        if not product.get("active", True):
            has_inactive = True

        if ea < qty and product.get("active", True):
            has_shortage = True

        safety = product.get("safety_stock", 0)
        if ea < safety and not has_shortage:
            has_low_stock = True

    if has_inactive and has_shortage:
        return "inactive_and_shortage"
    if has_inactive:
        return "inactive_sku"
    if has_shortage:
        return "shortage"
    if has_low_stock:
        return "low_stock"
    return "ready"


def shortage_skus(order: dict, products_index: dict[str, dict],
                  inv_lookup: dict[tuple[str, str], dict]) -> list[str]:
    """Return SKUs with effective_available < line quantity (active products only)."""
    warehouse = order.get("warehouse_id", "")
    result = []
    for line in order.get("lines", []):
        sku = line.get("sku", "")
        qty = line.get("quantity", 0)
        product = products_index.get(sku, {})
        if not product.get("active", True):
            continue
        inv = inv_lookup.get((sku, warehouse), {})
        if effective_available(inv) < qty:
            result.append(sku)
    return sorted(result)


def inactive_skus(order: dict, products_index: dict[str, dict]) -> list[str]:
    """Return SKUs in the order whose product.active is false."""
    result = []
    for line in order.get("lines", []):
        sku = line.get("sku", "")
        product = products_index.get(sku, {})
        if not product.get("active", True):
            result.append(sku)
    return sorted(result)


def low_stock_skus(order: dict, products_index: dict[str, dict],
                   inv_lookup: dict[tuple[str, str], dict]) -> list[str]:
    """Return SKUs below safety_stock but not in shortage."""
    warehouse = order.get("warehouse_id", "")
    shortage = set(shortage_skus(order, products_index, inv_lookup))
    result = []
    for line in order.get("lines", []):
        sku = line.get("sku", "")
        product = products_index.get(sku, {})
        if not product.get("active", True):
            continue
        if sku in shortage:
            continue
        inv = inv_lookup.get((sku, warehouse), {})
        if effective_available(inv) < product.get("safety_stock", 0):
            result.append(sku)
    return sorted(result)


# ---------------------------------------------------------------------------
# Shipping
# ---------------------------------------------------------------------------

def get_shipping_quote(
    base_url: str,
    warehouse_id: str,
    destination_zip: str,
    weight_lb: float,
    speed: str,
) -> dict:
    """Call /shipping/quote and return the parsed response."""
    return get_json(
        "/shipping/quote",
        base_url=base_url,
        warehouse_id=warehouse_id,
        destination_zip=destination_zip,
        weight_lb=str(weight_lb),
        speed=speed,
    )


def shipping_quote_for_order(
    base_url: str,
    order: dict,
    products_index: dict[str, dict],
) -> dict:
    """Convenience: compute weight from order, fetch quote, return dict."""
    weight = order_total_weight(order, products_index)
    return get_shipping_quote(
        base_url,
        order["warehouse_id"],
        order["destination_zip"],
        weight,
        order.get("shipping_speed", "ground"),
    )


# ---------------------------------------------------------------------------
# Purchase-order helpers
# ---------------------------------------------------------------------------

def timely_pos(
    pos: list[dict],
    sku: str,
    warehouse_id: str,
    by_date: str,
) -> list[dict]:
    """Return open/confirmed POs for *sku* at *warehouse_id* with eta <= *by_date*."""
    result = []
    for po in pos:
        if po.get("sku") != sku:
            continue
        if po.get("warehouse_id") != warehouse_id:
            continue
        if po.get("status") not in ("open", "confirmed"):
            continue
        eta = po.get("eta", "")
        if eta and eta <= by_date:
            result.append(po)
    return result


def timely_po_quantity(
    pos: list[dict], sku: str, warehouse_id: str, by_date: str
) -> int:
    """Total quantity from timely POs for the given SKU/warehouse."""
    return sum(po.get("quantity", 0) for po in timely_pos(pos, sku, warehouse_id, by_date))


# ---------------------------------------------------------------------------
# Incident helpers
# ---------------------------------------------------------------------------

def filter_incidents_by_date(
    incidents: list[dict],
    start_date: str,
    end_date: str,
    date_field: str = "open_date",
) -> list[dict]:
    """Return incidents where *date_field* falls in [start_date, end_date] inclusive."""
    result = []
    for inc in incidents:
        d = inc.get(date_field, "")
        if d and start_date <= d <= end_date:
            result.append(inc)
    return result


def incident_duration_days(incident: dict, analysis_date: str) -> float:
    """Days from open_date to close_date (or analysis_date if still open)."""
    fmt = "%Y-%m-%d"
    open_dt = datetime.strptime(incident["open_date"], fmt)
    close_raw = incident.get("close_date")
    if close_raw:
        close_dt = datetime.strptime(close_raw, fmt)
    else:
        close_dt = datetime.strptime(analysis_date, fmt)
    return (close_dt - open_dt).days


def group_incidents_by_supplier(incidents: list[dict]) -> dict[str, list[dict]]:
    """Return {supplier_id: [incident, ...]}."""
    groups: dict[str, list[dict]] = {}
    for inc in incidents:
        sid = inc.get("supplier_id", "")
        groups.setdefault(sid, []).append(inc)
    return groups


# ---------------------------------------------------------------------------
# BOM math
# ---------------------------------------------------------------------------

def bom_component_totals(
    boms: list[dict],
    build_quantities: dict[str, int],
) -> dict[str, int]:
    """Return {sku: total_required_units} across all BOMs given build quantities.

    *build_quantities* maps bom_id → number of kits to build.
    """
    totals: dict[str, int] = {}
    for bom in boms:
        qty = build_quantities.get(bom["bom_id"], 0)
        if qty <= 0:
            continue
        for comp in bom.get("components", []):
            sku = comp["sku"]
            totals[sku] = totals.get(sku, 0) + qty * comp["quantity_per_kit"]
    return totals


# ---------------------------------------------------------------------------
# Decision mappings (reusable classification tables)
# ---------------------------------------------------------------------------

# inventory_status × customer_exception → (final_decision, next_action)
EXPEDITE_DECISION_TABLE: dict[tuple[str, str], tuple[str, str]] = {
    # (inventory_status, customer_exception) → (final_decision, next_action)
    ("ready",          "none"):            ("ship_now",       "release_to_pick"),
    ("ready",          "review_required"): ("manual_review",  "send_account_review"),
    ("ready",          "account_blocked"): ("reject_hold",    "hold_credit_or_fraud"),
    ("ready",          "fraud_watch"):     ("reject_hold",    "hold_credit_or_fraud"),
    ("ready",          "credit_watch"):    ("manual_review",  "send_account_review"),
    ("low_stock",      "none"):            ("delayed_release", "delay_and_monitor"),
    ("low_stock",      "review_required"): ("manual_review",  "send_account_review"),
    ("low_stock",      "account_blocked"): ("reject_hold",    "hold_credit_or_fraud"),
    ("low_stock",      "fraud_watch"):     ("reject_hold",    "hold_credit_or_fraud"),
    ("low_stock",      "credit_watch"):    ("manual_review",  "send_account_review"),
    ("shortage",       "none"):            ("backorder",      "create_backorder"),
    ("shortage",       "review_required"): ("manual_review",  "send_account_review"),
    ("shortage",       "account_blocked"): ("reject_hold",    "hold_credit_or_fraud"),
    ("shortage",       "fraud_watch"):     ("reject_hold",    "hold_credit_or_fraud"),
    ("shortage",       "credit_watch"):    ("manual_review",  "send_account_review"),
    ("inactive_sku",   "none"):            ("manual_review",  "escalate_product_master"),
    ("inactive_sku",   "review_required"): ("manual_review",  "escalate_product_master"),
    ("inactive_sku",   "account_blocked"): ("reject_hold",    "hold_credit_or_fraud"),
    ("inactive_sku",   "fraud_watch"):     ("reject_hold",    "hold_credit_or_fraud"),
    ("inactive_sku",   "credit_watch"):    ("manual_review",  "escalate_product_master"),
    ("inactive_and_shortage", "none"):            ("manual_review",  "escalate_product_master"),
    ("inactive_and_shortage", "review_required"): ("manual_review",  "send_account_review"),
    ("inactive_and_shortage", "account_blocked"): ("reject_hold",    "hold_credit_or_fraud"),
    ("inactive_and_shortage", "fraud_watch"):     ("reject_hold",    "hold_credit_or_fraud"),
    ("inactive_and_shortage", "credit_watch"):    ("manual_review",  "escalate_product_master"),
}


def expedite_decision(inventory_status: str, customer_exception: str) -> tuple[str, str]:
    """Return (final_decision, next_action) for an expedite order record."""
    return EXPEDITE_DECISION_TABLE.get(
        (inventory_status, customer_exception),
        ("manual_review", "send_account_review"),
    )


# allocation line action helpers
ALLOCATION_CUSTOMER_BLOCK_REASONS = {
    "account_blocked": "account_blocked",
    "review_required": "account_review_required",
    "fraud_watch": "fraud_watch",
    "credit_watch": "account_review_required",
}


def allocation_primary_reason(
    customer_exception: str, product_active: bool, has_effective_stock: bool
) -> str:
    """Return primary_reason for an allocation line."""
    if customer_exception in ALLOCATION_CUSTOMER_BLOCK_REASONS:
        return ALLOCATION_CUSTOMER_BLOCK_REASONS[customer_exception]
    if not product_active:
        return "inactive_product"
    if not has_effective_stock:
        return "insufficient_effective_stock"
    return "none"


def is_allocation_blocked(customer_exception: str) -> bool:
    """Return True if the customer exception prevents automatic line release."""
    return customer_exception in ALLOCATION_CUSTOMER_BLOCK_REASONS


# ---------------------------------------------------------------------------
# Rounding
# ---------------------------------------------------------------------------

def usd(val: float) -> float:
    """Round to 2 decimal places (USD currency)."""
    return round(val, 2)


def pct1(val: float) -> float:
    """Round to 1 decimal place (percentages)."""
    return round(val, 1)


def dur(val: float) -> float:
    """Round to 2 decimal places (durations in days)."""
    return round(val, 2)
