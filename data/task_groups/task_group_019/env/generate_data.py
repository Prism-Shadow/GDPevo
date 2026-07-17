#!/usr/bin/env python3
"""Generate deterministic CLRP SQLite data and manifests."""

from __future__ import annotations

import datetime as dt
import json
import random
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "clrp.db"
PUBLIC_MANIFEST_PATH = DATA_DIR / "public_manifest.json"
CONSTRUCTION_MANIFEST_PATH = DATA_DIR / "construction_manifest.json"

SEEDS = {
    "contractors": 1901901,
    "alcohol": 1901902,
    "renewals": 1901903,
}

GENERATED_AT = "2026-07-07T00:00:00Z"

TRADES = [
    "General Builder",
    "Roofing",
    "Electrical",
    "Plumbing",
    "HVAC",
    "Solar",
    "Concrete",
    "Fire Protection",
]

BOND_REQUIREMENTS = {
    "General Builder": 15000,
    "Roofing": 18000,
    "Electrical": 16000,
    "Plumbing": 16000,
    "HVAC": 14000,
    "Solar": 20000,
    "Concrete": 12000,
    "Fire Protection": 17000,
}

INSURANCE_REQUIREMENTS = {
    "General Builder": 500000,
    "Roofing": 500000,
    "Electrical": 750000,
    "Plumbing": 750000,
    "HVAC": 500000,
    "Solar": 1000000,
    "Concrete": 500000,
    "Fire Protection": 1000000,
}

CONTRACTOR_BATCH_SIZES = {
    "HS-2026-Q1A": 12,
    "HS-2026-Q1B": 11,
    "HS-2026-Q2A": 14,
    "HS-2026-Q2B": 13,
}

CONTRACTOR_ISSUE_PATTERNS = {
    "HS-2026-Q1A": [
        ["NO_DEFICIENCY"],
        ["BOND_SHORTFALL"],
        ["INSURANCE_VERIFY"],
        ["UNRESOLVED_PENALTY"],
        ["FIELD_NOTE_HOLD"],
        ["BOND_CANCELLED"],
        ["EXPERIENCE_VERIFY"],
        ["NO_DEFICIENCY"],
        ["BOND_SHORTFALL", "INSURANCE_VERIFY"],
        ["DISQUALIFYING_CONDUCT"],
        ["NO_DEFICIENCY"],
        ["FIELD_NOTE_HOLD", "UNRESOLVED_PENALTY"],
    ],
    "HS-2026-Q1B": [
        ["ADVERSE_PRIOR_REGISTRATION"],
        ["BOND_CANCELLED"],
        ["NO_DEFICIENCY"],
        ["INSURANCE_VERIFY"],
        ["FIELD_NOTE_HOLD"],
        ["BOND_SHORTFALL"],
        ["NO_DEFICIENCY"],
        ["UNRESOLVED_PENALTY"],
        ["EXPERIENCE_VERIFY"],
        ["CORRESPONDENCE_HOLD"],
        ["NO_DEFICIENCY"],
    ],
    "HS-2026-Q2A": [
        ["NO_DEFICIENCY"],
        ["BOND_SHORTFALL"],
        ["INSURANCE_VERIFY"],
        ["CORRESPONDENCE_HOLD"],
        ["FIELD_NOTE_HOLD"],
        ["NO_DEFICIENCY"],
        ["UNRESOLVED_PENALTY"],
        ["BOND_CANCELLED"],
        ["DISQUALIFYING_CONDUCT"],
        ["EXPERIENCE_VERIFY"],
        ["NO_DEFICIENCY"],
        ["BOND_SHORTFALL", "INSURANCE_VERIFY"],
        ["NO_DEFICIENCY"],
        ["ADVERSE_PRIOR_REGISTRATION"],
    ],
    "HS-2026-Q2B": [
        ["BOND_SHORTFALL"],
        ["NO_DEFICIENCY"],
        ["INSURANCE_VERIFY"],
        ["FIELD_NOTE_HOLD"],
        ["UNRESOLVED_PENALTY"],
        ["NO_DEFICIENCY"],
        ["BOND_CANCELLED"],
        ["EXPERIENCE_VERIFY"],
        ["CORRESPONDENCE_HOLD"],
        ["NO_DEFICIENCY"],
        ["BOND_SHORTFALL"],
        ["DISQUALIFYING_CONDUCT"],
        ["NO_DEFICIENCY"],
    ],
}


def date_between(rng: random.Random, start: str, end: str) -> str:
    start_date = dt.date.fromisoformat(start)
    end_date = dt.date.fromisoformat(end)
    span = (end_date - start_date).days
    return (start_date + dt.timedelta(days=rng.randint(0, span))).isoformat()


def date_add(date_text: str, days: int) -> str:
    return (dt.date.fromisoformat(date_text) + dt.timedelta(days=days)).isoformat()


