#!/usr/bin/env python3
import json
import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path


SEED = 24024
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "portfolio.db"
MANIFEST_PATH = BASE_DIR / "data_manifest.json"
GENERATED_AT = "2026-07-18T00:00:00Z"

TEAMS = [
    "Platform Core",
    "Identity Services",
    "Infra Reliability",
    "Data Platform",
    "Mobile Client",
    "Growth Experiences",
    "AppSec",
    "Observability",
    "Core Services",
    "Integrations",
    "Billing",
    "API Foundations",
    "Revenue Platform",
    "Edge Delivery",
    "Release Engineering",
]

PRODUCT_AREAS = [
    "Atlas Backend",
    "Identity",
    "Data Reliability",
    "Checkout",
    "Security Operations",
    "Core Runtime",
    "API Connectivity",
    "Revenue Systems",
    "Edge Routing",
    "Release Train",
]

WORK_TYPES = [
    "Feature",
    "Enhancement",
    "Bug",
    "Incident",
    "Chore",
    "Refactor",
    "Security",
    "Compliance",
    "Reliability",
    "Dependency",
]

STATUSES = [
    "Backlog",
    "In Progress",
    "Review",
    "Done",
    "Verified",
    "Deployed",
    "Closed",
    "Cancelled",
    "Duplicate",
    "Reopened",
]

CLOSED_STATUSES = {"Done", "Verified", "Deployed", "Closed", "Cancelled", "Duplicate"}
SEVERITIES = ["S1", "S2", "S3", "S4"]
QUARTERS = ["2025-Q3", "2025-Q4", "2026-Q1"]


def iso(d):
    return d.isoformat() if d else None


def quarter_for(d):
    if d.year == 2025 and 7 <= d.month <= 9:
        return "2025-Q3"
    if d.year == 2025 and 10 <= d.month <= 12:
        return "2025-Q4"
    if d.year == 2026 and 1 <= d.month <= 3:
        return "2026-Q1"
    return None


def choose_release(rng, target_date, labels):
    if target_date < date(2025, 10, 1):
        return None
    if "rollout" in labels or "release" in labels or rng.random() < 0.38:
        if target_date <= date(2025, 12, 31):
            return "REL-NOVA-2025-12"
        if target_date <= date(2026, 2, 24):
            return "REL-ORION-2026-02"
        return "REL-ZEPHYR-2026-03"
    return None


def make_labels(rng, work_type, title_tokens):
    labels = set()
    type_labels = {
        "Security": ["security", "auth", "encryption"],
        "Compliance": ["security", "compliance"],
        "Reliability": ["reliability", "latency"],
        "Incident": ["incident", "outage"],
        "Refactor": ["refactor", "cleanup"],
        "Chore": ["cleanup"],
        "Dependency": ["migration", "dependency"],
        "Feature": ["feature", "rollout"],
        "Enhancement": ["feature"],
        "Bug": ["flaky"],
    }
    labels.update(type_labels.get(work_type, []))
    for token in title_tokens:
        if token in {
            "security",
            "cve",
            "auth",
            "encryption",
            "reliability",
            "incident",
            "outage",
            "latency",
            "flaky",
            "refactor",
            "migration",
            "cleanup",
            "feature",
            "rollout",
        }:
            labels.add(token)
    if rng.random() < 0.12:
        labels.add(rng.choice(["stale-export", "customer-request", "papertrail", "follow-up"]))
    return sorted(labels)


def create_schema(conn):
    conn.executescript(
        """
        DROP TABLE IF EXISTS work_items;
        DROP TABLE IF EXISTS mix_targets;
        DROP TABLE IF EXISTS sla_policy;
        DROP TABLE IF EXISTS releases;
        DROP TABLE IF EXISTS milestones;
        DROP TABLE IF EXISTS dependencies;
        DROP TABLE IF EXISTS blockers;

        CREATE TABLE work_items (
            id TEXT PRIMARY KEY,
            title TEXT,
            work_type TEXT,
            status TEXT,
            team TEXT,
            owner TEXT,
            product_area TEXT,
            created_at TEXT,
            due_at TEXT,
            closed_at TEXT,
            severity TEXT,
            priority INTEGER,
            labels TEXT,
            story_points INTEGER,
            release_id TEXT,
            milestone_id TEXT,
            duplicate_of TEXT,
            mirror_status TEXT,
            legacy_category TEXT
        );

        CREATE TABLE mix_targets (
            scope_id TEXT,
            quarter TEXT,
            team_group TEXT,
            product_area TEXT,
            new_feature_pct REAL,
            tech_debt_pct REAL,
            reliability_pct REAL,
            security_pct REAL
        );

        CREATE TABLE sla_policy (
            severity TEXT PRIMARY KEY,
            days_to_due INTEGER
        );

        CREATE TABLE releases (
            id TEXT PRIMARY KEY,
            name TEXT,
            target_date TEXT,
            train TEXT
        );

        CREATE TABLE milestones (
            id TEXT PRIMARY KEY,
            release_id TEXT,
            name TEXT,
            owner_team TEXT
        );

        CREATE TABLE dependencies (
            blocked_id TEXT,
            depends_on_id TEXT,
            relation TEXT
        );

        CREATE TABLE blockers (
            id TEXT PRIMARY KEY,
            work_item_id TEXT,
            release_id TEXT,
            severity TEXT,
            cause TEXT,
            status TEXT,
            opened_at TEXT,
            resolved_at TEXT
        );
        """
    )


