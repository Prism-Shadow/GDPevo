#!/usr/bin/env python3
"""Stdlib HTTP API for the Northwind Components ERP environment."""

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_FILES = {
    "products": "products.json",
    "suppliers": "suppliers.json",
    "customers": "customers.json",
    "warehouses": "warehouses.json",
    "inventory": "inventory.json",
    "purchase_orders": "purchase_orders.json",
    "orders": "orders.json",
    "boms": "boms.json",
    "incidents": "incidents.json",
    "manifest": "manifest.json",
}


def load_data() -> dict[str, object]:
    missing = [name for name in DATA_FILES.values() if not (DATA_DIR / name).exists()]
    if missing:
        raise RuntimeError(f"Missing generated data files: {', '.join(missing)}")
    return {key: json.loads((DATA_DIR / filename).read_text(encoding="utf-8")) for key, filename in DATA_FILES.items()}


def query_value(query: dict[str, list[str]], name: str) -> str | None:
    values = query.get(name)
    if not values:
        return None
    value = values[0].strip()
    return value or None


def matches(row: dict, query: dict[str, list[str]], field_names: list[str]) -> bool:
    for field in field_names:
        expected = query_value(query, field)
        if expected is not None and str(row.get(field)) != expected:
            return False
    return True


def in_date_window(row: dict, query: dict[str, list[str]], field: str) -> bool:
    value = row.get(field)
    start = query_value(query, "start")
    end = query_value(query, "end")
    if start is not None and (value is None or value < start):
        return False
    if end is not None and (value is None or value > end):
        return False
    return True


class ERPHandler(BaseHTTPRequestHandler):
    data: dict[str, object] = {}

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def send_error_json(self, status: HTTPStatus, message: str) -> None:
        self.send_json({"error": message, "status": status.value}, status)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        parts = [unquote(part) for part in path.split("/") if part]
        query = parse_qs(parsed.query)

        try:
            payload = self.route(parts, query)
        except KeyError as exc:
            self.send_error_json(HTTPStatus.NOT_FOUND, str(exc).strip("'"))
            return
        except ValueError as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            return
        self.send_json(payload)

    def route(self, parts: list[str], query: dict[str, list[str]]) -> object:
        if not parts and query == {}:
            return {
                "service": "Northwind Components ERP API",
                "endpoints": [
                    "/health",
                    "/products",
                    "/products/<sku>",
                    "/customers",
                    "/customers/<customer_id>",
                    "/warehouses",
                    "/inventory?warehouse_id=&sku=",
                    "/purchase_orders?supplier_id=&sku=&status=",
                    "/orders?wave=&required_date=&customer_id=",
                    "/orders/<order_id>",
                    "/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=",
                    "/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=",
                    "/suppliers",
                    "/boms",
                    "/boms/<bom_id>",
                ],
            }

        if parts == ["health"]:
            manifest = self.data["manifest"]
            return {"status": "ok", "manifest": manifest}

        if parts == ["products"]:
            return self.data["products"]
        if len(parts) == 2 and parts[0] == "products":
            return self.find_one("products", "sku", parts[1])

        if parts == ["suppliers"]:
            return self.data["suppliers"]

        if parts == ["customers"]:
            return self.data["customers"]
        if len(parts) == 2 and parts[0] == "customers":
            return self.find_one("customers", "customer_id", parts[1])

        if parts == ["warehouses"]:
            return self.data["warehouses"]

        if parts == ["inventory"]:
            return [row for row in self.data["inventory"] if matches(row, query, ["warehouse_id", "sku"])]

        if parts == ["purchase_orders"]:
            return [
                row for row in self.data["purchase_orders"] if matches(row, query, ["supplier_id", "sku", "status"])
            ]

        if parts == ["orders"]:
            return [
                row for row in self.data["orders"] if matches(row, query, ["wave", "required_date", "customer_id"])
            ]
        if len(parts) == 2 and parts[0] == "orders":
            return self.find_one("orders", "order_id", parts[1])

        if parts == ["shipping", "quote"]:
            return self.shipping_quote(query)

        if parts == ["incidents"]:
            return [
                row
                for row in self.data["incidents"]
                if matches(row, query, ["supplier_id", "sku", "incident_type", "status"])
                and in_date_window(row, query, "open_date")
            ]

        if parts == ["boms"]:
            return self.data["boms"]
        if len(parts) == 2 and parts[0] == "boms":
            return self.find_one("boms", "bom_id", parts[1])

        raise KeyError("endpoint not found")

    def find_one(self, collection: str, key: str, value: str) -> dict:
        for row in self.data[collection]:
            if str(row.get(key)) == value:
                return row
        raise KeyError(f"{collection} record not found")

    def shipping_quote(self, query: dict[str, list[str]]) -> dict:
        warehouse_id = query_value(query, "warehouse_id")
        destination_zip = query_value(query, "destination_zip")
        weight_raw = query_value(query, "weight_lb")
        speed = query_value(query, "speed") or "ground"
        if warehouse_id is None or destination_zip is None or weight_raw is None:
            raise ValueError("warehouse_id, destination_zip, and weight_lb are required")
        if speed not in {"ground", "two_day", "overnight"}:
            raise ValueError("speed must be one of ground, two_day, overnight")
        try:
            weight_lb = float(weight_raw)
        except ValueError as exc:
            raise ValueError("weight_lb must be numeric") from exc
        if weight_lb <= 0:
            raise ValueError("weight_lb must be positive")

        warehouse = self.find_one("warehouses", "warehouse_id", warehouse_id)
        origin_digit = int(str(warehouse["zip"])[0])
        dest_digit = int(destination_zip[0])
        zone_distance = abs(origin_digit - dest_digit)
        speed_factor = {"ground": 1.0, "two_day": 1.75, "overnight": 2.65}[speed]
        base = 8.75 + (1.18 * weight_lb) + (3.4 * zone_distance)
        total = round(base * speed_factor * 1.0925, 2)
        return {
            "warehouse_id": warehouse_id,
            "destination_zip": destination_zip,
            "weight_lb": round(weight_lb, 2),
            "speed": speed,
            "zone_distance": zone_distance,
            "carrier": "Northwind Parcel",
            "base_rate": round(base, 2),
            "fuel_surcharge_rate": 0.0925,
            "total_cost": total,
            "service_days": {"ground": 5 - min(zone_distance, 3), "two_day": 2, "overnight": 1}[speed],
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8007, type=int)
    args = parser.parse_args()

    ERPHandler.data = load_data()
    server = ThreadingHTTPServer((args.host, args.port), ERPHandler)
    print(f"Serving Northwind Components ERP API at http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
