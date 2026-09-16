#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime

BASE_URL = os.environ.get("TASK_ENV_BASE_URL", "http://task-env:9007").rstrip("/")


def fetch_json(path: str, params: dict | None = None, base_url: str = BASE_URL):
    if path.startswith("http://") or path.startswith("https://"):
        url = path
    else:
        url = f"{base_url}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url) as resp:
        return json.load(resp)


def load_catalogs(base_url: str = BASE_URL):
    return {
        "products": fetch_json("/products", base_url=base_url),
        "inventory": fetch_json("/inventory", base_url=base_url),
        "warehouses": fetch_json("/warehouses", base_url=base_url),
        "orders": fetch_json("/orders", base_url=base_url),
        "customers": fetch_json("/customers", base_url=base_url),
        "suppliers": fetch_json("/suppliers", base_url=base_url),
        "purchase_orders": fetch_json("/purchase_orders", base_url=base_url),
        "boms": fetch_json("/boms", base_url=base_url),
        "incidents": fetch_json("/incidents", base_url=base_url),
    }


def index_by(rows, key):
    return {row[key]: row for row in rows}


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def round2(value: float) -> float:
    return round(float(value), 2)


def inventory_key(warehouse_id: str, sku: str):
    return warehouse_id, sku


def inventory_record(inventory_index: dict, warehouse_id: str, sku: str):
    return inventory_index.get(
        inventory_key(warehouse_id, sku),
        {
            "warehouse_id": warehouse_id,
            "sku": sku,
            "on_hand": 0,
            "reserved": 0,
            "quarantined": 0,
            "last_count_date": None,
        },
    )


def product_record(product_index: dict, sku: str):
    return product_index.get(
        sku,
        {
            "sku": sku,
            "active": False,
            "safety_stock": 0,
            "overstock_threshold": 0,
            "supplier_id": None,
            "unit_cost": 0.0,
            "weight_lb": 0.0,
        },
    )


def free_stock(inventory_row: dict) -> int:
    return int(inventory_row["on_hand"]) - int(inventory_row["reserved"]) - int(inventory_row["quarantined"])


def effective_available(inventory_row: dict, product_row: dict) -> int:
    return free_stock(inventory_row) - int(product_row["safety_stock"])


def transferable_surplus(inventory_row: dict, product_row: dict) -> int:
    return max(0, effective_available(inventory_row, product_row))


def order_weight(order: dict, product_index: dict) -> float:
    total = 0.0
    for line in order.get("lines", []):
        total += float(line["quantity"]) * float(product_record(product_index, line["sku"])["weight_lb"])
    return total


def bom_requirements(boms, build_targets):
    bom_index = index_by(boms, "bom_id")
    kit_targets = []
    totals = defaultdict(int)
    for target in sorted(build_targets, key=lambda row: row["bom_id"]):
        bom = bom_index[target["bom_id"]]
        kit_targets.append(
            {
                "bom_id": target["bom_id"],
                "kit_name": bom["name"],
                "warehouse_id": bom["warehouse_id"],
                "build_quantity": int(target["target_build_quantity"]),
                "build_date": target["target_build_date"],
            }
        )
        for component in bom.get("components", []):
            totals[component["sku"]] += int(component["quantity_per_kit"]) * int(target["target_build_quantity"])
    return kit_targets, totals


def timely_po_quantity(purchase_orders, sku: str, warehouse_id: str, needed_by: str):
    qty = 0
    po_ids = []
    for po in purchase_orders:
        if (
            po["sku"] == sku
            and po["warehouse_id"] == warehouse_id
            and po["status"] in {"open", "confirmed"}
            and po["eta"] <= needed_by
        ):
            qty += int(po["quantity"])
            po_ids.append(po["po_id"])
    return qty, sorted(po_ids)


def candidate_transfer_sources(inventory_rows, product_index: dict, sku: str, target_warehouse_id: str):
    product = product_record(product_index, sku)
    candidates = []
    for row in inventory_rows:
        if row["sku"] != sku or row["warehouse_id"] == target_warehouse_id:
            continue
        surplus = transferable_surplus(row, product)
        if surplus <= 0:
            continue
        candidates.append(
            {
                "warehouse_id": row["warehouse_id"],
                "free_stock": free_stock(row),
                "effective_available": effective_available(row, product),
                "transferable_surplus": surplus,
            }
        )
    return sorted(candidates, key=lambda row: (-row["transferable_surplus"], row["warehouse_id"]))