def fixture_items():
    rows = [
        (
            "WI-24024-001",
            "Patch cve auth token replay in edge callback",
            "Security",
            "Deployed",
            "AppSec",
            "Avery Quinn",
            "Security Operations",
            "2025-07-12",
            "2025-07-19",
            "2025-07-18",
            "S1",
            1,
            ["security", "cve", "auth", "encryption"],
            5,
            None,
            None,
            None,
            "Closed",
            "feature",
        ),
        (
            "WI-24024-002",
            "Identity encryption key rotation rollout",
            "Security",
            "Verified",
            "Identity Services",
            "Mina Shah",
            "Identity",
            "2025-08-03",
            "2025-08-15",
            "2025-08-14",
            "S2",
            2,
            ["security", "encryption", "rollout"],
            8,
            None,
            None,
            None,
            "Done",
            "maintenance",
        ),
        (
            "WI-24024-003",
            "Checkout latency incident follow-up",
            "Incident",
            "Closed",
            "Infra Reliability",
            "Owen Hart",
            "Checkout",
            "2025-08-22",
            "2025-08-25",
            "2025-08-28",
            "S1",
            1,
            ["incident", "latency", "outage", "reliability"],
            3,
            None,
            None,
            None,
            "Closed",
            "bug",
        ),
        (
            "WI-24024-004",
            "Atlas backend feature flag rollout",
            "Feature",
            "Done",
            "Platform Core",
            "Nora Patel",
            "Atlas Backend",
            "2025-09-02",
            "2025-09-28",
            "2025-09-26",
            "S3",
            3,
            ["feature", "rollout"],
            13,
            None,
            None,
            None,
            "Done",
            "new",
        ),
        (
            "WI-24024-005",
            "Refactor legacy migration cleanup for event writer",
            "Refactor",
            "Closed",
            "Data Platform",
            "Liam Chen",
            "Data Reliability",
            "2025-09-11",
            "2025-10-04",
            "2025-10-06",
            "S3",
            4,
            ["refactor", "migration", "cleanup"],
            8,
            None,
            None,
            None,
            "Complete",
            "tech-debt",
        ),
        (
            "WI-24024-006",
            "Duplicate auth encryption alert from stale mirror",
            "Bug",
            "Duplicate",
            "AppSec",
            "Avery Quinn",
            "Security Operations",
            "2025-09-13",
            "2025-09-20",
            "2025-09-21",
            "S2",
            2,
            ["security", "auth", "stale-export"],
            2,
            None,
            None,
            "WI-24024-001",
            "Open",
            "security",
        ),
        (
            "WI-24024-007",
            "Mobile client flaky checkout retry bug",
            "Bug",
            "Closed",
            "Mobile Client",
            None,
            "Checkout",
            "2025-10-02",
            "2025-10-16",
            "2025-10-19",
            "S2",
            2,
            ["flaky", "reliability"],
            5,
            None,
            None,
            None,
            "Closed",
            "quality",
        ),
        (
            "WI-24024-008",
            "Release train Orion gateway readiness",
            "Feature",
            "Deployed",
            "Release Engineering",
            "Sofia Reyes",
            "Release Train",
            "2025-11-03",
            "2026-02-13",
            "2026-02-12",
            "S3",
            3,
            ["feature", "rollout", "release"],
            8,
            "REL-ORION-2026-02",
            "MIL-ORION-GA",
            None,
            "Done",
            "release",
        ),
        (
            "WI-24024-009",
            "Orion auth dependency upgrade",
            "Dependency",
            "Verified",
            "Identity Services",
            "Mina Shah",
            "Identity",
            "2025-12-01",
            "2026-01-22",
            "2026-01-20",
            "S2",
            2,
            ["auth", "migration", "security"],
            5,
            "REL-ORION-2026-02",
            "MIL-ORION-HARDEN",
            None,
            "Verified",
            "maintenance",
        ),
        (
            "WI-24024-010",
            "Orion edge routing outage rehearsal",
            "Reliability",
            "Review",
            "Edge Delivery",
            None,
            "Edge Routing",
            "2026-01-06",
            "2026-02-05",
            None,
            "S1",
            1,
            ["reliability", "outage", "latency"],
            8,
            "REL-ORION-2026-02",
            "MIL-ORION-RC",
            None,
            "In Progress",
            "incident",
        ),
        (
            "WI-24024-011",
            "Orion billing invoice feature rollout",
            "Feature",
            "Done",
            "Billing",
            "Theo Brooks",
            "Revenue Systems",
            "2026-01-08",
            "2026-02-15",
            "2026-02-16",
            "S3",
            3,
            ["feature", "rollout"],
            13,
            "REL-ORION-2026-02",
            "MIL-ORION-GA",
            None,
            "Done",
            "new",
        ),
        (
            "WI-24024-012",
            "Orion appsec blocker cve scan exception",
            "Security",
            "In Progress",
            "AppSec",
            "Priya Stone",
            "Security Operations",
            "2026-01-15",
            "2026-02-07",
            None,
            "S1",
            1,
            ["security", "cve", "auth"],
            5,
            "REL-ORION-2026-02",
            "MIL-ORION-HARDEN",
            None,
            "Open",
            "security",
        ),
        (
            "WI-24024-013",
            "Zephyr API connectivity migration cleanup",
            "Refactor",
            "Closed",
            "API Foundations",
            "Jon Bell",
            "API Connectivity",
            "2026-01-20",
            "2026-03-01",
            "2026-02-27",
            "S3",
            4,
            ["refactor", "migration", "cleanup"],
            8,
            "REL-ZEPHYR-2026-03",
            "MIL-ZEPHYR-BETA",
            None,
            "Closed",
            "tech-debt",
        ),
        (
            "WI-24024-014",
            "Zephyr revenue platform feature launch",
            "Feature",
            "Review",
            "Revenue Platform",
            "Mara Singh",
            "Revenue Systems",
            "2026-02-01",
            "2026-03-15",
            None,
            "S3",
            3,
            ["feature", "rollout"],
            13,
            "REL-ZEPHYR-2026-03",
            "MIL-ZEPHYR-GA",
            None,
            "Review",
            "new",
        ),
        (
            "WI-24024-015",
            "Zephyr data reliability latency guardrail",
            "Reliability",
            "Verified",
            "Data Platform",
            "Liam Chen",
            "Data Reliability",
            "2026-02-07",
            "2026-03-05",
            "2026-03-04",
            "S2",
            2,
            ["reliability", "latency"],
            8,
            "REL-ZEPHYR-2026-03",
            "MIL-ZEPHYR-HARDEN",
            None,
            "Verified",
            "quality",
        ),
        (
            "WI-24024-016",
            "Zephyr duplicate rollout smoke report",
            "Bug",
            "Duplicate",
            "Release Engineering",
            "Sofia Reyes",
            "Release Train",
            "2026-02-10",
            "2026-02-20",
            "2026-02-18",
            "S4",
            5,
            ["rollout", "stale-export"],
            1,
            "REL-ZEPHYR-2026-03",
            "MIL-ZEPHYR-GA",
            "WI-24024-014",
            "Open",
            "bug",
        ),
        (
            "WI-24024-017",
            "Zephyr encryption audit evidence",
            "Compliance",
            "Backlog",
            "AppSec",
            None,
            "Security Operations",
            "2026-02-14",
            "2026-03-08",
            None,
            "S2",
            2,
            ["security", "encryption", "compliance"],
            5,
            "REL-ZEPHYR-2026-03",
            "MIL-ZEPHYR-HARDEN",
            None,
            "Backlog",
            "security",
        ),
        (
            "WI-24024-018",
            "Nova release train cleanup report",
            "Chore",
            "Closed",
            "Release Engineering",
            "Sofia Reyes",
            "Release Train",
            "2025-10-12",
            "2025-12-15",
            "2025-12-17",
            "S4",
            5,
            ["cleanup", "release"],
            3,
            "REL-NOVA-2025-12",
            "MIL-NOVA-GA",
            None,
            "Closed",
            "admin",
        ),
    ]
    rows.extend(portfolio_scope_items())
    rows.extend(sla_scope_items())
    return rows


