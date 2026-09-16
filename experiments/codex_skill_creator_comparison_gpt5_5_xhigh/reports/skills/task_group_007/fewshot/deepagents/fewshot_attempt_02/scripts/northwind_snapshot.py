#!/usr/bin/env python3
"""Fetch a Northwind ERP API snapshot for operational JSON tasks."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from typing import Any


CORE_ENDPOINTS = (
    "products",
    "inventory",
    "warehouses",
    "orders",
    "customers",
    "suppliers",
    "purchase_orders",
    "boms",
    "incidents",
)


def get_json(base_url: str, path: str, params: dict[str, Any] | None = None) -> Any:
    base = base_url.rstrip("/") + "/"
    url = urllib.parse.urljoin(base, path.lstrip("/"))
    if params:
        query = urllib.parse.urlencode(params)
        url = f"{url}?{query}"
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def split_ids(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {part.strip() for part in raw.split(",") if part.strip()}


def by_key(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {row[key]: row for row in rows}


def enrich_inventory(
    inventory: list[dict[str, Any]], products_by_sku: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    enriched = []
    for row in inventory:
        product = products_by_sku.get(row["sku"], {})
        safety_stock = int(product.get("safety_stock", 0))
        out = dict(row)
        out["safety_stock"] = safety_stock
        out["effective_available"] = (
            int(row.get("on_hand", 0))
            - int(row.get("reserved", 0))
            - int(row.get("quarantined", 0))
            - safety_stock
        )
        enriched.append(out)
    return enriched


def order_weight(order: dict[str, Any], products_by_sku: dict[str, dict[str, Any]]) -> float:
    total = 0.0
    for line in order.get("lines", []):
        product = products_by_sku[line["sku"]]
        total += float(line["quantity"]) * float(product.get("weight_lb", 0.0))
    return round(total, 4)


def selected_orders(
    all_orders: list[dict[str, Any]], wave: str | None, order_ids: set[str]
) -> list[dict[str, Any]]:
    rows = all_orders
    if wave:
        rows = [order for order in rows if order.get("wave") == wave]
    if order_ids:
        rows = [order for order in rows if order.get("order_id") in order_ids]
    return sorted(rows, key=lambda order: order.get("order_id", ""))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Northwind ERP API base URL")
    parser.add_argument("--wave", help="Filter orders to a wave ID")
    parser.add_argument("--orders", help="Comma-separated order IDs to keep")
    parser.add_argument("--suppliers", help="Comma-separated supplier IDs to keep")
    parser.add_argument("--boms", help="Comma-separated BOM IDs to keep")
    parser.add_argument(
        "--quote-orders",
        action="store_true",
        help="Fetch shipping quotes for selected orders",
    )
    parser.add_argument("--out", help="Optional output JSON path")
    args = parser.parse_args()

    data = {endpoint: get_json(args.base_url, endpoint) for endpoint in CORE_ENDPOINTS}

    products_by_sku = by_key(data["products"], "sku")
    warehouses_by_id = by_key(data["warehouses"], "warehouse_id")
    customers_by_id = by_key(data["customers"], "customer_id")
    suppliers_by_id = by_key(data["suppliers"], "supplier_id")

    order_ids = split_ids(args.orders)
    supplier_ids = split_ids(args.suppliers)
    bom_ids = split_ids(args.boms)
    orders = selected_orders(data["orders"], args.wave, order_ids)

    if supplier_ids:
        suppliers = [
            row for row in data["suppliers"] if row.get("supplier_id") in supplier_ids
        ]
        purchase_orders = [
            row for row in data["purchase_orders"] if row.get("supplier_id") in supplier_ids
        ]
        incidents = [
            row for row in data["incidents"] if row.get("supplier_id") in supplier_ids
        ]
    else:
        suppliers = data["suppliers"]
        purchase_orders = data["purchase_orders"]
        incidents = data["incidents"]

    if bom_ids:
        boms = [row for row in data["boms"] if row.get("bom_id") in bom_ids]
    else:
        boms = data["boms"]

    inventory = enrich_inventory(data["inventory"], products_by_sku)

    quotes: dict[str, Any] = {}
    if args.quote_orders:
        for order in orders:
            weight = order_weight(order, products_by_sku)
            quote = get_json(
                args.base_url,
                "shipping/quote",
                {
                    "warehouse_id": order["warehouse_id"],
                    "destination_zip": order["destination_zip"],
                    "weight_lb": weight,
                    "speed": order.get("shipping_speed", "ground"),
                },
            )
            quotes[order["order_id"]] = quote

    snapshot = {
        "orders": orders,
        "products_by_sku": products_by_sku,
        "inventory": inventory,
        "warehouses_by_id": warehouses_by_id,
        "customers_by_id": customers_by_id,
        "suppliers": suppliers,
        "suppliers_by_id": suppliers_by_id,
        "purchase_orders": purchase_orders,
        "boms": boms,
        "incidents": incidents,
        "shipping_quotes_by_order_id": quotes,
    }

    text = json.dumps(snapshot, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
