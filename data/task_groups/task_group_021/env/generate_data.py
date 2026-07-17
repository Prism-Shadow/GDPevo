#!/usr/bin/env python3
"""Generate the deterministic SQLite dataset for the Asteria quality hub."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import random
import sqlite3
import struct
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SEED = 21072115
GENERATOR_VERSION = "1.0.0"
SCHEMA_VERSION = "asteria-1"
GENERATED_AT = "2026-07-15T00:00:00Z"
CANONICAL_SQLITE_VERSION_NUMBER = 3_040_001

CONTACT_COLLECTIONS = {
    "partner_onboarding_2026w03": (810, ["Partner Portal", "CRM", "Compliance Master"]),
    "field_service_roster_2026w05": (950, ["HR Directory", "Dispatch", "Identity Registry"]),
    "dealer_contacts_2026w11": (1050, ["Dealer Portal", "CRM", "Compliance Master"]),
    "warranty_contacts_2026w14": (1100, ["Warranty Claims", "Dealer Service", "Identity Registry"]),
    "archived_marketing_contacts_2025q4": (500, ["Marketing Cloud", "CRM Archive"]),
}
FUEL_COLLECTIONS = {
    "fuel_purchases_2026_01": 1350,
    "fuel_purchases_2026_03": 1500,
    "fuel_purchases_2025_12_archive": 500,
}
FREIGHT_COLLECTIONS = {
    "freight_charges_2026_02": 1225,
    "freight_charges_2026_04": 1375,
}
MAINTENANCE_COLLECTIONS = {
    "maintenance_events_2026_q1": 1450,
    "maintenance_events_2026_q2": 1700,
}

PUBLIC_VIEWS = {
    "v_contacts": [
        "collection_id", "row_id", "snapshot_id", "source_system", "source_record_id",
        "person_or_org_name", "email", "phone", "city", "region", "country",
        "consent_status", "record_status", "verified_flag", "business_updated_at",
        "ingested_at", "master_hint",
    ],
    "v_fuel_transactions": [
        "collection_id", "transaction_id", "snapshot_id", "asset_id", "merchant_id",
        "purchased_at", "expected_fuel_type", "purchased_description", "quantity",
        "quantity_unit", "currency", "amount", "record_status", "business_updated_at",
        "ingested_at",
    ],
    "v_freight_charges": [
        "collection_id", "charge_id", "snapshot_id", "invoice_id", "invoice_line_no",
        "carrier_id", "lane_id", "service_date", "expected_service_class", "description",
        "billed_weight", "weight_unit", "distance", "distance_unit", "currency", "amount",
        "record_status", "business_updated_at", "ingested_at",
    ],
    "v_maintenance_events": [
        "collection_id", "snapshot_id", "event_id", "work_order_id", "asset_id",
        "event_type", "event_time_raw", "odometer_value", "odometer_unit", "labor_hours",
        "parts_cost", "currency", "technician_id", "event_status", "business_updated_at",
        "ingested_at",
    ],
    "v_reference_aliases": [
        "domain", "alias_id", "alias_text", "canonical_value", "valid_from", "valid_to",
        "reference_status", "published_at",
    ],
    "v_unit_conversions": [
        "kind", "from_unit", "to_unit", "factor", "valid_from", "valid_to", "precision",
    ],
    "v_fx_rates": ["rate_date", "currency", "usd_per_unit", "rate_status", "published_at"],
    "v_source_snapshots": [
        "collection_id", "snapshot_id", "source_system", "snapshot_status", "business_cutoff",
        "created_at", "ingested_at", "row_count", "checksum",
    ],
}


def stream(label: str) -> random.Random:
    digest = hashlib.sha256(f"{SEED}:{label}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def iso_date(value: dt.date) -> str:
    return value.isoformat()


def iso_time(value: dt.datetime) -> str:
    return value.replace(microsecond=0).isoformat() + "Z"


def stable_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    except Exception:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass
        raise


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=DELETE;
        PRAGMA synchronous=FULL;
        PRAGMA foreign_keys=ON;
        CREATE TABLE private_contacts (
          collection_id TEXT NOT NULL, row_id TEXT NOT NULL, snapshot_id TEXT NOT NULL,
          source_system TEXT NOT NULL, source_record_id TEXT NOT NULL,
          person_or_org_name TEXT, email TEXT, phone TEXT, city TEXT, region TEXT, country TEXT,
          consent_status TEXT NOT NULL, record_status TEXT NOT NULL, verified_flag INTEGER NOT NULL,
          business_updated_at TEXT NOT NULL, ingested_at TEXT NOT NULL, master_hint TEXT,
          PRIMARY KEY (collection_id, row_id)
        ) WITHOUT ROWID;
        CREATE TABLE private_fuel_transactions (
          raw_id INTEGER PRIMARY KEY, collection_id TEXT NOT NULL, transaction_id TEXT NOT NULL,
          snapshot_id TEXT NOT NULL, asset_id TEXT NOT NULL, merchant_id TEXT NOT NULL,
          purchased_at TEXT NOT NULL, expected_fuel_type TEXT NOT NULL,
          purchased_description TEXT NOT NULL, quantity REAL, quantity_unit TEXT NOT NULL,
          currency TEXT NOT NULL, amount REAL, record_status TEXT NOT NULL,
          business_updated_at TEXT NOT NULL, ingested_at TEXT NOT NULL
        );
        CREATE TABLE private_freight_charges (
          raw_id INTEGER PRIMARY KEY, collection_id TEXT NOT NULL, charge_id TEXT NOT NULL,
          snapshot_id TEXT NOT NULL, invoice_id TEXT NOT NULL, invoice_line_no INTEGER NOT NULL,
          carrier_id TEXT NOT NULL, lane_id TEXT NOT NULL, service_date TEXT NOT NULL,
          expected_service_class TEXT NOT NULL, description TEXT NOT NULL,
          billed_weight REAL, weight_unit TEXT NOT NULL, distance REAL, distance_unit TEXT NOT NULL,
          currency TEXT NOT NULL, amount REAL, record_status TEXT NOT NULL,
          business_updated_at TEXT NOT NULL, ingested_at TEXT NOT NULL
        );
        CREATE TABLE private_maintenance_events (
          raw_id INTEGER PRIMARY KEY, collection_id TEXT NOT NULL, snapshot_id TEXT NOT NULL,
          event_id TEXT NOT NULL, work_order_id TEXT NOT NULL, asset_id TEXT NOT NULL,
          event_type TEXT NOT NULL, event_time_raw TEXT, odometer_value REAL,
          odometer_unit TEXT NOT NULL, labor_hours REAL, parts_cost REAL, currency TEXT NOT NULL,
          technician_id TEXT NOT NULL, event_status TEXT NOT NULL,
          business_updated_at TEXT NOT NULL, ingested_at TEXT NOT NULL
        );
        CREATE TABLE private_reference_aliases (
          domain TEXT NOT NULL, alias_id TEXT PRIMARY KEY, alias_text TEXT NOT NULL,
          canonical_value TEXT NOT NULL, valid_from TEXT NOT NULL, valid_to TEXT,
          reference_status TEXT NOT NULL, published_at TEXT NOT NULL
        ) WITHOUT ROWID;
        CREATE TABLE private_unit_conversions (
          kind TEXT NOT NULL, from_unit TEXT NOT NULL, to_unit TEXT NOT NULL, factor REAL NOT NULL,
          valid_from TEXT NOT NULL, valid_to TEXT, precision INTEGER NOT NULL,
          PRIMARY KEY (kind, from_unit, valid_from)
        ) WITHOUT ROWID;
        CREATE TABLE private_fx_rates (
          rate_date TEXT NOT NULL, currency TEXT NOT NULL, usd_per_unit REAL NOT NULL,
          rate_status TEXT NOT NULL, published_at TEXT NOT NULL,
          PRIMARY KEY (rate_date, currency, rate_status)
        ) WITHOUT ROWID;
        CREATE TABLE private_source_snapshots (
          collection_id TEXT NOT NULL, snapshot_id TEXT NOT NULL, source_system TEXT NOT NULL,
          snapshot_status TEXT NOT NULL, business_cutoff TEXT NOT NULL, created_at TEXT NOT NULL,
          ingested_at TEXT NOT NULL, row_count INTEGER NOT NULL, checksum TEXT NOT NULL,
          PRIMARY KEY (collection_id, snapshot_id)
        ) WITHOUT ROWID;
        CREATE TABLE private_collection_catalog (
          collection_id TEXT PRIMARY KEY, description TEXT NOT NULL, family TEXT NOT NULL,
          source_systems TEXT NOT NULL, time_start TEXT NOT NULL, time_end TEXT NOT NULL,
          approximate_record_count INTEGER NOT NULL, queryable INTEGER NOT NULL
        ) WITHOUT ROWID;

        CREATE VIEW v_contacts AS SELECT collection_id,row_id,snapshot_id,source_system,
          source_record_id,person_or_org_name,email,phone,city,region,country,consent_status,
          record_status,verified_flag,business_updated_at,ingested_at,master_hint
          FROM private_contacts;
        CREATE VIEW v_fuel_transactions AS SELECT collection_id,transaction_id,snapshot_id,
          asset_id,merchant_id,purchased_at,expected_fuel_type,purchased_description,quantity,
          quantity_unit,currency,amount,record_status,business_updated_at,ingested_at
          FROM private_fuel_transactions;
        CREATE VIEW v_freight_charges AS SELECT collection_id,charge_id,snapshot_id,invoice_id,
          invoice_line_no,carrier_id,lane_id,service_date,expected_service_class,description,
          billed_weight,weight_unit,distance,distance_unit,currency,amount,record_status,
          business_updated_at,ingested_at FROM private_freight_charges;
        CREATE VIEW v_maintenance_events AS SELECT collection_id,snapshot_id,event_id,
          work_order_id,asset_id,event_type,event_time_raw,odometer_value,odometer_unit,labor_hours,
          parts_cost,currency,technician_id,event_status,business_updated_at,ingested_at
          FROM private_maintenance_events;
        CREATE VIEW v_reference_aliases AS SELECT domain,alias_id,alias_text,canonical_value,
          valid_from,valid_to,reference_status,published_at FROM private_reference_aliases;
        CREATE VIEW v_unit_conversions AS SELECT kind,from_unit,to_unit,factor,valid_from,valid_to,
          precision FROM private_unit_conversions;
        CREATE VIEW v_fx_rates AS SELECT rate_date,currency,usd_per_unit,rate_status,published_at
          FROM private_fx_rates;
        CREATE VIEW v_source_snapshots AS SELECT collection_id,snapshot_id,source_system,
          snapshot_status,business_cutoff,created_at,ingested_at,row_count,checksum
          FROM private_source_snapshots;

        CREATE INDEX idx_contacts_collection_source ON private_contacts(collection_id,source_system,row_id);
        CREATE INDEX idx_fuel_collection_merchant ON private_fuel_transactions(collection_id,merchant_id,transaction_id);
        CREATE INDEX idx_freight_collection_carrier ON private_freight_charges(collection_id,carrier_id,charge_id);
        CREATE INDEX idx_maint_collection_asset ON private_maintenance_events(collection_id,asset_id,event_id);
        CREATE INDEX idx_alias_domain_dates ON private_reference_aliases(domain,valid_from,valid_to);
        CREATE INDEX idx_fx_date_currency ON private_fx_rates(rate_date,currency);
        """
    )


