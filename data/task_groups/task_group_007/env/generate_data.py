#!/usr/bin/env python3
"""Generate shared ERP fixture data for task_group_007."""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path


SEED = 7007
DATA_DIR = Path(__file__).resolve().parent / "data"


def money(value: float) -> float:
    return round(value + 1e-9, 2)


def iso_day(start: date, end: date, rng: random.Random) -> str:
    span = (end - start).days
    return (start + timedelta(days=rng.randint(0, span))).isoformat()


def write_json(name: str, payload: object) -> None:
    path = DATA_DIR / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_suppliers() -> list[dict]:
    names = [
        ("SUP-001", "Apex Capacitor Works", "Northeast", "approved"),
        ("SUP-002", "Apex Capacitors Intl.", "Northeast", "approved"),
        ("SUP-003", "Branson Relay Group", "Midwest", "quality_hold"),
        ("SUP-004", "Cobalt Industrial Supply", "South", "approved"),
        ("SUP-005", "Delta Harness Co.", "West", "approved"),
        ("SUP-006", "Edison Fastener Partners", "Midwest", "watch"),
        ("SUP-007", "Foxtrot Sensor Labs", "West", "approved"),
        ("SUP-008", "Granite Power Modules", "Northeast", "quality_hold"),
        ("SUP-009", "Harbor PCB Assembly", "South", "approved"),
        ("SUP-010", "Ionix Thermal Systems", "West", "watch"),
        ("SUP-011", "Juniper Packaging Ltd.", "Midwest", "approved"),
        ("SUP-012", "Keystone MRO Components", "Northeast", "approved"),
    ]
    return [
        {
            "supplier_id": supplier_id,
            "name": name,
            "region": region,
            "quality_status": quality_status,
        }
        for supplier_id, name, region, quality_status in names
    ]


