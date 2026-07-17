#!/usr/bin/env python3
"""Build the deterministic Atlas Commerce Operations SQLite baseline.

This script intentionally uses only the Python standard library.  It may be
rerun from any working directory; output defaults beside this file.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import random
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Iterable, Iterator, Sequence


SEED = 220716
SCHEMA_VERSION = "atlas-commerce-1.0"
START_DATE = dt.date(2026, 1, 1)
END_DATE = dt.date(2026, 6, 30)
UTC = dt.timezone.utc

DDL = r"""
PRAGMA foreign_keys = ON;

CREATE TABLE accounts (
    account_id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL,
    segment TEXT NOT NULL CHECK (segment IN ('CONSUMER','SMB','ENTERPRISE','STRATEGIC')),
    tier TEXT NOT NULL CHECK (tier IN ('STANDARD','SILVER','GOLD','PLATINUM')),
    region TEXT NOT NULL,
    currency TEXT NOT NULL,
    is_internal INTEGER NOT NULL CHECK (is_internal IN (0,1)),
    is_test INTEGER NOT NULL CHECK (is_test IN (0,1)),
    created_at TEXT NOT NULL
);

CREATE TABLE campaigns (
    campaign_id TEXT PRIMARY KEY,
    campaign_name TEXT NOT NULL UNIQUE,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    channel TEXT NOT NULL
);

CREATE TABLE warehouses (
    warehouse_id TEXT PRIMARY KEY,
    warehouse_name TEXT NOT NULL,
    region TEXT NOT NULL,
    timezone TEXT NOT NULL,
    daily_cutoff_local TEXT NOT NULL
);

CREATE TABLE employees (
    employee_id TEXT PRIMARY KEY,
    warehouse_id TEXT NOT NULL REFERENCES warehouses(warehouse_id),
    team_id TEXT NOT NULL,
    role TEXT NOT NULL,
    active_from TEXT NOT NULL,
    active_to TEXT
);

CREATE TABLE products (
    sku TEXT PRIMARY KEY,
    product_family TEXT NOT NULL,
    unit_weight_grams INTEGER NOT NULL CHECK (unit_weight_grams > 0),
    units_per_case INTEGER NOT NULL CHECK (units_per_case > 0),
    is_active INTEGER NOT NULL CHECK (is_active IN (0,1))
);

CREATE TABLE fx_rates (
    rate_date TEXT NOT NULL,
    currency TEXT NOT NULL,
    usd_per_unit REAL NOT NULL CHECK (usd_per_unit > 0),
    PRIMARY KEY (rate_date, currency)
);

CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    campaign_id TEXT REFERENCES campaigns(campaign_id),
    warehouse_id TEXT NOT NULL REFERENCES warehouses(warehouse_id),
    order_created_at TEXT NOT NULL,
    promised_at TEXT NOT NULL,
    currency TEXT NOT NULL,
    current_status TEXT NOT NULL,
    gross_amount_minor INTEGER NOT NULL CHECK (gross_amount_minor >= 0)
);

CREATE TABLE order_lines (
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    line_id INTEGER NOT NULL,
    sku TEXT NOT NULL REFERENCES products(sku),
    quantity_each INTEGER NOT NULL CHECK (quantity_each > 0),
    PRIMARY KEY (order_id, line_id)
);