def insert_many(conn: sqlite3.Connection, table: str, columns: list[str], rows: Iterable[dict[str, Any]]) -> None:
    sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})"
    conn.executemany(sql, ([row.get(column) for column in columns] for row in rows))


class SnapshotRegistry:
    def __init__(self) -> None:
        self.definitions: dict[tuple[str, str], dict[str, Any]] = {}
        self.counts: Counter[tuple[str, str]] = Counter()

    def add(
        self,
        collection: str,
        snapshot: str,
        source: str,
        status: str,
        cutoff: str,
        created: str,
        ingested: str,
    ) -> None:
        self.definitions[(collection, snapshot)] = {
            "collection_id": collection,
            "snapshot_id": snapshot,
            "source_system": source,
            "snapshot_status": status,
            "business_cutoff": cutoff,
            "created_at": created,
            "ingested_at": ingested,
        }

    def use(self, collection: str, snapshot: str) -> None:
        self.counts[(collection, snapshot)] += 1

    def rows(self) -> list[dict[str, Any]]:
        result = []
        for key in sorted(self.definitions):
            row = dict(self.definitions[key])
            row["row_count"] = self.counts[key]
            row["checksum"] = stable_hash(f"{key[0]}|{key[1]}|{row['row_count']}".encode())
            result.append(row)
        return result


FIRST_NAMES = ["Amina", "Noah", "Sofia", "Liam", "Marta", "Wei", "Lucía", "Owen", "Zoë", "Renée", "Akira", "Mateo"]
LAST_NAMES = ["Patel", "Nguyen", "Garcia", "Smith", "Kowalski", "Chen", "Müller", "Silva", "Brown", "Rossi", "Martin", "Kim"]
CITIES = [
    ("Austin", "TX", "US"), ("Toronto", "ON", "CA"), ("London", "England", "GB"),
    ("Berlin", "BE", "DE"), ("Madrid", "MD", "ES"), ("Singapore", "SG", "SG"),
]
NULL_MARKERS: list[str | None] = ["", "   ", None, "N/A", "none", "NULL"]


def mutate_name(name: str, variant: int) -> str:
    if variant == 0:
        return name.upper()
    if variant == 1:
        return f"  {name}  "
    return name.replace("é", "e").replace("ü", "u")


def format_phone(country: str, digits: str, variant: int) -> str:
    if country == "US":
        return [f"+1 {digits[:3]} {digits[3:6]} {digits[6:]}", f"({digits[:3]}) {digits[3:6]}-{digits[6:]}", digits][variant]
    if country == "GB":
        return [f"+44 {digits[:4]} {digits[4:]}", f"0{digits[:4]} {digits[4:]}", digits][variant]
    return [f"+{digits[:2]} {digits[2:6]} {digits[6:]}", f"{digits[:4]}-{digits[4:]}", digits][variant]


