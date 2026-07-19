#!/usr/bin/env python3
"""Generate deterministic Investigation Review Hub data."""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
from pathlib import Path


SEED = 17017
SERVICE_NAME = "investigation_review_hub"
STATE_MODE = "read_only"
CONTAINER_DB_PATH = "/app/data/review_hub.db"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "review_hub.db"
MANIFEST_PATH = DATA_DIR / "manifest.json"
JUDGE_DATA_PATH = DATA_DIR / "judge_data.json"

ENDPOINTS = [
    "GET /health",
    "GET /",
    "GET /api/schema",
    "GET /api/matters",
    "GET /api/subpoena-categories",
    "GET /api/productions",
    "GET /api/custodian-sources",
    "GET /api/documents/search",
    "GET /api/privilege-log",
    "GET /api/qc-findings",
    "GET /api/retention-events",
    "GET /api/remediation-actions",
    "POST /api/query",
    "POST /api/judge",
    "POST /admin/reset",
]

PRIMARY_MATTERS = [
    {
        "matter_id": "MTR-SENTINEL-GJ",
        "task_id": "train_001",
        "name": "Sentinel Motors grand jury subpoena review",
        "agency": "DOJ Antitrust Division",
        "investigation_type": "grand_jury_subpoena",
        "issued_date": "2025-01-27",
        "hold_date": "2025-01-27",
        "lead_partner": "Rachel Kim",
        "description": "Vehicle-safety dealer complaint and board oversight production review.",
        "status": "active_review",
    },
    {
        "matter_id": "MTR-HARBORSTONE-GJ",
        "task_id": "train_002",
        "name": "Harborstone Chemicals grand jury subpoena review",
        "agency": "DOJ Environmental Crimes Section",
        "investigation_type": "grand_jury_subpoena",
        "issued_date": "2024-11-14",
        "hold_date": "2024-11-14",
        "lead_partner": "Devon Bell",
        "description": "Environmental, lab, and audit-retention review for production deficiency assessment.",
        "status": "active_review",
    },
    {
        "matter_id": "MTR-GRAYCLIFF-SEC",
        "task_id": "train_003",
        "name": "Graycliff Capital SEC review",
        "agency": "SEC Enforcement",
        "investigation_type": "sec_subpoena",
        "issued_date": "2023-10-12",
        "hold_date": "2023-10-12",
        "lead_partner": "Maya Desai",
        "description": "Valuation, privilege, and collection-gap review for fund disclosure investigation.",
        "status": "active_review",
    },
    {
        "matter_id": "MTR-NORTHBAY-SEC",
        "task_id": "train_004",
        "name": "Northbay Therapeutics SEC review",
        "agency": "SEC Enforcement",
        "investigation_type": "sec_subpoena",
        "issued_date": "2024-03-18",
        "hold_date": "2024-03-18",
        "lead_partner": "Owen Pierce",
        "description": "Clinical-trial risk and privilege quality-control review.",
        "status": "active_review",
    },
    {
        "matter_id": "MTR-ALLOYWORKS-GJ",
        "task_id": "train_005",
        "name": "AlloyWorks procurement grand jury review",
        "agency": "DOJ Antitrust Division",
        "investigation_type": "grand_jury_subpoena",
        "issued_date": "2024-08-20",
        "hold_date": "2024-08-20",
        "lead_partner": "Hannah Ruiz",
        "description": "Bid files, personal messaging, and zero-production claim review.",
        "status": "active_review",
    },
    {
        "matter_id": "MTR-MERIDIAN-GJ",
        "task_id": "test_001",
        "name": "Meridian Autos grand jury subpoena review",
        "agency": "DOJ Antitrust Division",
        "investigation_type": "grand_jury_subpoena",
        "issued_date": "2025-03-17",
        "hold_date": "2025-03-17",
        "lead_partner": "Rachel Kim",
        "description": "Dealer safety escalation, board portal, and privilege log production review.",
        "status": "active_review",
    },
    {
        "matter_id": "MTR-PORTOLA-GJ",
        "task_id": "test_002",
        "name": "Portola Energy trading grand jury review",
        "agency": "DOJ Fraud Section",
        "investigation_type": "grand_jury_subpoena",
        "issued_date": "2025-01-09",
        "hold_date": "2025-01-09",
        "lead_partner": "Devon Bell",
        "description": "Trading blotter, chat, voice, and surveillance-retention review.",
        "status": "active_review",
    },
    {
        "matter_id": "MTR-BRIARGATE-SEC",
        "task_id": "test_003",
        "name": "Briargate Advisors SEC review",
        "agency": "SEC Enforcement",
        "investigation_type": "sec_subpoena",
        "issued_date": "2024-02-21",
        "hold_date": "2024-02-21",
        "lead_partner": "Maya Desai",
        "description": "Private-fund valuation, file loss, and privilege-waiver review.",
        "status": "active_review",
    },
    {
        "matter_id": "MTR-COBALTRIDGE-GJ",
        "task_id": "test_004",
        "name": "Cobalt Ridge M&A grand jury review",
        "agency": "DOJ Antitrust Division",
        "investigation_type": "grand_jury_subpoena",
        "issued_date": "2024-09-30",
        "hold_date": "2024-09-30",
        "lead_partner": "Hannah Ruiz",
        "description": "Side-channel banker communications, personal sources, and privilege production review.",
        "status": "active_review",
    },
    {
        "matter_id": "MTR-VIREO-SEC",
        "task_id": "test_005",
        "name": "Vireo Diagnostics SEC review",
        "agency": "SEC Enforcement",
        "investigation_type": "sec_subpoena",
        "issued_date": "2025-02-03",
        "hold_date": "2025-02-03",
        "lead_partner": "Owen Pierce",
        "description": "Lab-results, investor complaint, personal device, archive, and privilege review.",
        "status": "active_review",
    },
]

DISTRACTOR_MATTERS = [
    {
        "matter_id": "MTR-IRONPEAK-SEC",
        "name": "IronPeak Energy SEC review",
        "agency": "SEC Enforcement",
        "investigation_type": "sec_subpoena",
        "issued_date": "2024-05-10",
        "hold_date": "2024-05-10",
        "lead_partner": "Leah Chen",
        "description": "Revenue-recognition and board-material production review.",
        "status": "closed_monitoring",
    },
    {
        "matter_id": "MTR-LAKEFRONT-GJ",
        "name": "Lakefront Devices grand jury review",
        "agency": "DOJ Antitrust Division",
        "investigation_type": "grand_jury_subpoena",
        "issued_date": "2025-04-02",
        "hold_date": "2025-04-02",
        "lead_partner": "Rachel Kim",
        "description": "Dealer incentive, mobile-source, and privilege-log review.",
        "status": "active_review",
    },
    {
        "matter_id": "MTR-PINEVALE-SEC",
        "name": "Pinevale Biologics SEC review",
        "agency": "SEC Enforcement",
        "investigation_type": "sec_subpoena",
        "issued_date": "2024-12-12",
        "hold_date": "2024-12-12",
        "lead_partner": "Owen Pierce",
        "description": "Clinical disclosure and retention exception review.",
        "status": "active_review",
    },
    {
        "matter_id": "MTR-SILVERYARD-GJ",
        "name": "Silveryard Industrials grand jury review",
        "agency": "DOJ Fraud Section",
        "investigation_type": "grand_jury_subpoena",
        "issued_date": "2023-09-19",
        "hold_date": "2023-09-19",
        "lead_partner": "Devon Bell",
        "description": "Bid-channel and voice-retention review with no escalated defects.",
        "status": "closed_monitoring",
    },
    {
        "matter_id": "MTR-OAKHARBOR-SEC",
        "name": "Oak Harbor Advisors SEC review",
        "agency": "SEC Enforcement",
        "investigation_type": "sec_subpoena",
        "issued_date": "2025-01-24",
        "hold_date": "2025-01-24",
        "lead_partner": "Maya Desai",
        "description": "Valuation support and outside-adviser privilege review.",
        "status": "active_review",
    },
    {
        "matter_id": "MTR-RIVERBEND-GJ",
        "name": "Riverbend Trading grand jury review",
        "agency": "DOJ Fraud Section",
        "investigation_type": "grand_jury_subpoena",
        "issued_date": "2024-07-15",
        "hold_date": "2024-07-15",
        "lead_partner": "Hannah Ruiz",
        "description": "Chat-retention and surveillance archive production review.",
        "status": "active_review",
    },
]

