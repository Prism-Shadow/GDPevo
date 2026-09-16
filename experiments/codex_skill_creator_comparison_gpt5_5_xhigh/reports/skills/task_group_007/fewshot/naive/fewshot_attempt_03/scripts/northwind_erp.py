#!/usr/bin/env python3
"""Small public-API helper for Northwind ERP JSON tasks."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from decimal import Decimal, ROUND_HALF_UP


def money(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def get_json(base_url, path, params=None):
    base_url = base_url.rstrip("/") + "/"
    path = path.lstrip("/")
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(base_url + path + query) as response:
        return json.load(response)


def first_record(records, label):
    if not records:
        raise SystemExit(f"No record found for {label}")
    return records[0]


def effective_available(inventory_record, product_record):
    return (
        int(inventory_record.get("on_hand", 0))
        - int(inventory_record.get("reserved", 0))
        - int(inventory_record.get("quarantined", 0))
        - int(product_record.get("safety_stock", 0))
    )


def cmd_get(args):
    params = {}
    for item in args.param:
        if "=" not in item:
            raise SystemExit(f"Bad --param value {item!r}; expected key=value")
        key, value = item.split("=", 1)
        params[key] = value
    print(json.dumps(get_json(args.base_url, args.path, params), indent=2, sort_keys=True))


def cmd_effective(args):
    product = get_json(args.base_url, f"products/{args.sku}")
    inventory = first_record(
        get_json(args.base_url, "inventory", {"warehouse_id": args.warehouse_id, "sku": args.sku}),
        f"{args.warehouse_id}/{args.sku}",
    )
    output = {
        "warehouse_id": args.warehouse_id,
        "sku": args.sku,
        "on_hand": inventory.get("on_hand", 0),
        "reserved": inventory.get("reserved", 0),
        "quarantined": inventory.get("quarantined", 0),
        "safety_stock": product.get("safety_stock", 0),
        "effective_available": effective_available(inventory, product),
    }
    print(json.dumps(output, indent=2, sort_keys=True))


def cmd_quote_order(args):
    order = get_json(args.base_url, f"orders/{args.order_id}")
    total_weight = Decimal("0")
    for line in order["lines"]:
        product = get_json(args.base_url, f"products/{line['sku']}")
        total_weight += Decimal(str(line["quantity"])) * Decimal(str(product["weight_lb"]))
    quote = get_json(
        args.base_url,
        "shipping/quote",
        {
            "warehouse_id": order["warehouse_id"],
            "destination_zip": order["destination_zip"],
            "weight_lb": str(total_weight),
            "speed": order["shipping_speed"],
        },
    )
    output = {
        "order_id": order["order_id"],
        "warehouse_id": order["warehouse_id"],
        "destination_zip": order["destination_zip"],
        "speed": order["shipping_speed"],
        "weight_lb": float(total_weight),
        "zone_distance": quote["zone_distance"],
        "service_days": quote["service_days"],
        "total_cost_usd": money(quote["total_cost"]),
    }
    print(json.dumps(output, indent=2, sort_keys=True))


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(required=True)

    get_parser = subparsers.add_parser("get", help="Fetch a public API path as JSON")
    get_parser.add_argument("base_url")
    get_parser.add_argument("path")
    get_parser.add_argument("--param", action="append", default=[], help="Query parameter as key=value")
    get_parser.set_defaults(func=cmd_get)

    effective_parser = subparsers.add_parser("effective", help="Compute effective stock for one SKU")
    effective_parser.add_argument("base_url")
    effective_parser.add_argument("--warehouse-id", required=True)
    effective_parser.add_argument("--sku", required=True)
    effective_parser.set_defaults(func=cmd_effective)

    quote_parser = subparsers.add_parser("quote-order", help="Quote an order using line weights")
    quote_parser.add_argument("base_url")
    quote_parser.add_argument("--order-id", required=True)
    quote_parser.set_defaults(func=cmd_quote_order)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