def generate_contacts(conn: sqlite3.Connection, snapshots: SnapshotRegistry, noise: Counter[str]) -> dict[str, Any]:
    columns = PUBLIC_VIEWS["v_contacts"]
    truth: dict[str, Any] = {}
    for collection, (target, sources) in CONTACT_COLLECTIONS.items():
        rng = stream(f"contacts:{collection}")
        snapshot_for: dict[str, str] = {}
        for index, source in enumerate(sources):
            snapshot = f"{collection}-s{index + 1:02d}"
            snapshot_for[source] = snapshot
            status = "CERTIFIED" if index in (0, 2) else "PROVISIONAL"
            snapshots.add(collection, snapshot, source, status, "2026-04-10T23:59:59Z", "2026-04-11T02:00:00Z", "2026-04-11T04:00:00Z")

        rows: list[dict[str, Any]] = []
        duplicate_clusters: list[dict[str, Any]] = []
        cluster_count = 30 if collection != "archived_marketing_contacts_2025q4" else 12
        for cluster_index in range(cluster_count):
            first = FIRST_NAMES[(cluster_index + rng.randrange(len(FIRST_NAMES))) % len(FIRST_NAMES)]
            last = LAST_NAMES[(cluster_index * 3 + rng.randrange(len(LAST_NAMES))) % len(LAST_NAMES)]
            name = f"{first} {last}"
            city, region, country = CITIES[cluster_index % len(CITIES)]
            email = f"{first}.{last}.{cluster_index}@example-fleet.com".lower()
            raw_digits = f"{2100000000 + cluster_index + (rng.randrange(300) * 100):010d}"[-10:]
            member_ids: list[str] = []
            for variant in range(3):
                row_index = len(rows) + 1
                row_id = f"{collection[:3].upper()}-C{row_index:05d}"
                member_ids.append(row_id)
                source = sources[variant % len(sources)]
                conflict = cluster_index % 2 == 0 and variant == 1
                row = {
                    "collection_id": collection,
                    "row_id": row_id,
                    "snapshot_id": snapshot_for[source],
                    "source_system": source,
                    "source_record_id": f"{source[:2].upper()}-{cluster_index:04d}-{variant}",
                    "person_or_org_name": mutate_name(name, variant),
                    "email": email.upper() + " " if variant == 1 else email,
                    "phone": format_phone(country, raw_digits, variant),
                    "city": CITIES[(cluster_index + 1) % len(CITIES)][0] if conflict else city,
                    "region": region,
                    "country": country,
                    "consent_status": ["GRANTED", "GRANTED", "PENDING"][variant],
                    "record_status": "ACTIVE",
                    "verified_flag": 1 if variant in (0, 2) else 0,
                    "business_updated_at": f"2026-03-{10 + variant:02d}T09:00:00Z",
                    "ingested_at": f"2026-04-{10 + variant:02d}T0{variant + 2}:00:00Z",
                    "master_hint": f"MH-{cluster_index:04d}" if variant == 2 else None,
                }
                rows.append(row)
                snapshots.use(collection, row["snapshot_id"])
                noise["contact_duplicate_rows"] += 1
                if conflict:
                    noise["contact_field_conflicts"] += 1
            duplicate_clusters.append({
                "cluster_id": f"{collection}-cluster-{cluster_index + 1:03d}",
                "member_row_ids": member_ids,
                "survivor_row_id": member_ids[2],
                "canonical": {"name": name, "email": email, "phone_digits": raw_digits, "city": city},
                "reason": "verified source and business update precedence",
            })

        unusable_count = 25 if collection != "archived_marketing_contacts_2025q4" else 15
        for unusable_index in range(unusable_count):
            row_index = len(rows) + 1
            source = sources[unusable_index % len(sources)]
            city, region, country = CITIES[unusable_index % len(CITIES)]
            row = {
                "collection_id": collection,
                "row_id": f"{collection[:3].upper()}-C{row_index:05d}",
                "snapshot_id": snapshot_for[source],
                "source_system": source,
                "source_record_id": f"NC-{unusable_index:05d}",
                "person_or_org_name": f"{FIRST_NAMES[unusable_index % len(FIRST_NAMES)]} {LAST_NAMES[(unusable_index + 4) % len(LAST_NAMES)]}",
                "email": NULL_MARKERS[unusable_index % len(NULL_MARKERS)],
                "phone": NULL_MARKERS[(unusable_index + 2) % len(NULL_MARKERS)],
                "city": city,
                "region": region,
                "country": country,
                "consent_status": "UNKNOWN",
                "record_status": "ACTIVE",
                "verified_flag": 0,
                "business_updated_at": "2026-03-18T08:00:00Z",
                "ingested_at": "2026-04-11T05:00:00Z",
                "master_hint": None,
            }
            rows.append(row)
            snapshots.use(collection, row["snapshot_id"])
            noise["contact_unusable_contact"] += 1

        shared_identifiers: list[dict[str, Any]] = []
        shared_phone = "+1 512 555 0199"
        while len(rows) < target:
            index = len(rows)
            source = sources[index % len(sources)]
            city, region, country = CITIES[index % len(CITIES)]
            first = FIRST_NAMES[index % len(FIRST_NAMES)]
            last = LAST_NAMES[(index * 5 + 3) % len(LAST_NAMES)]
            shared = index < (cluster_count * 3 + unusable_count + 12)
            phone_digits = f"{3100000000 + index:010d}"[-10:]
            phone = shared_phone if shared else format_phone(country, phone_digits, index % 3)
            email = f"{first}.{last}.{collection[:4]}.{index}@mail.example".lower()
            if index % 71 == 0:
                email = f" {email.upper()} "
                noise["contact_unicode_case_whitespace"] += 1
            row_id = f"{collection[:3].upper()}-C{index + 1:05d}"
            row = {
                "collection_id": collection,
                "row_id": row_id,
                "snapshot_id": snapshot_for[source],
                "source_system": source,
                "source_record_id": f"SR-{index + 1:06d}",
                "person_or_org_name": f"{first} {last}",
                "email": email,
                "phone": phone,
                "city": city,
                "region": region,
                "country": country,
                "consent_status": ["GRANTED", "DENIED", "PENDING"][index % 3],
                "record_status": "INACTIVE" if index % 101 == 0 else "ACTIVE",
                "verified_flag": 1 if index % 4 == 0 else 0,
                "business_updated_at": f"2026-03-{1 + index % 27:02d}T{index % 24:02d}:00:00Z",
                "ingested_at": f"2026-04-{1 + index % 12:02d}T{(index + 3) % 24:02d}:00:00Z",
                "master_hint": "SHARED-HELPDESK" if shared else (f"NOISY-{index // 9}" if index % 43 == 0 else None),
            }
            rows.append(row)
            snapshots.use(collection, row["snapshot_id"])
            if shared:
                shared_identifiers.append({"row_id": row_id, "phone": shared_phone})
                noise["contact_shared_identifier"] += 1

        insert_many(conn, "private_contacts", columns, rows)
        truth[collection] = {
            "record_count": len(rows),
            "meaningful_duplicate_clusters": duplicate_clusters,
            "unusable_contact_row_ids": [row["row_id"] for row in rows if row["email"] in NULL_MARKERS and row["phone"] in NULL_MARKERS],
            "shared_identifier_rows": shared_identifiers,
            "focus_clusters": duplicate_clusters[:5],
        }
    return truth