def shipping_quote(order: dict, base_url: str = BASE_URL, product_index: dict | None = None):
    if product_index is None:
        raise ValueError("product_index is required for shipping_quote")
    return fetch_json(
        "/shipping/quote",
        params={
            "warehouse_id": order["warehouse_id"],
            "destination_zip": order["destination_zip"],
            "speed": order["shipping_speed"],
            "weight_lb": round(order_weight(order, product_index), 3),
        },
        base_url=base_url,
    )


def customer_exception(customer: dict) -> str:
    status = customer.get("account_status")
    risk = customer.get("risk_flag")
    if status == "blocked":
        return "account_blocked"
    if risk == "fraud_watch":
        return "fraud_watch"
    if risk == "credit_watch":
        return "credit_watch"
    if status == "review_required":
        return "review_required"
    return "none"


def line_inventory_state(line: dict, warehouse_id: str, inventory_index: dict, product_index: dict) -> dict:
    sku = line["sku"]
    inv = inventory_record(inventory_index, warehouse_id, sku)
    product = product_record(product_index, sku)
    eff = effective_available(inv, product)
    qty = int(line["quantity"])
    active = bool(product.get("active", True))

    inactive = not active
    shortage = eff < qty
    low_stock = active and not shortage and 0 <= eff < int(product["safety_stock"])

    if inactive and shortage:
        status = "inactive_and_shortage"
    elif inactive:
        status = "inactive_sku"
    elif shortage:
        status = "shortage"
    elif low_stock:
        status = "low_stock"
    else:
        status = "ready"

    return {
        "sku": sku,
        "quantity": qty,
        "inventory": inv,
        "product": product,
        "effective_available": eff,
        "status": status,
        "inactive": inactive,
        "shortage": shortage,
        "low_stock": low_stock,
    }


def order_inventory_state(order: dict, inventory_index: dict, product_index: dict) -> dict:
    states = [
        line_inventory_state(line, order["warehouse_id"], inventory_index, product_index)
        for line in order.get("lines", [])
    ]
    has_inactive = any(state["status"] in {"inactive_sku", "inactive_and_shortage"} for state in states)
    has_shortage = any(state["status"] in {"shortage", "inactive_and_shortage"} for state in states)
    has_low_stock = any(state["status"] == "low_stock" for state in states)

    if has_inactive and has_shortage:
        inventory_status = "inactive_and_shortage"
    elif has_inactive:
        inventory_status = "inactive_sku"
    elif has_shortage:
        inventory_status = "shortage"
    elif has_low_stock:
        inventory_status = "low_stock"
    else:
        inventory_status = "ready"

    return {"inventory_status": inventory_status, "lines": states}


def incident_duration_days(incident: dict, analysis_date: str) -> int:
    start = parse_date(incident["open_date"])
    end = parse_date(incident["close_date"]) if incident.get("close_date") else parse_date(analysis_date)
    return (end - start).days


def filter_incidents(incidents, start_date: str, end_date: str):
    start = parse_date(start_date)
    end = parse_date(end_date)
    return [row for row in incidents if start <= parse_date(row["open_date"]) <= end]


def recommendation_code(row: dict) -> str:
    if row["quality_status"] == "quality_hold" and row["incident_count"] >= 3:
        return "ESCALATE_SUPPLIER"
    if row["critical_rma_count"] > 0:
        return "ESCALATE_SUPPLIER"
    if row["rma_count"] >= 3 and row["total_resolution_cost"] >= 15000:
        return "ESCALATE_SUPPLIER"
    if row["work_order_count"] >= 3 and row["work_order_count"] > row["rma_count"]:
        return "PROCESS_REVIEW"
    if (
        row["quality_status"] in {"watch", "quality_hold"}
        or row["incident_count"] >= 4
        or row["total_resolution_cost"] >= 12000
        or row["severe_incident_count"] >= 2
    ):
        return "WATCHLIST"
    return "MONITOR"


