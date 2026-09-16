"""
Northwind ERP helper utilities.

Common functions for effective-inventory calculation, entity lookups,
and shipping-quote computation. Import and use in task-solving scripts.
"""

import requests
from collections import defaultdict


def fetch_all(base_url):
    """Fetch all collections from the ERP API and return as dicts keyed by ID."""
    def get(path):
        return requests.get(f"{base_url}{path}").json()

    products   = {p["sku"]: p for p in get("/products")}
    customers  = {c["customer_id"]: c for c in get("/customers")}
    warehouses = {w["warehouse_id"]: w for w in get("/warehouses")}
    suppliers  = {s["supplier_id"]: s for s in get("/suppliers")}
    boms       = {b["bom_id"]: b for b in get("/boms")}

    orders     = get("/orders")
    inventory  = get("/inventory")
    pos        = get("/purchase_orders")
    incidents  = get("/incidents")

    # Build inventory lookup: (warehouse_id, sku) -> record
    inv_lookup = {}
    for rec in inventory:
        inv_lookup[(rec["warehouse_id"], rec["sku"])] = rec

    return {
        "products": products,
        "customers": customers,
        "warehouses": warehouses,
        "suppliers": suppliers,
        "boms": boms,
        "orders": orders,
        "inventory": inventory,
        "inv_lookup": inv_lookup,
        "purchase_orders": pos,
        "incidents": incidents,
    }


def effective_available(inv_record):
    """Compute releasable inventory: on_hand - reserved - quarantined."""
    return inv_record["on_hand"] - inv_record["reserved"] - inv_record["quarantined"]


def get_inventory(data, warehouse_id, sku):
    """Get effective_available for a specific warehouse/SKU. Returns 0 if no record."""
    rec = data["inv_lookup"].get((warehouse_id, sku))
    if rec is None:
        return 0
    return effective_available(rec)


def get_shipping_quote(base_url, warehouse_id, destination_zip, weight_lb):
    """Get shipping quote for a shipment. Returns dict with zone_distance, service_days, total_cost."""
    resp = requests.get(
        f"{base_url}/shipping/quote",
        params={
            "warehouse_id": warehouse_id,
            "destination_zip": destination_zip,
            "weight_lb": weight_lb,
        }
    )
    return resp.json()


def order_total_weight(order, products):
    """Sum the total weight of all line items in an order."""
    total = 0.0
    for line in order["lines"]:
        prod = products.get(line["sku"])
        if prod:
            total += prod["weight_lb"] * line["quantity"]
    return total


def effective_available_all_warehouses(data, sku):
    """Return {warehouse_id: effective_available} for a SKU across all warehouses."""
    result = {}
    for (wh, s), rec in data["inv_lookup"].items():
        if s == sku:
            result[wh] = effective_available(rec)
    return result


def customer_exception(customer):
    """Classify customer exception level from account_status and risk_flag.

    Returns one of: "account_blocked", "review_required", "fraud_watch",
    "credit_watch", "none".
    """
    status = customer.get("account_status", "active")
    risk = customer.get("risk_flag", "none")

    if status == "blocked":
        return "account_blocked"
    if status == "review_required":
        return "review_required"
    if risk == "fraud_watch":
        return "fraud_watch"
    if risk == "credit_watch":
        return "credit_watch"
    return "none"


def is_timely_po(po, planning_warehouse, deadline_date):
    """Check if a PO is timely for a replenishment need.

    A PO is timely when status is open/confirmed, warehouse matches planning site,
    and ETA is on or before the deadline.
    """
    return (
        po["status"] in ("open", "confirmed")
        and po["warehouse_id"] == planning_warehouse
        and po["eta"] <= deadline_date
    )


def filter_incidents_by_date(incidents, start_date, end_date):
    """Return incidents with open_date between start_date and end_date (inclusive)."""
    return [
        inc for inc in incidents
        if start_date <= inc["open_date"] <= end_date
    ]


def incident_duration_days(incident, analysis_date):
    """Compute duration in days: close_date - open_date for closed, analysis_date - open_date for open."""
    from datetime import date
    open_d = date.fromisoformat(incident["open_date"])
    if incident["status"] == "closed" and incident.get("close_date"):
        close_d = date.fromisoformat(incident["close_date"])
    else:
        close_d = date.fromisoformat(analysis_date)
    return (close_d - open_d).days


def supplier_incident_aggregate(incidents, analysis_date):
    """Aggregate a list of incidents for one supplier.

    Returns dict with keys: incident_count, rma_count, work_order_count,
    open_incident_count, severe_incident_count, total_resolution_cost, durations.
    """
    from statistics import mean

    result = {
        "incident_count": len(incidents),
        "rma_count": 0,
        "work_order_count": 0,
        "open_incident_count": 0,
        "severe_incident_count": 0,
        "total_resolution_cost": 0.0,
        "durations": [],
    }

    for inc in incidents:
        if inc["incident_type"] == "RMA":
            result["rma_count"] += 1
        elif inc["incident_type"] == "WORK_ORDER":
            result["work_order_count"] += 1
        if inc["status"] == "open":
            result["open_incident_count"] += 1
        if inc["severity"] in ("high", "critical"):
            result["severe_incident_count"] += 1
        result["total_resolution_cost"] += inc["resolution_cost"]
        result["durations"].append(incident_duration_days(inc, analysis_date))

    result["avg_duration_days"] = round(mean(result["durations"]), 2) if result["durations"] else 0.0
    result["total_resolution_cost"] = round(result["total_resolution_cost"], 2)

    return result