def add_reference_data(conn: sqlite3.Connection, noise: Counter[str]) -> None:
    aliases: list[dict[str, Any]] = []
    fuel_aliases = {
        "DIESEL": ["diesel", "ulsd", "road diesel"],
        "UNLEADED": ["unleaded", "regular gas", "87 octane"],
        "PREMIUM_UNLEADED": ["premium unleaded", "premium gas", "93 octane"],
        "BIODIESEL": ["biodiesel", "b20", "bio diesel"],
        "ELECTRIC_CHARGE": ["electric charge", "ev charging", "kilowatt charge"],
    }
    freight_aliases = {
        "STANDARD": ["standard", "ground freight", "economy"],
        "EXPRESS": ["express", "priority air", "next day"],
        "REFRIGERATED": ["refrigerated", "reefer", "cold chain"],
        "HAZMAT": ["hazmat", "dangerous goods", "hazardous material"],
        "OVERSIZE": ["oversize", "over dimensional", "wide load"],
    }
    for domain, mapping in (("fuel", fuel_aliases), ("freight", freight_aliases)):
        alias_prefix = "FU" if domain == "fuel" else "FR"
        serial = 1
        for canonical, texts in mapping.items():
            for text in texts:
                aliases.append({
                    "domain": domain,
                    "alias_id": f"{alias_prefix}A-{serial:03d}",
                    "alias_text": text,
                    "canonical_value": canonical,
                    "valid_from": "2025-01-01",
                    "valid_to": None,
                    "reference_status": "ACTIVE",
                    "published_at": "2025-12-15T12:00:00Z",
                })
                serial += 1
        # Effective-dated and inactive distractors deliberately overlap active vocabulary.
        aliases.extend([
            {
                "domain": domain, "alias_id": f"{alias_prefix}A-{serial:03d}",
                "alias_text": "priority", "canonical_value": "EXPRESS" if domain == "freight" else "PREMIUM_UNLEADED",
                "valid_from": "2026-03-01", "valid_to": None, "reference_status": "ACTIVE",
                "published_at": "2026-02-20T12:00:00Z",
            },
            {
                "domain": domain, "alias_id": f"{alias_prefix}A-{serial + 1:03d}",
                "alias_text": "priority", "canonical_value": "STANDARD" if domain == "freight" else "UNLEADED",
                "valid_from": "2025-01-01", "valid_to": "2026-02-28", "reference_status": "INACTIVE",
                "published_at": "2025-01-01T12:00:00Z",
            },
            {
                "domain": domain, "alias_id": f"{alias_prefix}A-{serial + 2:03d}",
                "alias_text": "fleet service", "canonical_value": "STANDARD" if domain == "freight" else "DIESEL",
                "valid_from": "2025-01-01", "valid_to": None, "reference_status": "PROVISIONAL",
                "published_at": "2026-01-01T12:00:00Z",
            },
        ])
        noise["inactive_or_provisional_aliases"] += 2
    insert_many(conn, "private_reference_aliases", PUBLIC_VIEWS["v_reference_aliases"], aliases)

    conversions = [
        ("volume", "L", "L", 1.0, 3),
        ("volume", "US_GAL", "L", 3.785411784, 3),
        ("volume", "IMP_GAL", "L", 4.54609, 3),
        ("weight", "KG", "KG", 1.0, 3),
        ("weight", "LB", "KG", 0.45359237, 3),
        ("distance", "KM", "KM", 1.0, 3),
        ("distance", "MI", "KM", 1.609344, 3),
        ("odometer", "KM", "KM", 1.0, 1),
        ("odometer", "MI", "KM", 1.609344, 1),
    ]
    conversion_rows = [{
        "kind": kind, "from_unit": source, "to_unit": target, "factor": factor,
        "valid_from": "2025-01-01", "valid_to": None, "precision": precision,
    } for kind, source, target, factor, precision in conversions]
    insert_many(conn, "private_unit_conversions", PUBLIC_VIEWS["v_unit_conversions"], conversion_rows)

    fx_rows = []
    start = dt.date(2025, 12, 1)
    end = dt.date(2026, 6, 30)
    currencies = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "CAD": 0.74}
    day = start
    while day <= end:
        day_offset = (day - start).days
        for index, (currency, base) in enumerate(currencies.items()):
            certified = round(base * (1 + ((day_offset * (index + 3)) % 17 - 8) / 1000), 6)
            fx_rows.append({
                "rate_date": iso_date(day), "currency": currency, "usd_per_unit": certified,
                "rate_status": "CERTIFIED", "published_at": f"{iso_date(day)}T18:00:00Z",
            })
            if day_offset % 3 == 0 and currency != "USD":
                fx_rows.append({
                    "rate_date": iso_date(day), "currency": currency,
                    "usd_per_unit": round(certified * 1.006, 6), "rate_status": "PROVISIONAL",
                    "published_at": f"{iso_date(day)}T16:00:00Z",
                })
                noise["provisional_fx_rows"] += 1
        day += dt.timedelta(days=1)
    insert_many(conn, "private_fx_rates", PUBLIC_VIEWS["v_fx_rates"], fx_rows)


def certified_fx(date: dt.date, currency: str) -> float:
    bases = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "CAD": 0.74}
    offset = (date - dt.date(2025, 12, 1)).days
    index = list(bases).index(currency)
    return round(bases[currency] * (1 + ((offset * (index + 3)) % 17 - 8) / 1000), 6)


def register_transaction_snapshots(collection: str, family: str, snapshots: SnapshotRegistry, month_end: str) -> tuple[str, str]:
    certified = f"{collection}-certified"
    provisional = f"{collection}-provisional"
    snapshots.add(collection, certified, f"{family.title()} Ledger", "CERTIFIED", month_end, month_end, month_end)
    snapshots.add(collection, provisional, f"{family.title()} Feed", "PROVISIONAL", month_end, month_end, month_end)
    return certified, provisional