def portfolio_scope_items():
    rows = []

    def add(
        suffix,
        title,
        work_type,
        status,
        team,
        owner,
        product_area,
        created_at,
        due_at,
        closed_at,
        severity,
        priority,
        labels,
        story_points,
        duplicate_of=None,
        mirror_status="Closed",
        legacy_category="new",
    ):
        rows.append(
            (
                f"WI-24024-P{suffix:03d}",
                title,
                work_type,
                status,
                team,
                owner,
                product_area,
                created_at,
                due_at,
                closed_at,
                severity,
                priority,
                labels,
                story_points,
                None,
                None,
                duplicate_of,
                mirror_status,
                legacy_category,
            )
        )

    # train_001: Platform Core and Identity Services, Atlas Backend and Identity, Q4 2025 closed.
    add(
        1,
        "Atlas backend feature rollout with stale security label",
        "Feature",
        "Closed",
        "Platform Core",
        "Nora Patel",
        "Atlas Backend",
        "2025-09-24",
        "2025-10-11",
        "2025-10-10",
        "S3",
        3,
        ["feature", "rollout", "security"],
        8,
        legacy_category="security",
    )
    add(
        2,
        "Identity auth encryption refactor cleanup",
        "Refactor",
        "Verified",
        "Identity Services",
        "Mina Shah",
        "Identity",
        "2025-10-02",
        "2025-10-20",
        "2025-10-18",
        "S2",
        2,
        ["auth", "encryption", "cleanup", "refactor"],
        5,
        legacy_category="tech-debt",
    )
    add(
        3,
        "Atlas latency incident follow-up feature toggle",
        "Incident",
        "Done",
        "Platform Core",
        "Nora Patel",
        "Atlas Backend",
        "2025-10-08",
        "2025-10-25",
        "2025-10-24",
        "S1",
        1,
        ["incident", "latency", "feature", "reliability"],
        3,
        legacy_category="new",
    )
    add(
        4,
        "Identity consent screen feature migration",
        "Feature",
        "Deployed",
        "Identity Services",
        "Mina Shah",
        "Identity",
        "2025-10-14",
        "2025-11-05",
        "2025-11-02",
        "S3",
        3,
        ["feature", "migration"],
        13,
        legacy_category="maintenance",
    )
    add(
        5,
        "Atlas queue cleanup for flaky reliability alert",
        "Chore",
        "Closed",
        "Platform Core",
        "Devon Wells",
        "Atlas Backend",
        "2025-10-21",
        "2025-11-12",
        "2025-11-11",
        "S3",
        4,
        ["cleanup", "flaky", "reliability"],
        5,
        legacy_category="quality",
    )
    add(
        6,
        "Identity cve audit for rollout banner",
        "Security",
        "Verified",
        "Identity Services",
        "Avery Quinn",
        "Identity",
        "2025-11-01",
        "2025-11-14",
        "2025-11-13",
        "S1",
        1,
        ["security", "cve", "rollout"],
        8,
        legacy_category="new",
    )
    add(
        7,
        "Atlas migration cleanup with auth title",
        "Dependency",
        "Closed",
        "Platform Core",
        "Elena Park",
        "Atlas Backend",
        "2025-11-07",
        "2025-11-28",
        "2025-11-25",
        "S3",
        4,
        ["migration", "cleanup", "auth"],
        8,
        legacy_category="security",
    )
    add(
        8,
        "Identity outage recovery dashboard enhancement",
        "Enhancement",
        "Done",
        "Identity Services",
        "Mina Shah",
        "Identity",
        "2025-11-16",
        "2025-12-03",
        "2025-12-01",
        "S2",
        2,
        ["outage", "reliability", "feature"],
        5,
        legacy_category="new",
    )
    add(
        9,
        "Atlas duplicate migration note",
        "Bug",
        "Duplicate",
        "Platform Core",
        "Devon Wells",
        "Atlas Backend",
        "2025-11-20",
        "2025-12-01",
        "2025-12-02",
        "S4",
        5,
        ["cleanup", "migration"],
        1,
        duplicate_of="WI-24024-P007",
        mirror_status="Open",
        legacy_category="tech-debt",
    )
    add(
        10,
        "Identity cancelled auth feature spike",
        "Feature",
        "Cancelled",
        "Identity Services",
        "Mina Shah",
        "Identity",
        "2025-11-23",
        "2025-12-15",
        "2025-12-13",
        "S3",
        3,
        ["feature", "auth"],
        3,
        mirror_status="Done",
        legacy_category="new",
    )
    add(
        11,
        "Atlas backend security duplicate export",
        "Security",
        "Closed",
        "Platform Core",
        "Avery Quinn",
        "Atlas Backend",
        "2025-12-01",
        "2025-12-12",
        "2025-12-10",
        "S2",
        2,
        ["security", "stale-export"],
        2,
        duplicate_of="WI-24024-P006",
        legacy_category="security",
    )

    # train_004: Mobile Client and Growth Experiences, Checkout, Q4 2025 closed.
    add(
        21,
        "Mobile checkout reliability retry cleanup",
        "Bug",
        "Closed",
        "Mobile Client",
        "Cass Morgan",
        "Checkout",
        "2025-09-29",
        "2025-10-09",
        "2025-10-08",
        "S2",
        2,
        ["reliability", "flaky", "cleanup"],
        5,
        legacy_category="bug",
    )
    add(
        22,
        "Growth checkout feature rollout with auth guard",
        "Feature",
        "Verified",
        "Growth Experiences",
        "Elena Park",
        "Checkout",
        "2025-10-04",
        "2025-10-24",
        "2025-10-23",
        "S3",
        3,
        ["feature", "rollout", "auth"],
        8,
        legacy_category="security",
    )
    add(
        23,
        "Mobile encryption crash fix for checkout",
        "Security",
        "Deployed",
        "Mobile Client",
        "Cass Morgan",
        "Checkout",
        "2025-10-12",
        "2025-10-27",
        "2025-10-26",
        "S1",
        1,
        ["security", "encryption", "flaky"],
        5,
        legacy_category="quality",
    )
    add(
        24,
        "Growth checkout migration cleanup experiment",
        "Refactor",
        "Closed",
        "Growth Experiences",
        "Elena Park",
        "Checkout",
        "2025-10-19",
        "2025-11-07",
        "2025-11-06",
        "S3",
        4,
        ["migration", "cleanup", "feature"],
        8,
        legacy_category="new",
    )
    add(
        25,
        "Mobile checkout outage follow-up banner",
        "Incident",
        "Done",
        "Mobile Client",
        None,
        "Checkout",
        "2025-10-28",
        "2025-11-08",
        "2025-11-09",
        "S1",
        1,
        ["outage", "incident", "feature"],
        3,
        legacy_category="new",
    )
    add(
        26,
        "Growth payment sheet feature polish",
        "Enhancement",
        "Verified",
        "Growth Experiences",
        "Elena Park",
        "Checkout",
        "2025-11-03",
        "2025-11-20",
        "2025-11-19",
        "S4",
        4,
        ["feature", "rollout"],
        5,
        legacy_category="maintenance",
    )
    add(
        27,
        "Mobile checkout flaky latency guardrail",
        "Reliability",
        "Closed",
        "Mobile Client",
        "Cass Morgan",
        "Checkout",
        "2025-11-11",
        "2025-11-26",
        "2025-11-24",
        "S2",
        2,
        ["reliability", "latency", "flaky"],
        8,
        legacy_category="bug",
    )
    add(
        28,
        "Growth checkout cve copy update",
        "Compliance",
        "Done",
        "Growth Experiences",
        "Avery Quinn",
        "Checkout",
        "2025-11-18",
        "2025-12-04",
        "2025-12-03",
        "S2",
        2,
        ["security", "cve", "feature"],
        3,
        legacy_category="new",
    )
    add(
        29,
        "Mobile checkout duplicate retry report",
        "Bug",
        "Duplicate",
        "Mobile Client",
        "Cass Morgan",
        "Checkout",
        "2025-11-21",
        "2025-12-02",
        "2025-12-01",
        "S3",
        4,
        ["flaky", "reliability"],
        1,
        duplicate_of="WI-24024-P027",
        mirror_status="Open",
        legacy_category="quality",
    )
    add(
        30,
        "Growth checkout cancelled rollout deck",
        "Feature",
        "Cancelled",
        "Growth Experiences",
        "Elena Park",
        "Checkout",
        "2025-12-01",
        "2025-12-16",
        "2025-12-15",
        "S4",
        5,
        ["feature", "rollout"],
        2,
        mirror_status="Done",
        legacy_category="new",
    )
    add(
        31,
        "Mobile checkout cleanup duplicate record",
        "Chore",
        "Closed",
        "Mobile Client",
        "Cass Morgan",
        "Checkout",
        "2025-12-05",
        "2025-12-18",
        "2025-12-17",
        "S4",
        5,
        ["cleanup"],
        2,
        duplicate_of="WI-24024-P024",
        legacy_category="tech-debt",
    )

    # test_001: Data Platform and Observability, Data Reliability, Q4 2025 closed.
    add(
        41,
        "Data replay feature rollout with outage tag",
        "Feature",
        "Closed",
        "Data Platform",
        "Liam Chen",
        "Data Reliability",
        "2025-10-01",
        "2025-10-17",
        "2025-10-16",
        "S3",
        3,
        ["feature", "rollout", "outage"],
        13,
        legacy_category="quality",
    )
    add(
        42,
        "Observability latency guardrail refactor",
        "Refactor",
        "Verified",
        "Observability",
        "Devon Wells",
        "Data Reliability",
        "2025-10-06",
        "2025-10-23",
        "2025-10-21",
        "S2",
        2,
        ["latency", "reliability", "refactor"],
        8,
        legacy_category="tech-debt",
    )
    add(
        43,
        "Data pipeline cve library migration",
        "Dependency",
        "Closed",
        "Data Platform",
        "Liam Chen",
        "Data Reliability",
        "2025-10-13",
        "2025-11-01",
        "2025-10-31",
        "S2",
        2,
        ["cve", "migration", "security"],
        5,
        legacy_category="maintenance",
    )
    add(
        44,
        "Observability alert cleanup for feature launch",
        "Chore",
        "Done",
        "Observability",
        "Devon Wells",
        "Data Reliability",
        "2025-10-22",
        "2025-11-09",
        "2025-11-08",
        "S3",
        4,
        ["cleanup", "feature"],
        3,
        legacy_category="new",
    )
    add(
        45,
        "Data reliability outage postmortem automation",
        "Incident",
        "Deployed",
        "Data Platform",
        None,
        "Data Reliability",
        "2025-10-30",
        "2025-11-13",
        "2025-11-12",
        "S1",
        1,
        ["incident", "outage", "reliability"],
        5,
        legacy_category="bug",
    )
    add(
        46,
        "Observability encryption audit dashboard",
        "Compliance",
        "Verified",
        "Observability",
        "Avery Quinn",
        "Data Reliability",
        "2025-11-05",
        "2025-11-21",
        "2025-11-20",
        "S2",
        2,
        ["security", "encryption", "feature"],
        8,
        legacy_category="new",
    )
    add(
        47,
        "Data flaky partition repair rollout",
        "Bug",
        "Closed",
        "Data Platform",
        "Liam Chen",
        "Data Reliability",
        "2025-11-13",
        "2025-11-30",
        "2025-11-29",
        "S2",
        2,
        ["flaky", "reliability", "rollout"],
        5,
        legacy_category="quality",
    )
    add(
        48,
        "Observability retention migration cleanup",
        "Refactor",
        "Done",
        "Observability",
        "Devon Wells",
        "Data Reliability",
        "2025-11-19",
        "2025-12-08",
        "2025-12-07",
        "S3",
        4,
        ["migration", "cleanup"],
        8,
        legacy_category="security",
    )
    add(
        49,
        "Data reliability duplicate alert export",
        "Bug",
        "Duplicate",
        "Data Platform",
        "Liam Chen",
        "Data Reliability",
        "2025-11-23",
        "2025-12-04",
        "2025-12-03",
        "S3",
        4,
        ["reliability", "stale-export"],
        1,
        duplicate_of="WI-24024-P047",
        mirror_status="Open",
        legacy_category="quality",
    )
    add(
        50,
        "Observability cancelled feature cleanup plan",
        "Feature",
        "Cancelled",
        "Observability",
        "Devon Wells",
        "Data Reliability",
        "2025-12-02",
        "2025-12-16",
        "2025-12-15",
        "S4",
        5,
        ["feature", "cleanup"],
        2,
        mirror_status="Complete",
        legacy_category="new",
    )
    add(
        51,
        "Data platform security duplicate audit",
        "Security",
        "Closed",
        "Data Platform",
        "Avery Quinn",
        "Data Reliability",
        "2025-12-07",
        "2025-12-21",
        "2025-12-20",
        "S2",
        2,
        ["security", "auth"],
        3,
        duplicate_of="WI-24024-P043",
        legacy_category="security",
    )

    # test_004: Integrations, Billing, API Foundations, Revenue Platform across API Connectivity and Revenue Systems.
    add(
        61,
        "API connectivity feature rollout with latency label",
        "Feature",
        "Closed",
        "API Foundations",
        "Jon Bell",
        "API Connectivity",
        "2025-10-03",
        "2025-10-20",
        "2025-10-18",
        "S3",
        3,
        ["feature", "rollout", "latency"],
        13,
        legacy_category="quality",
    )
    add(
        62,
        "Billing encryption ledger migration",
        "Dependency",
        "Verified",
        "Billing",
        "Theo Brooks",
        "Revenue Systems",
        "2025-10-08",
        "2025-10-27",
        "2025-10-26",
        "S2",
        2,
        ["encryption", "migration", "security"],
        8,
        legacy_category="maintenance",
    )
    add(
        63,
        "Integrations outage retry cleanup",
        "Incident",
        "Closed",
        "Integrations",
        "Jon Bell",
        "API Connectivity",
        "2025-10-15",
        "2025-10-30",
        "2025-10-29",
        "S1",
        1,
        ["outage", "incident", "cleanup"],
        5,
        legacy_category="tech-debt",
    )
    add(
        64,
        "Revenue platform customer feature launch",
        "Feature",
        "Deployed",
        "Revenue Platform",
        "Mara Singh",
        "Revenue Systems",
        "2025-10-23",
        "2025-11-14",
        "2025-11-13",
        "S3",
        3,
        ["feature", "rollout"],
        13,
        legacy_category="new",
    )
    add(
        65,
        "API gateway auth cve remediation",
        "Security",
        "Verified",
        "API Foundations",
        "Avery Quinn",
        "API Connectivity",
        "2025-10-31",
        "2025-11-12",
        "2025-11-11",
        "S1",
        1,
        ["security", "auth", "cve"],
        8,
        legacy_category="bug",
    )
    add(
        66,
        "Billing flaky invoice reliability guardrail",
        "Reliability",
        "Done",
        "Billing",
        None,
        "Revenue Systems",
        "2025-11-06",
        "2025-11-24",
        "2025-11-22",
        "S2",
        2,
        ["flaky", "reliability"],
        5,
        legacy_category="quality",
    )
    add(
        67,
        "Integrations contract refactor feature cleanup",
        "Refactor",
        "Closed",
        "Integrations",
        "Jon Bell",
        "API Connectivity",
        "2025-11-14",
        "2025-12-02",
        "2025-12-01",
        "S3",
        4,
        ["refactor", "feature", "cleanup"],
        8,
        legacy_category="new",
    )
    add(
        68,
        "Revenue systems compliance encryption evidence",
        "Compliance",
        "Verified",
        "Revenue Platform",
        "Mara Singh",
        "Revenue Systems",
        "2025-11-20",
        "2025-12-09",
        "2025-12-08",
        "S2",
        2,
        ["security", "encryption", "compliance"],
        5,
        legacy_category="maintenance",
    )
    add(
        69,
        "API duplicate connectivity incident export",
        "Bug",
        "Duplicate",
        "API Foundations",
        "Jon Bell",
        "API Connectivity",
        "2025-11-23",
        "2025-12-05",
        "2025-12-04",
        "S3",
        4,
        ["incident", "stale-export"],
        1,
        duplicate_of="WI-24024-P063",
        mirror_status="Open",
        legacy_category="bug",
    )
    add(
        70,
        "Billing cancelled rollout migration",
        "Feature",
        "Cancelled",
        "Billing",
        "Theo Brooks",
        "Revenue Systems",
        "2025-12-01",
        "2025-12-16",
        "2025-12-14",
        "S4",
        5,
        ["feature", "migration"],
        3,
        mirror_status="Done",
        legacy_category="new",
    )
    add(
        71,
        "Revenue platform duplicate cve cleanup",
        "Security",
        "Closed",
        "Revenue Platform",
        "Avery Quinn",
        "Revenue Systems",
        "2025-12-04",
        "2025-12-18",
        "2025-12-17",
        "S2",
        2,
        ["security", "cve", "cleanup"],
        3,
        duplicate_of="WI-24024-P065",
        legacy_category="security",
    )

    return rows