CREATE TABLE order_events (
    event_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    event_type TEXT NOT NULL,
    event_at TEXT NOT NULL,
    source_system TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE shipments (
    shipment_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    carrier_code TEXT NOT NULL,
    warehouse_id TEXT NOT NULL REFERENCES warehouses(warehouse_id),
    shipped_at TEXT,
    promised_delivery_at TEXT NOT NULL,
    current_status TEXT NOT NULL
);

CREATE TABLE carrier_scans (
    scan_row_id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES shipments(shipment_id),
    source_system TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    raw_status TEXT NOT NULL,
    raw_event_at TEXT NOT NULL,
    canonical_status TEXT NOT NULL,
    canonical_event_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    import_batch_id TEXT NOT NULL REFERENCES source_import_batches(import_batch_id),
    corrected_at TEXT,
    correction_reason TEXT
);

CREATE TABLE payment_events (
    payment_event_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    provider TEXT NOT NULL,
    source_system TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    amount_minor INTEGER NOT NULL,
    currency TEXT NOT NULL,
    event_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    linked_event_id TEXT
);

CREATE TABLE refund_attempts (
    refund_row_id TEXT PRIMARY KEY,
    refund_id TEXT NOT NULL,
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    provider TEXT NOT NULL,
    source_system TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    status TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (amount_minor >= 0),
    currency TEXT NOT NULL,
    service_date TEXT NOT NULL,
    event_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    linked_refund_id TEXT
);

CREATE TABLE support_cases (
    case_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    order_id TEXT REFERENCES orders(order_id),
    priority TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    current_status TEXT NOT NULL,
    current_owner_team TEXT NOT NULL
);

CREATE TABLE case_events (
    case_event_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES support_cases(case_id),
    event_type TEXT NOT NULL,
    event_at TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    source_system TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE TABLE warehouse_tasks (
    task_id TEXT PRIMARY KEY,
    warehouse_id TEXT NOT NULL REFERENCES warehouses(warehouse_id),
    order_id TEXT REFERENCES orders(order_id),
    sku TEXT REFERENCES products(sku),
    assigned_employee_id TEXT NOT NULL REFERENCES employees(employee_id),
    task_type TEXT NOT NULL,
    work_class TEXT NOT NULL CHECK (work_class IN ('PRODUCTION','TRAINING')),
    priority TEXT NOT NULL,
    planned_units INTEGER NOT NULL CHECK (planned_units >= 0),
    created_at TEXT NOT NULL,
    due_at TEXT NOT NULL,
    current_status TEXT NOT NULL
);

CREATE TABLE warehouse_task_events (
    task_event_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES warehouse_tasks(task_id),
    event_type TEXT NOT NULL,
    event_at TEXT NOT NULL,
    units INTEGER NOT NULL CHECK (units >= 0),
    productive_minutes INTEGER NOT NULL CHECK (productive_minutes >= 0),
    source_system TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE TABLE inventory_movements (
    movement_row_id TEXT PRIMARY KEY,
    movement_id TEXT NOT NULL,
    warehouse_id TEXT NOT NULL REFERENCES warehouses(warehouse_id),
    sku TEXT NOT NULL REFERENCES products(sku),
    movement_type TEXT NOT NULL,
    raw_quantity INTEGER NOT NULL,
    raw_uom TEXT NOT NULL,
    raw_uom_multiplier INTEGER NOT NULL CHECK (raw_uom_multiplier > 0),
    canonical_quantity_each INTEGER NOT NULL,
    canonical_uom_multiplier INTEGER NOT NULL CHECK (canonical_uom_multiplier > 0),
    occurred_at TEXT NOT NULL,
    source_system TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    source_document_id TEXT NOT NULL,
    corrected_at TEXT,
    correction_reason TEXT
);

CREATE TABLE inventory_snapshots (
    warehouse_id TEXT NOT NULL REFERENCES warehouses(warehouse_id),
    sku TEXT NOT NULL REFERENCES products(sku),
    snapshot_at TEXT NOT NULL,
    on_hand_each INTEGER NOT NULL,
    reserved_each INTEGER NOT NULL,
    source_system TEXT NOT NULL,
    PRIMARY KEY (warehouse_id, sku, snapshot_at)
);

CREATE TABLE source_import_batches (
    import_batch_id TEXT PRIMARY KEY,
    source_system TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    record_count INTEGER NOT NULL CHECK (record_count >= 0),
    status TEXT NOT NULL
);

CREATE TABLE correction_audit (
    audit_id TEXT PRIMARY KEY,
    correction_key TEXT NOT NULL UNIQUE,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    source_row_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason_code TEXT NOT NULL,
    corrected_at TEXT NOT NULL,
    actor TEXT NOT NULL
);

CREATE INDEX idx_accounts_segment_region ON accounts(segment, region);
CREATE INDEX idx_orders_account_created ON orders(account_id, order_created_at);
CREATE INDEX idx_orders_campaign_created ON orders(campaign_id, order_created_at);
CREATE INDEX idx_orders_warehouse_promised ON orders(warehouse_id, promised_at);
CREATE INDEX idx_order_events_effective ON order_events(order_id, event_at, event_id);
CREATE INDEX idx_order_events_dedupe ON order_events(source_system, external_event_id, ingested_at);
CREATE INDEX idx_shipments_order ON shipments(order_id);
CREATE INDEX idx_shipments_warehouse_promised ON shipments(warehouse_id, promised_delivery_at);
CREATE INDEX idx_scans_shipment_effective ON carrier_scans(shipment_id, canonical_event_at, scan_row_id);
CREATE INDEX idx_scans_dedupe ON carrier_scans(source_system, external_event_id, ingested_at);
CREATE INDEX idx_scans_batch ON carrier_scans(import_batch_id);
CREATE INDEX idx_payments_order_event ON payment_events(order_id, event_at);
CREATE INDEX idx_payments_dedupe ON payment_events(source_system, external_event_id, ingested_at);
CREATE INDEX idx_refunds_order_service ON refund_attempts(order_id, service_date);
CREATE INDEX idx_refunds_dedupe ON refund_attempts(source_system, external_event_id, ingested_at);
CREATE INDEX idx_cases_account_opened ON support_cases(account_id, opened_at);
CREATE INDEX idx_case_events_effective ON case_events(case_id, event_at, case_event_id);
CREATE INDEX idx_case_events_dedupe ON case_events(source_system, external_event_id, ingested_at);
CREATE INDEX idx_tasks_warehouse_due ON warehouse_tasks(warehouse_id, due_at);
CREATE INDEX idx_tasks_employee ON warehouse_tasks(assigned_employee_id, created_at);
CREATE INDEX idx_task_events_effective ON warehouse_task_events(task_id, event_at, task_event_id);
CREATE INDEX idx_task_events_dedupe ON warehouse_task_events(source_system, external_event_id, ingested_at);
CREATE INDEX idx_movements_warehouse_sku_time ON inventory_movements(warehouse_id, sku, occurred_at);
CREATE INDEX idx_movements_dedupe ON inventory_movements(source_system, external_event_id, ingested_at);
CREATE INDEX idx_snapshots_time ON inventory_snapshots(snapshot_at, warehouse_id);
CREATE INDEX idx_audit_entity ON correction_audit(entity_type, entity_id, corrected_at);
"""


def iso(value: dt.datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def at_day(day_offset: int, minute: int = 0) -> dt.datetime:
    return dt.datetime.combine(START_DATE + dt.timedelta(days=day_offset), dt.time(), UTC) + dt.timedelta(minutes=minute)


def chunks(rows: Iterable[Sequence[object]], size: int = 5000) -> Iterator[list[Sequence[object]]]:
    batch: list[Sequence[object]] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def insert_many(conn: sqlite3.Connection, sql: str, rows: Iterable[Sequence[object]]) -> None:
    for batch in chunks(rows):
        conn.executemany(sql, batch)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def create_batches(conn: sqlite3.Connection) -> list[str]:
    systems = [
        ("CARRIER_HUB", "carrier_scan"),
        ("ORDER_CORE", "order_event"),
        ("PAYMENT_GATEWAY", "payment_event"),
        ("SUPPORT_DESK", "case_event"),
        ("WMS_EDGE", "warehouse_task_event"),
        ("ERP_LEDGER", "inventory_movement"),
    ]
    rows = []
    identifiers = []
    for month in range(1, 7):
        for system_index, (system, entity) in enumerate(systems):
            for half in range(2):
                batch_id = f"BATCH-{month:02d}-{system_index + 1:02d}-{half + 1}"
                day = dt.date(2026, month, 5 if half == 0 else 20)
                started = dt.datetime.combine(day, dt.time(1 + system_index, 0), UTC)
                rows.append((batch_id, system, entity, iso(started), iso(started + dt.timedelta(minutes=25)), 0, "COMPLETED"))
                identifiers.append(batch_id)
    conn.executemany("INSERT INTO source_import_batches VALUES (?,?,?,?,?,?,?)", rows)
    return identifiers


def build_database(output: Path) -> dict[str, object]:
    rng = random.Random(SEED)
    if output.exists():
        output.unlink()
    conn = sqlite3.connect(output)
    conn.execute("PRAGMA journal_mode = OFF")
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.executescript(DDL)
    create_batches(conn)

    warehouse_rows = [
        ("WH-NORTH-01", "Northstar Fulfillment", "NORTH", "America/New_York", "17:00"),
        ("WH-SOUTH-01", "Sunbelt Fulfillment", "SOUTH", "America/Chicago", "16:30"),
        ("WH-WEST-01", "Pacific Fulfillment", "WEST", "America/Los_Angeles", "16:00"),
        ("WH-EAST-01", "Atlantic Fulfillment", "EAST", "America/New_York", "17:30"),
        ("WH-CENTRAL-01", "Heartland Fulfillment", "CENTRAL", "America/Chicago", "16:45"),
    ]
    conn.executemany("INSERT INTO warehouses VALUES (?,?,?,?,?)", warehouse_rows)
    warehouses = [row[0] for row in warehouse_rows]
    regions = ["NORTH", "SOUTH", "WEST", "EAST", "CENTRAL"]
    currencies = ["USD", "EUR", "GBP", "CAD", "AUD"]

    campaign_rows = [
        ("CMP-SPRING-26", "Spring Forward 2026", "2026-03-01T00:00:00Z", "2026-03-31T23:59:59Z", "EMAIL"),
        ("CMP-SPRINGVIP-26", "Spring Forward VIP 2026", "2026-03-07T00:00:00Z", "2026-03-21T23:59:59Z", "PARTNER"),
        ("CMP-MAYPEAK-26", "May Peak 2026", "2026-05-18T00:00:00Z", "2026-05-31T23:59:59Z", "PAID_SEARCH"),
        ("CMP-MAYPEAK-PRE", "May Peak Preview", "2026-05-04T00:00:00Z", "2026-05-10T23:59:59Z", "SOCIAL"),
        ("CMP-NEWYEAR-26", "New Year Essentials", "2026-01-02T00:00:00Z", "2026-01-18T23:59:59Z", "EMAIL"),
        ("CMP-FEBLOYAL-26", "February Loyalty", "2026-02-09T00:00:00Z", "2026-02-22T23:59:59Z", "APP"),
        ("CMP-APRILHOME-26", "April Home Refresh", "2026-04-06T00:00:00Z", "2026-04-19T23:59:59Z", "DISPLAY"),
        ("CMP-JUNEB2B-26", "June Business Week", "2026-06-08T00:00:00Z", "2026-06-21T23:59:59Z", "PARTNER"),
    ]
    conn.executemany("INSERT INTO campaigns VALUES (?,?,?,?,?)", campaign_rows)

    account_rows = []
    segments = ["CONSUMER", "SMB", "ENTERPRISE", "STRATEGIC"]
    tiers = ["STANDARD", "SILVER", "GOLD", "PLATINUM"]
    for index in range(650):
        is_internal = 1 if index < 18 else 0
        is_test = 1 if 18 <= index < 32 else 0
        segment = segments[(index * 7 + index // 19) % len(segments)]
        tier = tiers[(index * 3 + index // 23) % len(tiers)]
        region = regions[(index * 11 + index // 13) % len(regions)]
        currency = currencies[(index * 5 + index // 17) % len(currencies)]
        prefix = "Internal" if is_internal else "Sandbox" if is_test else "Customer"
        created = at_day(-365 + (index % 330), index % 1440)
        account_rows.append((f"ACC-{index + 1:04d}", f"{prefix} Account {index + 1:04d}", segment, tier, region, currency, is_internal, is_test, iso(created)))
    conn.executemany("INSERT INTO accounts VALUES (?,?,?,?,?,?,?,?,?)", account_rows)

    employee_rows = []
    for index in range(90):
        warehouse = warehouses[index // 18]
        team = f"{warehouse}-TEAM-{(index % 18) // 6 + 1}"
        role = "SUPERVISOR" if index % 18 == 0 else "PICKER" if index % 3 else "PACKER"
        active_to = "2026-04-30T23:59:59Z" if index in (16, 53) else None
        employee_rows.append((f"EMP-{index + 1:04d}", warehouse, team, role, "2025-01-01T00:00:00Z", active_to))
    conn.executemany("INSERT INTO employees VALUES (?,?,?,?,?,?)", employee_rows)

    families = ["HOME", "ELECTRONICS", "OUTDOOR", "OFFICE", "APPAREL", "BEAUTY", "PET", "PANTRY", "FITNESS"]
    product_rows = []
    units_per_case: dict[str, int] = {}
    for index in range(900):
        sku = f"SKU-{index + 1:05d}"
        family = families[index // 100]
        upc = [4, 6, 8, 10, 12, 16, 20, 24][index % 8]
        units_per_case[sku] = upc
        product_rows.append((sku, family, 90 + ((index * 137) % 9900), upc, 0 if index >= 885 else 1))
    conn.executemany("INSERT INTO products VALUES (?,?,?,?,?)", product_rows)

    fx_base = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "CAD": 0.74, "AUD": 0.66}
    fx_rows = []
    for offset in range(-12, 192):
        day = START_DATE + dt.timedelta(days=offset)
        for currency_index, currency in enumerate(currencies):
            wave = (((offset + 13) * (currency_index + 3)) % 19 - 9) / 1000
            fx_rows.append((day.isoformat(), currency, round(fx_base[currency] + wave, 6)))
    conn.executemany("INSERT INTO fx_rates VALUES (?,?,?)", fx_rows)

    account_ids = [row[0] for row in account_rows]
    sku_ids = [row[0] for row in product_rows]
    campaign_ids = [row[0] for row in campaign_rows]
    order_rows = []
    order_meta: list[dict[str, object]] = []
    for index in range(14000):
        order_id = f"ORD-{index + 1:06d}"
        account_id = account_ids[(index * 37 + index // 101) % len(account_ids)]
        warehouse = warehouses[(index * 7 + index // 211) % len(warehouses)]
        day_offset = (index * 47 + index // 97) % 181
        created = at_day(day_offset, (index * 29) % 1320)
        promised = created + dt.timedelta(days=2 + index % 5, hours=4 + index % 8)
        campaign: str | None = None
        for campaign_id, _name, starts, ends, _channel in campaign_rows:
            if starts[:10] <= created.date().isoformat() <= ends[:10] and index % 3 != 0:
                campaign = campaign_id
                break
        if campaign is None and index % 17 == 0:
            campaign = campaign_ids[index % len(campaign_ids)]
        account_idx = int(account_id.split("-")[1]) - 1
        currency = account_rows[account_idx][5]
        terminal = "CANCELLED" if index % 23 == 0 else "DELIVERED" if index % 10 < 7 else "SHIPPED" if index % 10 < 9 else "PACKED"
        snapshot_status = terminal
        if index % 13 == 0:
            snapshot_status = ["CREATED", "ALLOCATED", "PACKED", "SHIPPED"][index % 4]
        gross = 1800 + ((index * 7919) % 180000)
        order_rows.append((order_id, account_id, campaign, warehouse, iso(created), iso(promised), currency, snapshot_status, gross))
        order_meta.append({"id": order_id, "created": created, "promised": promised, "terminal": terminal, "warehouse": warehouse, "currency": currency, "gross": gross})
    conn.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?)", order_rows)

    def line_rows() -> Iterator[Sequence[object]]:
        for index, meta in enumerate(order_meta):
            count = 3 if index < 12000 else 2
            for line in range(1, count + 1):
                sku = sku_ids[(index * 13 + line * 101) % len(sku_ids)]
                yield (meta["id"], line, sku, 1 + ((index + line * 3) % 8))

    insert_many(conn, "INSERT INTO order_lines VALUES (?,?,?,?)", line_rows())

    order_events: list[tuple[object, ...]] = []
    event_counter = 1
    dedupe_candidates: list[tuple[object, ...]] = []
    for index, meta in enumerate(order_meta):
        created = meta["created"]
        terminal = str(meta["terminal"])
        types = ["CREATED", "PAYMENT_CONFIRMED", "ALLOCATED", "PACKED", terminal] if index < 6400 else ["CREATED", "PAYMENT_CONFIRMED", "PACKED", terminal]
        for position, event_type in enumerate(types):
            if event_type == terminal:
                if terminal == "DELIVERED":
                    event_at = meta["promised"] + dt.timedelta(hours=(index % 29) - 15)
                elif terminal == "CANCELLED":
                    event_at = created + dt.timedelta(hours=3 + index % 30)
                elif terminal == "SHIPPED":
                    event_at = created + dt.timedelta(hours=20 + index % 42)
                else:
                    event_at = created + dt.timedelta(hours=12 + index % 20)
            else:
                event_at = created + dt.timedelta(hours=position * 5 + (index % 3))
            source = "ORDER_CORE"
            external = f"OC-{meta['id']}-{position + 1}"
            late_delay = dt.timedelta(days=2) if index % 211 == 0 and position == len(types) - 1 else dt.timedelta()
            ingested = event_at + dt.timedelta(minutes=4 + index % 50) + late_delay
            row = (f"OE-{event_counter:07d}", meta["id"], event_type, iso(event_at), source, external, iso(ingested), json.dumps({"sequence": position + 1}, separators=(",", ":")))
            order_events.append(row)
            if event_type not in ("CREATED",):
                dedupe_candidates.append(row)
            event_counter += 1
    for original in dedupe_candidates[:2600]:
        duplicate = list(original)
        duplicate[0] = f"OE-{event_counter:07d}"
        duplicate[6] = iso(dt.datetime.fromisoformat(str(original[6]).replace("Z", "+00:00")) + dt.timedelta(minutes=35))
        order_events.append(tuple(duplicate))
        event_counter += 1
    assert len(order_events) == 65000
    insert_many(conn, "INSERT INTO order_events VALUES (?,?,?,?,?,?,?,?)", order_events)

    eligible_orders = [meta for meta in order_meta if meta["terminal"] != "CANCELLED"]
    shipment_rows = []
    shipment_meta: list[dict[str, object]] = []
    carriers = ["NOVA", "PARCELPRO", "ROADRUNNER", "SKYPOST"]
    shipment_index = 0
    while shipment_index < 15000:
        meta = eligible_orders[shipment_index % len(eligible_orders)]
        part_number = shipment_index // len(eligible_orders) + 1
        shipment_id = f"SHP-{shipment_index + 1:06d}"
        shipped = meta["created"] + dt.timedelta(hours=18 + shipment_index % 38)
        promised_delivery = meta["promised"] + dt.timedelta(hours=part_number - 1)
        final_status = "DELIVERED" if meta["terminal"] == "DELIVERED" and not (part_number > 1 and shipment_index % 4 == 0) else "IN_TRANSIT" if meta["terminal"] == "SHIPPED" else "LABEL_CREATED"
        snapshot_status = final_status if shipment_index % 11 else "IN_TRANSIT"
        carrier = carriers[(shipment_index * 7 + shipment_index // 31) % len(carriers)]
        shipment_rows.append((shipment_id, meta["id"], carrier, meta["warehouse"], iso(shipped), iso(promised_delivery), snapshot_status))
        shipment_meta.append({"id": shipment_id, "shipped": shipped, "promised": promised_delivery, "final": final_status, "warehouse": meta["warehouse"]})
        shipment_index += 1
    conn.executemany("INSERT INTO shipments VALUES (?,?,?,?,?,?,?)", shipment_rows)

    carrier_batches = [f"BATCH-{month:02d}-01-{half}" for month in range(1, 7) for half in (1, 2)]
    scan_rows: list[tuple[object, ...]] = []
    scan_counter = 1
    scan_originals: list[tuple[object, ...]] = []
    planted_carrier_faults: list[dict[str, object]] = []
    fault_indices = {211, 997, 2501, 4499, 6203, 8801, 10103, 11777, 12991, 14321, 14701, 14911}
    for index, shipment in enumerate(shipment_meta):
        count = 6 if index < 1000 else 5
        sequence = ["LABEL_CREATED", "PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", shipment["final"]]
        if count == 6:
            sequence.insert(3, "AT_HUB")
        for position, raw_status in enumerate(sequence):
            event_at = shipment["shipped"] - dt.timedelta(hours=2) + dt.timedelta(hours=position * 11 + (index % 5))
            if raw_status == "DELIVERED":
                event_at = shipment["promised"] + dt.timedelta(hours=(index % 37) - 18)
            canonical_status = raw_status
            canonical_event_at = event_at
            is_fault = index in fault_indices and position == len(sequence) - 1
            if is_fault:
                if index % 2:
                    canonical_status = "IN_TRANSIT" if raw_status == "DELIVERED" else "DELIVERED"
                    field = "canonical_status"
                    old_value = canonical_status
                    expected_value = raw_status
                else:
                    canonical_event_at = event_at + dt.timedelta(hours=5)
                    field = "canonical_event_at"
                    old_value = iso(canonical_event_at)
                    expected_value = iso(event_at)
            source = "CARRIER_HUB"
            external = f"CH-{shipment['id']}-{position + 1}"
            late_delay = dt.timedelta(days=1, hours=6) if index % 263 == 0 and position == len(sequence) - 1 else dt.timedelta()
            ingested = event_at + dt.timedelta(minutes=12 + index % 90) + late_delay
            month = max(1, min(6, event_at.month))
            batch = carrier_batches[(month - 1) * 2 + (0 if event_at.day < 16 else 1)]
            scan_id = f"SCN-{scan_counter:07d}"
            row = (scan_id, shipment["id"], source, external, raw_status, iso(event_at), canonical_status, iso(canonical_event_at), iso(ingested), batch, None, None)
            scan_rows.append(row)
            scan_originals.append(row)
            if is_fault:
                planted_carrier_faults.append({"scan_row_id": scan_id, "shipment_id": shipment["id"], "warehouse_id": shipment["warehouse"], "field": field, "old_value": old_value, "expected_value": expected_value, "fixture": "train_carrier_fault" if len(planted_carrier_faults) < 6 else "test_carrier_fault"})
            scan_counter += 1
    assert len(scan_rows) == 76000
    for original in scan_originals[1700:5700]:
        duplicate = list(original)
        duplicate[0] = f"SCN-{scan_counter:07d}"
        duplicate[8] = iso(dt.datetime.fromisoformat(str(original[8]).replace("Z", "+00:00")) + dt.timedelta(minutes=50))
        scan_rows.append(tuple(duplicate))
        scan_counter += 1
    assert len(scan_rows) == 80000
    insert_many(conn, "INSERT INTO carrier_scans VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", scan_rows)

    payment_rows: list[tuple[object, ...]] = []
    payment_originals: list[tuple[object, ...]] = []
    for index in range(17280):
        order = order_meta[index % len(order_meta)]
        event_type = "CAPTURED" if index < 14000 else "AUTHORIZED"
        event_at = order["created"] + dt.timedelta(minutes=10 + index % 70)
        provider = ["STRIPE", "ADYEN", "BRAINTREE"][index % 3]
        external = f"PAY-{index + 1:06d}"
        row = (f"PE-{index + 1:06d}", order["id"], provider, "PAYMENT_GATEWAY", external, event_type, order["gross"], order["currency"], iso(event_at), iso(event_at + dt.timedelta(minutes=2 + index % 20)), None)
        payment_rows.append(row)
        payment_originals.append(row)
    for offset, original in enumerate(payment_originals[3000:3720], start=17281):
        duplicate = list(original)
        duplicate[0] = f"PE-{offset:06d}"
        duplicate[9] = iso(dt.datetime.fromisoformat(str(original[9]).replace("Z", "+00:00")) + dt.timedelta(minutes=40))
        payment_rows.append(tuple(duplicate))
    assert len(payment_rows) == 18000
    insert_many(conn, "INSERT INTO payment_events VALUES (?,?,?,?,?,?,?,?,?,?,?)", payment_rows)

    refund_rows: list[tuple[object, ...]] = []
    refund_originals: list[tuple[object, ...]] = []
    refund_business_ids: list[str] = []
    reasons = ["DAMAGED", "LATE_DELIVERY", "NOT_AS_DESCRIBED", "DUPLICATE_CHARGE", "CUSTOMER_RETURN"]
    for index in range(6500):
        order = order_meta[(index * 19 + 300) % len(order_meta)]
        refund_id = f"REF-{index + 1:06d}"
        refund_business_ids.append(refund_id)
        status = "SETTLED"
        linked: str | None = None
        if index % 13 == 0:
            status = "FAILED"
        elif index % 29 == 0:
            status = "VOIDED"
        elif index % 31 == 0 and index > 31:
            status = "REVERSED"
            linked = refund_business_ids[index - 31]
        service_date = START_DATE + dt.timedelta(days=(index * 23 + 5) % 181)
        event_at = dt.datetime.combine(service_date, dt.time(9 + index % 10, index % 60), UTC)
        provider = ["STRIPE", "ADYEN", "BRAINTREE"][index % 3]
        currency = currencies[(index * 7 + index // 100) % len(currencies)]
        amount = 500 + ((index * 421) % min(60000, int(order["gross"])))
        order_id = order["id"]
        if status == "REVERSED" and linked is not None:
            linked_row = refund_originals[index - 31]
            order_id = linked_row[2]
            provider = linked_row[3]
            amount = linked_row[8]
            currency = linked_row[9]
            event_at = dt.datetime.fromisoformat(str(linked_row[11]).replace("Z", "+00:00")) + dt.timedelta(days=3)
            service_date = event_at.date()
        external = f"RFX-{index + 1:06d}"
        row = (f"RFR-{index + 1:06d}", refund_id, order_id, provider, "PAYMENT_GATEWAY", external, status, reasons[index % len(reasons)], amount, currency, service_date.isoformat(), iso(event_at), iso(event_at + dt.timedelta(minutes=8 + index % 150)), linked)
        refund_rows.append(row)
        refund_originals.append(row)
    for offset, original in enumerate(refund_originals[1200:1700], start=6501):
        duplicate = list(original)
        duplicate[0] = f"RFR-{offset:06d}"
        duplicate[12] = iso(dt.datetime.fromisoformat(str(original[12]).replace("Z", "+00:00")) + dt.timedelta(minutes=75))
        refund_rows.append(tuple(duplicate))
    assert len(refund_rows) == 7000
    insert_many(conn, "INSERT INTO refund_attempts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", refund_rows)

    case_rows = []
    case_meta: list[dict[str, object]] = []
    for index in range(6000):
        account_id = account_ids[(index * 43 + 77) % len(account_ids)]
        order_id = order_meta[(index * 17 + 200) % len(order_meta)]["id"] if index % 7 else None
        opened = at_day((index * 31 + 3) % 181, (index * 17) % 1300)
        priority = ["LOW", "MEDIUM", "HIGH", "URGENT"][index % 4]
        final = "REOPENED" if index % 37 == 0 else "RESOLVED" if index % 5 < 3 else "OPEN"
        snapshot = final if index % 12 else "OPEN"
        owner = ["CARE-A", "CARE-B", "ESCALATIONS"][index % 3]
        case_id = f"CASE-{index + 1:06d}"
        case_rows.append((case_id, account_id, order_id, priority, iso(opened), snapshot, owner))
        case_meta.append({"id": case_id, "opened": opened, "final": final})
    conn.executemany("INSERT INTO support_cases VALUES (?,?,?,?,?,?,?)", case_rows)

    case_event_rows: list[tuple[object, ...]] = []
    case_originals: list[tuple[object, ...]] = []
    case_event_counter = 1
    for index, case in enumerate(case_meta):
        count = 5 if index < 2800 else 4
        if index % 9 == 0:
            sequence = ["OPENED", "ASSIGNED", "WAITING_CUSTOMER", "CUSTOMER_REPLIED", case["final"]]
        else:
            sequence = ["OPENED", "ASSIGNED", "AGENT_RESPONDED", "ESCALATED" if index % 11 == 0 else case["final"], "RESOLVED"]
        for position in range(count):
            event_type = sequence[position]
            event_at = case["opened"] + dt.timedelta(hours=position * (3 + index % 9), minutes=index % 45)
            actor = "CUSTOMER" if event_type in ("OPENED", "CUSTOMER_REPLIED") else "AGENT" if event_type not in ("ESCALATED",) else "SYSTEM"
            external = f"SUP-{case['id']}-{position + 1}"
            row = (f"CE-{case_event_counter:07d}", case["id"], event_type, iso(event_at), actor, "SUPPORT_DESK", external, iso(event_at + dt.timedelta(minutes=5 + index % 180)))
            case_event_rows.append(row)
            case_originals.append(row)
            case_event_counter += 1
    assert len(case_event_rows) == 26800
    for original in case_originals[3000:4200]:
        duplicate = list(original)
        duplicate[0] = f"CE-{case_event_counter:07d}"
        duplicate[7] = iso(dt.datetime.fromisoformat(str(original[7]).replace("Z", "+00:00")) + dt.timedelta(minutes=60))
        case_event_rows.append(tuple(duplicate))
        case_event_counter += 1
    assert len(case_event_rows) == 28000
    insert_many(conn, "INSERT INTO case_events VALUES (?,?,?,?,?,?,?,?)", case_event_rows)

    employee_by_warehouse: dict[str, list[str]] = {warehouse: [] for warehouse in warehouses}
    for employee in employee_rows:
        employee_by_warehouse[employee[1]].append(employee[0])
    task_rows = []
    task_meta: list[dict[str, object]] = []
    task_types = ["PICK", "PACK", "REPLENISH", "RECEIVE"]
    for index in range(34000):
        warehouse = warehouses[(index * 11 + index // 157) % len(warehouses)]
        employee = employee_by_warehouse[warehouse][(index * 7 + index // 41) % 18]
        created = at_day((index * 53 + 11) % 181, (index * 13) % 1380)
        due = created + dt.timedelta(hours=3 + index % 17)
        work_class = "TRAINING" if index % 14 == 0 else "PRODUCTION"
        final = "REWORK" if index % 29 == 0 else "COMPLETED" if index % 10 < 8 else "IN_PROGRESS"
        snapshot = final if index % 15 else "CREATED"
        order_id = order_meta[(index * 5 + 90) % len(order_meta)]["id"] if index % 6 else None
        sku = sku_ids[(index * 31 + 8) % len(sku_ids)] if index % 8 else None
        units = 4 + ((index * 17) % 90)
        task_id = f"WT-{index + 1:06d}"
        task_rows.append((task_id, warehouse, order_id, sku, employee, task_types[index % 4], work_class, ["NORMAL", "HIGH", "URGENT"][index % 3], units, iso(created), iso(due), snapshot))
        task_meta.append({"id": task_id, "created": created, "due": due, "final": final, "units": units})
    conn.executemany("INSERT INTO warehouse_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", task_rows)

    task_event_rows: list[tuple[object, ...]] = []
    task_originals: list[tuple[object, ...]] = []
    task_event_counter = 1
    for index, task in enumerate(task_meta):
        count = 3 if index < 33000 else 2
        sequence = ["CREATED", "STARTED", task["final"]]
        for position in range(count):
            event_type = sequence[position]
            event_at = task["created"] + dt.timedelta(minutes=position * (25 + index % 55))
            units = int(task["units"]) if event_type in ("COMPLETED", "REWORK") else 0
            minutes = 20 + (index * 7) % 100 if event_type in ("COMPLETED", "REWORK") else 0
            external = f"WMS-{task['id']}-{position + 1}"
            row = (f"WTE-{task_event_counter:07d}", task["id"], event_type, iso(event_at), units, minutes, "WMS_EDGE", external, iso(event_at + dt.timedelta(minutes=3 + index % 70)))
            task_event_rows.append(row)
            task_originals.append(row)
            task_event_counter += 1
    assert len(task_event_rows) == 101000
    for original in task_originals[9000:13000]:
        duplicate = list(original)
        duplicate[0] = f"WTE-{task_event_counter:07d}"
        duplicate[8] = iso(dt.datetime.fromisoformat(str(original[8]).replace("Z", "+00:00")) + dt.timedelta(minutes=48))
        task_event_rows.append(tuple(duplicate))
        task_event_counter += 1
    assert len(task_event_rows) == 105000
    insert_many(conn, "INSERT INTO warehouse_task_events VALUES (?,?,?,?,?,?,?,?,?)", task_event_rows)

    movement_rows: list[tuple[object, ...]] = []
    movement_originals: list[tuple[object, ...]] = []
    planted_inventory_faults: list[dict[str, object]] = []
    inventory_fault_indices = {109, 771, 5111, 10009, 17771, 24421, 31111, 37777, 44441, 51001}
    movement_types = ["RECEIPT", "SALE", "RETURN", "ADJUSTMENT", "TRANSFER_IN", "TRANSFER_OUT"]
    for index in range(52500):
        movement_id = f"MOV-{index + 1:07d}"
        warehouse = warehouses[(index * 13 + index // 199) % len(warehouses)]
        sku = sku_ids[(index * 29 + index // 67) % len(sku_ids)]
        movement_type = movement_types[index % len(movement_types)]
        sign = -1 if movement_type in ("SALE", "TRANSFER_OUT") else 1
        raw_uom = "CASE" if index % 9 == 0 else "EA"
        multiplier = units_per_case[sku] if raw_uom == "CASE" else 1
        raw_qty = sign * (1 + ((index * 11) % (8 if raw_uom == "CASE" else 40)))
        canonical_multiplier = multiplier
        canonical_qty = raw_qty * multiplier
        if index in inventory_fault_indices:
            canonical_multiplier = max(1, multiplier // 2) if raw_uom == "CASE" else units_per_case[sku]
            canonical_qty = raw_qty * canonical_multiplier
        occurred = at_day((index * 41 + 7) % 181, (index * 19) % 1430)
        external = f"ERP-{movement_id}"
        row_id = f"IMR-{index + 1:07d}"
        row = (row_id, movement_id, warehouse, sku, movement_type, raw_qty, raw_uom, multiplier, canonical_qty, canonical_multiplier, iso(occurred), "ERP_LEDGER", external, iso(occurred + dt.timedelta(minutes=10 + index % 240)), f"DOC-{index // 4 + 1:07d}", None, None)
        movement_rows.append(row)
        movement_originals.append(row)
        if index in inventory_fault_indices:
            planted_inventory_faults.append({"movement_row_id": row_id, "movement_id": movement_id, "warehouse_id": warehouse, "sku": sku, "product_family": families[(int(sku.split("-")[1]) - 1) // 100], "old_quantity_each": canonical_qty, "expected_quantity_each": raw_qty * multiplier, "old_multiplier": canonical_multiplier, "expected_multiplier": multiplier, "fixture": "test_inventory_fault" if len(planted_inventory_faults) < 5 else "inventory_distractor_fault"})
    for offset, original in enumerate(movement_originals[7000:9500], start=52501):
        duplicate = list(original)
        duplicate[0] = f"IMR-{offset:07d}"
        duplicate[13] = iso(dt.datetime.fromisoformat(str(original[13]).replace("Z", "+00:00")) + dt.timedelta(minutes=90))
        movement_rows.append(tuple(duplicate))
    assert len(movement_rows) == 55000
    insert_many(conn, "INSERT INTO inventory_movements VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", movement_rows)

    snapshot_rows = []
    snapshot_dates = [dt.datetime(2026, month, 1, 0, 0, tzinfo=UTC) for month in range(1, 7)] + [dt.datetime(2026, 6, 30, 23, 59, tzinfo=UTC)]
    for warehouse_index, warehouse in enumerate(warehouses):
        for sku_index, sku in enumerate(sku_ids):
            base = 80 + ((sku_index * 17 + warehouse_index * 103) % 900)
            for snap_index, snapshot_at in enumerate(snapshot_dates):
                on_hand = max(0, base + ((snap_index * 37 + sku_index) % 120) - 45)
                reserved = (sku_index * 7 + snap_index * 13 + warehouse_index) % max(1, min(160, on_hand + 1))
                snapshot_rows.append((warehouse, sku, iso(snapshot_at), on_hand, reserved, "ERP_LEDGER"))
    assert len(snapshot_rows) == 31500
    insert_many(conn, "INSERT INTO inventory_snapshots VALUES (?,?,?,?,?,?)", snapshot_rows)

    batch_count_updates = {
        "carrier_scan": len(scan_rows),
        "order_event": len(order_events),
        "payment_event": len(payment_rows),
        "case_event": len(case_event_rows),
        "warehouse_task_event": len(task_event_rows),
        "inventory_movement": len(movement_rows),
    }
    for entity_type, total in batch_count_updates.items():
        batch_ids = [row[0] for row in conn.execute("SELECT import_batch_id FROM source_import_batches WHERE entity_type=? ORDER BY import_batch_id", (entity_type,))]
        quotient, remainder = divmod(total, len(batch_ids))
        for position, batch_id in enumerate(batch_ids):
            conn.execute("UPDATE source_import_batches SET record_count=? WHERE import_batch_id=?", (quotient + (1 if position < remainder else 0), batch_id))

    conn.commit()
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_key_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or foreign_key_violations:
        raise RuntimeError("generated database failed integrity validation")
    table_names = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    row_counts = {table: conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] for table in table_names}
    source_system_counts = {row[0]: row[1] for row in conn.execute("SELECT source_system, COUNT(*) FROM source_import_batches GROUP BY source_system ORDER BY source_system")}
    late_arriving_events = conn.execute(
        "SELECT (SELECT COUNT(*) FROM order_events WHERE julianday(ingested_at) - julianday(event_at) > 1.0) + "
        "(SELECT COUNT(*) FROM carrier_scans WHERE julianday(ingested_at) - julianday(raw_event_at) > 1.0)"
    ).fetchone()[0]
    conn.execute("PRAGMA optimize")
    conn.close()

    noise_counts = {
        "duplicate_import_retries": {
            "order_events": 2600,
            "carrier_scans": 4000,
            "payment_events": 720,
            "refund_attempts": 500,
            "case_events": 1200,
            "warehouse_task_events": 4000,
            "inventory_movements": 2500,
        },
        "late_arriving_events": late_arriving_events,
        "internal_accounts": 18,
        "test_accounts": 14,
        "stale_order_snapshots": sum(1 for index in range(14000) if index % 13 == 0),
        "stale_shipment_snapshots": sum(1 for index in range(15000) if index % 11 == 0),
        "stale_support_snapshots": sum(1 for index in range(6000) if index % 12 == 0),
        "stale_warehouse_task_snapshots": sum(1 for index in range(34000) if index % 15 == 0),
        "canceled_orders": sum(1 for meta in order_meta if meta["terminal"] == "CANCELLED"),
        "partial_or_multiple_shipment_rows": 15000 - len(eligible_orders),
        "failed_refund_attempts": sum(1 for row in refund_originals if row[6] == "FAILED"),
        "voided_refund_attempts": sum(1 for row in refund_originals if row[6] == "VOIDED"),
        "refund_reversals": sum(1 for row in refund_originals if row[6] == "REVERSED"),
        "reopened_cases": sum(1 for case in case_meta if case["final"] == "REOPENED"),
        "waiting_customer_cases": sum(1 for index in range(6000) if index % 9 == 0),
        "training_warehouse_tasks": sum(1 for row in task_rows if row[6] == "TRAINING"),
        "explicit_rework_tasks": sum(1 for task in task_meta if task["final"] == "REWORK"),
        "carrier_canonical_faults": len(planted_carrier_faults),
        "inventory_uom_faults": len(planted_inventory_faults),
    }
    fixtures = {
        "candidate_campaigns": {
            "train": ["CMP-SPRING-26"],
            "test": ["CMP-MAYPEAK-26"],
            "distractors": ["CMP-SPRINGVIP-26", "CMP-MAYPEAK-PRE"],
        },
        "account_cohorts": {
            "enterprise_regions": ["NORTH", "EAST"],
            "strategic_region": "WEST",
            "refund_tiers": ["GOLD", "PLATINUM"],
        },
        "warehouse_windows": {
            "productivity_train": {"warehouse_id": "WH-NORTH-01", "start": "2026-04-06", "end": "2026-04-12"},
            "recovery_test": {"warehouse_ids": ["WH-WEST-01", "WH-CENTRAL-01"], "start": "2026-06-22", "end": "2026-06-28"},
        },
        "planted_carrier_faults": planted_carrier_faults,
        "planted_inventory_faults": planted_inventory_faults,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "seed": SEED,
        "table_row_counts": row_counts,
        "date_range": {"business_start": START_DATE.isoformat(), "business_end": END_DATE.isoformat(), "fx_start": (START_DATE - dt.timedelta(days=12)).isoformat(), "fx_end": (START_DATE + dt.timedelta(days=191)).isoformat()},
        "source_systems": source_system_counts,
        "import_batches": row_counts["source_import_batches"],
        "noise_anomaly_counts": noise_counts,
        "construction_only_fixtures": fixtures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    base = Path(__file__).resolve().parent
    parser.add_argument("--output", type=Path, default=base / "atlas_baseline.sqlite3")
    parser.add_argument("--manifest", type=Path, default=base / "manifest.json")
    args = parser.parse_args()
    output = args.output.resolve()
    manifest_path = args.manifest.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    details = build_database(output)
    details["generated_artifacts"] = [
        {"name": output.name, "sha256": file_sha256(output), "bytes": output.stat().st_size},
    ]
    details["generator"] = {"name": Path(__file__).name, "sha256": file_sha256(Path(__file__))}
    temporary = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    temporary.write_text(json.dumps(details, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, manifest_path)
    print(json.dumps({"database": str(output), "manifest": str(manifest_path), "rows": details["table_row_counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
