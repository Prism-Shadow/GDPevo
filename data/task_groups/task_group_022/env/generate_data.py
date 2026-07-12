#!/usr/bin/env python3
"""Generate the shared SaaS operations analytics SQLite environment."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path


SEED = 15015
WINDOW_START = date(2026, 1, 1)
WINDOW_END = date(2026, 6, 30)
TARGET_USAGE_ROWS = 18_000
TARGET_TICKET_ROWS = 1_200

REGIONS = ["NA", "EMEA", "APAC", "LATAM"]
SEGMENTS = ["enterprise", "commercial", "startup", "internal"]
PRODUCTS = [
    ("ATLASDB", "AtlasDB", "data platform", 1),
    ("HELIOSYNC", "HelioSync", "integration", 1),
    ("NEXAQUEUE", "NexaQueue", "workflow", 1),
    ("LUMAFORMS", "LumaForms", "experience", 1),
]


def iso_date(value: date) -> str:
    return value.isoformat()


def iso_dt(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def rand_date(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def rand_dt_on(rng: random.Random, day: date) -> datetime:
    return datetime.combine(day, datetime.min.time()) + timedelta(
        hours=rng.randint(0, 23),
        minutes=rng.randint(0, 59),
        seconds=rng.randint(0, 59),
    )


def csv_join(values: list[str]) -> str:
    return ",".join(values)


def load_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    conn.executescript(schema_path.read_text(encoding="utf-8"))


def build_accounts(rng: random.Random) -> list[tuple]:
    name_roots = [
        "Northstar",
        "BluePeak",
        "Vertex",
        "Summit",
        "Clearline",
        "Harbor",
        "Mercury",
        "Oakfield",
        "Quantum",
        "Redwood",
        "Silverline",
        "TrueNorth",
        "Waypoint",
        "Keystone",
        "Brightwell",
        "Cobalt",
    ]
    suffixes = ["Systems", "Analytics", "Labs", "Group", "Works", "Cloud"]
    accounts: list[tuple] = []
    counter = 1
    for region in REGIONS:
        for segment in ["enterprise", "commercial", "startup", "internal"]:
            for slot in range(6):
                account_id = f"ACCT-{counter:04d}"
                status = rng.choices(
                    ["active", "paused", "churned"],
                    weights=[76, 15, 9],
                    k=1,
                )[0]
                if segment == "internal":
                    status = rng.choice(["active", "test"])
                account_name = (
                    f"{rng.choice(name_roots)} {rng.choice(suffixes)} {region} {counter:03d}"
                )
                owner_team = f"{region} Customer Operations"
                created_at = rand_date(rng, date(2023, 1, 1), date(2026, 3, 15))
                accounts.append(
                    (
                        account_id,
                        account_name,
                        segment,
                        region,
                        status,
                        owner_team,
                        1 if segment == "internal" else 0,
                        iso_date(created_at),
                    )
                )
                counter += 1

    for slot in range(1, 9):
        account_id = f"INT-{slot:04d}"
        region = rng.choice(REGIONS)
        accounts.append(
            (
                account_id,
                f"Internal Validation Workspace {slot}",
                "internal",
                region,
                "test" if slot % 2 else "active",
                "Internal Operations",
                1,
                iso_date(rand_date(rng, date(2024, 1, 1), date(2026, 1, 31))),
            )
        )
    return accounts


def plan_for_segment(segment: str, rng: random.Random) -> str:
    if segment == "internal":
        return "internal"
    if segment == "enterprise":
        return rng.choices(["enterprise", "growth", "standard"], [70, 25, 5], k=1)[0]
    if segment == "commercial":
        return rng.choices(["growth", "standard", "trial"], [55, 35, 10], k=1)[0]
    return rng.choices(["standard", "trial", "growth"], [50, 35, 15], k=1)[0]


def build_subscriptions(rng: random.Random, accounts: list[tuple]) -> list[tuple]:
    subscriptions: list[tuple] = []
    customer_accounts = [row for row in accounts if row[6] == 0]
    internal_accounts = [row for row in accounts if row[6] == 1]
    weighted_accounts = customer_accounts * 5 + internal_accounts

    for idx in range(1, 181):
        account = rng.choice(weighted_accounts)
        account_id = account[0]
        segment = account[2]
        product_id = rng.choice(PRODUCTS)[0]
        plan_code = plan_for_segment(segment, rng)
        start = rand_date(rng, date(2025, 7, 1), date(2026, 6, 15))
        end = None
        if rng.random() < 0.24:
            end = rand_date(rng, max(start + timedelta(days=15), date(2025, 8, 1)), date(2026, 6, 30))
        if plan_code == "trial":
            status = "trial" if end is None or end >= WINDOW_END else "ended"
        elif end is not None and end < date(2026, 7, 1):
            status = "ended"
        else:
            status = rng.choices(["active", "paused"], [88, 12], k=1)[0]
        subscriptions.append(
            (
                f"SUB-{idx:04d}",
                account_id,
                product_id,
                plan_code,
                status,
                iso_date(start),
                iso_date(end) if end else None,
            )
        )
    return subscriptions


def usage_metrics(rng: random.Random, segment: str, product_id: str, environment: str) -> tuple[int, int, float, float]:
    scale = {"enterprise": 5.0, "commercial": 2.3, "startup": 1.0, "internal": 0.65}[segment]
    env_factor = {"production": 1.0, "staging": 0.22, "sandbox": 0.12, "internal": 0.08}[environment]
    product_factor = {"ATLASDB": 1.25, "HELIOSYNC": 1.0, "NEXAQUEUE": 0.85, "LUMAFORMS": 0.7}[product_id]
    seats = max(0, int(rng.gauss(18 * scale * env_factor, 6)))
    api_calls = max(0, int(rng.gauss(5800 * scale * env_factor * product_factor, 1400)))
    compute_hours = round(max(0.0, rng.gauss(19 * scale * env_factor * product_factor, 5.5)), 2)
    data_gb = round(max(0.0, rng.gauss(72 * scale * env_factor * product_factor, 16)), 2)
    return seats, api_calls, compute_hours, data_gb


def formal_usage_rows(rng: random.Random, accounts: list[tuple]) -> dict[str, list[tuple]]:
    customer_accounts = [row for row in accounts if row[6] == 0 and row[4] in ("active", "paused")]
    apr_accounts = customer_accounts[:7]
    may_accounts = customer_accounts[20:31]

    rows_a: list[tuple] = []
    for idx in range(1, 15):
        account = apr_accounts[(idx - 1) % len(apr_accounts)]
        activity = date(2026, 4, 5) + timedelta(days=idx)
        seats, api_calls, compute_hours, data_gb = usage_metrics(rng, account[2], "HELIOSYNC", "production")
        rows_a.append(
            (
                f"USG-DQ-APR-{idx:03d}",
                account[0],
                "HELIOSYNC",
                iso_date(activity),
                "production",
                "telemetry_v2",
                seats,
                api_calls,
                compute_hours,
                data_gb,
                0,
                iso_dt(rand_dt_on(rng, activity + timedelta(days=1))),
                None,
                None,
            )
        )

    rows_c: list[tuple] = []
    for idx in range(1, 12):
        account = may_accounts[(idx - 1) % len(may_accounts)]
        activity = date(2026, 5, 9) + timedelta(days=idx)
        seats, api_calls, compute_hours, data_gb = usage_metrics(rng, account[2], "NEXAQUEUE", "production")
        rows_c.append(
            (
                f"USG-DQ-MAY-{idx:03d}",
                account[0],
                "NEXAQUEUE",
                iso_date(activity),
                "production",
                "telemetry_v2",
                seats,
                api_calls,
                compute_hours,
                data_gb,
                0,
                iso_dt(rand_dt_on(rng, activity + timedelta(days=1))),
                None,
                None,
            )
        )
    return {
        "DQ-USG-2026-04-A": rows_a,
        "DQ-USG-2026-05-C": rows_c,
    }


def build_usage(rng: random.Random, accounts: list[tuple], subscriptions: list[tuple]) -> tuple[list[tuple], dict[str, list[str]]]:
    by_account = {row[0]: row for row in accounts}
    eligible_pairs = [(sub[1], sub[2]) for sub in subscriptions]
    formal = formal_usage_rows(rng, accounts)
    rows = [row for case_rows in formal.values() for row in case_rows]
    formal_targets = {case_id: [row[0] for row in case_rows] for case_id, case_rows in formal.items()}

    duplicate_signatures: list[tuple[str, str, str, str]] = []
    remaining = TARGET_USAGE_ROWS - len(rows)
    for idx in range(1, remaining + 1):
        if duplicate_signatures and rng.random() < 0.085:
            account_id, product_id, activity_s, environment = rng.choice(duplicate_signatures)
            activity = date.fromisoformat(activity_s)
            source = rng.choice(["telemetry_v1", "telemetry_v2"])
        else:
            account_id, product_id = rng.choice(eligible_pairs)
            activity = rand_date(rng, WINDOW_START, WINDOW_END)
            account = by_account[account_id]
            if account[6] == 1:
                environment = rng.choices(["internal", "staging", "sandbox", "production"], [70, 14, 10, 6], k=1)[0]
            else:
                environment = rng.choices(["production", "staging", "sandbox"], [83, 10, 7], k=1)[0]
            source = rng.choices(["telemetry_v2", "telemetry_v1", "import_patch"], [66, 24, 10], k=1)[0]
            if environment == "production" and rng.random() < 0.18:
                duplicate_signatures.append((account_id, product_id, iso_date(activity), environment))
        account = by_account[account_id]
        seats, api_calls, compute_hours, data_gb = usage_metrics(rng, account[2], product_id, environment)
        is_backfill = 1 if source == "import_patch" or rng.random() < 0.035 else 0
        lag_days = rng.choice([0, 1, 1, 1, 2, 3])
        if is_backfill and rng.random() < 0.55:
            lag_days = rng.randint(12, 75)
        recorded_at = rand_dt_on(rng, activity + timedelta(days=lag_days))
        audit_reason = None
        audit_updated_at = None
        if rng.random() < 0.012:
            audit_reason = rng.choice(["late backfill validation", "source replay check", "manual anomaly review"])
            audit_updated_at = iso_dt(recorded_at + timedelta(days=rng.randint(1, 9)))
        rows.append(
            (
                f"USG-{idx:06d}",
                account_id,
                product_id,
                iso_date(activity),
                environment,
                source,
                seats,
                api_calls,
                compute_hours,
                data_gb,
                is_backfill,
                iso_dt(recorded_at),
                audit_reason,
                audit_updated_at,
            )
        )
    return rows, formal_targets


def build_incidents(rng: random.Random) -> list[tuple]:
    incidents: list[tuple] = []
    for idx in range(1, 9):
        product_id = PRODUCTS[(idx - 1) % len(PRODUCTS)][0]
        started_day = rand_date(rng, WINDOW_START, WINDOW_END - timedelta(days=2))
        started_at = rand_dt_on(rng, started_day)
        resolved_at = started_at + timedelta(hours=rng.randint(2, 38), minutes=rng.randint(0, 59))
        incidents.append(
            (
                f"INC-2026-{idx:03d}",
                product_id,
                iso_dt(started_at),
                iso_dt(resolved_at),
                rng.choices(["SEV1", "SEV2", "SEV3"], [15, 35, 50], k=1)[0],
                rng.choice(REGIONS + ["GLOBAL"]),
                rng.choice(["resolved", "closed", "monitoring"]),
            )
        )
    return incidents


def ticket_sla(created_at: datetime, severity: str) -> datetime:
    hours = {"P1": 4, "P2": 12, "P3": 48, "P4": 120}[severity]
    return created_at + timedelta(hours=hours)


def formal_ticket_rows(rng: random.Random, accounts: list[tuple]) -> dict[str, list[tuple]]:
    customers = [row for row in accounts if row[6] == 0 and row[4] in ("active", "paused")]
    account_b = customers[11][0]
    account_d = customers[42][0]

    def make_ticket(
        ticket_id: str,
        account_id: str,
        product_id: str,
        created_at: datetime,
        severity: str,
        category: str,
        status: str,
        duplicate_of: str | None,
    ) -> tuple:
        closed_at = created_at + timedelta(hours=rng.randint(10, 96)) if status in ("resolved", "canceled") else None
        return (
            ticket_id,
            account_id,
            product_id,
            iso_dt(created_at),
            iso_dt(closed_at) if closed_at else None,
            status,
            severity,
            category,
            1,
            1 if duplicate_of else 0,
            duplicate_of,
            None,
            iso_dt(ticket_sla(created_at, severity)),
            None,
            None,
        )

    base_b = make_ticket(
        "TKT-DQ-MASTER-03-B",
        account_b,
        "ATLASDB",
        datetime(2026, 3, 14, 9, 12, 0),
        "P2",
        "bug",
        "resolved",
        None,
    )
    dup_b_ids = ["TKT-DQ-MAR-B-001", "TKT-DQ-MAR-B-002", "TKT-DQ-MAR-B-003"]
    rows_b = [base_b]
    for offset, ticket_id in enumerate(dup_b_ids, start=1):
        rows_b.append(
            make_ticket(
                ticket_id,
                account_b,
                "ATLASDB",
                datetime(2026, 3, 14, 9 + offset, 17, 0),
                "P2",
                "bug",
                "resolved",
                None,
            )
        )

    base_d = make_ticket(
        "TKT-DQ-MASTER-05-D",
        account_d,
        "LUMAFORMS",
        datetime(2026, 5, 21, 13, 5, 0),
        "P3",
        "performance",
        "resolved",
        None,
    )
    dup_d_ids = ["TKT-DQ-MAY-D-001", "TKT-DQ-MAY-D-002"]
    rows_d = [base_d]
    for offset, ticket_id in enumerate(dup_d_ids, start=1):
        rows_d.append(
            make_ticket(
                ticket_id,
                account_d,
                "LUMAFORMS",
                datetime(2026, 5, 21, 13 + offset, 22, 0),
                "P3",
                "performance",
                "resolved",
                None,
            )
        )
    return {
        "DQ-TKT-2026-03-B": rows_b,
        "DQ-TKT-2026-05-D": rows_d,
    }


def build_tickets(
    rng: random.Random,
    accounts: list[tuple],
    incidents: list[tuple],
) -> tuple[list[tuple], dict[str, list[str]]]:
    by_account = {row[0]: row for row in accounts}
    incident_ids_by_product: dict[str, list[str]] = {}
    for incident in incidents:
        incident_ids_by_product.setdefault(incident[1], []).append(incident[0])

    formal = formal_ticket_rows(rng, accounts)
    rows = [row for case_rows in formal.values() for row in case_rows]
    formal_targets = {
        "DQ-TKT-2026-03-B": ["TKT-DQ-MAR-B-001", "TKT-DQ-MAR-B-002", "TKT-DQ-MAR-B-003"],
        "DQ-TKT-2026-05-D": ["TKT-DQ-MAY-D-001", "TKT-DQ-MAY-D-002"],
    }
    inserted_ids_by_pair: dict[tuple[str, str], list[str]] = {}
    for row in rows:
        inserted_ids_by_pair.setdefault((row[1], row[2]), []).append(row[0])

    all_accounts = accounts
    categories = ["bug", "outage", "performance", "data_loss", "how_to", "billing", "feature_request", "internal_test"]
    remaining = TARGET_TICKET_ROWS - len(rows)
    for idx in range(1, remaining + 1):
        account = rng.choice(all_accounts)
        account_id = account[0]
        product_id = rng.choice(PRODUCTS)[0]
        created_at = rand_dt_on(rng, rand_date(rng, WINDOW_START, WINDOW_END))
        severity = rng.choices(["P1", "P2", "P3", "P4"], [5, 17, 43, 35], k=1)[0]
        if account[6] == 1:
            category = rng.choices(categories, [7, 5, 8, 1, 10, 4, 8, 57], k=1)[0]
        else:
            category = rng.choices(categories[:-1], [30, 8, 18, 3, 20, 10, 11], k=1)[0]
        status = rng.choices(["open", "in_progress", "resolved", "canceled"], [13, 12, 67, 8], k=1)[0]
        closed_at = None
        if status in ("resolved", "canceled"):
            closed_at = created_at + timedelta(hours=rng.randint(1, 210), minutes=rng.randint(0, 59))
        customer_impact = 0 if account[6] == 1 or category in ("how_to", "billing", "feature_request", "internal_test") else 1

        duplicate_of = None
        pair = (account_id, product_id)
        if inserted_ids_by_pair.get(pair) and rng.random() < 0.075:
            duplicate_of = rng.choice(inserted_ids_by_pair[pair])
            is_duplicate = 1
        else:
            is_duplicate = 0

        linked_incident_id = None
        if category in ("outage", "performance", "data_loss") and incident_ids_by_product.get(product_id) and rng.random() < 0.42:
            linked_incident_id = rng.choice(incident_ids_by_product[product_id])
        audit_reason = None
        audit_updated_at = None
        if rng.random() < 0.02:
            audit_reason = rng.choice(["support merge review", "severity normalization", "customer impact cleanup"])
            audit_updated_at = iso_dt(created_at + timedelta(days=rng.randint(1, 12)))
        row = (
            f"TKT-{idx:06d}",
            account_id,
            product_id,
            iso_dt(created_at),
            iso_dt(closed_at) if closed_at else None,
            status,
            severity,
            category,
            customer_impact,
            is_duplicate,
            duplicate_of,
            linked_incident_id,
            iso_dt(ticket_sla(created_at, severity)),
            audit_reason,
            audit_updated_at,
        )
        rows.append(row)
        inserted_ids_by_pair.setdefault(pair, []).append(row[0])
    return rows, formal_targets


def build_data_quality_cases(
    usage_targets: dict[str, list[str]],
    ticket_targets: dict[str, list[str]],
) -> list[tuple]:
    return [
        (
            "DQ-USG-2026-04-A",
            "usage_product_correction",
            "approved",
            "usage_daily",
            csv_join(usage_targets["DQ-USG-2026-04-A"]),
            "product_id",
            "HELIOSYNC",
            "ATLASDB",
            "APR-2026-USG-A-APPROVED",
            "approved correction DQ-USG-2026-04-A",
            "2026-04-23 10:15:00",
        ),
        (
            "DQ-TKT-2026-03-B",
            "ticket_duplicate_correction",
            "approved",
            "tickets",
            csv_join(ticket_targets["DQ-TKT-2026-03-B"]),
            "duplicate_of",
            "",
            "TKT-DQ-MASTER-03-B",
            "MAR-2026-TKT-B-APPROVED",
            "approved correction DQ-TKT-2026-03-B",
            "2026-03-18 16:40:00",
        ),
        (
            "DQ-USG-2026-05-C",
            "usage_product_correction",
            "approved",
            "usage_daily",
            csv_join(usage_targets["DQ-USG-2026-05-C"]),
            "product_id",
            "NEXAQUEUE",
            "LUMAFORMS",
            "MAY-2026-USG-C-APPROVED",
            "approved correction DQ-USG-2026-05-C",
            "2026-05-27 09:25:00",
        ),
        (
            "DQ-TKT-2026-05-D",
            "ticket_duplicate_correction",
            "approved",
            "tickets",
            csv_join(ticket_targets["DQ-TKT-2026-05-D"]),
            "duplicate_of",
            "",
            "TKT-DQ-MASTER-05-D",
            "MAY-2026-TKT-D-APPROVED",
            "approved correction DQ-TKT-2026-05-D",
            "2026-05-29 12:05:00",
        ),
        (
            "DQ-USG-2026-02-X",
            "usage_product_correction",
            "draft",
            "usage_daily",
            "USG-000021,USG-000022",
            "product_id",
            "ATLASDB",
            "HELIOSYNC",
            "FEB-2026-USG-X-DRAFT",
            "draft correction awaiting product owner review",
            "2026-02-19 14:22:00",
        ),
        (
            "DQ-TKT-2026-04-Y",
            "ticket_duplicate_correction",
            "rejected",
            "tickets",
            "TKT-000031,TKT-000044",
            "duplicate_of",
            "",
            "TKT-000012",
            "APR-2026-TKT-Y-REJECTED",
            "rejected duplicate proposal after support review",
            "2026-04-11 11:00:00",
        ),
        (
            "DQ-USG-2026-06-Z",
            "usage_product_correction",
            "draft",
            "usage_daily",
            "USG-000301,USG-000302,USG-000303",
            "product_id",
            "LUMAFORMS",
            "NEXAQUEUE",
            "JUN-2026-USG-Z-DRAFT",
            "draft correction pending telemetry owner approval",
            "2026-06-20 17:10:00",
        ),
        (
            "DQ-TKT-2026-01-W",
            "ticket_duplicate_correction",
            "rejected",
            "tickets",
            "TKT-000105",
            "duplicate_of",
            "",
            "TKT-000099",
            "JAN-2026-TKT-W-REJECTED",
            "rejected because customer reports were unrelated",
            "2026-01-31 08:45:00",
        ),
    ]


def build_metric_notes() -> list[tuple]:
    return [
        ("NOTE-001", "usage", "Usage rows represent one account, product, date, environment, and telemetry source observation.", "2026-06-30 00:00:00"),
        ("NOTE-002", "production", "Production environment rows are customer-facing workload observations.", "2026-06-30 00:00:00"),
        ("NOTE-003", "backfill", "Backfill rows are late-arriving records loaded after normal telemetry processing.", "2026-06-30 00:00:00"),
        ("NOTE-004", "defect", "Support defect analysis commonly includes bug, outage, performance, and data loss categories.", "2026-06-30 00:00:00"),
        ("NOTE-005", "duplicate tickets", "A duplicate ticket references the primary support ticket in duplicate_of.", "2026-06-30 00:00:00"),
        ("NOTE-006", "customer impact", "Customer impact indicates whether the support issue affected an external customer workflow.", "2026-06-30 00:00:00"),
        ("NOTE-007", "internal accounts", "Internal and test accounts support validation and should be treated separately from external customers.", "2026-06-30 00:00:00"),
        ("NOTE-008", "incidents", "Incident links identify support tickets associated with product availability or reliability events.", "2026-06-30 00:00:00"),
        ("NOTE-009", "audit fields", "Audit fields are populated when an approved correction or manual review changes a record.", "2026-06-30 00:00:00"),
        ("NOTE-010", "source systems", "Telemetry v1, telemetry v2, and import patch records may overlap during migration periods.", "2026-06-30 00:00:00"),
    ]


def insert_all(conn: sqlite3.Connection, rows: dict[str, list[tuple]]) -> None:
    conn.executemany(
        "INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows["accounts"],
    )
    conn.executemany(
        "INSERT INTO products VALUES (?, ?, ?, ?)",
        rows["products"],
    )
    conn.executemany(
        "INSERT INTO subscriptions VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows["subscriptions"],
    )
    conn.executemany(
        "INSERT INTO usage_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows["usage_daily"],
    )
    conn.executemany(
        "INSERT INTO incidents VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows["incidents"],
    )
    conn.executemany(
        "INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows["tickets"],
    )
    conn.executemany(
        "INSERT INTO data_quality_cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows["data_quality_cases"],
    )
    conn.executemany(
        "INSERT INTO metric_notes VALUES (?, ?, ?, ?)",
        rows["metric_notes"],
    )


def counts(conn: sqlite3.Connection) -> dict[str, int]:
    table_names = [
        "accounts",
        "products",
        "subscriptions",
        "usage_daily",
        "tickets",
        "incidents",
        "data_quality_cases",
        "metric_notes",
    ]
    return {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in table_names
    }


def manifest_relative_path(path: Path, manifest_path: Path) -> str:
    return os.path.relpath(path.resolve(), manifest_path.resolve().parent).replace(os.sep, "/")


def write_manifest(
    manifest_path: Path,
    db_path: Path,
    conn: sqlite3.Connection,
    usage_targets: dict[str, list[str]],
    ticket_targets: dict[str, list[str]],
) -> None:
    formal_cases = {
        "DQ-USG-2026-04-A": {
            "target_table": "usage_daily",
            "target_ids": usage_targets["DQ-USG-2026-04-A"],
            "field_name": "product_id",
            "old_value": "HELIOSYNC",
            "new_value": "ATLASDB",
        },
        "DQ-TKT-2026-03-B": {
            "target_table": "tickets",
            "target_ids": ticket_targets["DQ-TKT-2026-03-B"],
            "field_name": "duplicate_of",
            "new_value": "TKT-DQ-MASTER-03-B",
        },
        "DQ-USG-2026-05-C": {
            "target_table": "usage_daily",
            "target_ids": usage_targets["DQ-USG-2026-05-C"],
            "field_name": "product_id",
            "old_value": "NEXAQUEUE",
            "new_value": "LUMAFORMS",
        },
        "DQ-TKT-2026-05-D": {
            "target_table": "tickets",
            "target_ids": ticket_targets["DQ-TKT-2026-05-D"],
            "field_name": "duplicate_of",
            "new_value": "TKT-DQ-MASTER-05-D",
        },
    }
    manifest = {
        "environment": "api_wrapped_ops_analytics",
        "sqlite_db": manifest_relative_path(db_path, manifest_path),
        "api_entrypoint": "TASK_ENV_BASE_URL",
        "seed": SEED,
        "date_window": {
            "start": iso_date(WINDOW_START),
            "end": iso_date(WINDOW_END),
        },
        "record_counts": counts(conn),
        "formal_cases": formal_cases,
        "notes": [
            "Solver-facing access is through the HTTP API base URL exported by task_env.sh.",
            "The SQLite database path is relative to this manifest and is retained for environment setup.",
            "This manifest is hidden construction metadata and is not solver-facing.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate(conn: sqlite3.Connection) -> None:
    foreign_key_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_errors:
        raise RuntimeError(f"foreign key check failed: {foreign_key_errors[:5]}")
    actual_counts = counts(conn)
    if actual_counts["usage_daily"] != TARGET_USAGE_ROWS:
        raise RuntimeError(f"expected {TARGET_USAGE_ROWS} usage rows, found {actual_counts['usage_daily']}")
    if actual_counts["tickets"] != TARGET_TICKET_ROWS:
        raise RuntimeError(f"expected {TARGET_TICKET_ROWS} ticket rows, found {actual_counts['tickets']}")


def generate(db_path: Path, schema_path: Path, manifest_path: Path) -> None:
    rng = random.Random(SEED)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        load_schema(conn, schema_path)
        accounts = build_accounts(rng)
        subscriptions = build_subscriptions(rng, accounts)
        usage, usage_targets = build_usage(rng, accounts, subscriptions)
        incidents = build_incidents(rng)
        tickets, ticket_targets = build_tickets(rng, accounts, incidents)
        rows = {
            "accounts": accounts,
            "products": PRODUCTS,
            "subscriptions": subscriptions,
            "usage_daily": usage,
            "incidents": incidents,
            "tickets": tickets,
            "data_quality_cases": build_data_quality_cases(usage_targets, ticket_targets),
            "metric_notes": build_metric_notes(),
        }
        insert_all(conn, rows)
        validate(conn)
        conn.commit()
        write_manifest(manifest_path, db_path, conn, usage_targets, ticket_targets)
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parent
    parser.add_argument("--db", type=Path, default=here / "generated" / "ops_analytics.sqlite")
    parser.add_argument("--schema", type=Path, default=here / "schema.sql")
    parser.add_argument("--manifest", type=Path, default=here / "generated" / "manifest.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate(args.db, args.schema, args.manifest)


if __name__ == "__main__":
    main()
