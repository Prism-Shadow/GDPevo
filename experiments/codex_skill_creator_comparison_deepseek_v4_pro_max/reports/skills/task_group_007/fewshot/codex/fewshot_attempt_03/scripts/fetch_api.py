#!/usr/bin/env python3
"""Fetch data from the Northwind ERP API."""

import json
import sys
import urllib.request


def fetch_all(base_url, endpoint):
    """Fetch a list endpoint and return the parsed JSON."""
    url = f"{base_url}/{endpoint}"
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode())


def fetch_one(base_url, endpoint, entity_id):
    """Fetch a single entity by ID. Falls back to filtering the list if a
    404 is returned (not all detail endpoints are supported)."""
    url = f"{base_url}/{endpoint}/{entity_id}"
    try:
        with urllib.request.urlopen(url) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Fallback: fetch all and filter
            all_items = fetch_all(base_url, endpoint)
            # Determine the id field name from the endpoint
            id_field_map = {
                "products": "sku",
                "inventory": None,  # no single inventory endpoint
                "warehouses": "warehouse_id",
                "orders": "order_id",
                "customers": "customer_id",
                "suppliers": "supplier_id",
                "purchase_orders": "po_id",
                "boms": "bom_id",
                "incidents": "incident_id",
            }
            id_field = id_field_map.get(endpoint)
            if id_field is None:
                return all_items  # return all, caller filters
            for item in all_items:
                if item.get(id_field) == entity_id:
                    return item
            return None
        raise


def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_api.py <BASE_URL> [endpoint [entity_id]]", file=sys.stderr)
        print("  BASE_URL: e.g., http://task-env:9007", file=sys.stderr)
        print("  endpoint: products, inventory, warehouses, orders, customers,", file=sys.stderr)
        print("            suppliers, purchase_orders, boms, incidents", file=sys.stderr)
        print("  entity_id: optional single-entity lookup", file=sys.stderr)
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    endpoint = sys.argv[2] if len(sys.argv) > 2 else None
    entity_id = sys.argv[3] if len(sys.argv) > 3 else None

    if endpoint is None:
        # Fetch all collections and dump them
        collections = [
            "products", "inventory", "warehouses", "orders",
            "customers", "suppliers", "purchase_orders", "boms", "incidents"
        ]
        result = {}
        for coll in collections:
            result[coll] = fetch_all(base_url, coll)
        json.dump(result, sys.stdout, indent=2)
    elif entity_id is None:
        data = fetch_all(base_url, endpoint)
        json.dump(data, sys.stdout, indent=2)
    else:
        data = fetch_one(base_url, endpoint, entity_id)
        json.dump(data, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