def sla_scope_items():
    rows = []

    def add(
        suffix,
        title,
        work_type,
        status,
        team,
        owner,
        product_area,
        created_at,
        due_at,
        closed_at,
        severity,
        priority,
        labels,
        story_points,
        duplicate_of=None,
        mirror_status="Open",
        legacy_category="quality",
    ):
        rows.append(
            (
                f"WI-24024-S{suffix:03d}",
                title,
                work_type,
                status,
                team,
                owner,
                product_area,
                created_at,
                due_at,
                closed_at,
                severity,
                priority,
                labels,
                story_points,
                None,
                None,
                duplicate_of,
                mirror_status,
                legacy_category,
            )
        )

    # train_002: Infra Reliability and Data Platform, as_of 2026-01-15, recent closed window 14 days.
    add(
        1,
        "Infra reliability outage runbook overdue",
        "Reliability",
        "In Progress",
        "Infra Reliability",
        "Owen Hart",
        "Data Reliability",
        "2026-01-03",
        "2026-01-10",
        None,
        "S2",
        1,
        ["reliability", "outage"],
        5,
    )
    add(
        2,
        "Data platform cve replay patch overdue",
        "Security",
        "Review",
        "Data Platform",
        "Liam Chen",
        "Data Reliability",
        "2026-01-05",
        "2026-01-12",
        None,
        "S1",
        1,
        ["security", "cve"],
        3,
        legacy_category="security",
    )
    add(
        3,
        "Infra latency alert boundary due",
        "Incident",
        "Backlog",
        "Infra Reliability",
        "Owen Hart",
        "Data Reliability",
        "2026-01-09",
        "2026-01-15",
        None,
        "S3",
        3,
        ["latency", "incident", "reliability"],
        3,
    )
    add(
        4,
        "Data reliability closed overdue incident",
        "Incident",
        "Closed",
        "Data Platform",
        "Liam Chen",
        "Data Reliability",
        "2025-12-28",
        "2026-01-04",
        "2026-01-05",
        "S2",
        2,
        ["incident", "reliability"],
        5,
        mirror_status="Closed",
    )
    add(
        5,
        "Infra security closed before due",
        "Security",
        "Verified",
        "Infra Reliability",
        "Avery Quinn",
        "Security Operations",
        "2026-01-02",
        "2026-01-20",
        "2026-01-14",
        "S2",
        2,
        ["security", "auth"],
        8,
        mirror_status="Done",
        legacy_category="security",
    )
    add(
        6,
        "Data platform reliability missing owner",
        "Reliability",
        "In Progress",
        "Data Platform",
        None,
        "Data Reliability",
        "2026-01-04",
        "2026-01-08",
        None,
        "S2",
        1,
        ["reliability", "flaky"],
        5,
    )
    add(
        7,
        "Infra encryption audit missing owner",
        "Compliance",
        "Review",
        "Infra Reliability",
        None,
        "Security Operations",
        "2026-01-06",
        "2026-01-25",
        None,
        "S3",
        3,
        ["security", "encryption"],
        3,
        legacy_category="security",
    )
    add(
        8,
        "Data latency guardrail not overdue",
        "Reliability",
        "In Progress",
        "Data Platform",
        "Liam Chen",
        "Data Reliability",
        "2026-01-12",
        "2026-01-28",
        None,
        "S3",
        3,
        ["reliability", "latency"],
        8,
    )
    add(
        9,
        "Infra duplicate outage ticket",
        "Bug",
        "Duplicate",
        "Infra Reliability",
        "Owen Hart",
        "Data Reliability",
        "2026-01-11",
        "2026-01-18",
        "2026-01-12",
        "S3",
        4,
        ["outage", "reliability"],
        1,
        duplicate_of="WI-24024-S001",
        mirror_status="Open",
    )
    add(
        10,
        "Data duplicate cve export",
        "Security",
        "Duplicate",
        "Data Platform",
        "Avery Quinn",
        "Security Operations",
        "2026-01-10",
        "2026-01-14",
        "2026-01-13",
        "S2",
        2,
        ["security", "cve", "stale-export"],
        1,
        duplicate_of="WI-24024-S002",
        mirror_status="Open",
        legacy_category="security",
    )

    # train_005: AppSec and Identity Services, as_of 2026-01-22, recent closed window 21 days.
    add(
        21,
        "AppSec cve exception overdue",
        "Security",
        "In Progress",
        "AppSec",
        "Priya Stone",
        "Security Operations",
        "2026-01-08",
        "2026-01-12",
        None,
        "S1",
        1,
        ["security", "cve"],
        5,
        legacy_category="security",
    )
    add(
        22,
        "Identity auth outage follow-up overdue",
        "Incident",
        "Review",
        "Identity Services",
        "Mina Shah",
        "Identity",
        "2026-01-06",
        "2026-01-16",
        None,
        "S2",
        1,
        ["auth", "outage", "reliability"],
        3,
    )
    add(
        23,
        "AppSec encryption evidence not overdue",
        "Compliance",
        "Backlog",
        "AppSec",
        "Priya Stone",
        "Security Operations",
        "2026-01-15",
        "2026-01-31",
        None,
        "S3",
        3,
        ["security", "encryption"],
        5,
        legacy_category="security",
    )
    add(
        24,
        "Identity reliability closed late",
        "Reliability",
        "Closed",
        "Identity Services",
        "Mina Shah",
        "Identity",
        "2026-01-01",
        "2026-01-10",
        "2026-01-18",
        "S2",
        2,
        ["reliability", "latency"],
        8,
        mirror_status="Closed",
    )
    add(
        25,
        "AppSec security closed before due",
        "Security",
        "Verified",
        "AppSec",
        "Avery Quinn",
        "Security Operations",
        "2026-01-03",
        "2026-01-24",
        "2026-01-19",
        "S2",
        2,
        ["security", "auth"],
        5,
        mirror_status="Done",
        legacy_category="security",
    )
    add(
        26,
        "Identity cve owner gap overdue",
        "Security",
        "In Progress",
        "Identity Services",
        None,
        "Identity",
        "2026-01-10",
        "2026-01-18",
        None,
        "S1",
        1,
        ["security", "cve", "auth"],
        5,
        legacy_category="security",
    )
    add(
        27,
        "AppSec flaky scanner reliability owner gap",
        "Reliability",
        "Review",
        "AppSec",
        None,
        "Security Operations",
        "2026-01-11",
        "2026-01-29",
        None,
        "S3",
        3,
        ["reliability", "flaky"],
        3,
    )
    add(
        28,
        "Identity encryption rotation due today",
        "Security",
        "In Progress",
        "Identity Services",
        "Mina Shah",
        "Identity",
        "2026-01-14",
        "2026-01-22",
        None,
        "S2",
        2,
        ["security", "encryption"],
        8,
        legacy_category="security",
    )
    add(
        29,
        "AppSec duplicate cve alert",
        "Security",
        "Duplicate",
        "AppSec",
        "Priya Stone",
        "Security Operations",
        "2026-01-18",
        "2026-01-21",
        "2026-01-20",
        "S1",
        1,
        ["security", "cve"],
        1,
        duplicate_of="WI-24024-S021",
        mirror_status="Open",
        legacy_category="security",
    )
    add(
        30,
        "Identity duplicate outage mirror",
        "Bug",
        "Duplicate",
        "Identity Services",
        "Mina Shah",
        "Identity",
        "2026-01-16",
        "2026-01-20",
        "2026-01-21",
        "S2",
        2,
        ["outage", "reliability", "stale-export"],
        1,
        duplicate_of="WI-24024-S022",
        mirror_status="Open",
    )

    # test_002: Core Services and Platform Core, as_of 2026-01-18, recent closed window 10 days.
    add(
        41,
        "Core runtime incident overdue",
        "Incident",
        "In Progress",
        "Core Services",
        "Devon Wells",
        "Core Runtime",
        "2026-01-07",
        "2026-01-11",
        None,
        "S2",
        1,
        ["incident", "reliability"],
        5,
    )
    add(
        42,
        "Platform auth cve overdue",
        "Security",
        "Review",
        "Platform Core",
        "Avery Quinn",
        "Atlas Backend",
        "2026-01-09",
        "2026-01-13",
        None,
        "S1",
        1,
        ["security", "auth", "cve"],
        3,
        legacy_category="security",
    )
    add(
        43,
        "Core latency repair not overdue",
        "Reliability",
        "Backlog",
        "Core Services",
        "Devon Wells",
        "Core Runtime",
        "2026-01-12",
        "2026-01-25",
        None,
        "S3",
        3,
        ["reliability", "latency"],
        8,
    )
    add(
        44,
        "Platform outage closed late",
        "Incident",
        "Closed",
        "Platform Core",
        "Nora Patel",
        "Atlas Backend",
        "2026-01-01",
        "2026-01-08",
        "2026-01-15",
        "S2",
        2,
        ["outage", "reliability"],
        5,
        mirror_status="Closed",
    )
    add(
        45,
        "Core security closed before due",
        "Security",
        "Verified",
        "Core Services",
        "Avery Quinn",
        "Core Runtime",
        "2026-01-05",
        "2026-01-21",
        "2026-01-17",
        "S2",
        2,
        ["security", "encryption"],
        5,
        mirror_status="Done",
        legacy_category="security",
    )
    add(
        46,
        "Platform reliability owner gap overdue",
        "Reliability",
        "In Progress",
        "Platform Core",
        None,
        "Atlas Backend",
        "2026-01-06",
        "2026-01-12",
        None,
        "S2",
        1,
        ["reliability", "flaky"],
        5,
    )
    add(
        47,
        "Core cve owner gap not overdue",
        "Security",
        "Review",
        "Core Services",
        None,
        "Core Runtime",
        "2026-01-14",
        "2026-01-28",
        None,
        "S3",
        3,
        ["security", "cve"],
        3,
        legacy_category="security",
    )
    add(
        48,
        "Platform latency boundary due",
        "Reliability",
        "In Progress",
        "Platform Core",
        "Nora Patel",
        "Atlas Backend",
        "2026-01-13",
        "2026-01-18",
        None,
        "S3",
        3,
        ["reliability", "latency"],
        8,
    )
    add(
        49,
        "Core duplicate incident export",
        "Bug",
        "Duplicate",
        "Core Services",
        "Devon Wells",
        "Core Runtime",
        "2026-01-13",
        "2026-01-17",
        "2026-01-16",
        "S3",
        4,
        ["incident", "reliability"],
        1,
        duplicate_of="WI-24024-S041",
        mirror_status="Open",
    )
    add(
        50,
        "Platform duplicate cve mirror",
        "Security",
        "Duplicate",
        "Platform Core",
        "Avery Quinn",
        "Atlas Backend",
        "2026-01-14",
        "2026-01-18",
        "2026-01-17",
        "S2",
        2,
        ["security", "cve", "stale-export"],
        1,
        duplicate_of="WI-24024-S042",
        mirror_status="Open",
        legacy_category="security",
    )

    # test_005: Edge Delivery, as_of 2026-01-25, recent closed window 14 days.
    add(
        61,
        "Edge routing outage overdue",
        "Incident",
        "In Progress",
        "Edge Delivery",
        "Elena Park",
        "Edge Routing",
        "2026-01-12",
        "2026-01-17",
        None,
        "S1",
        1,
        ["outage", "incident", "reliability"],
        5,
    )
    add(
        62,
        "Edge cve certificate patch overdue",
        "Security",
        "Review",
        "Edge Delivery",
        "Avery Quinn",
        "Edge Routing",
        "2026-01-14",
        "2026-01-20",
        None,
        "S2",
        1,
        ["security", "cve", "encryption"],
        3,
        legacy_category="security",
    )
    add(
        63,
        "Edge latency guardrail not overdue",
        "Reliability",
        "Backlog",
        "Edge Delivery",
        "Elena Park",
        "Edge Routing",
        "2026-01-18",
        "2026-02-02",
        None,
        "S3",
        3,
        ["reliability", "latency"],
        8,
    )
    add(
        64,
        "Edge reliability closed late",
        "Reliability",
        "Closed",
        "Edge Delivery",
        "Elena Park",
        "Edge Routing",
        "2026-01-05",
        "2026-01-12",
        "2026-01-18",
        "S2",
        2,
        ["reliability", "flaky"],
        5,
        mirror_status="Closed",
    )
    add(
        65,
        "Edge security closed before due",
        "Security",
        "Verified",
        "Edge Delivery",
        "Avery Quinn",
        "Edge Routing",
        "2026-01-08",
        "2026-01-28",
        "2026-01-23",
        "S2",
        2,
        ["security", "auth"],
        5,
        mirror_status="Done",
        legacy_category="security",
    )
    add(
        66,
        "Edge outage owner gap overdue",
        "Incident",
        "In Progress",
        "Edge Delivery",
        None,
        "Edge Routing",
        "2026-01-10",
        "2026-01-15",
        None,
        "S1",
        1,
        ["outage", "reliability"],
        5,
    )
    add(
        67,
        "Edge encryption owner gap not overdue",
        "Compliance",
        "Review",
        "Edge Delivery",
        None,
        "Edge Routing",
        "2026-01-16",
        "2026-02-05",
        None,
        "S3",
        3,
        ["security", "encryption"],
        3,
        legacy_category="security",
    )
    add(
        68,
        "Edge latency due today",
        "Reliability",
        "In Progress",
        "Edge Delivery",
        "Elena Park",
        "Edge Routing",
        "2026-01-19",
        "2026-01-25",
        None,
        "S3",
        3,
        ["reliability", "latency"],
        8,
    )
    add(
        69,
        "Edge duplicate outage export",
        "Bug",
        "Duplicate",
        "Edge Delivery",
        "Elena Park",
        "Edge Routing",
        "2026-01-20",
        "2026-01-23",
        "2026-01-22",
        "S3",
        4,
        ["outage", "reliability"],
        1,
        duplicate_of="WI-24024-S061",
        mirror_status="Open",
    )
    add(
        70,
        "Edge duplicate cve mirror",
        "Security",
        "Duplicate",
        "Edge Delivery",
        "Avery Quinn",
        "Edge Routing",
        "2026-01-20",
        "2026-01-24",
        "2026-01-24",
        "S2",
        2,
        ["security", "cve", "stale-export"],
        1,
        duplicate_of="WI-24024-S062",
        mirror_status="Open",
        legacy_category="security",
    )

    return rows