CATEGORY_CODES = {
    "MTR-SENTINEL-GJ": [f"R{i:02d}" for i in range(1, 16)],
    "MTR-HARBORSTONE-GJ": list("ABCDEFGHI"),
    "MTR-GRAYCLIFF-SEC": [f"SEC-{i}" for i in range(1, 6)],
    "MTR-NORTHBAY-SEC": [f"SEC-{c}" for c in "ABCDE"],
    "MTR-ALLOYWORKS-GJ": list("ABCDEF"),
    "MTR-MERIDIAN-GJ": [f"MD-{i:02d}" for i in range(1, 16)],
    "MTR-PORTOLA-GJ": [f"PE-{c}" for c in "ABCDEFGHI"],
    "MTR-BRIARGATE-SEC": [f"SEC-{c}" for c in "ABCDE"],
    "MTR-COBALTRIDGE-GJ": [f"CR-{i:02d}" for i in range(1, 16)],
    "MTR-VIREO-SEC": [f"VL-{c}" for c in "ABCDEFGHIJ"],
    "MTR-IRONPEAK-SEC": [f"IP-{c}" for c in "ABCDEFG"],
    "MTR-LAKEFRONT-GJ": [f"LF-{i:02d}" for i in range(1, 11)],
    "MTR-PINEVALE-SEC": [f"PV-{c}" for c in "ABCDEF"],
    "MTR-SILVERYARD-GJ": [f"SY-{c}" for c in "ABCDEFG"],
    "MTR-OAKHARBOR-SEC": [f"OH-{c}" for c in "ABCDEF"],
    "MTR-RIVERBEND-GJ": [f"RB-{c}" for c in "ABCDEFGH"],
}

SPECIAL_CATEGORY_TITLES = {
    ("MTR-SENTINEL-GJ", "R09"): "Dealer complaints and safety escalations",
    ("MTR-SENTINEL-GJ", "R11"): "Legal hold and privilege communications",
    ("MTR-SENTINEL-GJ", "R15"): "Mobile messaging and personal device communications",
    ("MTR-HARBORSTONE-GJ", "B"): "Historical lab test data",
    ("MTR-HARBORSTONE-GJ", "D"): "Employee EHS communications",
    ("MTR-HARBORSTONE-GJ", "E"): "Internal audits and Calverley review materials",
    ("MTR-GRAYCLIFF-SEC", "SEC-1"): "Valuation model source communications",
    ("MTR-GRAYCLIFF-SEC", "SEC-2"): "Shared drive valuation support files",
    ("MTR-GRAYCLIFF-SEC", "SEC-3"): "Investor disclosure drafts",
    ("MTR-GRAYCLIFF-SEC", "SEC-4"): "Custodian device data",
    ("MTR-NORTHBAY-SEC", "SEC-C"): "Clinical risk and trial-update disclosures",
    ("MTR-ALLOYWORKS-GJ", "F"): "Bid communications and competing quote support",
    ("MTR-MERIDIAN-GJ", "MD-09"): "Dealer safety complaints and escalations",
    ("MTR-MERIDIAN-GJ", "MD-15"): "Mobile messaging and personal devices",
    ("MTR-PORTOLA-GJ", "PE-D"): "Deal chat and voice communications",
    ("MTR-PORTOLA-GJ", "PE-E"): "Trading attachments and archive exports",
    ("MTR-BRIARGATE-SEC", "SEC-A"): "Valuation communications and source files",
    ("MTR-BRIARGATE-SEC", "SEC-C"): "Investor disclosure drafts",
    ("MTR-COBALTRIDGE-GJ", "CR-06"): "Banker side-channel deal communications",
    ("MTR-COBALTRIDGE-GJ", "CR-15"): "Personal communications and mobile devices",
    ("MTR-VIREO-SEC", "VL-I"): "Investor results complaints",
    ("MTR-VIREO-SEC", "VL-H"): "QA audit and lab-results retention",
}