def build_products(rng: random.Random, suppliers: list[dict]) -> list[dict]:
    categories = [
        ("electronics", ["controller", "sensor", "relay", "capacitor", "pcb", "terminal"]),
        ("industrial_spares", ["bearing", "valve", "filter", "coupler", "seal", "pump"]),
        ("maintenance_kits", ["inspection kit", "seal kit", "retrofit kit", "fastener kit"]),
        ("power", ["driver", "inverter", "power module", "thermal block"]),
    ]
    products: list[dict] = []
    for i in range(54):
        category, nouns = categories[i % len(categories)]
        noun = nouns[(i // len(categories)) % len(nouns)]
        supplier = suppliers[(i * 5 + rng.randint(0, 3)) % len(suppliers)]
        sku = f"NW-{1000 + i}"
        unit_cost = money(rng.uniform(7.5, 420.0) * (1.25 if category == "power" else 1.0))
        safety_stock = rng.randint(6, 55)
        products.append(
            {
                "sku": sku,
                "name": f"{noun.title()} {chr(65 + (i % 26))}-{rng.randint(10, 99)}",
                "category": category,
                "supplier_id": supplier["supplier_id"],
                "unit_cost": unit_cost,
                "weight_lb": round(rng.uniform(0.15, 34.0), 2),
                "safety_stock": safety_stock,
                "overstock_threshold": safety_stock + rng.randint(55, 260),
                "active": False if i in {7, 19, 33, 48} else True,
            }
        )
    return products


def build_customers(rng: random.Random) -> list[dict]:
    prefixes = [
        "Acme",
        "Blue Ridge",
        "Caldera",
        "Dover",
        "Evergreen",
        "Fulton",
        "Garrison",
        "Helio",
        "Ironbridge",
        "Jasper",
    ]
    suffixes = ["Mfg", "Systems", "Service", "Transit", "Automation", "Foundry"]
    customers: list[dict] = []
    for i in range(40):
        status = rng.choices(["active", "review_required", "blocked"], weights=[27, 9, 4], k=1)[0]
        risk_flag = rng.choices(["none", "fraud_watch", "credit_watch"], weights=[30, 4, 6], k=1)[0]
        if status == "blocked" and risk_flag == "none":
            risk_flag = rng.choice(["fraud_watch", "credit_watch"])
        customers.append(
            {
                "customer_id": f"CUST-{2000 + i}",
                "name": f"{prefixes[i % len(prefixes)]} {suffixes[(i * 3) % len(suffixes)]}",
                "tier": rng.choice(["strategic", "standard", "economy"]),
                "account_status": status,
                "risk_flag": risk_flag,
                "margin_band": rng.choice(["low", "medium", "high"]),
            }
        )
    return customers


def build_inventory(rng: random.Random, products: list[dict], warehouses: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for warehouse in warehouses:
        for idx, product in enumerate(products):
            base = rng.randint(0, 260)
            if idx % 17 == 0:
                base = rng.randint(0, 18)
            reserved = rng.randint(0, min(base, 80))
            quarantined = rng.choice([0, 0, 0, rng.randint(1, min(max(base - reserved, 1), 30))])
            last_count = iso_day(date(2025, 10, 1), date(2026, 5, 24), rng)
            rows.append(
                {
                    "warehouse_id": warehouse["warehouse_id"],
                    "sku": product["sku"],
                    "on_hand": base,
                    "reserved": reserved,
                    "quarantined": quarantined,
                    "last_count_date": last_count,
                }
            )
    return rows


def build_purchase_orders(rng: random.Random, products: list[dict], warehouses: list[dict]) -> list[dict]:
    rows: list[dict] = []
    statuses = ["open", "confirmed", "received", "cancelled"]
    for i in range(92):
        product = rng.choice(products)
        status = rng.choices(statuses, weights=[32, 26, 24, 10], k=1)[0]
        rows.append(
            {
                "po_id": f"PO-{50000 + i}",
                "supplier_id": product["supplier_id"],
                "sku": product["sku"],
                "warehouse_id": rng.choice(warehouses)["warehouse_id"],
                "quantity": rng.randint(20, 420),
                "eta": iso_day(date(2026, 1, 3), date(2026, 8, 31), rng),
                "status": status,
            }
        )
    return rows


def build_orders(
    rng: random.Random, products: list[dict], customers: list[dict], warehouses: list[dict]
) -> list[dict]:
    waves = [
        "TRAIN_EXPEDITE_A",
        "TRAIN_TRANSFER_B",
        "TRAIN_REPLENISH_C",
        "TEST_PRIORITY_D",
        "TEST_QUALITY_E",
        "TEST_BOARD_F",
        "BACKLOG_STANDARD_G",
    ]
    speeds = ["ground", "two_day", "overnight"]
    priorities = ["low", "normal", "high", "critical"]
    rows: list[dict] = []
    for i in range(88):
        line_count = rng.randint(1, 5)
        line_skus = rng.sample(products, line_count)
        lines = []
        for line_idx, product in enumerate(line_skus, start=1):
            markup = rng.uniform(1.18, 1.72)
            lines.append(
                {
                    "line_id": line_idx,
                    "sku": product["sku"],
                    "quantity": rng.randint(1, 36),
                    "unit_price": money(product["unit_cost"] * markup),
                }
            )
        rows.append(
            {
                "order_id": f"SO-{70000 + i}",
                "wave": waves[i % len(waves)],
                "customer_id": rng.choice(customers)["customer_id"],
                "warehouse_id": rng.choice(warehouses)["warehouse_id"],
                "destination_zip": f"{rng.choice([0, 1, 2, 3, 4, 6, 8, 9])}{rng.randint(1000, 9999)}",
                "shipping_speed": rng.choices(speeds, weights=[42, 30, 16], k=1)[0],
                "priority": rng.choices(priorities, weights=[12, 42, 25, 9], k=1)[0],
                "required_date": iso_day(date(2026, 2, 1), date(2026, 7, 31), rng),
                "lines": lines,
            }
        )
    return rows


def build_boms(rng: random.Random, products: list[dict], warehouses: list[dict]) -> list[dict]:
    rows: list[dict] = []
    active_products = [product for product in products if product["active"]]
    for i in range(9):
        component_count = rng.randint(3, 7)
        components = []
        for product in rng.sample(active_products, component_count):
            components.append({"sku": product["sku"], "quantity_per_kit": rng.randint(1, 8)})
        rows.append(
            {
                "bom_id": f"BOM-{300 + i}",
                "name": f"{rng.choice(['PM', 'Retrofit', 'Emergency', 'Line Change'])} Kit {i + 1}",
                "target_date": iso_day(date(2026, 3, 1), date(2026, 8, 15), rng),
                "warehouse_id": rng.choice(warehouses)["warehouse_id"],
                "components": components,
            }
        )
    return rows


def build_incidents(rng: random.Random, products: list[dict], warehouses: list[dict]) -> list[dict]:
    rows: list[dict] = []
    root_causes = [
        "supplier_defect",
        "carrier_damage",
        "count_variance",
        "incorrect_pick",
        "engineering_change",
        "customer_return",
    ]
    for i in range(212):
        product = rng.choice(products)
        status = rng.choices(["open", "closed"], weights=[44, 168], k=1)[0]
        open_dt = date.fromisoformat(iso_day(date(2025, 1, 1), date(2026, 5, 28), rng))
        close_dt = None
        if status == "closed":
            close_dt = open_dt + timedelta(days=rng.randint(2, 75))
        rows.append(
            {
                "incident_id": f"INC-{90000 + i}",
                "incident_type": rng.choice(["RMA", "WORK_ORDER"]),
                "supplier_id": product["supplier_id"],
                "sku": product["sku"],
                "warehouse_id": rng.choice(warehouses)["warehouse_id"],
                "open_date": open_dt.isoformat(),
                "close_date": close_dt.isoformat() if close_dt else None,
                "status": status,
                "severity": rng.choices(["low", "medium", "high", "critical"], weights=[72, 82, 42, 16], k=1)[0],
                "resolution_cost": money(rng.uniform(25.0, 7200.0)),
                "root_cause": rng.choice(root_causes),
            }
        )
    return rows


def main() -> None:
    rng = random.Random(SEED)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    suppliers = build_suppliers()
    products = build_products(rng, suppliers)
    customers = build_customers(rng)
    warehouses = [
        {
            "warehouse_id": "WH_NORTH",
            "name": "New Jersey Regional Warehouse",
            "zip": "07102",
            "region": "Northeast",
        },
        {
            "warehouse_id": "WH_CENTRAL",
            "name": "Illinois Central Warehouse",
            "zip": "60607",
            "region": "Midwest",
        },
        {
            "warehouse_id": "WH_WEST",
            "name": "Nevada West Warehouse",
            "zip": "89502",
            "region": "West",
        },
    ]
    inventory = build_inventory(rng, products, warehouses)
    purchase_orders = build_purchase_orders(rng, products, warehouses)
    orders = build_orders(rng, products, customers, warehouses)
    boms = build_boms(rng, products, warehouses)
    incidents = build_incidents(rng, products, warehouses)

    files = {
        "products.json": products,
        "suppliers.json": suppliers,
        "customers.json": customers,
        "warehouses.json": warehouses,
        "inventory.json": inventory,
        "purchase_orders.json": purchase_orders,
        "orders.json": orders,
        "boms.json": boms,
        "incidents.json": incidents,
    }
    for name, payload in files.items():
        write_json(name, payload)

    manifest = {
        "seed": SEED,
        "generation_timestamp": "2026-06-01T00:00:00Z",
        "record_counts": {name.removesuffix(".json"): len(payload) for name, payload in files.items()},
        "file_list": sorted(list(files) + ["manifest.json"]),
    }
    write_json("manifest.json", manifest)
    print(f"Generated ERP data in {DATA_DIR}")


if __name__ == "__main__":
    main()