def generate_fuel(conn: sqlite3.Connection, snapshots: SnapshotRegistry, noise: Counter[str]) -> dict[str, Any]:
    truth: dict[str, Any] = {}
    descriptions = {
        "DIESEL": ["ULSD road diesel pump", "Road Diesel - fleet lane"],
        "UNLEADED": ["Regular gas 87 octane", "Unleaded vehicle fuel"],
        "PREMIUM_UNLEADED": ["Premium unleaded 93 octane", "Premium gas vehicle fuel"],
        "BIODIESEL": ["B20 biodiesel blend", "Bio diesel fleet pump"],
        "ELECTRIC_CHARGE": ["EV charging session", "Electric charge depot"],
    }
    factors = {"L": 1.0, "US_GAL": 3.785411784, "IMP_GAL": 4.54609}
    categories = list(descriptions)
    currencies = ["USD", "EUR", "GBP", "CAD"]
    for collection, target in FUEL_COLLECTIONS.items():
        rng = stream(f"fuel:{collection}")
        if "2026_01" in collection:
            month_start, days = dt.date(2026, 1, 1), 31
        elif "2026_03" in collection:
            month_start, days = dt.date(2026, 3, 1), 31
        else:
            month_start, days = dt.date(2025, 12, 1), 31
        certified, provisional = register_transaction_snapshots(collection, "fuel", snapshots, f"{iso_date(month_start + dt.timedelta(days=days - 1))}T23:59:59Z")
        duplicate_count = max(20, target // 30)
        unique_count = target - duplicate_count
        rows: list[dict[str, Any]] = []
        outcomes: list[dict[str, Any]] = []
        for index in range(unique_count):
            business_date = month_start + dt.timedelta(days=index % days)
            actual = categories[index % len(categories)]
            expected = categories[(index + (1 if index % 13 == 0 else 0)) % len(categories)]
            reason = None
            if index % 97 == 0:
                quantity = -round(10 + rng.random() * 70, 3)
                description = descriptions[actual][index % 2]
                reason = "invalid_quantity"
                noise["fuel_invalid_numeric"] += 1
            else:
                quantity = round(10 + rng.random() * 110, 3)
                if index % 89 == 0:
                    description = "diesel and unleaded mixed card entry"
                    reason = "ambiguous_alias"
                    noise["fuel_ambiguous_alias"] += 1
                elif index % 83 == 0:
                    description = "Fleet energy XQ service"
                    reason = "unrecognized_alias"
                    noise["fuel_unrecognized_alias"] += 1
                elif index % 79 == 0:
                    description = "biodieseline additive, no dispensed fuel label"
                    reason = "unrecognized_alias"
                    noise["fuel_false_substring"] += 1
                else:
                    description = descriptions[actual][index % 2]
            unit = ["L", "US_GAL", "IMP_GAL"][index % 3]
            currency = currencies[index % len(currencies)]
            amount = round(abs(quantity or 0) * (1.2 + categories.index(actual) * 0.18) / factors[unit], 2)
            transaction_id = f"FT-{collection[-7:].replace('_', '')}-{index + 1:06d}"
            snapshot = certified if index % 5 != 0 else provisional
            row = {
                "collection_id": collection, "transaction_id": transaction_id,
                "snapshot_id": snapshot, "asset_id": f"AST-{index % 240:04d}",
                "merchant_id": f"MER-{index % 37:03d}",
                "purchased_at": f"{iso_date(business_date)}T{index % 24:02d}:{index % 60:02d}:00Z",
                "expected_fuel_type": expected, "purchased_description": description,
                "quantity": quantity, "quantity_unit": unit, "currency": currency, "amount": amount,
                "record_status": "POSTED" if reason is None else "REVIEW",
                "business_updated_at": f"{iso_date(business_date)}T{(index + 2) % 24:02d}:30:00Z",
                "ingested_at": f"{iso_date(business_date + dt.timedelta(days=1))}T03:00:00Z",
            }
            rows.append(row)
            snapshots.use(collection, snapshot)
            outcome = {
                "transaction_id": transaction_id, "snapshot_id": snapshot,
                "normalized_category": None if reason else actual,
                "expected_category": expected, "mismatch": reason is None and actual != expected,
                "quarantine_reason": reason,
                "volume_l": None if reason else round(quantity * factors[unit], 3),
                "amount_usd": None if reason else round(amount * certified_fx(business_date, currency), 2),
                "business_updated_at": row["business_updated_at"],
            }
            outcomes.append(outcome)
            if outcome["mismatch"]:
                noise["fuel_expected_actual_mismatch"] += 1
        for duplicate_index in range(duplicate_count):
            source_index = (duplicate_index * 23) % unique_count
            row = dict(rows[source_index])
            row["snapshot_id"] = provisional if row["snapshot_id"] == certified else certified
            row["ingested_at"] = row["ingested_at"][:11] + "09:00:00Z"
            rows.append(row)
            snapshots.use(collection, row["snapshot_id"])
            copied = dict(outcomes[source_index])
            copied["snapshot_id"] = row["snapshot_id"]
            outcomes.append(copied)
            noise["fuel_duplicate_source_rows"] += 1
        insert_many(conn, "private_fuel_transactions", PUBLIC_VIEWS["v_fuel_transactions"], rows)
        status_rank = {certified: 2, provisional: 1}
        retained: dict[str, dict[str, Any]] = {}
        for outcome in outcomes:
            current = retained.get(outcome["transaction_id"])
            key = (status_rank[outcome["snapshot_id"]], outcome["business_updated_at"], outcome["snapshot_id"])
            if current is None or key > (status_rank[current["snapshot_id"]], current["business_updated_at"], current["snapshot_id"]):
                retained[outcome["transaction_id"]] = outcome
        valid = [item for item in retained.values() if item["quarantine_reason"] is None]
        truth[collection] = {
            "record_count": len(rows),
            "logical_transaction_count": len(retained),
            "duplicate_raw_count": len(rows) - len(retained),
            "quarantine_counts": dict(sorted(Counter(item["quarantine_reason"] for item in retained.values() if item["quarantine_reason"]).items())),
            "normalized_category_counts": dict(sorted(Counter(item["normalized_category"] for item in valid).items())),
            "expected_actual_mismatch_count": sum(bool(item["mismatch"]) for item in valid),
            "corrected_volume_l": round(sum(item["volume_l"] for item in valid), 3),
            "corrected_amount_usd": round(sum(item["amount_usd"] for item in valid), 2),
            "record_outcomes": outcomes,
        }
    return truth


def generate_freight(conn: sqlite3.Connection, snapshots: SnapshotRegistry, noise: Counter[str]) -> dict[str, Any]:
    truth: dict[str, Any] = {}
    descriptions = {
        "STANDARD": ["standard ground freight", "economy linehaul"],
        "EXPRESS": ["express next day delivery", "priority air shipment"],
        "REFRIGERATED": ["refrigerated cold chain service", "reefer temperature control"],
        "HAZMAT": ["hazmat dangerous goods move", "hazardous material service"],
        "OVERSIZE": ["oversize wide load freight", "over dimensional shipment"],
    }
    weight_factor = {"KG": 1.0, "LB": 0.45359237}
    distance_factor = {"KM": 1.0, "MI": 1.609344}
    classes = list(descriptions)
    currencies = ["USD", "EUR", "GBP", "CAD"]
    for collection, target in FREIGHT_COLLECTIONS.items():
        rng = stream(f"freight:{collection}")
        month_start = dt.date(2026, 2 if "_02" in collection else 4, 1)
        days = 28 if month_start.month == 2 else 30
        certified, provisional = register_transaction_snapshots(collection, "freight", snapshots, f"{iso_date(month_start + dt.timedelta(days=days - 1))}T23:59:59Z")
        duplicate_count = max(25, target // 27)
        unique_count = target - duplicate_count
        rows: list[dict[str, Any]] = []
        outcomes: list[dict[str, Any]] = []
        for index in range(unique_count):
            date = month_start + dt.timedelta(days=index % days)
            actual = classes[index % len(classes)]
            expected = classes[(index + (1 if index % 11 == 0 else 0)) % len(classes)]
            reason = None
            weight = round(50 + rng.random() * 9500, 3)
            distance = round(15 + rng.random() * 2100, 3)
            if index % 101 == 0:
                weight = -weight
                reason = "invalid_weight"
                noise["freight_invalid_numeric"] += 1
            elif index % 107 == 0:
                distance = 0
                reason = "invalid_distance"
                noise["freight_invalid_numeric"] += 1
            if index % 91 == 0 and reason is None:
                description = "express standard mixed instruction"
                reason = "ambiguous_alias"
                noise["freight_ambiguous_alias"] += 1
            elif index % 87 == 0 and reason is None:
                description = "custom logistics service QZ"
                reason = "unrecognized_alias"
                noise["freight_unrecognized_alias"] += 1
            else:
                description = descriptions[actual][index % 2] + (" with liftgate accessorial" if index % 7 == 0 else "")
            weight_unit = ["KG", "LB"][index % 2]
            distance_unit = ["KM", "MI"][index % 2]
            currency = currencies[index % len(currencies)]
            amount = round(abs(weight) * weight_factor[weight_unit] * 0.12 + abs(distance) * distance_factor[distance_unit] * 0.38, 2)
            charge_id = f"FC-{collection[-7:].replace('_', '')}-{index + 1:06d}"
            snapshot = certified if index % 6 != 0 else provisional
            row = {
                "collection_id": collection, "charge_id": charge_id, "snapshot_id": snapshot,
                "invoice_id": f"INV-{index // 4:06d}", "invoice_line_no": index % 4 + 1,
                "carrier_id": f"CAR-{index % 29:03d}", "lane_id": f"LANE-{index % 83:03d}",
                "service_date": iso_date(date), "expected_service_class": expected,
                "description": description, "billed_weight": weight, "weight_unit": weight_unit,
                "distance": distance, "distance_unit": distance_unit, "currency": currency,
                "amount": amount, "record_status": "BILLED" if reason is None else "REVIEW",
                "business_updated_at": f"{iso_date(date)}T{(index + 5) % 24:02d}:20:00Z",
                "ingested_at": f"{iso_date(date + dt.timedelta(days=2))}T02:00:00Z",
            }
            rows.append(row)
            snapshots.use(collection, snapshot)
            outcome = {
                "charge_id": charge_id, "snapshot_id": snapshot,
                "normalized_service_class": None if reason else actual,
                "expected_service_class": expected, "mismatch": reason is None and actual != expected,
                "quarantine_reason": reason,
                "weight_kg": None if reason else round(weight * weight_factor[weight_unit], 3),
                "distance_km": None if reason else round(distance * distance_factor[distance_unit], 3),
                "amount_usd": None if reason else round(amount * certified_fx(date, currency), 2),
                "business_updated_at": row["business_updated_at"],
            }
            outcomes.append(outcome)
            if outcome["mismatch"]:
                noise["freight_expected_actual_mismatch"] += 1
        for duplicate_index in range(duplicate_count):
            source_index = (duplicate_index * 19) % unique_count
            row = dict(rows[source_index])
            row["snapshot_id"] = provisional if row["snapshot_id"] == certified else certified
            row["ingested_at"] = row["ingested_at"][:11] + "12:00:00Z"
            rows.append(row)
            snapshots.use(collection, row["snapshot_id"])
            copied = dict(outcomes[source_index])
            copied["snapshot_id"] = row["snapshot_id"]
            outcomes.append(copied)
            noise["freight_duplicate_invoice_lines"] += 1
        insert_many(conn, "private_freight_charges", PUBLIC_VIEWS["v_freight_charges"], rows)
        status_rank = {certified: 2, provisional: 1}
        retained: dict[str, dict[str, Any]] = {}
        for outcome in outcomes:
            current = retained.get(outcome["charge_id"])
            key = (status_rank[outcome["snapshot_id"]], outcome["business_updated_at"], outcome["snapshot_id"])
            if current is None or key > (status_rank[current["snapshot_id"]], current["business_updated_at"], current["snapshot_id"]):
                retained[outcome["charge_id"]] = outcome
        valid = [item for item in retained.values() if item["quarantine_reason"] is None]
        truth[collection] = {
            "record_count": len(rows), "logical_charge_count": len(retained),
            "duplicate_raw_count": len(rows) - len(retained),
            "quarantine_counts": dict(sorted(Counter(item["quarantine_reason"] for item in retained.values() if item["quarantine_reason"]).items())),
            "normalized_service_counts": dict(sorted(Counter(item["normalized_service_class"] for item in valid).items())),
            "expected_actual_mismatch_count": sum(bool(item["mismatch"]) for item in valid),
            "corrected_weight_kg": round(sum(item["weight_kg"] for item in valid), 3),
            "corrected_distance_km": round(sum(item["distance_km"] for item in valid), 3),
            "corrected_amount_usd": round(sum(item["amount_usd"] for item in valid), 2),
            "record_outcomes": outcomes,
        }
    return truth


def generate_maintenance(conn: sqlite3.Connection, snapshots: SnapshotRegistry, noise: Counter[str]) -> dict[str, Any]:
    truth: dict[str, Any] = {}
    event_types = ["INSPECTION", "OIL_CHANGE", "BRAKE_SERVICE", "TIRE_SERVICE", "ENGINE_REPAIR"]
    for collection, target in MAINTENANCE_COLLECTIONS.items():
        rng = stream(f"maintenance:{collection}")
        q2 = collection.endswith("q2")
        base_date = dt.date(2026, 3, 25) if q2 else dt.date(2026, 1, 1)
        certified = f"{collection}-certified"
        provisional = f"{collection}-provisional"
        stale = f"{collection}-stale"
        snapshots.add(collection, certified, "Maintenance ERP", "CERTIFIED", "2026-06-30T23:59:59Z" if q2 else "2026-03-31T23:59:59Z", "2026-07-01T01:00:00Z", "2026-07-01T03:00:00Z")
        snapshots.add(collection, provisional, "Mobile Work Orders", "PROVISIONAL", "2026-07-02T23:59:59Z" if q2 else "2026-04-02T23:59:59Z", "2026-07-03T01:00:00Z", "2026-07-03T02:00:00Z")
        if q2:
            snapshots.add(collection, stale, "Legacy Maintenance Export", "STALE", "2026-05-31T23:59:59Z", "2026-06-10T01:00:00Z", "2026-06-15T02:00:00Z")
        duplicate_count = target // 24
        unique_count = target - duplicate_count
        rows: list[dict[str, Any]] = []
        outcomes: list[dict[str, Any]] = []
        last_odo: dict[str, float] = {}
        regression_cases: list[dict[str, Any]] = []
        for index in range(unique_count):
            asset = f"AST-{index % 180:04d}"
            sequence = index // 180
            date = base_date + dt.timedelta(days=sequence * 7 + index % 5)
            snapshot_choices = [certified] * 6 + [provisional] * 2 + ([stale] if q2 else [])
            snapshot = snapshot_choices[index % len(snapshot_choices)]
            event_id = f"ME-{collection[-2:].upper()}-{index + 1:06d}"
            work_order = f"WO-{collection[-2:].upper()}-{index + 1:06d}"
            event_time: str | None = f"{iso_date(date)}T{index % 24:02d}:{index % 60:02d}:00Z"
            unit = "MI" if index % 4 == 0 else "KM"
            prior = last_odo.get(asset, 20000 + (index % 180) * 410)
            odo_km = prior + 120 + rng.random() * 180
            flags: list[str] = []
            if index % 131 == 0:
                event_time = None
                flags.append("missing_timestamp")
                noise["maintenance_invalid_timestamp"] += 1
            elif index % 139 == 0:
                event_time = "2026-99-45 25:61"
                flags.append("invalid_timestamp")
                noise["maintenance_invalid_timestamp"] += 1
            if index > 180 and index % 137 == 0:
                odo_km = prior - (350 + rng.random() * 500)
                flags.append("odometer_regression")
                regression_cases.append({"event_id": event_id, "asset_id": asset, "prior_km": round(prior, 1), "current_km": round(odo_km, 1)})
                noise["maintenance_odometer_regression"] += 1
            labor = round(0.25 + rng.random() * 11, 2)
            if index % 149 == 0:
                labor = -labor
                flags.append("negative_labor")
                noise["maintenance_invalid_labor"] += 1
            elif index % 157 == 0:
                labor = 120.0
                flags.append("extreme_labor")
                noise["maintenance_invalid_labor"] += 1
            if index % 163 == 0:
                odo_km = -100.0
                flags.append("invalid_odometer")
                noise["maintenance_invalid_odometer"] += 1
            display_odo = round(odo_km / 1.609344, 1) if unit == "MI" else round(odo_km, 1)
            last_odo[asset] = max(prior, odo_km) if not flags else prior
            row = {
                "collection_id": collection, "snapshot_id": snapshot, "event_id": event_id,
                "work_order_id": work_order, "asset_id": asset,
                "event_type": event_types[index % len(event_types)], "event_time_raw": event_time,
                "odometer_value": display_odo, "odometer_unit": unit, "labor_hours": labor,
                "parts_cost": round(20 + rng.random() * 2200, 2),
                "currency": ["USD", "EUR", "GBP", "CAD"][index % 4],
                "technician_id": f"TECH-{index % 64:03d}",
                "event_status": ["COMPLETED", "CLOSED", "OPEN"][index % 3],
                "business_updated_at": f"{iso_date(date)}T{(index + 4) % 24:02d}:30:00Z",
                "ingested_at": f"{iso_date(date + dt.timedelta(days=(index % 5) + 1))}T06:00:00Z",
            }
            rows.append(row)
            snapshots.use(collection, snapshot)
            outcomes.append({
                "event_id": event_id, "snapshot_id": snapshot, "asset_id": asset,
                "normalized_odometer_km": round(odo_km, 1), "issue_flags": flags,
                "business_updated_at": row["business_updated_at"], "retained": True,
            })
        duplicate_groups: list[dict[str, Any]] = []
        for duplicate_index in range(duplicate_count):
            source_index = (duplicate_index * 17) % unique_count
            row = dict(rows[source_index])
            row["snapshot_id"] = provisional if row["snapshot_id"] == certified else certified
            row["event_status"] = "OPEN" if row["event_status"] != "OPEN" else "CLOSED"
            row["ingested_at"] = row["ingested_at"][:11] + "18:00:00Z"
            rows.append(row)
            snapshots.use(collection, row["snapshot_id"])
            copied = dict(outcomes[source_index])
            copied["snapshot_id"] = row["snapshot_id"]
            copied["retained"] = row["snapshot_id"] == certified
            outcomes.append(copied)
            duplicate_groups.append({"event_id": row["event_id"], "snapshots": sorted({rows[source_index]["snapshot_id"], row["snapshot_id"]}), "retained_snapshot": certified})
            noise["maintenance_duplicate_events"] += 1
        insert_many(conn, "private_maintenance_events", PUBLIC_VIEWS["v_maintenance_events"], rows)
        truth[collection] = {
            "record_count": len(rows), "logical_event_count": unique_count,
            "issue_counts": dict(sorted(Counter(flag for item in outcomes[:unique_count] for flag in item["issue_flags"]).items())),
            "duplicate_groups": duplicate_groups,
            "regression_cases": regression_cases,
            "overlapping_q1_baseline_count": sum(1 for row in rows if q2 and row["event_time_raw"] and row["event_time_raw"][:10] <= "2026-03-31"),
            "event_outcomes": outcomes,
        }
    return truth


def insert_snapshots(conn: sqlite3.Connection, snapshots: SnapshotRegistry) -> None:
    insert_many(conn, "private_source_snapshots", PUBLIC_VIEWS["v_source_snapshots"], snapshots.rows())


def insert_catalog(conn: sqlite3.Connection) -> None:
    rows: list[dict[str, Any]] = []
    descriptions = {
        "contacts": "Raw contact records from operational source systems.",
        "fuel": "Raw fleet fuel and charging transactions.",
        "freight": "Raw carrier invoice charge lines.",
        "maintenance": "Raw maintenance work-order events across snapshots.",
        "quote": "Non-binding freight quotes retained for planning context.",
        "telematics": "Vehicle telemetry alert index retained for operational context.",
    }
    for collection, (count, sources) in CONTACT_COLLECTIONS.items():
        rows.append({"collection_id": collection, "description": descriptions["contacts"], "family": "contacts", "source_systems": json.dumps(sources), "time_start": "2025-10-01" if "archived" in collection else "2026-01-01", "time_end": "2026-04-15", "approximate_record_count": count, "queryable": 1})
    for collection, count in FUEL_COLLECTIONS.items():
        rows.append({"collection_id": collection, "description": descriptions["fuel"], "family": "fuel", "source_systems": json.dumps(["Fuel Ledger", "Fuel Feed"]), "time_start": "2025-12-01", "time_end": "2026-03-31", "approximate_record_count": count, "queryable": 1})
    for collection, count in FREIGHT_COLLECTIONS.items():
        rows.append({"collection_id": collection, "description": descriptions["freight"], "family": "freight", "source_systems": json.dumps(["Freight Ledger", "Freight Feed"]), "time_start": "2026-02-01", "time_end": "2026-04-30", "approximate_record_count": count, "queryable": 1})
    for collection, count in MAINTENANCE_COLLECTIONS.items():
        rows.append({"collection_id": collection, "description": descriptions["maintenance"], "family": "maintenance", "source_systems": json.dumps(["Maintenance ERP", "Mobile Work Orders", "Legacy Maintenance Export"]), "time_start": "2026-01-01", "time_end": "2026-06-30", "approximate_record_count": count, "queryable": 1})
    rows.extend([
        {"collection_id": "freight_quotes_2026q1", "description": descriptions["quote"], "family": "quote", "source_systems": json.dumps(["Carrier Sourcing"]), "time_start": "2026-01-01", "time_end": "2026-03-31", "approximate_record_count": 400, "queryable": 0},
        {"collection_id": "telematics_alerts_2026_q2", "description": descriptions["telematics"], "family": "telematics", "source_systems": json.dumps(["Telematics Platform"]), "time_start": "2026-04-01", "time_end": "2026-06-30", "approximate_record_count": 620, "queryable": 0},
    ])
    columns = ["collection_id", "description", "family", "source_systems", "time_start", "time_end", "approximate_record_count", "queryable"]
    insert_many(conn, "private_collection_catalog", columns, rows)


def database_counts(conn: sqlite3.Connection) -> tuple[dict[str, int], dict[str, int]]:
    view_counts = {name: int(conn.execute(f"SELECT count(*) FROM {name}").fetchone()[0]) for name in PUBLIC_VIEWS}
    collection_counts: dict[str, int] = {}
    for view in ("v_contacts", "v_fuel_transactions", "v_freight_charges", "v_maintenance_events"):
        for collection, count in conn.execute(f"SELECT collection_id,count(*) FROM {view} GROUP BY collection_id"):
            collection_counts[collection] = int(count)
    for collection, count in conn.execute("SELECT collection_id,approximate_record_count FROM private_collection_catalog WHERE queryable=0"):
        collection_counts[collection] = int(count)
    return dict(sorted(view_counts.items())), dict(sorted(collection_counts.items()))


def canonicalize_sqlite_file(path: Path) -> None:
    """Zero b-tree slack and fix header metadata across SQLite versions."""

    with path.open("r+b") as handle:
        header = handle.read(100)
        if header[:16] != b"SQLite format 3\x00":
            raise RuntimeError("generated database has an invalid SQLite header")
        page_size = struct.unpack(">H", header[16:18])[0]
        if page_size == 1:
            page_size = 65_536
        file_size = path.stat().st_size
        if file_size % page_size:
            raise RuntimeError("generated database has a partial SQLite page")

        for page_index in range(file_size // page_size):
            page_start = page_index * page_size
            header_offset = 100 if page_index == 0 else 0
            handle.seek(page_start + header_offset)
            page_header = handle.read(12)
            page_type = page_header[0]
            if page_type not in {0x02, 0x05, 0x0A, 0x0D}:
                continue
            header_size = 12 if page_type in {0x02, 0x05} else 8
            cell_count = struct.unpack(">H", page_header[3:5])[0]
            cell_content_start = struct.unpack(">H", page_header[5:7])[0]
            if cell_content_start == 0:
                cell_content_start = 65_536
            pointer_array_end = header_offset + header_size + 2 * cell_count
            if not pointer_array_end <= cell_content_start <= page_size:
                raise RuntimeError("generated database has an invalid b-tree page")
            handle.seek(page_start + pointer_array_end)
            handle.write(b"\x00" * (cell_content_start - pointer_array_end))

        handle.seek(96)
        handle.write(struct.pack(">I", CANONICAL_SQLITE_VERSION_NUMBER))
        handle.flush()
        os.fsync(handle.fileno())


def generate(output: Path, manifest_path: Path, truth_path: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    os.close(fd)
    temp_db = Path(temp_name)
    try:
        conn = sqlite3.connect(temp_db)
        try:
            conn.execute("PRAGMA secure_delete=ON")
            create_schema(conn)
            noise: Counter[str] = Counter()
            snapshots = SnapshotRegistry()
            add_reference_data(conn, noise)
            contacts_truth = generate_contacts(conn, snapshots, noise)
            fuel_truth = generate_fuel(conn, snapshots, noise)
            freight_truth = generate_freight(conn, snapshots, noise)
            maintenance_truth = generate_maintenance(conn, snapshots, noise)
            insert_snapshots(conn, snapshots)
            insert_catalog(conn)
            conn.execute("PRAGMA user_version=1")
            conn.commit()
            view_counts, collection_counts = database_counts(conn)
            quick = conn.execute("PRAGMA quick_check").fetchone()[0]
            if quick != "ok":
                raise RuntimeError("generated database failed integrity check")
            conn.execute("VACUUM")
        finally:
            conn.close()
        canonicalize_sqlite_file(temp_db)
        os.replace(temp_db, output)
    except Exception:
        try:
            temp_db.unlink()
        except FileNotFoundError:
            pass
        raise

    endpoints_path = Path(__file__).with_name("endpoints.txt")
    manifest = {
        "generator_version": GENERATOR_VERSION,
        "seed": SEED,
        "schema_version": SCHEMA_VERSION,
        "generated_at": GENERATED_AT,
        "sqlite": {"path": "data/asteria_quality.db", "sha256": file_hash(output)},
        "views": view_counts,
        "collections": collection_counts,
        "noise_counts": dict(sorted(noise.items())),
        "endpoint_inventory_sha256": file_hash(endpoints_path),
    }
    truth = {
        "generator_version": GENERATOR_VERSION,
        "seed": SEED,
        "generated_at": GENERATED_AT,
        "contacts": contacts_truth,
        "fuel": fuel_truth,
        "freight": freight_truth,
        "maintenance": maintenance_truth,
        "snapshot_membership": {
            f"{collection}|{snapshot}": count for (collection, snapshot), count in sorted(snapshots.counts.items())
        },
        "noise_counts": dict(sorted(noise.items())),
    }
    atomic_json(manifest_path, manifest)
    atomic_json(truth_path, truth)


def verify(output: Path, manifest_path: Path, truth_path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("generated metadata is unavailable") from exc
    if manifest.get("seed") != SEED or truth.get("seed") != SEED:
        raise RuntimeError("seed mismatch")
    if manifest.get("sqlite", {}).get("sha256") != file_hash(output):
        raise RuntimeError("database checksum mismatch")
    if manifest.get("endpoint_inventory_sha256") != file_hash(Path(__file__).with_name("endpoints.txt")):
        raise RuntimeError("endpoint inventory checksum mismatch")
    uri = f"file:{output.resolve()}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    try:
        if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError("database integrity check failed")
        for view, expected_fields in PUBLIC_VIEWS.items():
            actual_fields = [row[1] for row in conn.execute(f"PRAGMA table_info({view})")]
            if actual_fields != expected_fields:
                raise RuntimeError(f"public view contract mismatch: {view}")
        view_counts, collection_counts = database_counts(conn)
        if view_counts != manifest.get("views") or collection_counts != manifest.get("collections"):
            raise RuntimeError("manifest count mismatch")
        expected = {
            **{name: value[0] for name, value in CONTACT_COLLECTIONS.items()},
            **FUEL_COLLECTIONS,
            **FREIGHT_COLLECTIONS,
            **MAINTENANCE_COLLECTIONS,
            "freight_quotes_2026q1": 400,
            "telematics_alerts_2026_q2": 620,
        }
        if collection_counts != dict(sorted(expected.items())):
            raise RuntimeError("collection count contract mismatch")
        if conn.execute("SELECT count(*) FROM v_reference_aliases WHERE reference_status='ACTIVE'").fetchone()[0] < 25:
            raise RuntimeError("reference alias coverage is insufficient")
        if conn.execute("SELECT count(*) FROM v_source_snapshots WHERE row_count<=0").fetchone()[0]:
            raise RuntimeError("empty source snapshot")
    finally:
        conn.close()
    return {
        "status": "ok",
        "seed": SEED,
        "schema_version": SCHEMA_VERSION,
        "database_sha256": manifest["sqlite"]["sha256"],
        "views": manifest["views"],
        "collections": manifest["collections"],
    }


def parse_args() -> argparse.Namespace:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=base / "data" / "asteria_quality.db")
    parser.add_argument("--manifest", type=Path, default=base / "manifest.json")
    parser.add_argument("--truth", type=Path, default=base / "construction_truth.json")
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.verify:
        result = verify(args.output, args.manifest, args.truth)
    else:
        generate(args.output, args.manifest, args.truth)
        result = verify(args.output, args.manifest, args.truth)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