def supplier_scorecard(incidents, suppliers, start_date: str, end_date: str, analysis_date: str):
    supplier_index = index_by(suppliers, "supplier_id")
    filtered = filter_incidents(incidents, start_date, end_date)
    by_supplier = defaultdict(list)
    for incident in filtered:
        by_supplier[incident["supplier_id"]].append(incident)

    rows = []
    total_filtered = len(filtered)
    for supplier_id in sorted(by_supplier):
        items = by_supplier[supplier_id]
        supplier = supplier_index.get(supplier_id, {})
        incident_count = len(items)
        rma_count = sum(1 for item in items if item["incident_type"] == "RMA")
        work_order_count = sum(1 for item in items if item["incident_type"] == "WORK_ORDER")
        critical_rma_count = sum(
            1
            for item in items
            if item["incident_type"] == "RMA" and item["severity"] == "critical"
        )
        open_count = sum(1 for item in items if item["status"] == "open")
        severe_count = sum(1 for item in items if item["severity"] in {"high", "critical"})
        total_cost = round2(sum(float(item["resolution_cost"]) for item in items))
        avg_duration = round2(
            sum(incident_duration_days(item, analysis_date) for item in items) / incident_count
        )

        row = {
            "supplier_id": supplier_id,
            "supplier_name": supplier.get("name", ""),
            "incident_count": incident_count,
            "incident_percentage": round(incident_count * 100 / total_filtered, 1) if total_filtered else 0.0,
            "total_resolution_cost": total_cost,
            "avg_duration_days": avg_duration,
            "rma_count": rma_count,
            "work_order_count": work_order_count,
            "open_incident_count": open_count,
            "severe_incident_count": severe_count,
            "quality_status": supplier.get("quality_status", "approved"),
            "critical_rma_count": critical_rma_count,
        }
        row["recommendation_code"] = recommendation_code(row)
        rows.append(row)

    top_escalations = sorted(
        [row for row in rows if row["recommendation_code"] == "ESCALATE_SUPPLIER"],
        key=lambda row: (-row["incident_count"], -row["total_resolution_cost"], row["supplier_id"]),
    )

    summary = {
        "filtered_incident_count": total_filtered,
        "supplier_count": len(rows),
        "total_resolution_cost": round2(sum(row["total_resolution_cost"] for row in rows)),
        "overall_rma_count": sum(row["rma_count"] for row in rows),
        "overall_work_order_count": sum(row["work_order_count"] for row in rows),
    }

    return {
        "analysis_window": {
            "start_date": start_date,
            "end_date": end_date,
            "analysis_date": analysis_date,
        },
        "summary": summary,
        "supplier_scorecard": [
            {
                key: value
                for key, value in row.items()
                if key not in {"quality_status", "critical_rma_count"}
            }
            for row in rows
        ],
        "top_escalation_suppliers": [row["supplier_id"] for row in top_escalations],
        "highest_cost_supplier_id": sorted(rows, key=lambda row: (-row["total_resolution_cost"], row["supplier_id"]))[0]["supplier_id"]
        if rows
        else "",
        "highest_share_supplier_id": sorted(rows, key=lambda row: (-row["incident_count"], row["supplier_id"]))[0]["supplier_id"]
        if rows
        else "",
    }


def print_json(value):
    json.dump(value, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Northwind ERP helper utilities")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("effective", help="Show inventory math for one SKU at one warehouse")
    p.add_argument("sku")
    p.add_argument("warehouse_id")

    p = sub.add_parser("quote", help="Fetch a shipping quote from the live API")
    p.add_argument("warehouse_id")
    p.add_argument("destination_zip")
    p.add_argument("speed")
    p.add_argument("weight_lb", type=float)

    p = sub.add_parser("scorecard", help="Build the supplier scorecard from the live API")
    p.add_argument("start_date")
    p.add_argument("end_date")
    p.add_argument("analysis_date")

    args = parser.parse_args(argv)

    if args.cmd == "effective":
        catalogs = load_catalogs()
        products = index_by(catalogs["products"], "sku")
        inventory = {(row["warehouse_id"], row["sku"]): row for row in catalogs["inventory"]}
        row = inventory_record(inventory, args.warehouse_id, args.sku)
        product = product_record(products, args.sku)
        print_json(
            {
                "sku": args.sku,
                "warehouse_id": args.warehouse_id,
                "on_hand": row["on_hand"],
                "reserved": row["reserved"],
                "quarantined": row["quarantined"],
                "safety_stock": product["safety_stock"],
                "free_stock": free_stock(row),
                "effective_available": effective_available(row, product),
                "transferable_surplus": transferable_surplus(row, product),
            }
        )
        return 0

    if args.cmd == "quote":
        print_json(
            fetch_json(
                "/shipping/quote",
                params={
                    "warehouse_id": args.warehouse_id,
                    "destination_zip": args.destination_zip,
                    "speed": args.speed,
                    "weight_lb": args.weight_lb,
                },
            )
        )
        return 0

    if args.cmd == "scorecard":
        catalogs = load_catalogs()
        print_json(
            supplier_scorecard(
                catalogs["incidents"],
                catalogs["suppliers"],
                args.start_date,
                args.end_date,
                args.analysis_date,
            )
        )
        return 0

    parser.error("unknown command")


if __name__ == "__main__":
    raise SystemExit(main())
