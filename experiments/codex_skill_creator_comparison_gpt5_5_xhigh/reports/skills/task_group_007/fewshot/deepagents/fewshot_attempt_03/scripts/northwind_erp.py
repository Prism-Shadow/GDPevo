#!/usr/bin/env python3
"""Reusable helpers for Northwind ERP JSON tasks.

The module avoids task-specific ids and can be imported from ad hoc solver
scripts, or used as a small CLI for inspecting records and quote calculations.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


LIST_ENDPOINTS = (
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


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/"


def fetch_json(base_url: str, path: str, params: dict[str, Any] | None = None) -> Any:
    base = normalize_base_url(base_url)
    path = path.lstrip("/")
    url = base + path
    if params:
        url += "?" + urlencode(params)
    with urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def load_all(base_url: str) -> dict[str, Any]:
    return {name: fetch_json(base_url, name) for name in LIST_ENDPOINTS}


def index_by(records: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(record[key]): record for record in records}


def inventory_index(records: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(record["sku"], record["warehouse_id"]): record for record in records}


def effective_available(inv_record: dict[str, Any] | None, product: dict[str, Any]) -> int:
    if inv_record is None:
        return -int(product.get("safety_stock", 0))
    raw_available = (
        int(inv_record.get("on_hand", 0))
        - int(inv_record.get("reserved", 0))
        - int(inv_record.get("quarantined", 0))
    )
    return raw_available - int(product.get("safety_stock", 0))


def usable_units(inv_record: dict[str, Any] | None, product: dict[str, Any]) -> int:
    return max(0, effective_available(inv_record, product))


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def in_date_window(value: str, start: str, end: str) -> bool:
    current = parse_date(value)
    return parse_date(start) <= current <= parse_date(end)


def days_between(start: str, end: str) -> int:
    return (parse_date(end) - parse_date(start)).days


def incident_duration_days(incident: dict[str, Any], analysis_date: str) -> int:
    end = incident.get("close_date") or analysis_date
    return days_between(incident["open_date"], end)


def round_decimal(value: Any, places: int = 2) -> float:
    quant = Decimal("1").scaleb(-places)
    rounded = Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP)
    return float(rounded)


def group_by(records: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[str(record[key])].append(record)
    return dict(groups)


def order_weight(order: dict[str, Any], products_by_sku: dict[str, dict[str, Any]]) -> float:
    total = Decimal("0")
    for line in order.get("lines", []):
        product = products_by_sku[line["sku"]]
        total += Decimal(str(line["quantity"])) * Decimal(str(product["weight_lb"]))
    return float(total)


def shipping_quote(
    base_url: str,
    order: dict[str, Any],
    products_by_sku: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    params = {
        "warehouse_id": order["warehouse_id"],
        "destination_zip": order["destination_zip"],
        "weight_lb": order_weight(order, products_by_sku),
    }
    if order.get("shipping_speed"):
        params["speed"] = order["shipping_speed"]
    return fetch_json(base_url, "shipping/quote", params)


def open_confirmed_pos(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [record for record in records if record.get("status") in {"open", "confirmed"}]


def timely_pos(
    records: list[dict[str, Any]],
    sku: str,
    warehouse_id: str,
    needed_by: str,
) -> list[dict[str, Any]]:
    return sorted(
        [
            record
            for record in open_confirmed_pos(records)
            if record.get("sku") == sku
            and record.get("warehouse_id") == warehouse_id
            and record.get("eta")
            and record["eta"] <= needed_by
        ],
        key=lambda record: record["po_id"],
    )


def source_availability(
    sku: str,
    target_warehouse_id: str,
    inventory_by_sku_wh: dict[tuple[str, str], dict[str, Any]],
    products_by_sku: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    product = products_by_sku[sku]
    rows = []
    for (row_sku, warehouse_id), inv_record in inventory_by_sku_wh.items():
        if row_sku != sku or warehouse_id == target_warehouse_id:
            continue
        available = usable_units(inv_record, product)
        if available > 0:
            rows.append({"warehouse_id": warehouse_id, "available": available})
    return sorted(rows, key=lambda row: (-row["available"], row["warehouse_id"]))


def cmd_snapshot(args: argparse.Namespace) -> None:
    data = load_all(args.base_url)
    print(json.dumps({name: len(value) for name, value in data.items()}, indent=2))


def cmd_effective(args: argparse.Namespace) -> None:
    data = load_all(args.base_url)
    products = index_by(data["products"], "sku")
    inventory = inventory_index(data["inventory"])
    product = products[args.sku]
    inv_record = inventory.get((args.sku, args.warehouse_id))
    print(
        json.dumps(
            {
                "sku": args.sku,
                "warehouse_id": args.warehouse_id,
                "effective_available": effective_available(inv_record, product),
                "usable_units": usable_units(inv_record, product),
            },
            indent=2,
        )
    )


def cmd_quote(args: argparse.Namespace) -> None:
    data = load_all(args.base_url)
    products = index_by(data["products"], "sku")
    orders = index_by(data["orders"], "order_id")
    print(json.dumps(shipping_quote(args.base_url, orders[args.order_id], products), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(required=True)

    snapshot = subparsers.add_parser("snapshot", help="Print record counts for list endpoints.")
    snapshot.add_argument("base_url")
    snapshot.set_defaults(func=cmd_snapshot)

    effective = subparsers.add_parser("effective", help="Compute effective stock for a SKU/warehouse.")
    effective.add_argument("base_url")
    effective.add_argument("sku")
    effective.add_argument("warehouse_id")
    effective.set_defaults(func=cmd_effective)

    quote = subparsers.add_parser("quote", help="Calculate the API shipping quote for an order id.")
    quote.add_argument("base_url")
    quote.add_argument("order_id")
    quote.set_defaults(func=cmd_quote)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