NOISE_TITLES = [
    "ordinary status update",
    "collection exception note",
    "privilege review handoff",
    "production batch reconciliation",
    "custodian interview follow-up",
    "source map validation",
    "board deck excerpt",
    "responsive family exception",
    "vendor load-file issue",
    "duplicate family overlay",
]


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS matters;
        DROP TABLE IF EXISTS subpoena_categories;
        DROP TABLE IF EXISTS production_stats;
        DROP TABLE IF EXISTS custodian_sources;
        DROP TABLE IF EXISTS review_documents;
        DROP TABLE IF EXISTS privilege_entries;
        DROP TABLE IF EXISTS qc_findings;
        DROP TABLE IF EXISTS retention_events;
        DROP TABLE IF EXISTS remediation_actions;

        CREATE TABLE matters (
            matter_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            agency TEXT NOT NULL,
            investigation_type TEXT NOT NULL,
            issued_date TEXT NOT NULL,
            hold_date TEXT NOT NULL,
            lead_partner TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL
        );

        CREATE TABLE subpoena_categories (
            matter_id TEXT NOT NULL,
            category_code TEXT NOT NULL,
            title TEXT NOT NULL,
            date_start TEXT,
            date_end TEXT,
            request_text TEXT NOT NULL,
            topic_tags TEXT NOT NULL,
            PRIMARY KEY (matter_id, category_code)
        );

        CREATE TABLE production_stats (
            matter_id TEXT NOT NULL,
            batch_id TEXT NOT NULL,
            batch_date TEXT NOT NULL,
            category_code TEXT NOT NULL,
            produced_count INTEGER NOT NULL,
            withheld_count INTEGER NOT NULL,
            responsive_count INTEGER NOT NULL,
            nonresponsive_count INTEGER NOT NULL,
            status TEXT NOT NULL,
            zero_claim_reason TEXT,
            notes TEXT NOT NULL,
            PRIMARY KEY (matter_id, batch_id, category_code)
        );

        CREATE TABLE custodian_sources (
            source_id TEXT PRIMARY KEY,
            matter_id TEXT NOT NULL,
            custodian_name TEXT NOT NULL,
            role TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_label TEXT NOT NULL,
            status TEXT NOT NULL,
            event_date TEXT,
            post_hold INTEGER NOT NULL,
            category_impacts TEXT NOT NULL,
            issue_tags TEXT NOT NULL,
            notes TEXT NOT NULL
        );

        CREATE TABLE review_documents (
            doc_id TEXT PRIMARY KEY,
            matter_id TEXT NOT NULL,
            title TEXT NOT NULL,
            doc_date TEXT NOT NULL,
            custodian_name TEXT NOT NULL,
            source_system TEXT NOT NULL,
            category_code TEXT NOT NULL,
            responsiveness TEXT NOT NULL,
            privilege_status TEXT NOT NULL,
            produced_status TEXT NOT NULL,
            issue_tags TEXT NOT NULL,
            summary TEXT NOT NULL
        );

        CREATE TABLE privilege_entries (
            entry_id TEXT PRIMARY KEY,
            matter_id TEXT NOT NULL,
            category_code TEXT NOT NULL,
            custodian_name TEXT NOT NULL,
            doc_count INTEGER NOT NULL,
            withheld_count INTEGER NOT NULL,
            logged_count INTEGER NOT NULL,
            issue_type TEXT NOT NULL,
            third_party INTEGER NOT NULL,
            notes TEXT NOT NULL
        );

        CREATE TABLE qc_findings (
            finding_id TEXT PRIMARY KEY,
            matter_id TEXT NOT NULL,
            batch_id TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            doc_count INTEGER NOT NULL,
            affected_category TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            severity TEXT NOT NULL,
            notes TEXT NOT NULL
        );

        CREATE TABLE retention_events (
            event_id TEXT PRIMARY KEY,
            matter_id TEXT NOT NULL,
            record_type TEXT NOT NULL,
            event_date TEXT NOT NULL,
            hold_date TEXT NOT NULL,
            policy_section TEXT NOT NULL,
            retention_period_months INTEGER NOT NULL,
            volume_count INTEGER NOT NULL,
            volume_unit TEXT NOT NULL,
            status TEXT NOT NULL,
            affected_categories TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            notes TEXT NOT NULL
        );

        CREATE TABLE remediation_actions (
            action_id TEXT PRIMARY KEY,
            matter_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            priority TEXT NOT NULL,
            severity TEXT NOT NULL,
            owner TEXT NOT NULL,
            target_ref TEXT NOT NULL,
            due_days INTEGER NOT NULL,
            description TEXT NOT NULL
        );

        CREATE INDEX idx_categories_matter ON subpoena_categories(matter_id);
        CREATE INDEX idx_production_matter_category ON production_stats(matter_id, category_code);
        CREATE INDEX idx_sources_matter_status ON custodian_sources(matter_id, status);
        CREATE INDEX idx_docs_matter_category ON review_documents(matter_id, category_code);
        CREATE INDEX idx_priv_matter_issue ON privilege_entries(matter_id, issue_type);
        CREATE INDEX idx_qc_matter_issue ON qc_findings(matter_id, issue_type);
        CREATE INDEX idx_ret_matter_status ON retention_events(matter_id, status);
        CREATE INDEX idx_rem_matter_priority ON remediation_actions(matter_id, priority);
        """
    )


def insert(conn: sqlite3.Connection, table: str, row: dict) -> None:
    columns = list(row)
    placeholders = ",".join("?" for _ in columns)
    conn.execute(
        f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})",
        [row[column] for column in columns],
    )


def as_csv(items: list[str] | tuple[str, ...] | str) -> str:
    if isinstance(items, str):
        return items
    return ",".join(items)


def track(injected: dict[str, list[str]], matter_id: str, record_id: str) -> None:
    injected.setdefault(matter_id, []).append(record_id)


def slug(matter_id: str) -> str:
    return matter_id.replace("MTR-", "").replace("-", "")[:10]


def category_title(matter_id: str, code: str) -> str:
    if (matter_id, code) in SPECIAL_CATEGORY_TITLES:
        return SPECIAL_CATEGORY_TITLES[(matter_id, code)]
    return f"{code} investigation request materials"


def generate_matters(conn: sqlite3.Connection) -> None:
    for matter in PRIMARY_MATTERS + DISTRACTOR_MATTERS:
        row = {
            key: matter[key]
            for key in (
                "matter_id",
                "name",
                "agency",
                "investigation_type",
                "issued_date",
                "hold_date",
                "lead_partner",
                "description",
                "status",
            )
        }
        insert(conn, "matters", row)


def generate_categories(conn: sqlite3.Connection, rng: random.Random) -> None:
    topic_pool = [
        "pricing",
        "dealer",
        "safety",
        "valuation",
        "audit",
        "retention",
        "mobile",
        "board",
        "privilege",
        "clinical",
        "lab",
        "trading",
        "chat",
        "bid",
        "investor",
    ]
    for matter_id, codes in CATEGORY_CODES.items():
        for idx, code in enumerate(codes, start=1):
            tags = [rng.choice(topic_pool), rng.choice(topic_pool)]
            title = category_title(matter_id, code)
            if "Dealer" in title or "dealer" in title:
                tags = ["dealer", "safety", "complaint"]
            elif "Mobile" in title or "Personal" in title or "personal" in title:
                tags = ["mobile", "personal_sources", "collection_gap"]
            elif "Valuation" in title or "valuation" in title:
                tags = ["valuation", "model", "investor"]
            elif "audit" in title.lower() or "retention" in title.lower():
                tags = ["retention", "audit", "policy"]
            insert(
                conn,
                "subpoena_categories",
                {
                    "matter_id": matter_id,
                    "category_code": code,
                    "title": title,
                    "date_start": f"{2020 + (idx % 4)}-01-01",
                    "date_end": f"{2025 if idx % 3 else 2024}-12-31",
                    "request_text": (
                        f"Produce communications, records, drafts, attachments, and source materials "
                        f"concerning {title.lower()} for matter {matter_id}."
                    ),
                    "topic_tags": as_csv(sorted(set(tags))),
                },
            )


def generate_productions(conn: sqlite3.Connection, rng: random.Random) -> None:
    zero_claims = {
        ("MTR-ALLOYWORKS-GJ", "F"): (
            "BATCH-ALLOY-004",
            "No responsive bid communications located in collected custodial mail.",
            "zero_claim_contradicted",
        ),
        ("MTR-COBALTRIDGE-GJ", "CR-06"): (
            "BATCH-COBALT-003",
            "No responsive side-channel banker communications found.",
            "zero_claim_contradicted",
        ),
    }
    for matter_id, codes in CATEGORY_CODES.items():
        matter_slug = slug(matter_id)
        for idx, code in enumerate(codes, start=1):
            if (matter_id, code) in zero_claims:
                batch_id, reason, status = zero_claims[(matter_id, code)]
                insert(
                    conn,
                    "production_stats",
                    {
                        "matter_id": matter_id,
                        "batch_id": batch_id,
                        "batch_date": "2025-04-11",
                        "category_code": code,
                        "produced_count": 0,
                        "withheld_count": 0,
                        "responsive_count": 0,
                        "nonresponsive_count": rng.randint(70, 180),
                        "status": status,
                        "zero_claim_reason": reason,
                        "notes": "Zero-production certification has open QC exceptions tied to miscoded documents.",
                    },
                )
                continue
            produced = rng.randint(25, 480)
            withheld = rng.randint(0, 80)
            responsive = produced + withheld + rng.randint(0, 25)
            nonresponsive = rng.randint(15, 350)
            status = rng.choice(["produced", "supplement_pending", "rolling_review", "closed"])
            insert(
                conn,
                "production_stats",
                {
                    "matter_id": matter_id,
                    "batch_id": f"BATCH-{matter_slug}-{idx:03d}",
                    "batch_date": f"2025-{(idx % 9) + 1:02d}-{(idx * 3 % 27) + 1:02d}",
                    "category_code": code,
                    "produced_count": produced,
                    "withheld_count": withheld,
                    "responsive_count": responsive,
                    "nonresponsive_count": nonresponsive,
                    "status": status,
                    "zero_claim_reason": "",
                    "notes": rng.choice(
                        [
                            "Includes family-level deduplication adjustments.",
                            "Counts exclude documents pending privilege re-review.",
                            "Batch uses corrected responsiveness overlay.",
                            "Vendor reconciliation complete with minor metadata gaps.",
                        ]
                    ),
                },
            )


def add_source(
    conn: sqlite3.Connection,
    injected: dict[str, list[str]],
    *,
    source_id: str,
    matter_id: str,
    custodian_name: str,
    role: str,
    source_type: str,
    source_label: str,
    status: str,
    event_date: str,
    post_hold: int,
    category_impacts: list[str] | str,
    issue_tags: list[str] | str,
    notes: str,
    is_injected: bool = True,
) -> None:
    insert(
        conn,
        "custodian_sources",
        {
            "source_id": source_id,
            "matter_id": matter_id,
            "custodian_name": custodian_name,
            "role": role,
            "source_type": source_type,
            "source_label": source_label,
            "status": status,
            "event_date": event_date,
            "post_hold": post_hold,
            "category_impacts": as_csv(category_impacts),
            "issue_tags": as_csv(issue_tags),
            "notes": notes,
        },
    )
    if is_injected:
        track(injected, matter_id, source_id)


def generate_key_sources(conn: sqlite3.Connection, injected: dict[str, list[str]]) -> None:
    add_source(
        conn,
        injected,
        source_id="SRC-SENT-ALDEN-PHONE",
        matter_id="MTR-SENTINEL-GJ",
        custodian_name="Nora Alden",
        role="Vice President, Dealer Network",
        source_type="personal_phone",
        source_label="Nora Alden personal iPhone",
        status="lost",
        event_date="2025-02-04",
        post_hold=1,
        category_impacts=["R15", "R09"],
        issue_tags=["post_subpoena_erasure", "personal_device", "collection_gap"],
        notes="Personal iPhone erased on 2025-02-04 after subpoena issuance on 2025-01-27.",
    )
    add_source(
        conn,
        injected,
        source_id="SRC-SENT-BOARD-SP",
        matter_id="MTR-SENTINEL-GJ",
        custodian_name="Board Secretary Office",
        role="Board operations",
        source_type="sharepoint_site",
        source_label="SharePoint board site",
        status="not_collected",
        event_date="2025-02-12",
        post_hold=1,
        category_impacts=["R07", "R08", "R09"],
        issue_tags=["board_materials", "collection_gap"],
        notes="Board SharePoint site was scoped but not collected in the first two rolling productions.",
    )
    add_source(
        conn,
        injected,
        source_id="SRC-HARB-IRONVAULT",
        matter_id="MTR-HARBORSTONE-GJ",
        custodian_name="Archive Operations",
        role="Enterprise records",
        source_type="email_archive",
        source_label="IronVault archive",
        status="available",
        event_date="2025-01-09",
        post_hold=1,
        category_impacts=["D", "E"],
        issue_tags=["archive_available", "remediation_source"],
        notes="Email archive retains seven years and is available for EHS communications and audit materials.",
    )
    add_source(
        conn,
        injected,
        source_id="SRC-GRAY-HALE-LAPTOP",
        matter_id="MTR-GRAYCLIFF-SEC",
        custodian_name="Marcus Hale",
        role="Portfolio manager",
        source_type="laptop",
        source_label="Marcus Hale laptop",
        status="lost",
        event_date="2023-12-01",
        post_hold=1,
        category_impacts=["SEC-1", "SEC-4"],
        issue_tags=["post_hold_wipe", "valuation_source_gap"],
        notes="Laptop replaced post-hold and wiped on 2023-12-01.",
    )
    add_source(
        conn,
        injected,
        source_id="SRC-GRAY-HALE-GMAIL",
        matter_id="MTR-GRAYCLIFF-SEC",
        custodian_name="Marcus Hale",
        role="Portfolio manager",
        source_type="personal_email",
        source_label="Hale personal Gmail",
        status="not_collected",
        event_date="2024-01-17",
        post_hold=1,
        category_impacts=["SEC-1", "SEC-3"],
        issue_tags=["personal_email", "collection_gap"],
        notes="Personal Gmail identified in interview notes but not collected.",
    )
    add_source(
        conn,
        injected,
        source_id="SRC-ALLOY-KLINE-SIGNAL",
        matter_id="MTR-ALLOYWORKS-GJ",
        custodian_name="Tessa Kline",
        role="Sales director",
        source_type="personal_messaging",
        source_label="Kline Signal",
        status="not_collected",
        event_date="2024-10-02",
        post_hold=1,
        category_impacts=["D", "F"],
        issue_tags=["signal", "personal_messaging", "collection_gap"],
        notes="Signal messages were identified in custodian interview but not collected.",
    )
    add_source(
        conn,
        injected,
        source_id="SRC-ALLOY-MORENO-SMS",
        matter_id="MTR-ALLOYWORKS-GJ",
        custodian_name="Luis Moreno",
        role="Bid desk manager",
        source_type="personal_messaging",
        source_label="Moreno SMS",
        status="not_collected",
        event_date="2024-09-27",
        post_hold=1,
        category_impacts=["D", "F"],
        issue_tags=["sms", "personal_messaging", "collection_gap"],
        notes="Personal SMS source remains outside collected review corpus.",
    )
    add_source(
        conn,
        injected,
        source_id="SRC-ALLOY-TEAMS-ARCHIVE",
        matter_id="MTR-ALLOYWORKS-GJ",
        custodian_name="Archive Operations",
        role="Enterprise records",
        source_type="teams_archive",
        source_label="Deleted pricing Teams channel archive",
        status="available",
        event_date="2024-12-18",
        post_hold=1,
        category_impacts=["D", "E"],
        issue_tags=["archive_available", "deleted_channel"],
        notes="Archive backup is available for deleted pricing Teams channel.",
    )
    add_source(
        conn,
        injected,
        source_id="SRC-MER-CARROW-PHONE",
        matter_id="MTR-MERIDIAN-GJ",
        custodian_name="Leo Carrow",
        role="Dealer operations director",
        source_type="personal_phone",
        source_label="Leo Carrow phone",
        status="lost",
        event_date="2025-03-25",
        post_hold=1,
        category_impacts=["MD-15", "MD-09"],
        issue_tags=["remote_erasure", "personal_device", "collection_gap"],
        notes="Phone remote-erased after subpoena and hold notices were issued.",
    )
    add_source(
        conn,
        injected,
        source_id="SRC-MER-BOARD-ROOM",
        matter_id="MTR-MERIDIAN-GJ",
        custodian_name="Board Secretary Office",
        role="Board operations",
        source_type="board_portal",
        source_label="BoardRoom portal",
        status="not_collected",
        event_date="2025-04-03",
        post_hold=1,
        category_impacts=["MD-07", "MD-08", "MD-09"],
        issue_tags=["board_materials", "collection_gap"],
        notes="Board portal was not included in the first collection plan.",
    )
    add_source(
        conn,
        injected,
        source_id="SRC-PORT-ENERGYCOMMS",
        matter_id="MTR-PORTOLA-GJ",
        custodian_name="Archive Operations",
        role="Trading records",
        source_type="chat_archive",
        source_label="EnergyComms archive",
        status="available",
        event_date="2025-02-15",
        post_hold=1,
        category_impacts=["PE-D", "PE-E"],
        issue_tags=["archive_available", "chat_attachments"],
        notes="Archive available for deal-chat attachments.",
    )
    add_source(
        conn,
        injected,
        source_id="SRC-BRIAR-LIN-LAPTOP",
        matter_id="MTR-BRIARGATE-SEC",
        custodian_name="Evelyn Lin",
        role="Managing director",
        source_type="laptop",
        source_label="Evelyn Lin laptop",
        status="lost",
        event_date="2024-04-12",
        post_hold=1,
        category_impacts=["SEC-A", "SEC-D"],
        issue_tags=["post_hold_wipe", "valuation_source_gap"],
        notes="Laptop wiped after the hold date and before forensic image capture.",
    )
    add_source(
        conn,
        injected,
        source_id="SRC-BRIAR-LIN-PMAIL",
        matter_id="MTR-BRIARGATE-SEC",
        custodian_name="Evelyn Lin",
        role="Managing director",
        source_type="personal_email",
        source_label="Lin ProtonMail",
        status="not_collected",
        event_date="2024-05-01",
        post_hold=1,
        category_impacts=["SEC-A", "SEC-C"],
        issue_tags=["personal_email", "collection_gap"],
        notes="ProtonMail address appears in investor drafts but has not been collected.",
    )
    add_source(
        conn,
        injected,
        source_id="SRC-COBALT-PARK-GMAIL",
        matter_id="MTR-COBALTRIDGE-GJ",
        custodian_name="Rina Park",
        role="Corporate development lead",
        source_type="personal_email",
        source_label="Rina Park personal Gmail",
        status="not_collected",
        event_date="2024-11-04",
        post_hold=1,
        category_impacts=["CR-06", "CR-15"],
        issue_tags=["personal_email", "collection_gap"],
        notes="Personal Gmail not collected despite side-channel banker references.",
    )
    add_source(
        conn,
        injected,
        source_id="SRC-COBALT-PARK-PHONE",
        matter_id="MTR-COBALTRIDGE-GJ",
        custodian_name="Rina Park",
        role="Corporate development lead",
        source_type="personal_phone",
        source_label="Rina Park phone",
        status="partial_collection",
        event_date="2024-11-08",
        post_hold=1,
        category_impacts=["CR-15"],
        issue_tags=["signal_missing", "partial_collection"],
        notes="Personal phone collection excluded Signal messages.",
    )
    add_source(
        conn,
        injected,
        source_id="SRC-VIREO-CHEN-PHONE",
        matter_id="MTR-VIREO-SEC",
        custodian_name="Mei Chen",
        role="Head of diagnostics",
        source_type="personal_phone",
        source_label="Mei Chen phone",
        status="not_collected",
        event_date="2025-03-02",
        post_hold=1,
        category_impacts=["VL-D", "VL-J"],
        issue_tags=["personal_device", "collection_gap"],
        notes="Personal phone was identified as used for investor and lab-result messaging but not collected.",
    )
    add_source(
        conn,
        injected,
        source_id="SRC-VIREO-ARCHIVE",
        matter_id="MTR-VIREO-SEC",
        custodian_name="Archive Operations",
        role="Enterprise records",
        source_type="cloud_mail_archive",
        source_label="Cloud mail archive",
        status="available",
        event_date="2025-03-18",
        post_hold=1,
        category_impacts=["VL-D", "VL-E"],
        issue_tags=["archive_available", "purged_mail"],
        notes="Cloud archive is available for purged custodian mail.",
    )


def generate_noise_sources(conn: sqlite3.Connection, rng: random.Random) -> None:
    names = [
        "Avery Stone",
        "Jordan Miles",
        "Priya Shah",
        "Callum Reed",
        "Elena Voss",
        "Nora Alden",
        "Marcus Hale",
        "Evelyn Lin",
        "Rina Park",
        "Mei Chen",
    ]
    roles = ["Finance lead", "Sales director", "Legal operations", "Board liaison", "Product manager"]
    source_types = ["mailbox", "network_share", "teams_export", "mobile_backup", "contract_repository"]
    statuses = ["collected", "available", "in_review", "not_collected", "partial_collection"]
    for matter_id, codes in CATEGORY_CODES.items():
        matter_slug = slug(matter_id)
        for idx in range(1, 15):
            impacts = sorted(rng.sample(codes, k=min(len(codes), rng.randint(1, 3))))
            status = rng.choice(statuses)
            issue_tags = ["routine"]
            if status in {"not_collected", "partial_collection"}:
                issue_tags = [rng.choice(["collection_gap", "scope_exception", "metadata_gap"])]
            add_source(
                conn,
                {},
                source_id=f"SRC-{matter_slug}-{idx:03d}",
                matter_id=matter_id,
                custodian_name=rng.choice(names),
                role=rng.choice(roles),
                source_type=rng.choice(source_types),
                source_label=f"{rng.choice(source_types).replace('_', ' ').title()} source {idx}",
                status=status,
                event_date=f"2025-{rng.randint(1, 5):02d}-{rng.randint(1, 27):02d}",
                post_hold=1 if rng.random() < 0.45 else 0,
                category_impacts=impacts,
                issue_tags=issue_tags,
                notes=rng.choice(
                    [
                        "Source map entry has minor metadata normalization issues.",
                        "Collection status differs between custodian tracker and vendor load report.",
                        "No production-impacting issue has been escalated yet.",
                        "Requires matter-level filtering because similar issue labels appear across matters.",
                    ]
                ),
                is_injected=False,
            )


def add_document(
    conn: sqlite3.Connection,
    injected: dict[str, list[str]],
    *,
    doc_id: str,
    matter_id: str,
    title: str,
    doc_date: str,
    custodian_name: str,
    source_system: str,
    category_code: str,
    responsiveness: str,
    privilege_status: str,
    produced_status: str,
    issue_tags: list[str] | str,
    summary: str,
    is_injected: bool = True,
) -> None:
    insert(
        conn,
        "review_documents",
        {
            "doc_id": doc_id,
            "matter_id": matter_id,
            "title": title,
            "doc_date": doc_date,
            "custodian_name": custodian_name,
            "source_system": source_system,
            "category_code": category_code,
            "responsiveness": responsiveness,
            "privilege_status": privilege_status,
            "produced_status": produced_status,
            "issue_tags": as_csv(issue_tags),
            "summary": summary,
        },
    )
    if is_injected:
        track(injected, matter_id, doc_id)


def generate_key_documents(conn: sqlite3.Connection, injected: dict[str, list[str]]) -> None:
    docs = [
        {
            "doc_id": "DOC-SENT-ALDEN-DEALER-ESC",
            "matter_id": "MTR-SENTINEL-GJ",
            "title": "Dealer complaint escalation email",
            "doc_date": "2024-10-18",
            "custodian_name": "Nora Alden",
            "source_system": "email",
            "category_code": "R09",
            "responsiveness": "nonresponsive",
            "privilege_status": "nonprivileged",
            "produced_status": "not_produced",
            "issue_tags": ["dealer_complaint", "miscoded_nonresponsive", "safety_escalation"],
            "summary": "Dealer complaint email is responsive to R09 but coded nonresponsive and omitted from production.",
        },
        {
            "doc_id": "DOC-GRAY-CASCADE-V3",
            "matter_id": "MTR-GRAYCLIFF-SEC",
            "title": "Cascade valuation model v3",
            "doc_date": "2023-09-14",
            "custodian_name": "Marcus Hale",
            "source_system": "shared_drive",
            "category_code": "SEC-2",
            "responsiveness": "responsive",
            "privilege_status": "nonprivileged",
            "produced_status": "unrecovered",
            "issue_tags": ["valuation", "unrecovered_file"],
            "summary": "Unrecovered valuation file referenced by recovered folder index.",
        },
        {
            "doc_id": "DOC-GRAY-ORION-DRAFT",
            "matter_id": "MTR-GRAYCLIFF-SEC",
            "title": "Orion investor disclosure draft",
            "doc_date": "2023-09-22",
            "custodian_name": "Marcus Hale",
            "source_system": "shared_drive",
            "category_code": "SEC-3",
            "responsiveness": "responsive",
            "privilege_status": "nonprivileged",
            "produced_status": "unrecovered",
            "issue_tags": ["investor_disclosure", "unrecovered_file"],
            "summary": "Unrecovered investor disclosure draft with valuation support references.",
        },
        {
            "doc_id": "DOC-GRAY-ORION-BACKINTO",
            "matter_id": "MTR-GRAYCLIFF-SEC",
            "title": "Orion back-into valuation email",
            "doc_date": "2023-08-18",
            "custodian_name": "Marcus Hale",
            "source_system": "email",
            "category_code": "SEC-1",
            "responsiveness": "responsive",
            "privilege_status": "nonprivileged",
            "produced_status": "produced",
            "issue_tags": ["valuation_red_flag", "back_into_target"],
            "summary": "Email says team should back into a target valuation before investor update.",
        },
        {
            "doc_id": "DOC-GRAY-CASCADE-97M",
            "matter_id": "MTR-GRAYCLIFF-SEC",
            "title": "Cascade 97M support note",
            "doc_date": "2023-08-21",
            "custodian_name": "Marcus Hale",
            "source_system": "email",
            "category_code": "SEC-1",
            "responsiveness": "responsive",
            "privilege_status": "nonprivileged",
            "produced_status": "produced",
            "issue_tags": ["valuation_red_flag", "unsupported_metric"],
            "summary": "Valuation note flags the 97M mark as unsupported by operating metrics.",
        },
        {
            "doc_id": "DOC-NORTH-TRIAL-RISK",
            "matter_id": "MTR-NORTHBAY-SEC",
            "title": "Clinical-risk update email",
            "doc_date": "2024-02-08",
            "custodian_name": "Lena Brooks",
            "source_system": "email",
            "category_code": "SEC-C",
            "responsiveness": "nonresponsive",
            "privilege_status": "nonprivileged",
            "produced_status": "not_produced",
            "issue_tags": ["clinical_risk", "miscoded_nonresponsive"],
            "summary": "Clinical-risk email is responsive to SEC-C but coded nonresponsive.",
        },
        {
            "doc_id": "DOC-ALLOY-BID-EMAIL-1",
            "matter_id": "MTR-ALLOYWORKS-GJ",
            "title": "Bid desk price protection email",
            "doc_date": "2024-07-19",
            "custodian_name": "Luis Moreno",
            "source_system": "email",
            "category_code": "F",
            "responsiveness": "nonresponsive",
            "privilege_status": "nonprivileged",
            "produced_status": "not_produced",
            "issue_tags": ["bid_email", "miscoded_nonresponsive", "zero_claim_contradiction"],
            "summary": "Responsive bid communication contradicts the category F zero-production claim.",
        },
        {
            "doc_id": "DOC-ALLOY-BID-EMAIL-2",
            "matter_id": "MTR-ALLOYWORKS-GJ",
            "title": "Competing quote alignment email",
            "doc_date": "2024-07-23",
            "custodian_name": "Tessa Kline",
            "source_system": "email",
            "category_code": "F",
            "responsiveness": "nonresponsive",
            "privilege_status": "nonprivileged",
            "produced_status": "not_produced",
            "issue_tags": ["bid_email", "miscoded_nonresponsive", "zero_claim_contradiction"],
            "summary": "Second responsive bid email coded nonresponsive and not produced.",
        },
        {
            "doc_id": "DOC-MER-DEALER-SAFETY",
            "matter_id": "MTR-MERIDIAN-GJ",
            "title": "Dealer safety escalation email",
            "doc_date": "2025-01-31",
            "custodian_name": "Leo Carrow",
            "source_system": "email",
            "category_code": "MD-09",
            "responsiveness": "nonresponsive",
            "privilege_status": "nonprivileged",
            "produced_status": "not_produced",
            "issue_tags": ["dealer_safety", "miscoded_nonresponsive"],
            "summary": "Dealer safety escalation is responsive to MD-09 but coded nonresponsive and not produced.",
        },
        {
            "doc_id": "DOC-BRIAR-SOLARIS-MODEL",
            "matter_id": "MTR-BRIARGATE-SEC",
            "title": "Solaris valuation model",
            "doc_date": "2024-01-18",
            "custodian_name": "Evelyn Lin",
            "source_system": "sync_folder",
            "category_code": "SEC-B",
            "responsiveness": "responsive",
            "privilege_status": "nonprivileged",
            "produced_status": "unrecovered",
            "issue_tags": ["valuation", "unrecovered_file"],
            "summary": "Unrecovered synchronized folder model referenced by folder index.",
        },
        {
            "doc_id": "DOC-BRIAR-NOVA-WATERFALL",
            "matter_id": "MTR-BRIARGATE-SEC",
            "title": "Nova waterfall draft",
            "doc_date": "2024-01-25",
            "custodian_name": "Evelyn Lin",
            "source_system": "sync_folder",
            "category_code": "SEC-C",
            "responsiveness": "responsive",
            "privilege_status": "nonprivileged",
            "produced_status": "unrecovered",
            "issue_tags": ["investor_disclosure", "unrecovered_file"],
            "summary": "Unrecovered draft supporting investor waterfall disclosures.",
        },
        {
            "doc_id": "DOC-BRIAR-NOVA-BACKSOLVE",
            "matter_id": "MTR-BRIARGATE-SEC",
            "title": "Nova backsolve valuation email",
            "doc_date": "2024-01-12",
            "custodian_name": "Evelyn Lin",
            "source_system": "email",
            "category_code": "SEC-A",
            "responsiveness": "responsive",
            "privilege_status": "nonprivileged",
            "produced_status": "produced",
            "issue_tags": ["valuation_red_flag", "backsolve"],
            "summary": "Email discusses backsolving the valuation to match investor distribution.",
        },
        {
            "doc_id": "DOC-BRIAR-SOLARIS-OVERRIDE",
            "matter_id": "MTR-BRIARGATE-SEC",
            "title": "Solaris override support note",
            "doc_date": "2024-01-15",
            "custodian_name": "Evelyn Lin",
            "source_system": "email",
            "category_code": "SEC-A",
            "responsiveness": "responsive",
            "privilege_status": "nonprivileged",
            "produced_status": "produced",
            "issue_tags": ["valuation_red_flag", "unsupported_override"],
            "summary": "Valuation note flags a management override unsupported by source metrics.",
        },
        {
            "doc_id": "DOC-COBALT-BANKER-SIDE",
            "matter_id": "MTR-COBALTRIDGE-GJ",
            "title": "Side-channel banker email",
            "doc_date": "2024-08-09",
            "custodian_name": "Rina Park",
            "source_system": "email",
            "category_code": "CR-06",
            "responsiveness": "nonresponsive",
            "privilege_status": "nonprivileged",
            "produced_status": "not_produced",
            "issue_tags": ["banker_side_channel", "miscoded_nonresponsive", "zero_claim_contradiction"],
            "summary": "Banker side-channel email is responsive to CR-06 but coded nonresponsive.",
        },
        {
            "doc_id": "DOC-VIREO-INVESTOR-MISCODE",
            "matter_id": "MTR-VIREO-SEC",
            "title": "Investor results complaint email",
            "doc_date": "2025-01-16",
            "custodian_name": "Mei Chen",
            "source_system": "email",
            "category_code": "VL-I",
            "responsiveness": "nonresponsive",
            "privilege_status": "nonprivileged",
            "produced_status": "not_produced",
            "issue_tags": ["investor_complaint", "miscoded_nonresponsive"],
            "summary": "Investor-results complaint email is responsive to VL-I but coded nonresponsive.",
        },
    ]
    for doc in docs:
        add_document(conn, injected, **doc)


def generate_noise_documents(conn: sqlite3.Connection, rng: random.Random) -> None:
    custodians = [
        "Nora Alden",
        "Marcus Hale",
        "Lena Brooks",
        "Tessa Kline",
        "Leo Carrow",
        "Evelyn Lin",
        "Rina Park",
        "Mei Chen",
        "Avery Stone",
        "Jordan Miles",
        "Priya Shah",
    ]
    source_systems = ["email", "teams", "shared_drive", "contract_repository", "board_portal", "archive"]
    tags = [
        "routine",
        "family_member",
        "metadata_gap",
        "potentially_responsive",
        "privilege_overlay",
        "duplicate",
        "review_escalation",
        "custodian_alias",
    ]
    for matter_id, codes in CATEGORY_CODES.items():
        matter_slug = slug(matter_id)
        doc_total = (
            140 if matter_id.startswith("MTR-") and matter_id in {m["matter_id"] for m in PRIMARY_MATTERS} else 90
        )
        for idx in range(1, doc_total + 1):
            code = rng.choice(codes)
            responsiveness = rng.choices(["responsive", "nonresponsive", "needs_review"], weights=[5, 4, 1])[0]
            privilege_status = rng.choices(["nonprivileged", "privileged", "unknown"], weights=[7, 2, 1])[0]
            produced_status = rng.choices(["produced", "withheld", "not_produced"], weights=[7, 2, 1])[0]
            add_document(
                conn,
                {},
                doc_id=f"DOC-{matter_slug}-{idx:04d}",
                matter_id=matter_id,
                title=f"{category_title(matter_id, code)} - {rng.choice(NOISE_TITLES)}",
                doc_date=f"2024-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
                custodian_name=rng.choice(custodians),
                source_system=rng.choice(source_systems),
                category_code=code,
                responsiveness=responsiveness,
                privilege_status=privilege_status,
                produced_status=produced_status,
                issue_tags=sorted(set(rng.sample(tags, k=rng.randint(1, 3)))),
                summary=rng.choice(
                    [
                        "Routine review item with similar wording to escalated exceptions in other matters.",
                        "Potentially responsive family member requiring matter and category filtering.",
                        "Metadata overlay changed date fields but did not alter production status.",
                        "Review note references a source exception that is not independently escalated.",
                        "Document appears in a noisy search result set but is not one of the stable exception records.",
                    ]
                ),
                is_injected=False,
            )


def add_privilege(
    conn: sqlite3.Connection,
    injected: dict[str, list[str]],
    *,
    entry_id: str,
    matter_id: str,
    category_code: str,
    custodian_name: str,
    doc_count: int,
    withheld_count: int,
    logged_count: int,
    issue_type: str,
    third_party: int,
    notes: str,
    is_injected: bool = True,
) -> None:
    insert(
        conn,
        "privilege_entries",
        {
            "entry_id": entry_id,
            "matter_id": matter_id,
            "category_code": category_code,
            "custodian_name": custodian_name,
            "doc_count": doc_count,
            "withheld_count": withheld_count,
            "logged_count": logged_count,
            "issue_type": issue_type,
            "third_party": third_party,
            "notes": notes,
        },
    )
    if is_injected:
        track(injected, matter_id, entry_id)


def generate_key_privilege(conn: sqlite3.Connection, injected: dict[str, list[str]]) -> None:
    rows = [
        (
            "PRIV-SENT-LOG-GAP",
            "MTR-SENTINEL-GJ",
            "R11",
            "Legal Department",
            3180,
            3180,
            1410,
            "incomplete_log",
            0,
            "Privilege log covers 1410 of 3180 withheld R11 documents.",
        ),
        (
            "PRIV-GRAY-WINSLOW",
            "MTR-GRAYCLIFF-SEC",
            "SEC-3",
            "Marcus Hale",
            3,
            3,
            3,
            "third_party_waiver",
            1,
            "Three privileged emails were forwarded to Derek Winslow.",
        ),
        (
            "PRIV-GRAY-OVERDESIG",
            "MTR-GRAYCLIFF-SEC",
            "SEC-1",
            "Review Team",
            12,
            12,
            12,
            "over_designated",
            0,
            "Twelve business-only emails are over-designated as privileged.",
        ),
        (
            "PRIV-NORTH-LOG-GAP",
            "MTR-NORTHBAY-SEC",
            "SEC-D",
            "Legal Department",
            840,
            840,
            365,
            "incomplete_log",
            0,
            "Only 365 of 840 withheld privileged documents are logged.",
        ),
        (
            "PRIV-NORTH-CC-BIZ",
            "MTR-NORTHBAY-SEC",
            "SEC-C",
            "Clinical Operations",
            27,
            27,
            27,
            "over_designated",
            0,
            "Business-only counsel-cc emails were over-designated.",
        ),
        (
            "PRIV-NORTH-CONSULTANT",
            "MTR-NORTHBAY-SEC",
            "SEC-C",
            "Trial Strategy Team",
            5,
            5,
            5,
            "third_party_waiver",
            1,
            "Legal-advice emails were forwarded to a trial consultant outside the privilege group.",
        ),
        (
            "PRIV-MER-LOG-GAP",
            "MTR-MERIDIAN-GJ",
            "MD-11",
            "Legal Department",
            2260,
            2260,
            910,
            "incomplete_log",
            0,
            "Only 910 of 2260 withheld privileged documents are logged.",
        ),
        (
            "PRIV-BRIAR-ADVISER-WAIVER",
            "MTR-BRIARGATE-SEC",
            "SEC-C",
            "Evelyn Lin",
            4,
            4,
            4,
            "third_party_waiver",
            1,
            "Four privileged emails were forwarded to an outside placement adviser.",
        ),
        (
            "PRIV-BRIAR-OVERDESIG",
            "MTR-BRIARGATE-SEC",
            "SEC-A",
            "Review Team",
            15,
            15,
            15,
            "over_designated",
            0,
            "Fifteen logistics emails were over-designated.",
        ),
        (
            "PRIV-COBALT-LOG-GAP",
            "MTR-COBALTRIDGE-GJ",
            "CR-11",
            "Legal Department",
            1290,
            1290,
            480,
            "incomplete_log",
            0,
            "Only 480 of 1290 withheld documents are logged.",
        ),
        (
            "PRIV-COBALT-SELLER-WAIVER",
            "MTR-COBALTRIDGE-GJ",
            "CR-06",
            "Rina Park",
            6,
            6,
            6,
            "third_party_waiver",
            1,
            "Six attorney-client emails were forwarded to a seller-side banker.",
        ),
        (
            "PRIV-VIREO-LOG-GAP",
            "MTR-VIREO-SEC",
            "VL-G",
            "Legal Department",
            1755,
            1755,
            702,
            "incomplete_log",
            0,
            "Only 702 of 1755 withheld documents are logged.",
        ),
        (
            "PRIV-VIREO-THIRD-PARTY",
            "MTR-VIREO-SEC",
            "VL-I",
            "Mei Chen",
            3,
            3,
            3,
            "third_party_waiver",
            1,
            "Three privileged emails were forwarded to an outside CRO.",
        ),
    ]
    for row in rows:
        add_privilege(
            conn,
            injected,
            entry_id=row[0],
            matter_id=row[1],
            category_code=row[2],
            custodian_name=row[3],
            doc_count=row[4],
            withheld_count=row[5],
            logged_count=row[6],
            issue_type=row[7],
            third_party=row[8],
            notes=row[9],
        )


def generate_noise_privilege(conn: sqlite3.Connection, rng: random.Random) -> None:
    issues = ["clean", "incomplete_log", "over_designated", "third_party_waiver", "family_mismatch"]
    custodians = ["Legal Department", "Review Team", "Avery Stone", "Jordan Miles", "Board Secretary Office"]
    for matter_id, codes in CATEGORY_CODES.items():
        matter_slug = slug(matter_id)
        for idx in range(1, 9):
            doc_count = rng.randint(8, 420)
            withheld = rng.randint(0, doc_count)
            issue = rng.choice(issues)
            logged = withheld if issue != "incomplete_log" else rng.randint(0, withheld)
            add_privilege(
                conn,
                {},
                entry_id=f"PRIV-{matter_slug}-{idx:03d}",
                matter_id=matter_id,
                category_code=rng.choice(codes),
                custodian_name=rng.choice(custodians),
                doc_count=doc_count,
                withheld_count=withheld,
                logged_count=logged,
                issue_type=issue,
                third_party=1 if issue == "third_party_waiver" else 0,
                notes=rng.choice(
                    [
                        "Privilege sample has ordinary review variance.",
                        "Potential issue requires category-level context before escalation.",
                        "Entry included to create similar labels across matters.",
                        "Review team marked this item for follow-up but not immediate remediation.",
                    ]
                ),
                is_injected=False,
            )


def add_qc(
    conn: sqlite3.Connection,
    injected: dict[str, list[str]],
    *,
    finding_id: str,
    matter_id: str,
    batch_id: str,
    issue_type: str,
    doc_count: int,
    affected_category: str,
    source_ref: str,
    severity: str,
    notes: str,
    is_injected: bool = True,
) -> None:
    insert(
        conn,
        "qc_findings",
        {
            "finding_id": finding_id,
            "matter_id": matter_id,
            "batch_id": batch_id,
            "issue_type": issue_type,
            "doc_count": doc_count,
            "affected_category": affected_category,
            "source_ref": source_ref,
            "severity": severity,
            "notes": notes,
        },
    )
    if is_injected:
        track(injected, matter_id, finding_id)


def generate_key_qc(conn: sqlite3.Connection, injected: dict[str, list[str]]) -> None:
    rows = [
        (
            "QC-SENT-R09-NR",
            "MTR-SENTINEL-GJ",
            "BATCH-SENTINELGJ-009",
            "miscoded_nonresponsive",
            1,
            "R09",
            "DOC-SENT-ALDEN-DEALER-ESC",
            "high",
            "One complaint email miscoded nonresponsive for R09.",
        ),
        (
            "QC-GRAY-MISCODED-PRIV",
            "MTR-GRAYCLIFF-SEC",
            "BATCH-GRAYCLIFF-002",
            "miscoded_privilege",
            45,
            "SEC-3",
            "PRIV-GRAY-WINSLOW",
            "high",
            "Forty-five privileged documents were initially coded non-privileged.",
        ),
        (
            "QC-NORTH-MISCODED-PRIV",
            "MTR-NORTHBAY-SEC",
            "BATCH-NORTHBAY-003",
            "miscoded_privilege",
            31,
            "SEC-D",
            "PRIV-NORTH-LOG-GAP",
            "medium",
            "Privileged investigation advice docs coded non-privileged.",
        ),
        (
            "QC-ALLOY-ZERO-CLAIM",
            "MTR-ALLOYWORKS-GJ",
            "BATCH-ALLOY-004",
            "zero_claim_contradiction",
            2,
            "F",
            "DOC-ALLOY-BID-EMAIL-1,DOC-ALLOY-BID-EMAIL-2",
            "high",
            "Category F zero-production claim contradicted by two responsive bid emails.",
        ),
        (
            "QC-MER-MD09-NR",
            "MTR-MERIDIAN-GJ",
            "BATCH-MERIDIANGJ-009",
            "miscoded_nonresponsive",
            1,
            "MD-09",
            "DOC-MER-DEALER-SAFETY",
            "high",
            "One complaint/safety document miscoded nonresponsive.",
        ),
        (
            "QC-BRIAR-MISCODED-PRIV",
            "MTR-BRIARGATE-SEC",
            "BATCH-BRIARGATE-002",
            "miscoded_privilege",
            38,
            "SEC-C",
            "PRIV-BRIAR-ADVISER-WAIVER",
            "high",
            "Thirty-eight privileged docs coded non-privileged.",
        ),
        (
            "QC-COBALT-ZERO-CR06",
            "MTR-COBALTRIDGE-GJ",
            "BATCH-COBALT-003",
            "zero_claim_contradiction",
            1,
            "CR-06",
            "DOC-COBALT-BANKER-SIDE",
            "high",
            "Zero-claim for CR-06 contradicted by nonresponsive-coded banker email.",
        ),
        (
            "QC-VIREO-MISCODED-PRIV",
            "MTR-VIREO-SEC",
            "BATCH-VIREOSEC-004",
            "miscoded_privilege",
            29,
            "VL-I",
            "PRIV-VIREO-THIRD-PARTY",
            "medium",
            "Privileged investigation documents coded non-privileged.",
        ),
    ]
    for row in rows:
        add_qc(
            conn,
            injected,
            finding_id=row[0],
            matter_id=row[1],
            batch_id=row[2],
            issue_type=row[3],
            doc_count=row[4],
            affected_category=row[5],
            source_ref=row[6],
            severity=row[7],
            notes=row[8],
        )


def generate_noise_qc(conn: sqlite3.Connection, rng: random.Random) -> None:
    issues = ["metadata_gap", "family_break", "date_normalization", "duplicate_overlay", "near_duplicate"]
    severities = ["low", "medium", "high"]
    for matter_id, codes in CATEGORY_CODES.items():
        matter_slug = slug(matter_id)
        for idx in range(1, 9):
            add_qc(
                conn,
                {},
                finding_id=f"QC-{matter_slug}-{idx:03d}",
                matter_id=matter_id,
                batch_id=f"BATCH-{matter_slug}-{rng.randint(1, max(len(codes), 2)):03d}",
                issue_type=rng.choice(issues),
                doc_count=rng.randint(1, 65),
                affected_category=rng.choice(codes),
                source_ref=f"DOC-{matter_slug}-{rng.randint(1, 24):04d}",
                severity=rng.choice(severities),
                notes=rng.choice(
                    [
                        "Quality-control sample is noisy but not dispositive without source comparison.",
                        "Finding is similar to escalated records in another matter.",
                        "Review manager requested re-sampling before escalation.",
                        "Corrected in later overlay but retained for audit trail.",
                    ]
                ),
                is_injected=False,
            )


def add_retention(
    conn: sqlite3.Connection,
    injected: dict[str, list[str]],
    *,
    event_id: str,
    matter_id: str,
    record_type: str,
    event_date: str,
    hold_date: str,
    policy_section: str,
    retention_period_months: int,
    volume_count: int,
    volume_unit: str,
    status: str,
    affected_categories: list[str] | str,
    source_ref: str,
    notes: str,
    is_injected: bool = True,
) -> None:
    insert(
        conn,
        "retention_events",
        {
            "event_id": event_id,
            "matter_id": matter_id,
            "record_type": record_type,
            "event_date": event_date,
            "hold_date": hold_date,
            "policy_section": policy_section,
            "retention_period_months": retention_period_months,
            "volume_count": volume_count,
            "volume_unit": volume_unit,
            "status": status,
            "affected_categories": as_csv(affected_categories),
            "source_ref": source_ref,
            "notes": notes,
        },
    )
    if is_injected:
        track(injected, matter_id, event_id)


def generate_key_retention(conn: sqlite3.Connection, injected: dict[str, list[str]]) -> None:
    rows = [
        (
            "RET-HARB-LAB-2019",
            "MTR-HARBORSTONE-GJ",
            "lab_test_data",
            "2023-01-18",
            "2024-11-14",
            "3.1",
            48,
            4,
            "boxes",
            "policy_destroyed_pre_hold",
            "B",
            "Warehouse ticket WH-8821",
            "Four boxes of 2019 lab test data destroyed pre-hold under policy section 3.1.",
        ),
        (
            "RET-HARB-EHS-POST",
            "MTR-HARBORSTONE-GJ",
            "ehs_correspondence",
            "2025-01-06",
            "2024-11-14",
            "4.2",
            60,
            2,
            "boxes",
            "post_hold_loss",
            "C,D,H",
            "Warehouse ticket WH-9144",
            "Two boxes destroyed after the hold date.",
        ),
        (
            "RET-HARB-VOICE",
            "MTR-HARBORSTONE-GJ",
            "voicemail",
            "2025-02-12",
            "2024-11-14",
            "7.4",
            3,
            90,
            "days",
            "auto_purged",
            "D",
            "Voice platform auto-delete",
            "Voicemail auto-delete is configured for 90 days.",
        ),
        (
            "RET-HARB-TEAMS",
            "MTR-HARBORSTONE-GJ",
            "teams_messages",
            "2022-02-01",
            "2024-11-14",
            "6.3",
            36,
            1,
            "system_window",
            "system_loss",
            "D,E",
            "Teams active system",
            "Teams messages before 2022-02-01 are lost from active system.",
        ),
        (
            "RET-HARB-AUDIT",
            "MTR-HARBORSTONE-GJ",
            "calverley_audit",
            "2023-10-31",
            "2024-11-14",
            "5.6",
            60,
            1,
            "report",
            "should_exist_missing",
            "E,F,I",
            "Calverley audit register",
            "October 2023 Calverley audit is missing but retention requires 60 months.",
        ),
        (
            "RET-GRAY-SHARE-DEL",
            "MTR-GRAYCLIFF-SEC",
            "shared_drive_files",
            "2023-11-10",
            "2023-10-12",
            "8.2",
            60,
            37,
            "files",
            "post_hold_partial_recovery",
            "SEC-2,SEC-3",
            "Shared drive recovery log",
            "Thirty-seven shared-drive files deleted after hold; 29 recovered and 8 unrecovered.",
        ),
        (
            "RET-ALLOY-BOX-POST",
            "MTR-ALLOYWORKS-GJ",
            "offsite_bid_files",
            "2024-10-10",
            "2024-08-20",
            "4.9",
            72,
            6,
            "boxes",
            "post_hold_loss",
            "A,C,F",
            "Off-site vendor ticket OS-441",
            "Six off-site bid file boxes destroyed after hold.",
        ),
        (
            "RET-PORT-TRADE-2018",
            "MTR-PORTOLA-GJ",
            "trade_blotters",
            "2024-11-30",
            "2025-01-09",
            "2.7",
            72,
            12,
            "monthly_blotters",
            "policy_destroyed_pre_hold",
            "PE-B",
            "Trading records schedule",
            "2018 trade blotters destroyed pre-hold per 72-month retention.",
        ),
        (
            "RET-PORT-CHAT-POST",
            "MTR-PORTOLA-GJ",
            "deal_chat_exports",
            "2025-02-04",
            "2025-01-09",
            "6.2",
            60,
            18,
            "exports",
            "post_hold_loss",
            "PE-D,PE-E",
            "Chat export ticket CE-190",
            "Eighteen deal-chat exports deleted after hold.",
        ),
        (
            "RET-PORT-VOICE",
            "MTR-PORTOLA-GJ",
            "trader_voicemail",
            "2025-03-11",
            "2025-01-09",
            "7.4",
            4,
            120,
            "days",
            "auto_purged",
            "PE-D",
            "Voice platform auto-delete",
            "Trader voicemail auto-purges after 120 days.",
        ),
        (
            "RET-PORT-AUDIT-MISSING",
            "MTR-PORTOLA-GJ",
            "surveillance_report",
            "2024-12-31",
            "2025-01-09",
            "5.8",
            60,
            1,
            "report",
            "should_exist_missing",
            "PE-F,PE-I",
            "Surveillance report index",
            "The 2024 surveillance report should exist but is missing.",
        ),
        (
            "RET-BRIAR-CLOUD-DEL",
            "MTR-BRIARGATE-SEC",
            "sync_folder_files",
            "2024-03-19",
            "2024-02-21",
            "8.2",
            60,
            24,
            "files",
            "post_hold_partial_recovery",
            "SEC-B,SEC-C",
            "Cloud sync recovery log",
            "Twenty-four synchronized folder files deleted post-hold; 17 recovered and 7 unrecovered.",
        ),
        (
            "RET-VIREO-LAB-POST",
            "MTR-VIREO-SEC",
            "lab_results_archive",
            "2025-03-20",
            "2025-02-03",
            "3.1",
            60,
            3,
            "boxes",
            "post_hold_loss",
            "VL-B,VL-H",
            "Archive ticket AR-662",
            "Three lab-results archive boxes destroyed post-hold.",
        ),
        (
            "RET-VIREO-AUDIT-MISSING",
            "MTR-VIREO-SEC",
            "qa_audit",
            "2025-05-01",
            "2025-02-03",
            "5.6",
            60,
            1,
            "report",
            "should_exist_missing",
            "VL-C,VL-H",
            "QA audit register",
            "The 2025 QA audit should exist but is missing.",
        ),
    ]
    for row in rows:
        add_retention(
            conn,
            injected,
            event_id=row[0],
            matter_id=row[1],
            record_type=row[2],
            event_date=row[3],
            hold_date=row[4],
            policy_section=row[5],
            retention_period_months=row[6],
            volume_count=row[7],
            volume_unit=row[8],
            status=row[9],
            affected_categories=row[10],
            source_ref=row[11],
            notes=row[12],
        )


def generate_noise_retention(conn: sqlite3.Connection, rng: random.Random) -> None:
    record_types = ["email_archive", "shared_drive", "voice_mail", "box_storage", "chat_export", "audit_report"]
    statuses = ["retained", "available", "policy_destroyed_pre_hold", "system_loss", "should_exist_missing"]
    for matter in PRIMARY_MATTERS + DISTRACTOR_MATTERS:
        matter_id = matter["matter_id"]
        matter_slug = slug(matter_id)
        codes = CATEGORY_CODES[matter_id]
        for idx in range(1, 8):
            affected = sorted(rng.sample(codes, k=min(len(codes), rng.randint(1, 3))))
            status = rng.choice(statuses)
            add_retention(
                conn,
                {},
                event_id=f"RET-{matter_slug}-{idx:03d}",
                matter_id=matter_id,
                record_type=rng.choice(record_types),
                event_date=f"2024-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
                hold_date=matter["hold_date"],
                policy_section=f"{rng.randint(2, 9)}.{rng.randint(1, 9)}",
                retention_period_months=rng.choice([24, 36, 48, 60, 72, 84]),
                volume_count=rng.randint(1, 40),
                volume_unit=rng.choice(["files", "boxes", "exports", "mailboxes", "reports"]),
                status=status,
                affected_categories=affected,
                source_ref=f"Records schedule {matter_slug}-{idx:02d}",
                notes=rng.choice(
                    [
                        "Retention entry is relevant only after comparing hold date and policy period.",
                        "Entry creates a similar label but has no unresolved production impact.",
                        "Vendor tracker and legal hold tracker use slightly different record labels.",
                        "Potential issue was remediated by archive collection.",
                    ]
                ),
                is_injected=False,
            )


def generate_remediation(conn: sqlite3.Connection, rng: random.Random, injected: dict[str, list[str]]) -> None:
    targets: list[tuple[str, str, str, str, str]] = []
    for matter_id, record_ids in injected.items():
        for record_id in record_ids:
            if record_id.startswith(("SRC-", "RET-", "QC-", "PRIV-")):
                severity = (
                    "high"
                    if any(token in record_id for token in ["LOG-GAP", "POST", "ZERO", "MISCODED", "PHONE", "LAPTOP"])
                    else "medium"
                )
                action_type = "supplemental_collection"
                if record_id.startswith("PRIV-"):
                    action_type = "privilege_rework"
                elif record_id.startswith("RET-"):
                    action_type = "retention_exception_review"
                elif record_id.startswith("QC-"):
                    action_type = "qc_remediation"
                targets.append((matter_id, record_id, action_type, severity, "open"))
    for idx, (matter_id, target_ref, action_type, severity, _status) in enumerate(targets, start=1):
        action_id = f"ACT-{slug(matter_id)}-{idx:03d}"
        insert(
            conn,
            "remediation_actions",
            {
                "action_id": action_id,
                "matter_id": matter_id,
                "action_type": action_type,
                "priority": "P1" if severity == "high" else "P2",
                "severity": severity,
                "owner": rng.choice(["Review Operations", "Legal Hold Team", "Privilege Team", "Forensics"]),
                "target_ref": target_ref,
                "due_days": 7 if severity == "high" else 14,
                "description": f"Review and remediate {target_ref} before next production certification.",
            },
        )
    for matter_id, codes in CATEGORY_CODES.items():
        for idx in range(1, 4):
            insert(
                conn,
                "remediation_actions",
                {
                    "action_id": f"ACT-{slug(matter_id)}-NOISE-{idx:02d}",
                    "matter_id": matter_id,
                    "action_type": rng.choice(["load_file_cleanup", "custodian_followup", "sampling_review"]),
                    "priority": rng.choice(["P2", "P3"]),
                    "severity": rng.choice(["low", "medium"]),
                    "owner": rng.choice(["Review Operations", "Vendor Team", "Matter Associate"]),
                    "target_ref": rng.choice(codes),
                    "due_days": rng.choice([14, 21, 30]),
                    "description": "Routine action included as realistic operational noise.",
                },
            )


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = [
        "matters",
        "subpoena_categories",
        "production_stats",
        "custodian_sources",
        "review_documents",
        "privilege_entries",
        "qc_findings",
        "retention_events",
        "remediation_actions",
    ]
    return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}


def write_judge_placeholder() -> None:
    if JUDGE_DATA_PATH.exists():
        try:
            existing = json.loads(JUDGE_DATA_PATH.read_text())
            if isinstance(existing, dict) and existing.get("tasks"):
                return
        except json.JSONDecodeError:
            pass
    data = {
        "schema_version": 1,
        "notice": "Placeholder judge data. Task builders may replace train task points during integration.",
        "tasks": {
            f"train_{idx:03d}": {
                "points": [],
                "empty_behavior": "score_zero_until_points_are_supplied",
            }
            for idx in range(1, 6)
        },
    }
    JUDGE_DATA_PATH.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def write_manifest(conn: sqlite3.Connection, injected: dict[str, list[str]]) -> dict:
    manifest = {
        "service": SERVICE_NAME,
        "seed": SEED,
        "generated": "static-deterministic-seed-17017",
        "database_path": CONTAINER_DB_PATH,
        "state_mode": STATE_MODE,
        "table_counts": table_counts(conn),
        "primary_matters": [
            {"matter_id": matter["matter_id"], "task_id": matter["task_id"]} for matter in PRIMARY_MATTERS
        ],
        "injected_record_ids": {matter_id: sorted(record_ids) for matter_id, record_ids in sorted(injected.items())},
        "endpoint_inventory": ENDPOINTS,
        "business_endpoint_list": [
            endpoint
            for endpoint in ENDPOINTS
            if endpoint not in {"GET /health", "POST /api/judge", "POST /admin/reset"}
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def generate_all() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    rng = random.Random(SEED)
    injected: dict[str, list[str]] = {}
    conn = sqlite3.connect(DB_PATH)
    try:
        create_schema(conn)
        generate_matters(conn)
        generate_categories(conn, rng)
        generate_productions(conn, rng)
        generate_key_sources(conn, injected)
        generate_noise_sources(conn, rng)
        generate_key_documents(conn, injected)
        generate_noise_documents(conn, rng)
        generate_key_privilege(conn, injected)
        generate_noise_privilege(conn, rng)
        generate_key_qc(conn, injected)
        generate_noise_qc(conn, rng)
        generate_key_retention(conn, injected)
        generate_noise_retention(conn, rng)
        generate_remediation(conn, rng, injected)
        conn.commit()
        manifest = write_manifest(conn, injected)
    finally:
        conn.close()
    write_judge_placeholder()
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Investigation Review Hub data.")
    parser.add_argument("--print-manifest", action="store_true", help="Print the generated manifest JSON.")
    args = parser.parse_args()
    manifest = generate_all()
    if args.print_manifest:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        counts = ", ".join(f"{table}={count}" for table, count in manifest["table_counts"].items())
        print(f"Generated {DB_PATH} with seed {SEED}: {counts}")


if __name__ == "__main__":
    main()