def insert_static_rows(conn):
    releases = [
        ("REL-ORION-2026-02", "Orion February portfolio train", "2026-02-20", "Orion"),
        ("REL-ZEPHYR-2026-03", "Zephyr March portfolio train", "2026-03-27", "Zephyr"),
        ("REL-NOVA-2025-12", "Nova December maintenance train", "2025-12-19", "Nova"),
    ]
    conn.executemany("INSERT INTO releases VALUES (?, ?, ?, ?)", releases)

    milestones = [
        ("MIL-ORION-BETA", "REL-ORION-2026-02", "Orion beta freeze", "Release Engineering"),
        ("MIL-ORION-HARDEN", "REL-ORION-2026-02", "Orion security and reliability hardening", "AppSec"),
        ("MIL-ORION-RC", "REL-ORION-2026-02", "Orion release candidate", "Edge Delivery"),
        ("MIL-ORION-GA", "REL-ORION-2026-02", "Orion general availability", "Release Engineering"),
        ("MIL-ZEPHYR-BETA", "REL-ZEPHYR-2026-03", "Zephyr beta freeze", "API Foundations"),
        ("MIL-ZEPHYR-HARDEN", "REL-ZEPHYR-2026-03", "Zephyr hardening checkpoint", "Data Platform"),
        ("MIL-ZEPHYR-RC", "REL-ZEPHYR-2026-03", "Zephyr release candidate", "Revenue Platform"),
        ("MIL-ZEPHYR-GA", "REL-ZEPHYR-2026-03", "Zephyr general availability", "Release Engineering"),
        ("MIL-NOVA-GA", "REL-NOVA-2025-12", "Nova maintenance availability", "Release Engineering"),
    ]
    conn.executemany("INSERT INTO milestones VALUES (?, ?, ?, ?)", milestones)

    sla = [("S1", 3), ("S2", 10), ("S3", 21), ("S4", 45)]
    conn.executemany("INSERT INTO sla_policy VALUES (?, ?)", sla)

    team_groups = {
        "Core Systems": ["Platform Core", "Core Services", "API Foundations"],
        "Trust": ["Identity Services", "AppSec", "Infra Reliability"],
        "Customer Revenue": ["Billing", "Revenue Platform", "Growth Experiences"],
        "Delivery": ["Release Engineering", "Edge Delivery", "Mobile Client"],
        "Data": ["Data Platform", "Observability", "Integrations"],
    }
    rows = []
    rng = random.Random(SEED + 99)
    for quarter in QUARTERS:
        for group in team_groups:
            for area in rng.sample(PRODUCT_AREAS, 5):
                security = round(rng.uniform(0.08, 0.22), 2)
                reliability = round(rng.uniform(0.14, 0.28), 2)
                tech_debt = round(rng.uniform(0.18, 0.32), 2)
                new_feature = round(max(0.15, 1.0 - security - reliability - tech_debt), 2)
                scope_id = f"{quarter}:{group}:{area}".replace(" ", "-").upper()
                rows.append((scope_id, quarter, group, area, new_feature, tech_debt, reliability, security))
    rows.extend(
        [
            (
                "train_001",
                "2025-Q4",
                "Platform Core + Identity Services",
                "Atlas Backend + Identity",
                0.34,
                0.24,
                0.22,
                0.20,
            ),
            ("train_004", "2025-Q4", "Mobile Client + Growth Experiences", "Checkout", 0.42, 0.20, 0.24, 0.14),
            ("test_001", "2025-Q4", "Data Platform + Observability", "Data Reliability", 0.30, 0.26, 0.28, 0.16),
            (
                "test_004",
                "2025-Q4",
                "Integrations + Billing + API Foundations + Revenue Platform",
                "API Connectivity + Revenue Systems",
                0.36,
                0.22,
                0.20,
                0.22,
            ),
        ]
    )
    conn.executemany("INSERT INTO mix_targets VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)


def insert_work_items(conn):
    rng = random.Random(SEED)
    rows = fixture_items()
    used_ids = {row[0] for row in rows}
    title_actions = [
        "stabilize",
        "rollout",
        "cleanup",
        "refactor",
        "migrate",
        "harden",
        "audit",
        "repair",
        "extend",
        "deprecate",
    ]
    title_subjects = [
        "auth session cache",
        "checkout adapter",
        "edge routing policy",
        "billing ledger writer",
        "mobile telemetry batch",
        "atlas backend queue",
        "api gateway contract",
        "release train dashboard",
        "observability alert",
        "data replay worker",
        "identity consent record",
        "core runtime scheduler",
    ]
    title_signals = [
        "security",
        "cve",
        "auth",
        "encryption",
        "reliability",
        "incident",
        "outage",
        "latency",
        "flaky",
        "refactor",
        "migration",
        "cleanup",
        "feature",
        "rollout",
    ]
    owners = [
        "Avery Quinn",
        "Mina Shah",
        "Owen Hart",
        "Nora Patel",
        "Liam Chen",
        "Sofia Reyes",
        "Theo Brooks",
        "Priya Stone",
        "Jon Bell",
        "Mara Singh",
        "Cass Morgan",
        "Elena Park",
        "Devon Wells",
    ]
    release_milestones = {
        "REL-ORION-2026-02": ["MIL-ORION-BETA", "MIL-ORION-HARDEN", "MIL-ORION-RC", "MIL-ORION-GA"],
        "REL-ZEPHYR-2026-03": ["MIL-ZEPHYR-BETA", "MIL-ZEPHYR-HARDEN", "MIL-ZEPHYR-RC", "MIL-ZEPHYR-GA"],
        "REL-NOVA-2025-12": ["MIL-NOVA-GA"],
    }

    start = date(2025, 7, 1)
    end = date(2026, 3, 31)
    total_days = (end - start).days

    for i in range(19, 156):
        item_id = f"WI-24024-{i:03d}"
        while item_id in used_ids:
            i += 1
            item_id = f"WI-24024-{i:03d}"
        used_ids.add(item_id)
        created = start + timedelta(days=rng.randint(0, total_days))
        work_type = rng.choices(
            WORK_TYPES,
            weights=[17, 14, 14, 7, 9, 11, 9, 5, 8, 6],
            k=1,
        )[0]
        signal = rng.choice(title_signals)
        action = rng.choice(title_actions)
        subject = rng.choice(title_subjects)
        title_tokens = [signal]
        title = f"{action.title()} {signal} {subject}"
        status = rng.choices(STATUSES, weights=[8, 12, 10, 16, 11, 12, 11, 4, 4, 2], k=1)[0]
        severity = rng.choices(SEVERITIES, weights=[10, 28, 42, 20], k=1)[0]
        labels = make_labels(rng, work_type, title_tokens)
        due = created + timedelta(days=rng.randint(4, 55))
        closed = None
        if status in CLOSED_STATUSES:
            closed = created + timedelta(days=rng.randint(2, 70))
            if closed > end + timedelta(days=12):
                closed = None
                status = rng.choice(["In Progress", "Review", "Reopened"])
        release_id = choose_release(rng, due, labels)
        milestone_id = rng.choice(release_milestones[release_id]) if release_id else None
        duplicate_of = None
        if rng.random() < 0.08 and rows:
            duplicate_of = rng.choice(rows)[0]
            status = "Duplicate"
            closed = created + timedelta(days=rng.randint(1, 15))
        owner = None if rng.random() < 0.09 else rng.choice(owners)
        mirror_status = rng.choice(["Open", "In Progress", "Done", "Closed", "Complete", "Blocked"])
        legacy_category = rng.choice(["new", "bug", "maintenance", "security", "tech-debt", "quality", "admin"])
        rows.append(
            (
                item_id,
                title,
                work_type,
                status,
                rng.choice(TEAMS),
                owner,
                rng.choice(PRODUCT_AREAS),
                iso(created),
                iso(due),
                iso(closed),
                severity,
                rng.randint(1, 5),
                labels,
                rng.choice([1, 2, 3, 5, 8, 13]),
                release_id,
                milestone_id,
                duplicate_of,
                mirror_status,
                legacy_category,
            )
        )

    conn.executemany(
        """
        INSERT INTO work_items (
            id, title, work_type, status, team, owner, product_area, created_at,
            due_at, closed_at, severity, priority, labels, story_points,
            release_id, milestone_id, duplicate_of, mirror_status, legacy_category
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                row[5],
                row[6],
                row[7],
                row[8],
                row[9],
                row[10],
                row[11],
                json.dumps(row[12], separators=(",", ":")),
                row[13],
                row[14],
                row[15],
                row[16],
                row[17],
                row[18],
            )
            for row in rows
        ],
    )
    return rows


def insert_dependencies_and_blockers(conn, work_rows):
    rng = random.Random(SEED + 7)
    dependencies = [
        ("WI-24024-010", "WI-24024-009", "blocks-release-readiness"),
        ("WI-24024-012", "WI-24024-001", "security-review-required"),
        ("WI-24024-014", "WI-24024-013", "implementation-dependency"),
        ("WI-24024-017", "WI-24024-015", "audit-evidence-required"),
    ]
    release_items = [row for row in work_rows if row[14]]
    for row in rng.sample(release_items, min(28, len(release_items))):
        candidate = rng.choice(work_rows)
        if row[0] != candidate[0]:
            dependencies.append(
                (row[0], candidate[0], rng.choice(["depends-on", "blocks-release-readiness", "validation-required"]))
            )
    conn.executemany("INSERT INTO dependencies VALUES (?, ?, ?)", dependencies)

    blockers = [
        (
            "BLK-24024-001",
            "WI-24024-010",
            "REL-ORION-2026-02",
            "High",
            "open reliability rehearsal gap",
            "Open",
            "2026-02-06",
            None,
        ),
        (
            "BLK-24024-002",
            "WI-24024-012",
            "REL-ORION-2026-02",
            "Critical",
            "unresolved cve exception",
            "Open",
            "2026-02-08",
            None,
        ),
        (
            "BLK-24024-003",
            "WI-24024-017",
            "REL-ZEPHYR-2026-03",
            "High",
            "missing encryption audit evidence",
            "Open",
            "2026-03-03",
            None,
        ),
        (
            "BLK-24024-004",
            "WI-24024-015",
            "REL-ZEPHYR-2026-03",
            "Medium",
            "latency guardrail verification",
            "Resolved",
            "2026-03-01",
            "2026-03-04",
        ),
        (
            "BLK-24024-005",
            "WI-24024-018",
            "REL-NOVA-2025-12",
            "Low",
            "late cleanup report signoff",
            "Resolved",
            "2025-12-16",
            "2025-12-18",
        ),
    ]
    for idx, row in enumerate(rng.sample(release_items, min(18, len(release_items))), start=6):
        opened = datetime.strptime(row[7], "%Y-%m-%d").date() + timedelta(days=rng.randint(8, 45))
        status = rng.choices(["Open", "Resolved", "Monitoring"], weights=[3, 6, 2], k=1)[0]
        resolved = None if status != "Resolved" else opened + timedelta(days=rng.randint(1, 12))
        blockers.append(
            (
                f"BLK-24024-{idx:03d}",
                row[0],
                row[14],
                rng.choice(["Low", "Medium", "High"]),
                rng.choice(
                    [
                        "owner unavailable",
                        "dependency validation late",
                        "contract review pending",
                        "customer escalation review",
                        "release note evidence gap",
                    ]
                ),
                status,
                iso(opened),
                iso(resolved),
            )
        )
    conn.executemany("INSERT INTO blockers VALUES (?, ?, ?, ?, ?, ?, ?, ?)", blockers)


def table_counts(conn):
    tables = ["work_items", "mix_targets", "sla_policy", "releases", "milestones", "dependencies", "blockers"]
    return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    try:
        create_schema(conn)
        insert_static_rows(conn)
        work_rows = insert_work_items(conn)
        insert_dependencies_and_blockers(conn, work_rows)
        conn.commit()
        counts = table_counts(conn)
    finally:
        conn.close()

    manifest = {
        "seed": SEED,
        "generated_at": GENERATED_AT,
        "files": ["portfolio.db", "data_manifest.json"],
        "row_counts": counts,
        "injected_scope_ids": [
            "train_001",
            "train_002",
            "train_004",
            "train_005",
            "test_001",
            "test_002",
            "test_004",
            "test_005",
            "portfolio-mix-2025-q3",
            "portfolio-mix-2025-q4",
            "portfolio-mix-2026-q1",
            "sla-open-and-recently-closed",
            "duplicates-and-missing-owners",
            "release-readiness-orion",
            "release-readiness-zephyr",
        ],
        "available_releases": ["REL-ORION-2026-02", "REL-ZEPHYR-2026-03", "REL-NOVA-2025-12"],
        "endpoint_count": 13,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "database": str(DB_PATH), "row_counts": counts}, sort_keys=True))


if __name__ == "__main__":
    main()