def insert_many(conn: sqlite3.Connection, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    placeholders = ", ".join(["?"] * len(columns))
    column_sql = ", ".join(columns)
    values = [[row[column] for column in columns] for row in rows]
    conn.executemany(
        f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
        values,
    )


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = OFF;

        CREATE TABLE contractor_applications (
            application_id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            legal_name TEXT NOT NULL,
            dba TEXT NOT NULL,
            principal_name TEXT NOT NULL,
            trade TEXT NOT NULL,
            application_date TEXT NOT NULL,
            exam_score INTEGER NOT NULL,
            experience_years INTEGER NOT NULL,
            financial_statement_filed INTEGER NOT NULL,
            background_status TEXT NOT NULL,
            declared_bond_amount INTEGER NOT NULL,
            declared_insurance_carrier TEXT NOT NULL,
            declared_insurance_policy TEXT NOT NULL,
            prior_registration_id TEXT
        );

        CREATE TABLE contractor_bonds (
            bond_id TEXT PRIMARY KEY,
            legal_name TEXT NOT NULL,
            principal_name TEXT NOT NULL,
            trade TEXT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL,
            effective_date TEXT NOT NULL,
            cancellation_date TEXT,
            surety TEXT NOT NULL,
            last_update TEXT NOT NULL,
            note TEXT NOT NULL
        );

        CREATE TABLE contractor_insurance (
            policy_id TEXT PRIMARY KEY,
            legal_name TEXT NOT NULL,
            carrier TEXT NOT NULL,
            policy_number TEXT NOT NULL,
            status TEXT NOT NULL,
            coverage_amount INTEGER NOT NULL,
            effective_date TEXT NOT NULL,
            expiration_date TEXT NOT NULL,
            verification_status TEXT NOT NULL,
            last_update TEXT NOT NULL
        );

        CREATE TABLE contractor_violations (
            violation_id TEXT PRIMARY KEY,
            legal_name TEXT NOT NULL,
            principal_name TEXT NOT NULL,
            violation_date TEXT NOT NULL,
            violation_type TEXT NOT NULL,
            status TEXT NOT NULL,
            penalty_due_cents INTEGER NOT NULL,
            ag_referral INTEGER NOT NULL,
            severity TEXT NOT NULL
        );

        CREATE TABLE contractor_complaints (
            complaint_id TEXT PRIMARY KEY,
            legal_name TEXT NOT NULL,
            received_date TEXT NOT NULL,
            complaint_type TEXT NOT NULL,
            status TEXT NOT NULL,
            linked_field_note_id TEXT,
            severity TEXT NOT NULL
        );

        CREATE TABLE contractor_field_notes (
            note_id TEXT PRIMARY KEY,
            legal_name TEXT NOT NULL,
            inspection_date TEXT NOT NULL,
            inspector TEXT NOT NULL,
            finding_type TEXT NOT NULL,
            summary TEXT NOT NULL,
            recommended_action TEXT NOT NULL
        );

        CREATE TABLE contractor_correspondence (
            item_id TEXT PRIMARY KEY,
            received_date TEXT NOT NULL,
            subject_name TEXT NOT NULL,
            item_type TEXT NOT NULL,
            summary TEXT NOT NULL,
            affects_application_id TEXT,
            document_status TEXT NOT NULL
        );

        CREATE TABLE contractor_bulletins (
            bulletin_id TEXT PRIMARY KEY,
            effective_date TEXT NOT NULL,
            trade_scope TEXT NOT NULL,
            rule_type TEXT NOT NULL,
            threshold_value INTEGER NOT NULL,
            citation TEXT NOT NULL,
            summary TEXT NOT NULL,
            prior_rule TEXT NOT NULL
        );

        CREATE TABLE alcohol_applications (
            application_id TEXT PRIMARY KEY,
            premises_id TEXT NOT NULL,
            applicant_name TEXT NOT NULL,
            dba TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            license_type TEXT NOT NULL,
            review_month TEXT NOT NULL,
            requested_posture TEXT NOT NULL
        );

        CREATE TABLE alcohol_premises (
            premises_id TEXT PRIMARY KEY,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            current_dba TEXT NOT NULL,
            same_premises_basis TEXT NOT NULL,
            prior_licensee TEXT NOT NULL,
            risk_summary TEXT NOT NULL
        );

        CREATE TABLE alcohol_incidents (
            incident_id TEXT PRIMARY KEY,
            premises_id TEXT NOT NULL,
            incident_date TEXT NOT NULL,
            incident_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            disposition TEXT,
            source TEXT NOT NULL
        );

        CREATE TABLE alcohol_settlements (
            settlement_id TEXT PRIMARY KEY,
            premises_id TEXT NOT NULL,
            settlement_date TEXT NOT NULL,
            prior_or_current TEXT NOT NULL,
            original_posture TEXT NOT NULL,
            final_terms_summary TEXT NOT NULL
        );

        CREATE TABLE alcohol_restrictions (
            restriction_id TEXT PRIMARY KEY,
            premises_id TEXT NOT NULL,
            settlement_id TEXT NOT NULL,
            restriction_code TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            evidence_required TEXT NOT NULL
        );

        CREATE TABLE alcohol_standard_obligations (
            obligation_id TEXT PRIMARY KEY,
            license_type TEXT NOT NULL,
            obligation_code TEXT NOT NULL,
            description TEXT NOT NULL,
            evidence_required TEXT NOT NULL
        );

        CREATE TABLE renewal_licensees (
            license_id TEXT PRIMARY KEY,
            facility_name TEXT NOT NULL,
            legal_name TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            channel_type TEXT NOT NULL,
            license_type TEXT NOT NULL,
            status TEXT NOT NULL,
            release_batch TEXT NOT NULL,
            successor_hint TEXT
        );

        CREATE TABLE renewal_violations (
            violation_id TEXT PRIMARY KEY,
            historical_name TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            violation_date TEXT NOT NULL,
            violation_code TEXT NOT NULL,
            theme TEXT NOT NULL,
            disposition TEXT,
            fine_cents INTEGER NOT NULL,
            alert_related INTEGER NOT NULL,
            severity TEXT NOT NULL
        );

        CREATE INDEX idx_contractor_app_batch ON contractor_applications(batch_id);
        CREATE INDEX idx_contractor_app_name ON contractor_applications(legal_name);
        CREATE INDEX idx_contractor_app_principal ON contractor_applications(principal_name);
        CREATE INDEX idx_contractor_bonds_name ON contractor_bonds(legal_name);
        CREATE INDEX idx_contractor_bonds_principal ON contractor_bonds(principal_name);
        CREATE INDEX idx_contractor_bonds_update ON contractor_bonds(last_update);
        CREATE INDEX idx_contractor_insurance_name ON contractor_insurance(legal_name);
        CREATE INDEX idx_contractor_violations_name ON contractor_violations(legal_name);
        CREATE INDEX idx_contractor_violations_principal ON contractor_violations(principal_name);
        CREATE INDEX idx_contractor_violations_date ON contractor_violations(violation_date);
        CREATE INDEX idx_contractor_complaints_name ON contractor_complaints(legal_name);
        CREATE INDEX idx_contractor_field_notes_name ON contractor_field_notes(legal_name);
        CREATE INDEX idx_contractor_correspondence_app ON contractor_correspondence(affects_application_id);
        CREATE INDEX idx_contractor_bulletins_date ON contractor_bulletins(effective_date);

        CREATE INDEX idx_alcohol_app_month ON alcohol_applications(review_month);
        CREATE INDEX idx_alcohol_app_premises ON alcohol_applications(premises_id);
        CREATE INDEX idx_alcohol_premises_address ON alcohol_premises(address);
        CREATE INDEX idx_alcohol_incidents_premises ON alcohol_incidents(premises_id);
        CREATE INDEX idx_alcohol_incidents_date ON alcohol_incidents(incident_date);
        CREATE INDEX idx_alcohol_settlements_premises ON alcohol_settlements(premises_id);
        CREATE INDEX idx_alcohol_restrictions_premises ON alcohol_restrictions(premises_id);
        CREATE INDEX idx_alcohol_obligations_type ON alcohol_standard_obligations(license_type);

        CREATE INDEX idx_renewal_licensees_batch ON renewal_licensees(release_batch);
        CREATE INDEX idx_renewal_licensees_address ON renewal_licensees(address);
        CREATE INDEX idx_renewal_licensees_name ON renewal_licensees(facility_name);
        CREATE INDEX idx_renewal_violations_city ON renewal_violations(city);
        CREATE INDEX idx_renewal_violations_address ON renewal_violations(address);
        CREATE INDEX idx_renewal_violations_name ON renewal_violations(historical_name);
        CREATE INDEX idx_renewal_violations_date ON renewal_violations(violation_date);
        """
    )


def contractor_name(index: int) -> tuple[str, str, str]:
    first = [
        "Alder",
        "Beacon",
        "Cascade",
        "Duwamish",
        "Evergreen",
        "Fircrest",
        "Glacier",
        "Harbor",
        "Ironwood",
        "Juniper",
        "Kestrel",
        "Larch",
        "Madrona",
        "Northstar",
        "Orchard",
        "Pioneer",
        "Quarry",
        "Rainier",
        "Soundview",
        "Timberline",
        "Union",
        "Vashon",
        "Westlake",
        "Yarrow",
    ]
    second = [
        "Summit",
        "Cedar",
        "Ridge",
        "Marina",
        "Foundry",
        "Station",
        "Terrace",
        "Point",
        "Harbor",
        "Bridge",
        "Valley",
        "Crest",
    ]
    suffix = [
        "Builders LLC",
        "Contracting Inc",
        "Construction Group",
        "Restoration LLC",
        "Works Co",
        "Services LLC",
    ]
    legal = f"{first[index % len(first)]} {second[(index // len(first)) % len(second)]} {suffix[index % len(suffix)]}"
    if index >= len(first) * len(second):
        legal = f"{legal} {index:03d}"
    dba = legal.replace(" LLC", "").replace(" Inc", "").replace(" Co", "")
    principal = f"{['Morgan', 'Taylor', 'Jordan', 'Casey', 'Riley', 'Avery', 'Quinn', 'Rowan'][index % 8]} {['Chen', 'Patel', 'Nguyen', 'Garcia', 'Bennett', 'Murphy', 'Singh', 'Lopez'][(index // 8) % 8]}"
    return legal, dba, principal


def build_contractor_bulletins() -> list[dict]:
    rows: list[dict] = []
    specs = [
        (
            "CB-2026-001",
            "2026-01-05",
            "ALL",
            "EXAM_MINIMUM",
            72,
            "HSRC 18.12.040",
            "Minimum passing exam score is 72 for 2026 submissions.",
            "Passing score was 70.",
        ),
        (
            "CB-2026-002",
            "2026-01-15",
            "General Builder",
            "BOND_MINIMUM",
            15000,
            "HSRC 18.20.110",
            "General Builder bonds must meet the 2026 minimum.",
            "Prior minimum was 12000.",
        ),
        (
            "CB-2026-003",
            "2026-01-20",
            "Concrete",
            "BOND_MINIMUM",
            12000,
            "HSRC 18.20.115",
            "Concrete trade minimum bond remains lower than structural trades.",
            "Prior minimum was 10000.",
        ),
        (
            "CB-2026-004",
            "2026-02-01",
            "Roofing",
            "BOND_MINIMUM",
            18000,
            "HSRC 18.20.130",
            "Roofing registrations require higher storm-loss bond coverage.",
            "Prior minimum was 15000.",
        ),
        (
            "CB-2026-005",
            "2026-02-01",
            "Roofing",
            "INSURANCE_MINIMUM",
            500000,
            "HSRC 18.22.055",
            "Roofing files require active liability coverage verified by carrier.",
            "Carrier attestation was previously optional.",
        ),
        (
            "CB-2026-006",
            "2026-02-10",
            "Electrical",
            "BOND_MINIMUM",
            16000,
            "HSRC 18.20.140",
            "Electrical contractor bonds must meet the updated amount.",
            "Prior minimum was 14000.",
        ),
        (
            "CB-2026-007",
            "2026-02-10",
            "Electrical",
            "INSURANCE_MINIMUM",
            750000,
            "HSRC 18.22.062",
            "Electrical liability coverage minimum increased.",
            "Prior minimum was 500000.",
        ),
        (
            "CB-2026-008",
            "2026-02-15",
            "Plumbing",
            "BOND_MINIMUM",
            16000,
            "HSRC 18.20.150",
            "Plumbing contractor bond minimum increased.",
            "Prior minimum was 13000.",
        ),
        (
            "CB-2026-009",
            "2026-02-15",
            "Plumbing",
            "INSURANCE_MINIMUM",
            750000,
            "HSRC 18.22.064",
            "Plumbing liability coverage minimum increased.",
            "Prior minimum was 500000.",
        ),
        (
            "CB-2026-010",
            "2026-03-01",
            "HVAC",
            "BOND_MINIMUM",
            14000,
            "HSRC 18.20.160",
            "HVAC bond minimum increased for refrigerant work.",
            "Prior minimum was 11000.",
        ),
        (
            "CB-2026-011",
            "2026-03-01",
            "HVAC",
            "EXPERIENCE_MINIMUM",
            3,
            "HSRC 18.18.030",
            "HVAC principals must document three years of qualifying experience.",
            "Prior requirement was two years.",
        ),
        (
            "CB-2026-012",
            "2026-03-12",
            "Solar",
            "BOND_MINIMUM",
            20000,
            "HSRC 18.20.170",
            "Solar installer bond minimum increased for storage projects.",
            "Prior minimum was 15000.",
        ),
        (
            "CB-2026-013",
            "2026-03-12",
            "Solar",
            "INSURANCE_MINIMUM",
            1000000,
            "HSRC 18.22.070",
            "Solar installers must carry one million dollars in liability coverage.",
            "Prior minimum was 750000.",
        ),
        (
            "CB-2026-014",
            "2026-03-20",
            "Fire Protection",
            "BOND_MINIMUM",
            17000,
            "HSRC 18.20.180",
            "Fire Protection bond minimum increased.",
            "Prior minimum was 14000.",
        ),
        (
            "CB-2026-015",
            "2026-03-20",
            "Fire Protection",
            "INSURANCE_MINIMUM",
            1000000,
            "HSRC 18.22.075",
            "Fire Protection files require verified one million dollar coverage.",
            "Prior minimum was 750000.",
        ),
        (
            "CB-2026-016",
            "2026-04-01",
            "ALL",
            "BACKGROUND_SCREENING",
            1,
            "HSRC 18.16.090",
            "Unresolved financial penalties require hold before board review.",
            "Unresolved penalties were discretionary review notes.",
        ),
        (
            "CB-2026-017",
            "2026-04-10",
            "ALL",
            "CORRESPONDENCE_REVIEW",
            1,
            "HSRC 18.10.050",
            "Material correspondence received after filing must be reviewed before approval.",
            "Late correspondence was reviewed after registration issuance.",
        ),
        (
            "CB-2026-018",
            "2026-05-01",
            "General Builder",
            "EXPERIENCE_MINIMUM",
            4,
            "HSRC 18.18.010",
            "General Builder principals must show four years of qualifying experience.",
            "Prior requirement was three years.",
        ),
        (
            "CB-2026-019",
            "2026-05-01",
            "Concrete",
            "EXPERIENCE_MINIMUM",
            3,
            "HSRC 18.18.020",
            "Concrete principals must show three years of qualifying experience.",
            "Prior requirement was two years.",
        ),
        (
            "CB-2026-020",
            "2026-05-15",
            "ALL",
            "FIELD_NOTE_REVIEW",
            1,
            "HSRC 18.14.080",
            "Open field-note holds must be resolved before registration issuance.",
            "Inspector notes were advisory unless escalated.",
        ),
    ]
    for bulletin_id, effective_date, trade_scope, rule_type, threshold_value, citation, summary, prior_rule in specs:
        rows.append(
            {
                "bulletin_id": bulletin_id,
                "effective_date": effective_date,
                "trade_scope": trade_scope,
                "rule_type": rule_type,
                "threshold_value": threshold_value,
                "citation": citation,
                "summary": summary,
                "prior_rule": prior_rule,
            }
        )
    return rows


def build_contractor_domain() -> tuple[dict[str, list[dict]], dict]:
    rng = random.Random(SEEDS["contractors"])
    applications: list[dict] = []
    app_tags: dict[str, list[str]] = {}
    anchor_metadata: dict[str, list[dict]] = {}
    app_index = 0

    batch_start_dates = {
        "HS-2026-Q1A": ("2026-01-10", "2026-02-20"),
        "HS-2026-Q1B": ("2026-02-22", "2026-03-31"),
        "HS-2026-Q2A": ("2026-04-01", "2026-05-15"),
        "HS-2026-Q2B": ("2026-05-16", "2026-06-28"),
    }

    for batch_id, count in CONTRACTOR_BATCH_SIZES.items():
        anchor_metadata[batch_id] = []
        for batch_offset in range(count):
            app_index += 1
            legal_name, dba, principal = contractor_name(app_index)
            trade = TRADES[(app_index + batch_offset) % len(TRADES)]
            issue_tags = CONTRACTOR_ISSUE_PATTERNS[batch_id][batch_offset]
            start, end = batch_start_dates[batch_id]
            application_date = date_between(rng, start, end)
            required_bond = BOND_REQUIREMENTS[trade]
            declared_bond_amount = required_bond
            if "BOND_SHORTFALL" in issue_tags:
                declared_bond_amount = required_bond - rng.choice([1000, 1500, 2500])
            exam_score = 74 + (app_index % 18)
            if "DISQUALIFYING_CONDUCT" in issue_tags:
                exam_score = 79
            experience_years = 4 + (app_index % 7)
            if "EXPERIENCE_VERIFY" in issue_tags:
                experience_years = max(1, rng.choice([1, 2]))
            background_status = "clear"
            if "ADVERSE_PRIOR_REGISTRATION" in issue_tags:
                background_status = "needs_review"
            if "DISQUALIFYING_CONDUCT" in issue_tags:
                background_status = "adverse"
            prior_registration_id = ""
            if "ADVERSE_PRIOR_REGISTRATION" in issue_tags or "DISQUALIFYING_CONDUCT" in issue_tags:
                prior_registration_id = f"REG-2024-{app_index:04d}"
            applications.append(
                {
                    "application_id": f"CA-2026-{app_index:04d}",
                    "batch_id": batch_id,
                    "legal_name": legal_name,
                    "dba": dba,
                    "principal_name": principal,
                    "trade": trade,
                    "application_date": application_date,
                    "exam_score": exam_score,
                    "experience_years": experience_years,
                    "financial_statement_filed": 0
                    if "CORRESPONDENCE_HOLD" in issue_tags and app_index % 2 == 0
                    else 1,
                    "background_status": background_status,
                    "declared_bond_amount": declared_bond_amount,
                    "declared_insurance_carrier": rng.choice(
                        ["Northwest Mutual Casualty", "Sound Surety Risk", "Cedar State Insurance", "Harbor Indemnity"]
                    ),
                    "declared_insurance_policy": f"POL-HS-{app_index:05d}",
                    "prior_registration_id": prior_registration_id,
                }
            )
            app_tags[legal_name] = issue_tags
            anchor_metadata[batch_id].append(
                {
                    "application_id": f"CA-2026-{app_index:04d}",
                    "legal_name": legal_name,
                    "issue_tags": issue_tags,
                }
            )

    extra_batches = ["HS-2026-Q3A", "HS-2026-Q3B", "HS-2026-LEGACY", "HS-2026-SPECIAL"]
    random_issue_pool = [
        ["NO_DEFICIENCY"],
        ["NO_DEFICIENCY"],
        ["BOND_SHORTFALL"],
        ["INSURANCE_VERIFY"],
        ["FIELD_NOTE_HOLD"],
        ["UNRESOLVED_PENALTY"],
        ["BOND_CANCELLED"],
        ["EXPERIENCE_VERIFY"],
    ]
    while len(applications) < 88:
        app_index += 1
        legal_name, dba, principal = contractor_name(app_index)
        batch_id = rng.choice(extra_batches)
        trade = rng.choice(TRADES)
        issue_tags = list(rng.choice(random_issue_pool))
        application_date = date_between(rng, "2026-01-05", "2026-06-30")
        required_bond = BOND_REQUIREMENTS[trade]
        declared_bond_amount = (
            required_bond - rng.choice([1000, 2000]) if "BOND_SHORTFALL" in issue_tags else required_bond
        )
        applications.append(
            {
                "application_id": f"CA-2026-{app_index:04d}",
                "batch_id": batch_id,
                "legal_name": legal_name,
                "dba": dba,
                "principal_name": principal,
                "trade": trade,
                "application_date": application_date,
                "exam_score": rng.randint(68, 94),
                "experience_years": rng.randint(1, 9),
                "financial_statement_filed": 1 if rng.random() > 0.08 else 0,
                "background_status": rng.choices(["clear", "needs_review", "adverse"], weights=[82, 14, 4])[0],
                "declared_bond_amount": declared_bond_amount,
                "declared_insurance_carrier": rng.choice(
                    ["Northwest Mutual Casualty", "Sound Surety Risk", "Cedar State Insurance", "Harbor Indemnity"]
                ),
                "declared_insurance_policy": f"POL-HS-{app_index:05d}",
                "prior_registration_id": "" if rng.random() > 0.18 else f"REG-2024-{rng.randint(1000, 9999)}",
            }
        )
        app_tags[legal_name] = issue_tags

    bonds: list[dict] = []
    sureties = ["Cascadia Bonding", "Harbor Surety", "Evergreen Surety", "Sound Indemnity", "Pioneer Bonds"]
    for i, app in enumerate(applications, start=1):
        tags = app_tags[app["legal_name"]]
        required = BOND_REQUIREMENTS[app["trade"]]
        status = "active"
        cancellation_date = ""
        amount = required
        note = "Active bond matched to current application."
        if "BOND_SHORTFALL" in tags:
            amount = max(5000, required - rng.choice([1000, 2000, 3000]))
            note = "Active bond amount is below current bulletin minimum."
        if "BOND_CANCELLED" in tags:
            status = "cancelled"
            cancellation_date = date_add(app["application_date"], rng.randint(4, 24))
            note = "Surety cancellation notice received before reviewer clearance."
        if "NO_DEFICIENCY" in tags and rng.random() < 0.05:
            status = "reduced"
            amount = required - 500
            note = "Surety sent reduction notice pending review."
        bonds.append(
            {
                "bond_id": f"BND-2026-{i:04d}",
                "legal_name": app["legal_name"],
                "principal_name": app["principal_name"],
                "trade": app["trade"],
                "amount": amount,
                "status": status,
                "effective_date": date_add(app["application_date"], -rng.randint(5, 60)),
                "cancellation_date": cancellation_date,
                "surety": rng.choice(sureties),
                "last_update": date_add(app["application_date"], rng.randint(0, 35)),
                "note": note,
            }
        )
    while len(bonds) < 96:
        source = rng.choice(applications)
        bonds.append(
            {
                "bond_id": f"BND-2026-{len(bonds) + 1:04d}",
                "legal_name": source["legal_name"].replace("LLC", "Holdings LLC").replace("Inc", "Services Inc"),
                "principal_name": source["principal_name"],
                "trade": source["trade"],
                "amount": BOND_REQUIREMENTS[source["trade"]],
                "status": rng.choice(["active", "expired", "cancelled"]),
                "effective_date": date_between(rng, "2024-01-01", "2025-12-31"),
                "cancellation_date": "" if rng.random() > 0.4 else date_between(rng, "2025-01-01", "2026-02-01"),
                "surety": rng.choice(sureties),
                "last_update": date_between(rng, "2025-01-01", "2026-06-30"),
                "note": "Distractor surety record for similar legal name or prior entity.",
            }
        )

    insurance: list[dict] = []
    carriers = [
        "Northwest Mutual Casualty",
        "Sound Surety Risk",
        "Cedar State Insurance",
        "Harbor Indemnity",
        "Rainier Liability Exchange",
    ]
    priority_apps = sorted(applications, key=lambda row: 0 if row["batch_id"] in CONTRACTOR_BATCH_SIZES else 1)
    for app in priority_apps[:82]:
        tags = app_tags[app["legal_name"]]
        carrier = app["declared_insurance_carrier"]
        status = "active"
        verification_status = "verified"
        coverage_amount = INSURANCE_REQUIREMENTS[app["trade"]]
        if "INSURANCE_VERIFY" in tags:
            verification_status = rng.choice(["pending", "carrier_mismatch"])
            if verification_status == "carrier_mismatch":
                carrier = rng.choice([name for name in carriers if name != app["declared_insurance_carrier"]])
        elif rng.random() < 0.08:
            status = "expired"
            verification_status = "stale"
        insurance.append(
            {
                "policy_id": f"INS-2026-{len(insurance) + 1:04d}",
                "legal_name": app["legal_name"],
                "carrier": carrier,
                "policy_number": app["declared_insurance_policy"],
                "status": status,
                "coverage_amount": coverage_amount,
                "effective_date": date_add(app["application_date"], -rng.randint(20, 90)),
                "expiration_date": date_between(rng, "2026-08-01", "2027-08-01")
                if status == "active"
                else date_between(rng, "2025-08-01", "2026-02-01"),
                "verification_status": verification_status,
                "last_update": date_add(app["application_date"], rng.randint(0, 25)),
            }
        )

    violations: list[dict] = []
    violation_types = [
        "unlicensed activity",
        "advertising misrepresentation",
        "permit abandonment",
        "wage complaint",
        "fraudulent registration",
        "safety order ignored",
    ]
    for app in applications:
        tags = app_tags[app["legal_name"]]
        if "UNRESOLVED_PENALTY" in tags or "DISQUALIFYING_CONDUCT" in tags or "ADVERSE_PRIOR_REGISTRATION" in tags:
            vtype = "fraudulent registration" if "DISQUALIFYING_CONDUCT" in tags else rng.choice(violation_types)
            violations.append(
                {
                    "violation_id": f"CV-2026-{len(violations) + 1:04d}",
                    "legal_name": app["legal_name"],
                    "principal_name": app["principal_name"],
                    "violation_date": date_between(rng, "2023-01-01", "2026-05-31"),
                    "violation_type": vtype,
                    "status": "unresolved",
                    "penalty_due_cents": rng.choice([45000, 80000, 125000, 220000]),
                    "ag_referral": 1 if vtype in {"fraudulent registration", "unlicensed activity"} else 0,
                    "severity": "high" if vtype in {"fraudulent registration", "safety order ignored"} else "medium",
                }
            )
    while len(violations) < 88:
        app = rng.choice(applications)
        resolved = rng.random() > 0.28
        violations.append(
            {
                "violation_id": f"CV-2026-{len(violations) + 1:04d}",
                "legal_name": app["legal_name"] if rng.random() > 0.1 else app["dba"],
                "principal_name": app["principal_name"],
                "violation_date": date_between(rng, "2022-01-01", "2026-06-30"),
                "violation_type": rng.choice(violation_types),
                "status": "resolved" if resolved else "unresolved",
                "penalty_due_cents": 0 if resolved else rng.choice([25000, 50000, 90000, 175000]),
                "ag_referral": 1 if rng.random() < 0.12 else 0,
                "severity": rng.choices(["low", "medium", "high"], weights=[48, 38, 14])[0],
            }
        )

    field_notes: list[dict] = []
    inspectors = ["I. Alvarez", "M. Brooks", "S. Chandra", "T. Evans", "N. Foster"]
    for app in applications:
        tags = app_tags[app["legal_name"]]
        if "FIELD_NOTE_HOLD" in tags:
            field_notes.append(
                {
                    "note_id": f"FN-2026-{len(field_notes) + 1:04d}",
                    "legal_name": app["legal_name"],
                    "inspection_date": date_add(app["application_date"], rng.randint(1, 18)),
                    "inspector": rng.choice(inspectors),
                    "finding_type": "open hold",
                    "summary": "Inspector found unresolved site-control or subcontractor documentation issue.",
                    "recommended_action": "hold for inspector clearance",
                }
            )
    while len(field_notes) < 44:
        app = rng.choice(applications)
        field_notes.append(
            {
                "note_id": f"FN-2026-{len(field_notes) + 1:04d}",
                "legal_name": app["legal_name"],
                "inspection_date": date_between(rng, "2025-01-01", "2026-06-30"),
                "inspector": rng.choice(inspectors),
                "finding_type": rng.choice(["resolved note", "site visit", "document check", "open hold"]),
                "summary": rng.choice(
                    [
                        "Field contact confirmed project address and license category.",
                        "Inspector requested lien disclosure backup.",
                        "Prior job complaint appears resolved with owner acknowledgement.",
                        "Open inspector hold awaiting photographs and permit correction.",
                    ]
                ),
                "recommended_action": rng.choice(
                    ["no action", "verify documents", "hold for inspector clearance", "attach to application file"]
                ),
            }
        )

    complaints: list[dict] = []
    linked_note_ids = [row["note_id"] for row in field_notes]
    complaint_types = ["unlicensed activity", "workmanship", "payment dispute", "abandoned project", "advertising"]
    for i in range(44):
        app = rng.choice(applications)
        tags = app_tags[app["legal_name"]]
        status = "open" if "FIELD_NOTE_HOLD" in tags or rng.random() < 0.28 else "closed"
        complaints.append(
            {
                "complaint_id": f"CC-2026-{i + 1:04d}",
                "legal_name": app["legal_name"],
                "received_date": date_between(rng, "2024-01-01", "2026-06-30"),
                "complaint_type": rng.choice(complaint_types),
                "status": status,
                "linked_field_note_id": rng.choice(linked_note_ids) if rng.random() < 0.45 else "",
                "severity": rng.choices(["low", "medium", "high"], weights=[52, 36, 12])[0],
            }
        )

    correspondence: list[dict] = []
    for app in applications:
        tags = app_tags[app["legal_name"]]
        if any(
            tag in tags
            for tag in ["BOND_CANCELLED", "INSURANCE_VERIFY", "CORRESPONDENCE_HOLD", "ADVERSE_PRIOR_REGISTRATION"]
        ):
            item_type = "material notice"
            summary = "Material follow-up received after application filing."
            if "BOND_CANCELLED" in tags:
                summary = "Surety cancellation notice received; reviewer must reconcile with bond record."
            elif "INSURANCE_VERIFY" in tags:
                summary = "Carrier verification differs from declared policy or remains pending."
            elif "ADVERSE_PRIOR_REGISTRATION" in tags:
                summary = "Prior-registration file requested because principal may be successor to adverse entity."
            correspondence.append(
                {
                    "item_id": f"COR-2026-{len(correspondence) + 1:04d}",
                    "received_date": date_add(app["application_date"], rng.randint(1, 30)),
                    "subject_name": app["legal_name"],
                    "item_type": item_type,
                    "summary": summary,
                    "affects_application_id": app["application_id"],
                    "document_status": rng.choice(["new", "needs_review", "indexed"]),
                }
            )
    while len(correspondence) < 58:
        app = rng.choice(applications)
        correspondence.append(
            {
                "item_id": f"COR-2026-{len(correspondence) + 1:04d}",
                "received_date": date_between(rng, "2026-01-01", "2026-06-30"),
                "subject_name": app["legal_name"],
                "item_type": rng.choice(
                    ["public inquiry", "certificate upload", "address correction", "material notice"]
                ),
                "summary": rng.choice(
                    [
                        "Applicant uploaded certificate copy.",
                        "Public inquiry references a similarly named contractor.",
                        "Mailroom indexed address correction for the application file.",
                        "Reviewer requested updated financial statement.",
                    ]
                ),
                "affects_application_id": app["application_id"],
                "document_status": rng.choice(["indexed", "needs_review", "closed"]),
            }
        )

    return (
        {
            "contractor_applications": applications,
            "contractor_bonds": bonds,
            "contractor_insurance": insurance,
            "contractor_violations": violations,
            "contractor_complaints": complaints,
            "contractor_field_notes": field_notes,
            "contractor_correspondence": correspondence,
            "contractor_bulletins": build_contractor_bulletins(),
        },
        anchor_metadata,
    )


def build_alcohol_domain() -> tuple[dict[str, list[dict]], dict]:
    rng = random.Random(SEEDS["alcohol"])
    cities = ["Port Mason", "Lakeview", "Silverton", "Cedar Falls", "Bay Crossing"]
    street_names = ["Market", "Pine", "Union", "Harbor", "Cedar", "Summit", "Front", "Rail", "Orchard", "Mill"]
    dba_words = [
        "Lantern",
        "Juniper",
        "Copper",
        "Waypoint",
        "Mosaic",
        "Harbor",
        "Foundry",
        "Garden",
        "Anchor",
        "Signal",
    ]
    review_months = ["2026-02", "2026-03", "2026-05", "2026-04", "2026-06"]
    license_types = ["F-COM", "TAVERN", "BREWPUB", "F-RTL"]

    anchor_premises = {
        "2026-02": [
            ("PM-2026-003", ["SAME_PREMISES_OVERLAP", "STANDARD_OBLIGATION", "INCIDENT_HISTORY"]),
            ("PM-2026-011", ["VERIFICATION_GAP", "PRIOR_SETTLEMENT"]),
        ],
        "2026-03": [
            ("PM-2026-018", ["SAME_PREMISES_OVERLAP", "CONTROL_OVERLAP", "FIRST_90_DAY_CHECK"]),
            ("PM-2026-024", ["STANDARD_OBLIGATION", "INCIDENT_HISTORY"]),
        ],
        "2026-05": [
            ("PM-2026-036", ["SAME_PREMISES_OVERLAP", "CONTROL_OVERLAP", "VERIFICATION_GAP"]),
            ("PM-2026-044", ["PRIOR_SETTLEMENT", "FIRST_90_DAY_CHECK"]),
        ],
    }

    premises: list[dict] = []
    applications: list[dict] = []
    anchor_metadata: dict[str, list[dict]] = {"2026-02": [], "2026-03": [], "2026-05": []}
    premises_tags: dict[str, list[str]] = {}

    for idx in range(1, 57):
        premises_id = f"PM-2026-{idx:03d}"
        city = cities[idx % len(cities)]
        address = f"{100 + idx * 7} {street_names[idx % len(street_names)]} St"
        current_dba = f"{dba_words[idx % len(dba_words)]} Room {idx:02d}"
        prior_licensee = f"{dba_words[(idx + 3) % len(dba_words)]} Hospitality LLC"
        month = review_months[idx % len(review_months)]
        issue_tags: list[str] = []
        for anchor_month, specs in anchor_premises.items():
            for anchor_id, tags in specs:
                if premises_id == anchor_id:
                    month = anchor_month
                    issue_tags = tags
        if not issue_tags and rng.random() < 0.22:
            issue_tags = rng.choice(
                [
                    ["INCIDENT_HISTORY"],
                    ["PRIOR_SETTLEMENT"],
                    ["STANDARD_OBLIGATION"],
                    ["VERIFICATION_GAP"],
                    ["SAME_PREMISES_OVERLAP"],
                ]
            )
        premises_tags[premises_id] = issue_tags
        same_basis = "none"
        risk_summary = "No current same-premises issue found in public history."
        if "SAME_PREMISES_OVERLAP" in issue_tags:
            same_basis = "same address and overlapping service area as prior licensee"
            risk_summary = "Prior same-premises operation had incidents that overlap proposed controls."
        elif "PRIOR_SETTLEMENT" in issue_tags:
            same_basis = "prior settlement at address"
            risk_summary = "Settlement history requires restriction comparison before issuance."
        premises.append(
            {
                "premises_id": premises_id,
                "address": address,
                "city": city,
                "current_dba": current_dba,
                "same_premises_basis": same_basis,
                "prior_licensee": prior_licensee,
                "risk_summary": risk_summary,
            }
        )
        application_id = f"AA-2026-{idx:04d}"
        license_type = license_types[idx % len(license_types)]
        applications.append(
            {
                "application_id": application_id,
                "premises_id": premises_id,
                "applicant_name": f"{current_dba} License Group LLC",
                "dba": current_dba,
                "address": address,
                "city": city,
                "license_type": license_type,
                "review_month": month,
                "requested_posture": "restricted issuance"
                if issue_tags
                else rng.choice(["standard issuance", "restricted issuance", "follow-up needed"]),
            }
        )
        if month in anchor_metadata and issue_tags:
            anchor_metadata[month].append(
                {
                    "application_id": application_id,
                    "premises_id": premises_id,
                    "dba": current_dba,
                    "issue_tags": issue_tags,
                }
            )

    incident_types = [
        "service to visibly intoxicated patron",
        "minor on premises",
        "late-night disorder",
        "noise complaint",
        "security plan lapse",
        "assault call",
    ]
    incidents: list[dict] = []
    for premise in premises:
        tags = premises_tags[premise["premises_id"]]
        base_count = 1 if "INCIDENT_HISTORY" in tags else 0
        if "SAME_PREMISES_OVERLAP" in tags:
            base_count += 2
        for _ in range(base_count):
            incidents.append(
                {
                    "incident_id": f"AI-2026-{len(incidents) + 1:04d}",
                    "premises_id": premise["premises_id"],
                    "incident_date": date_between(rng, "2023-01-01", "2026-05-31"),
                    "incident_type": rng.choice(incident_types),
                    "severity": rng.choices(["low", "medium", "high"], weights=[18, 48, 34])[0],
                    "disposition": rng.choice(["warning", "citation", "settled", "pending", ""]),
                    "source": rng.choice(
                        ["police call log", "license inspection", "public complaint", "settlement exhibit"]
                    ),
                }
            )
    while len(incidents) < 150:
        premise = rng.choice(premises)
        incidents.append(
            {
                "incident_id": f"AI-2026-{len(incidents) + 1:04d}",
                "premises_id": premise["premises_id"],
                "incident_date": date_between(rng, "2022-01-01", "2026-06-30"),
                "incident_type": rng.choice(incident_types),
                "severity": rng.choices(["low", "medium", "high"], weights=[50, 35, 15])[0],
                "disposition": rng.choice(["warning", "citation", "settled", "pending", "", "no violation found"]),
                "source": rng.choice(
                    ["police call log", "license inspection", "public complaint", "neighborhood letter"]
                ),
            }
        )

    settlements: list[dict] = []
    settlement_premises = [premise for premise in premises if premises_tags[premise["premises_id"]]]
    while len(settlement_premises) < 34:
        candidate = rng.choice(premises)
        if candidate not in settlement_premises:
            settlement_premises.append(candidate)
    for premise in settlement_premises[:34]:
        tags = premises_tags[premise["premises_id"]]
        settlements.append(
            {
                "settlement_id": f"AS-2026-{len(settlements) + 1:04d}",
                "premises_id": premise["premises_id"],
                "settlement_date": date_between(rng, "2022-01-01", "2026-04-30"),
                "prior_or_current": "prior" if "SAME_PREMISES_OVERLAP" in tags or rng.random() < 0.7 else "current",
                "original_posture": rng.choice(["deny", "suspend", "restricted issue", "warning"]),
                "final_terms_summary": rng.choice(
                    [
                        "Restricted late-night service and required door logs.",
                        "Required security staffing and incident reporting.",
                        "Settlement allowed operation with age-verification controls.",
                        "Noise abatement and quarterly inspection condition.",
                    ]
                ),
            }
        )

    restrictions: list[dict] = []
    restriction_specs = [
        (
            "NO_AFTER_MIDNIGHT_SERVICE",
            "No alcohol service after midnight",
            "premises-specific",
            "00:00",
            "06:00",
            "service log",
        ),
        ("SECURITY_LOG", "Maintain security staffing and incident log", "premises-specific", "", "", "weekly log"),
        (
            "AGE_CHECK",
            "Electronic age-verification for all alcohol sales",
            "premises-specific",
            "",
            "",
            "device audit",
        ),
        ("PATIO_LIMIT", "Close patio service by 10 PM", "premises-specific", "22:00", "06:00", "patio closure log"),
        ("TRAINING_STANDARD", "Server training evidence required", "standard-obligation", "", "", "training roster"),
        (
            "FOOD_SERVICE",
            "Maintain required food service during alcohol sales",
            "standard-obligation",
            "",
            "",
            "menu and receipts",
        ),
    ]
    for settlement in settlements:
        count = 2 if len(restrictions) < 58 else 1
        for _ in range(count):
            code, description, category, start_time, end_time, evidence = rng.choice(restriction_specs)
            restrictions.append(
                {
                    "restriction_id": f"AR-2026-{len(restrictions) + 1:04d}",
                    "premises_id": settlement["premises_id"],
                    "settlement_id": settlement["settlement_id"],
                    "restriction_code": code,
                    "description": description,
                    "category": category,
                    "start_time": start_time,
                    "end_time": end_time,
                    "evidence_required": evidence,
                }
            )
            if len(restrictions) >= 65:
                break
        if len(restrictions) >= 65:
            break

    obligations: list[dict] = []
    obligation_specs = {
        "F-COM": [
            ("F_COM_FOOD", "Maintain commercial food service while alcohol is sold.", "menu, invoices"),
            ("F_COM_SERVER", "Keep server training records on site.", "training roster"),
            ("F_COM_MINORS", "Post minor-access restrictions at entrances.", "photo evidence"),
        ],
        "TAVERN": [
            ("TAVERN_AGE", "Verify age for all alcohol service.", "inspection log"),
            ("TAVERN_HOURS", "Comply with licensed hours and closing checks.", "closing log"),
            ("TAVERN_SECURITY", "Maintain incident response plan.", "security plan"),
        ],
        "BREWPUB": [
            ("BREW_PRODUCTION", "Maintain production-area separation.", "floor plan"),
            ("BREW_SAMPLES", "Track sample service limits.", "sample log"),
            ("BREW_TRAINING", "Keep alcohol server permits current.", "permit roster"),
        ],
        "F-RTL": [
            ("RTL_DISPLAY", "Display license and age signage.", "photo evidence"),
            ("RTL_SALES", "Maintain off-premises sale controls.", "sales audit"),
            ("RTL_STAFF", "Train clerks on restricted sales.", "training roster"),
        ],
    }
    for license_type, specs in obligation_specs.items():
        for code, description, evidence in specs:
            obligations.append(
                {
                    "obligation_id": f"AO-2026-{len(obligations) + 1:04d}",
                    "license_type": license_type,
                    "obligation_code": code,
                    "description": description,
                    "evidence_required": evidence,
                }
            )
    obligations.extend(
        [
            {
                "obligation_id": "AO-2026-0013",
                "license_type": "ALL",
                "obligation_code": "PUBLIC_RECORDS",
                "description": "Keep licensing records available for inspection.",
                "evidence_required": "records binder",
            },
            {
                "obligation_id": "AO-2026-0014",
                "license_type": "ALL",
                "obligation_code": "INCIDENT_REPORT",
                "description": "Report severe incidents to the board within required timelines.",
                "evidence_required": "incident report log",
            },
        ]
    )

    return (
        {
            "alcohol_applications": applications,
            "alcohol_premises": premises,
            "alcohol_incidents": incidents,
            "alcohol_settlements": settlements,
            "alcohol_restrictions": restrictions,
            "alcohol_standard_obligations": obligations,
        },
        anchor_metadata,
    )


def close_match_name(name: str, rng: random.Random) -> str:
    replacements = [
        ("Grill", "Grille"),
        ("Market", "Mkt"),
        ("Cafe", "Cafe and Bar"),
        ("Room", "Rm"),
        ("House", "Haus"),
        ("Kitchen", "Kitch"),
    ]
    for old, new in replacements:
        if old in name:
            return name.replace(old, new)
    return f"{name} Formerly"


def build_renewal_domain() -> tuple[dict[str, list[dict]], dict]:
    rng = random.Random(SEEDS["renewals"])
    batches = [("RV-2026-SPRING", 50), ("RV-2026-SUMMER", 52), ("RV-2026-FALL", 54)]
    cities = ["Port Mason", "Lakeview", "Silverton", "Cedar Falls", "Bay Crossing", "Northport"]
    channels = ["bar", "restaurant", "grocery", "club", "hotel", "music venue"]
    license_types = ["F-COM", "TAVERN", "F-RTL", "BREWPUB"]
    street_names = [
        "Market",
        "Pine",
        "Union",
        "Harbor",
        "Cedar",
        "Summit",
        "Front",
        "Rail",
        "Orchard",
        "Mill",
        "Dock",
        "State",
    ]
    name_words = [
        "Blue",
        "Maple",
        "Signal",
        "Copper",
        "Drift",
        "Civic",
        "Hearth",
        "Pier",
        "Crescent",
        "Urban",
        "Depot",
        "Vista",
    ]
    second_words = [
        "Grill",
        "Market",
        "Cafe",
        "Room",
        "House",
        "Kitchen",
        "Tap",
        "Bottle",
        "Lounge",
        "Diner",
        "Cellar",
        "Hall",
    ]
    release_boundaries = {
        "RV-2026-SPRING": "2026-04-15",
        "RV-2026-SUMMER": "2026-07-15",
        "RV-2026-FALL": "2026-10-15",
    }
    anchor_patterns = {
        "RV-2026-SPRING": [
            ["EXACT_MATCH", "ALERT_PATTERN"],
            ["CLOSE_MATCH"],
            ["SHARED_ADDRESS"],
            ["FINE_HISTORY"],
            ["POST_BOUNDARY"],
            ["SEVERE_CONDUCT"],
            ["NO_REVIEW"],
            ["EXACT_MATCH"],
            ["CLOSE_MATCH", "FINE_HISTORY"],
            ["ALERT_PATTERN"],
        ],
        "RV-2026-SUMMER": [
            ["EXACT_MATCH", "ALERT_PATTERN"],
            ["CLOSE_MATCH"],
            ["SHARED_ADDRESS"],
            ["POST_BOUNDARY"],
            ["FINE_HISTORY"],
            ["SEVERE_CONDUCT"],
            ["EXACT_MATCH"],
            ["CLOSE_MATCH", "ALERT_PATTERN"],
            ["NO_REVIEW"],
            ["SHARED_ADDRESS"],
            ["FINE_HISTORY"],
            ["POST_BOUNDARY"],
        ],
        "RV-2026-FALL": [
            ["EXACT_MATCH"],
            ["CLOSE_MATCH"],
            ["ALERT_PATTERN"],
            ["SHARED_ADDRESS"],
            ["SEVERE_CONDUCT"],
            ["POST_BOUNDARY"],
            ["FINE_HISTORY"],
            ["CLOSE_MATCH", "FINE_HISTORY"],
            ["NO_REVIEW"],
            ["EXACT_MATCH", "ALERT_PATTERN"],
            ["SHARED_ADDRESS"],
            ["POST_BOUNDARY"],
        ],
    }

    licensees: list[dict] = []
    anchor_metadata: dict[str, list[dict]] = {batch: [] for batch, _ in batches}
    license_tags: dict[str, list[str]] = {}
    idx = 0
    for batch, count in batches:
        for local_idx in range(count):
            idx += 1
            facility_name = f"{name_words[idx % len(name_words)]} {second_words[(idx // len(name_words)) % len(second_words)]} {idx:03d}"
            city = cities[idx % len(cities)]
            address_number = 200 + idx * 5
            if local_idx in {2, 9}:
                address_number = 777
            address = f"{address_number} {street_names[idx % len(street_names)]} Ave"
            license_id = f"LIC-RV-2026-{idx:04d}"
            tags = (
                anchor_patterns.get(batch, [])[local_idx]
                if local_idx < len(anchor_patterns.get(batch, []))
                else rng.choice(
                    [
                        ["NO_REVIEW"],
                        ["EXACT_MATCH"],
                        ["CLOSE_MATCH"],
                        ["FINE_HISTORY"],
                        ["POST_BOUNDARY"],
                        ["ALERT_PATTERN"],
                    ]
                )
            )
            license_tags[license_id] = tags
            successor_hint = ""
            if "CLOSE_MATCH" in tags:
                successor_hint = close_match_name(facility_name, rng)
            if idx in {22, 86, 129}:
                successor_hint = "successor at prior restricted premises"
            licensees.append(
                {
                    "license_id": license_id,
                    "facility_name": facility_name,
                    "legal_name": f"{facility_name} Operations LLC",
                    "address": address,
                    "city": city,
                    "channel_type": channels[idx % len(channels)],
                    "license_type": license_types[idx % len(license_types)],
                    "status": rng.choices(["active", "conditional", "pending renewal"], weights=[78, 14, 8])[0],
                    "release_batch": batch,
                    "successor_hint": successor_hint,
                }
            )
            if local_idx < len(anchor_patterns.get(batch, [])):
                anchor_metadata[batch].append(
                    {
                        "license_id": license_id,
                        "facility_name": facility_name,
                        "address": address,
                        "issue_tags": tags,
                    }
                )

    violation_codes = [
        "LATE_RENEWAL",
        "MINOR_SALE",
        "ALERT",
        "UNPAID_FINE",
        "SUSPENSION",
        "DISORDER",
        "INSPECTION_FAIL",
        "NOISE",
    ]
    themes = [
        "administrative",
        "minor service",
        "ALERT pattern",
        "fine collection",
        "board sanction",
        "public safety",
        "inspection",
        "neighborhood impact",
    ]
    violations: list[dict] = []
    for licensee in licensees:
        tags = license_tags[licensee["license_id"]]
        boundary = release_boundaries[licensee["release_batch"]]
        count = 0
        if "NO_REVIEW" not in tags:
            count += 1
        if "ALERT_PATTERN" in tags or "FINE_HISTORY" in tags or "SEVERE_CONDUCT" in tags:
            count += 1
        if "POST_BOUNDARY" in tags:
            count += 1
        for entry_index in range(count):
            historical_name = licensee["facility_name"]
            if "CLOSE_MATCH" in tags and entry_index == 0:
                historical_name = close_match_name(licensee["facility_name"], rng)
            violation_date = date_between(rng, "2024-01-01", date_add(boundary, -1))
            if "POST_BOUNDARY" in tags and entry_index == count - 1:
                violation_date = date_between(rng, date_add(boundary, 1), "2026-12-15")
            code = rng.choice(violation_codes)
            theme = themes[violation_codes.index(code)]
            alert_related = 1 if "ALERT_PATTERN" in tags or code == "ALERT" else 0
            fine = 0
            if "FINE_HISTORY" in tags or code in {"UNPAID_FINE", "MINOR_SALE", "SUSPENSION"}:
                fine = rng.choice([15000, 30000, 75000, 125000])
            severity = (
                "high"
                if "SEVERE_CONDUCT" in tags or code == "SUSPENSION"
                else rng.choices(["low", "medium", "high"], weights=[42, 42, 16])[0]
            )
            violations.append(
                {
                    "violation_id": f"RV-2026-{len(violations) + 1:04d}",
                    "historical_name": historical_name,
                    "address": licensee["address"],
                    "city": licensee["city"],
                    "violation_date": violation_date,
                    "violation_code": code,
                    "theme": theme,
                    "disposition": rng.choice(["paid", "warning", "settled", "suspended", "", "pending"]),
                    "fine_cents": fine,
                    "alert_related": alert_related,
                    "severity": severity,
                }
            )

    while len(violations) < 336:
        licensee = rng.choice(licensees)
        boundary = release_boundaries[licensee["release_batch"]]
        code = rng.choice(violation_codes)
        post_boundary = rng.random() < 0.16
        historical_name = licensee["facility_name"]
        if rng.random() < 0.18:
            historical_name = close_match_name(licensee["facility_name"], rng)
        address = licensee["address"]
        if rng.random() < 0.08:
            address = f"Suite B, {address}"
        violations.append(
            {
                "violation_id": f"RV-2026-{len(violations) + 1:04d}",
                "historical_name": historical_name,
                "address": address,
                "city": licensee["city"],
                "violation_date": date_between(rng, date_add(boundary, 1), "2026-12-20")
                if post_boundary
                else date_between(rng, "2023-01-01", date_add(boundary, -1)),
                "violation_code": code,
                "theme": themes[violation_codes.index(code)],
                "disposition": rng.choice(["paid", "warning", "settled", "suspended", "", "pending", "dismissed"]),
                "fine_cents": rng.choice([0, 0, 10000, 25000, 50000, 100000]),
                "alert_related": 1 if code == "ALERT" or rng.random() < 0.18 else 0,
                "severity": rng.choices(["low", "medium", "high"], weights=[52, 34, 14])[0],
            }
        )

    return (
        {
            "renewal_licensees": licensees,
            "renewal_violations": violations,
        },
        anchor_metadata,
    )


def record_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = [
        "contractor_applications",
        "contractor_bonds",
        "contractor_insurance",
        "contractor_violations",
        "contractor_complaints",
        "contractor_field_notes",
        "contractor_correspondence",
        "contractor_bulletins",
        "alcohol_applications",
        "alcohol_premises",
        "alcohol_incidents",
        "alcohol_settlements",
        "alcohol_restrictions",
        "alcohol_standard_obligations",
        "renewal_licensees",
        "renewal_violations",
    ]
    return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}


def api_summary() -> list[str]:
    return [
        "GET /health",
        "GET /api/contractors/applications?batch_id=...",
        "GET /api/contractors/bonds?name=...",
        "GET /api/contractors/insurance?name=...",
        "GET /api/contractors/violations?name=...",
        "GET /api/contractors/complaints?name=...",
        "GET /api/contractors/field-notes?name=...",
        "GET /api/contractors/correspondence?batch_id=...",
        "GET /api/contractors/bulletins?effective_on=YYYY-MM-DD",
        "GET /api/alcohol/applications?review_month=YYYY-MM",
        "GET /api/alcohol/premises?premises_id=...",
        "GET /api/alcohol/incidents?premises_id=...",
        "GET /api/alcohol/settlements?premises_id=...",
        "GET /api/alcohol/restrictions?premises_id=...",
        "GET /api/alcohol/standard-obligations?license_type=...",
        "GET /api/renewals/licensees?release_batch=...",
        "GET /api/renewals/violations?city=...",
        "GET /api/search/address?address=...",
        "GET /exports/contractor_batch_<batch_id>.csv",
        "GET /exports/renewal_roster_<release_batch>.csv",
    ]


def write_manifests(conn: sqlite3.Connection, anchors: dict) -> None:
    counts = record_counts(conn)
    public_manifest = {
        "environment": "Cascadia Licensing Review Portal",
        "task_group": "task_group_019",
        "generated_at": GENERATED_AT,
        "seed_values": SEEDS,
        "record_counts": counts,
        "generated_files": [
            "data/clrp.db",
            "data/public_manifest.json",
            "data/construction_manifest.json",
        ],
        "api_summary": api_summary(),
        "anchor_metadata": {
            "contractor_batches": {
                batch_id: {
                    "application_count": len(items),
                    "application_ids": [item["application_id"] for item in items],
                }
                for batch_id, items in anchors["contractor_batches"].items()
            },
            "alcohol_review_months": {
                month: {
                    "anchor_count": len(items),
                    "premises_ids": [item["premises_id"] for item in items],
                }
                for month, items in anchors["alcohol_review_months"].items()
            },
            "renewal_release_batches": {
                batch: {
                    "anchor_count": len(items),
                    "license_ids": [item["license_id"] for item in items],
                }
                for batch, items in anchors["renewal_release_batches"].items()
            },
        },
    }
    construction_manifest = {
        "environment": "Cascadia Licensing Review Portal",
        "task_group": "task_group_019",
        "generated_at": GENERATED_AT,
        "seed_values": SEEDS,
        "record_counts": counts,
        "anchor_metadata": anchors,
        "release_boundaries": {
            "RV-2026-SPRING": "2026-04-15",
            "RV-2026-SUMMER": "2026-07-15",
            "RV-2026-FALL": "2026-10-15",
        },
        "planned_inputs": {
            "contractor_train_batches": ["HS-2026-Q1A", "HS-2026-Q1B"],
            "contractor_test_batches": ["HS-2026-Q2A", "HS-2026-Q2B"],
            "alcohol_review_months": ["2026-02", "2026-03", "2026-05"],
            "renewal_train_batch": "RV-2026-SPRING",
            "renewal_test_batches": ["RV-2026-SUMMER", "RV-2026-FALL"],
        },
        "limitations": "Anchor tags identify intended review issues only; this manifest does not contain task-specific full answers.",
    }
    PUBLIC_MANIFEST_PATH.write_text(json.dumps(public_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    CONSTRUCTION_MANIFEST_PATH.write_text(
        json.dumps(construction_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def generate() -> dict[str, int]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    try:
        create_schema(conn)
        contractor_rows, contractor_anchors = build_contractor_domain()
        alcohol_rows, alcohol_anchors = build_alcohol_domain()
        renewal_rows, renewal_anchors = build_renewal_domain()

        for table, rows in contractor_rows.items():
            insert_many(conn, table, rows)
        for table, rows in alcohol_rows.items():
            insert_many(conn, table, rows)
        for table, rows in renewal_rows.items():
            insert_many(conn, table, rows)
        conn.commit()

        anchors = {
            "contractor_batches": contractor_anchors,
            "alcohol_review_months": alcohol_anchors,
            "renewal_release_batches": renewal_anchors,
        }
        write_manifests(conn, anchors)
        return record_counts(conn)
    finally:
        conn.close()


def main() -> None:
    counts = generate()
    print(f"Generated {DB_PATH}")
    for table in sorted(counts):
        print(f"{table}: {counts[table]}")
    print(f"Wrote {PUBLIC_MANIFEST_PATH}")
    print(f"Wrote {CONSTRUCTION_MANIFEST_PATH}")


if __name__ == "__main__":
    main()
