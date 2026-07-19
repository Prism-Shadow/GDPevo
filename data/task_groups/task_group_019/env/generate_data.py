import json
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path


SEED = 19019
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "licensing.db"
MANIFEST_PATH = DATA_DIR / "manifest.json"

CONTRACTOR_TARGETS = {
    "train_001": [f"C-TR1-{idx:03d}" for idx in range(1, 9)],
    "train_004": [f"C-TR4-{idx:03d}" for idx in range(1, 8)],
    "test_001": [f"C-TE1-{idx:03d}" for idx in range(1, 10)],
    "test_004": [f"C-TE4-{idx:03d}" for idx in range(1, 16)],
}

LIQUOR_TARGETS = {
    "train_002": {"application_id": "L-TR2-001", "location_id": "LOC-TR2"},
    "train_005": {"application_id": "L-TR5-001", "location_id": "LOC-TR5"},
    "test_003": {"application_id": "L-TE3-001", "location_id": "LOC-TE3"},
}

RENEWAL_TARGETS = {
    "train_003": {
        "target_queue_size": 10,
        "boundary": "2025-04-10",
        "prefix": "AL-TR3",
    },
    "test_002": {
        "target_queue_size": 12,
        "boundary": "2025-06-15",
        "prefix": "AL-TE2",
    },
    "test_005": {
        "target_queue_size": 8,
        "boundary": "2025-05-20",
        "prefix": "AL-TE5",
    },
}

RENEWAL_NON_EXACT_CASES = {
    "train_003": {
        "current_idx": 6,
        "old_license_no": "AL-TR3-OLD-006",
        "match_basis": "successor_to",
        "expected_match_confidence": "successor",
        "current_exact_violations": [
            {
                "suffix": "1",
                "days_before": 86,
                "theme": "missing posting",
                "severity": "minor",
                "disposition": "warning",
                "fine_balance": 0.0,
                "alert_flag": 0,
            }
        ],
        "old_violations": [
            {
                "suffix": "S1",
                "days_before": 11,
                "theme": "sale to minor",
                "severity": "serious",
                "disposition": "open",
                "fine_balance": 0.0,
                "alert_flag": 1,
            },
            {
                "suffix": "S2",
                "days_before": 28,
                "theme": "unpaid fine",
                "severity": "serious",
                "disposition": "pending",
                "fine_balance": 500.0,
                "alert_flag": 1,
            },
        ],
    },
    "test_002": {
        "current_idx": 12,
        "old_license_no": "AL-TE2-OLD-012",
        "match_basis": "successor_to",
        "expected_match_confidence": "successor",
        "current_exact_violations": [
            {
                "suffix": "1",
                "days_before": 74,
                "theme": "late renewal",
                "severity": "minor",
                "disposition": "warning",
                "fine_balance": 0.0,
                "alert_flag": 0,
            }
        ],
        "old_violations": [
            {
                "suffix": "S1",
                "days_before": 5,
                "theme": "sale to minor",
                "severity": "serious",
                "disposition": "open",
                "fine_balance": 0.0,
                "alert_flag": 1,
            },
            {
                "suffix": "S2",
                "days_before": 23,
                "theme": "after hours",
                "severity": "serious",
                "disposition": "pending",
                "fine_balance": 450.0,
                "alert_flag": 1,
            },
        ],
    },
    "test_005": {
        "current_idx": 3,
        "old_license_no": "AL-TE5-OLD-003",
        "old_address": "233 Lincoln Avenue",
        "match_basis": "successor_to_close_address",
        "expected_match_confidence": "close_successor",
        "current_exact_violations": [
            {
                "suffix": "1",
                "days_before": 61,
                "theme": "missing posting",
                "severity": "minor",
                "disposition": "warning",
                "fine_balance": 0.0,
                "alert_flag": 0,
            }
        ],
        "old_violations": [
            {
                "suffix": "S1",
                "days_before": 4,
                "theme": "sale to minor",
                "severity": "serious",
                "disposition": "open",
                "fine_balance": 0.0,
                "alert_flag": 1,
            },
            {
                "suffix": "S2",
                "days_before": 29,
                "theme": "unpaid fine",
                "severity": "serious",
                "disposition": "pending",
                "fine_balance": 350.0,
                "alert_flag": 1,
            },
        ],
    },
}

TABLES = [
    "policies",
    "contractor_applications",
    "contractor_bonds",
    "contractor_insurance",
    "contractor_license_history",
    "contractor_violations",
    "contractor_correspondence",
    "contractor_inspections",
    "liquor_applications",
    "liquor_settlements",
    "liquor_privileges",
    "liquor_incidents",
    "liquor_site_evidence",
    "alcohol_licensees",
    "alcohol_violations",
    "renewal_rules",
]

TRADE_CONFIGS = [
    {
        "trade": "Electrical",
        "requested_class": "Class A",
        "min_bond": 50000,
        "min_insurance": 1000000,
        "experience": 5,
        "endorsement": "EE-1",
    },
    {
        "trade": "Plumbing",
        "requested_class": "Class B",
        "min_bond": 30000,
        "min_insurance": 750000,
        "experience": 4,
        "endorsement": "PH-2",
    },
    {
        "trade": "HVAC",
        "requested_class": "Class B",
        "min_bond": 25000,
        "min_insurance": 500000,
        "experience": 3,
        "endorsement": "MECH-H",
    },
    {
        "trade": "General Building",
        "requested_class": "Class A",
        "min_bond": 75000,
        "min_insurance": 1000000,
        "experience": 5,
        "endorsement": "GB-A",
    },
    {
        "trade": "Roofing",
        "requested_class": "Limited",
        "min_bond": 20000,
        "min_insurance": 500000,
        "experience": 2,
        "endorsement": None,
    },
    {
        "trade": "Solar",
        "requested_class": "Specialty",
        "min_bond": 30000,
        "min_insurance": 750000,
        "experience": 3,
        "endorsement": "SOL-PLUS",
    },
]


def iso(year, month, day):
    return date(year, month, day).isoformat()


def date_between(rng, start, end):
    span = (end - start).days
    return (start + timedelta(days=rng.randint(0, span))).isoformat()


def insert_many(cur, table, rows):
    if not rows:
        return
    keys = list(rows[0].keys())
    placeholders = ", ".join(["?"] * len(keys))
    columns = ", ".join(keys)
    cur.executemany(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
        [tuple(row[key] for key in keys) for row in rows],
    )


def create_schema(cur):
    for table in reversed(TABLES):
        cur.execute(f"DROP TABLE IF EXISTS {table}")

    cur.executescript(
        """
        CREATE TABLE policies (
            policy_id TEXT PRIMARY KEY,
            agency TEXT NOT NULL,
            family TEXT NOT NULL,
            effective_date TEXT NOT NULL,
            title TEXT NOT NULL,
            citation TEXT NOT NULL,
            rule_code TEXT NOT NULL,
            details_json TEXT NOT NULL
        );

        CREATE TABLE contractor_applications (
            application_id TEXT PRIMARY KEY,
            applicant_name TEXT NOT NULL,
            trade TEXT NOT NULL,
            county TEXT NOT NULL,
            submitted_date TEXT NOT NULL,
            years_experience INTEGER NOT NULL,
            endorsement_status TEXT NOT NULL,
            prior_license_id TEXT,
            requested_class TEXT NOT NULL,
            self_disclosed_issue TEXT,
            target_group TEXT
        );

        CREATE TABLE contractor_bonds (
            bond_id TEXT PRIMARY KEY,
            application_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL,
            effective_date TEXT NOT NULL,
            cancel_date TEXT,
            source_date TEXT NOT NULL,
            surety TEXT NOT NULL
        );

        CREATE TABLE contractor_insurance (
            insurance_id TEXT PRIMARY KEY,
            application_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL,
            verified_date TEXT NOT NULL,
            expiration_date TEXT NOT NULL,
            insurer TEXT NOT NULL
        );

        CREATE TABLE contractor_license_history (
            license_id TEXT PRIMARY KEY,
            applicant_name TEXT NOT NULL,
            status TEXT NOT NULL,
            status_date TEXT NOT NULL,
            trade TEXT NOT NULL,
            notes TEXT
        );

        CREATE TABLE contractor_violations (
            violation_id TEXT PRIMARY KEY,
            related_application_id TEXT,
            license_id TEXT,
            violation_date TEXT NOT NULL,
            severity TEXT NOT NULL,
            theme TEXT NOT NULL,
            status TEXT NOT NULL,
            resolved_date TEXT
        );

        CREATE TABLE contractor_correspondence (
            correspondence_id TEXT PRIMARY KEY,
            related_application_id TEXT NOT NULL,
            received_date TEXT NOT NULL,
            subject TEXT NOT NULL,
            assertion_type TEXT NOT NULL,
            assertion_value TEXT NOT NULL,
            verified_by_agency INTEGER NOT NULL,
            notes TEXT
        );

        CREATE TABLE contractor_inspections (
            inspection_id TEXT PRIMARY KEY,
            related_application_id TEXT NOT NULL,
            inspection_date TEXT NOT NULL,
            result TEXT NOT NULL,
            finding_code TEXT NOT NULL,
            notes TEXT
        );

        CREATE TABLE liquor_applications (
            application_id TEXT PRIMARY KEY,
            agency TEXT NOT NULL,
            applicant_name TEXT NOT NULL,
            dba TEXT NOT NULL,
            address TEXT NOT NULL,
            license_class TEXT NOT NULL,
            location_id TEXT NOT NULL,
            submitted_date TEXT NOT NULL,
            requested_posture TEXT NOT NULL,
            target_group TEXT
        );

        CREATE TABLE liquor_settlements (
            settlement_id TEXT PRIMARY KEY,
            location_id TEXT NOT NULL,
            effective_date TEXT NOT NULL,
            settlement_type TEXT NOT NULL,
            basis_code TEXT NOT NULL,
            controls_json TEXT NOT NULL,
            source_name TEXT NOT NULL
        );

        CREATE TABLE liquor_privileges (
            privilege_id TEXT PRIMARY KEY,
            license_class TEXT NOT NULL,
            obligation_code TEXT NOT NULL,
            description TEXT NOT NULL,
            standard_required INTEGER NOT NULL
        );

        CREATE TABLE liquor_incidents (
            incident_id TEXT PRIMARY KEY,
            location_id TEXT NOT NULL,
            incident_date TEXT NOT NULL,
            risk_code TEXT NOT NULL,
            severity TEXT NOT NULL,
            status TEXT NOT NULL,
            source_name TEXT NOT NULL
        );

        CREATE TABLE liquor_site_evidence (
            evidence_id TEXT PRIMARY KEY,
            location_id TEXT NOT NULL,
            evidence_date TEXT NOT NULL,
            evidence_code TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT
        );

        CREATE TABLE alcohol_licensees (
            license_no TEXT PRIMARY KEY,
            agency TEXT NOT NULL,
            facility_name TEXT NOT NULL,
            address TEXT NOT NULL,
            channel_type TEXT NOT NULL,
            active INTEGER NOT NULL,
            location_id TEXT NOT NULL,
            successor_to TEXT,
            target_group TEXT
        );

        CREATE TABLE alcohol_violations (
            violation_id TEXT PRIMARY KEY,
            license_no TEXT NOT NULL,
            facility_name TEXT NOT NULL,
            address TEXT NOT NULL,
            violation_date TEXT NOT NULL,
            theme TEXT NOT NULL,
            severity TEXT NOT NULL,
            disposition TEXT NOT NULL,
            fine_balance REAL NOT NULL,
            alert_flag INTEGER NOT NULL,
            source_name TEXT NOT NULL
        );

        CREATE TABLE renewal_rules (
            rule_id TEXT PRIMARY KEY,
            agency TEXT NOT NULL,
            effective_date TEXT NOT NULL,
            release_boundary TEXT NOT NULL,
            title TEXT NOT NULL,
            details_json TEXT NOT NULL
        );
        """
    )

    index_statements = [
        "CREATE INDEX idx_contractor_app_target ON contractor_applications(target_group)",
        "CREATE INDEX idx_contractor_bonds_app ON contractor_bonds(application_id)",
        "CREATE INDEX idx_contractor_ins_app ON contractor_insurance(application_id)",
        "CREATE INDEX idx_contractor_viol_app ON contractor_violations(related_application_id)",
        "CREATE INDEX idx_liquor_apps_location ON liquor_applications(location_id)",
        "CREATE INDEX idx_liquor_settlements_location ON liquor_settlements(location_id)",
        "CREATE INDEX idx_liquor_incidents_location ON liquor_incidents(location_id)",
        "CREATE INDEX idx_alcohol_licensees_target ON alcohol_licensees(target_group)",
        "CREATE INDEX idx_alcohol_violations_license ON alcohol_violations(license_no)",
        "CREATE INDEX idx_alcohol_violations_date ON alcohol_violations(violation_date)",
    ]
    for statement in index_statements:
        cur.execute(statement)


def build_policy_rows():
    rows = []
    for idx, cfg in enumerate(TRADE_CONFIGS, start=1):
        rows.append(
            {
                "policy_id": f"POL-CON-{idx:03d}",
                "agency": "State Contractors Licensing Board",
                "family": "contractor",
                "effective_date": "2025-01-01" if idx % 2 else "2025-03-15",
                "title": f"{cfg['trade']} {cfg['requested_class']} application standards",
                "citation": f"SCLB 2025-{idx:02d}",
                "rule_code": f"CON-{cfg['trade'][:3].upper()}-{cfg['requested_class'].replace(' ', '')}",
                "details_json": json.dumps(
                    {
                        "minimum_bond": cfg["min_bond"],
                        "minimum_insurance": cfg["min_insurance"],
                        "minimum_years_experience": cfg["experience"],
                        "required_endorsement": cfg["endorsement"],
                        "serious_open_violation_blocks": True,
                    },
                    sort_keys=True,
                ),
            }
        )

    extra_policies = [
        (
            "POL-CON-LEGACY",
            "contractor",
            "2024-01-01",
            "Prior contractor review baseline",
            "SCLB 2024-10",
            "CON-LEGACY",
            {
                "minimum_bond_reduction": 10000,
                "endorsement_required_for_specialty": False,
                "use_for_prior_rule_comparison": True,
            },
        ),
        (
            "POL-LIQ-001",
            "liquor",
            "2024-11-20",
            "Restricted premises control review",
            "ABC 4.18",
            "LIQ-SETTLEMENT-CONTROLS",
            {
                "same_premises_history_matters": True,
                "current_site_evidence_required": True,
                "standard_privileges_separate_from_controls": True,
            },
        ),
        (
            "POL-LIQ-002",
            "liquor",
            "2025-02-01",
            "Incident severity matrix",
            "ABC 7.04",
            "LIQ-RISK-MATRIX",
            {"major_incidents_trigger_board_review": True},
        ),
        (
            "POL-REN-001",
            "renewal",
            "2025-01-01",
            "Renewal hold release export boundary",
            "OLCC REN-2025",
            "REN-BOUNDARY",
            {
                "known_on_or_before_boundary_only": True,
                "exact_license_match_preferred": True,
                "successor_match_mark_uncertain": True,
            },
        ),
    ]
    for policy_id, family, effective, title, citation, rule_code, details in extra_policies:
        rows.append(
            {
                "policy_id": policy_id,
                "agency": "Office of Licensing Review",
                "family": family,
                "effective_date": effective,
                "title": title,
                "citation": citation,
                "rule_code": rule_code,
                "details_json": json.dumps(details, sort_keys=True),
            }
        )
    return rows


def build_privilege_rows():
    classes = ["Tavern", "Restaurant", "BeerWine", "Package"]
    obligations = [
        ("ID_CHECK", "Age verification procedures at point of sale", 1),
        ("HOURS", "Restricted operating hours must be posted", 1),
        ("SECURITY", "Security staffing during late service windows", 0),
        ("FOOD_SERVICE", "Meal availability during alcohol service", 1),
        ("CCTV", "Camera coverage for entry and sale points", 0),
        ("PATIO", "Outdoor service plan and boundary markers", 0),
        ("NOISE", "Noise mitigation log for residential adjacency", 0),
        ("DELIVERY", "Delivery endorsement controls", 0),
    ]
    rows = []
    idx = 1
    for license_class in classes:
        for obligation, description, required in obligations:
            if license_class == "Package" and obligation in {"FOOD_SERVICE", "PATIO"}:
                continue
            if license_class == "BeerWine" and obligation == "DELIVERY":
                continue
            rows.append(
                {
                    "privilege_id": f"PRV-{idx:03d}",
                    "license_class": license_class,
                    "obligation_code": obligation,
                    "description": description,
                    "standard_required": required,
                }
            )
            idx += 1
    return rows


def build_renewal_rules():
    rule_specs = [
        ("REN-001", "2025-01-01", "2025-04-10", "Spring early release review"),
        ("REN-002", "2025-02-15", "2025-05-20", "Spring late release review"),
        ("REN-003", "2025-03-01", "2025-06-15", "Summer release review"),
        ("REN-004", "2024-12-01", "2025-03-01", "Legacy alert migration"),
        ("REN-005", "2025-06-01", "2025-07-15", "Post-release monitoring"),
    ]
    rows = []
    for rule_id, effective, boundary, title in rule_specs:
        rows.append(
            {
                "rule_id": rule_id,
                "agency": "Alcohol Renewal Unit",
                "effective_date": effective,
                "release_boundary": boundary,
                "title": title,
                "details_json": json.dumps(
                    {
                        "use_violations_on_or_before": boundary,
                        "late_rows_are_distractors": True,
                        "unpaid_fines_require_hold": True,
                        "alert_flag_requires_manual_review": True,
                    },
                    sort_keys=True,
                ),
            }
        )
    return rows


def build_contractor_data(rng):
    counties = ["Summit", "Lake", "Canyon", "Redwood", "Prairie", "Harbor"]
    name_roots = [
        "Alder",
        "Blue Ridge",
        "Cedar",
        "Delta",
        "Evergreen",
        "Frontier",
        "Granite",
        "Harborline",
        "Ironwood",
        "Juniper",
        "Keystone",
        "Larch",
        "Mesa",
        "Northbank",
        "Orchard",
        "Pioneer",
        "Quartz",
        "Riverview",
        "Sage",
        "Timber",
    ]
    sureties = [
        "Union Surety",
        "Civic Bonding",
        "Northwest Indemnity",
        "Granite Mutual",
        "Harbor Surety",
    ]
    insurers = [
        "Civic Risk Pool",
        "Northfield Casualty",
        "Evergreen Commercial",
        "Builders Mutual",
        "Prairie Shield",
    ]

    applications = []
    bonds = []
    insurance = []
    histories = []
    violations = []
    correspondence = []
    inspections = []
    manifest_targets = {}

    target_offsets = {"train_001": 0, "train_004": 1, "test_001": 2, "test_004": 3}

    def add_application(app_id, target_group, idx, is_target):
        cfg = TRADE_CONFIGS[(idx + target_offsets.get(target_group, 0)) % len(TRADE_CONFIGS)]
        applicant_name = (
            f"{name_roots[(idx * 3) % len(name_roots)]} {cfg['trade']} Services LLC"
            if is_target
            else f"{rng.choice(name_roots)} {rng.choice(['Contracting', 'Works', 'Builders', 'Systems'])} {idx:03d}"
        )
        status_cycle = ["verified", "missing", "pending", "not_required"]
        endorsement_status = "not_required" if cfg["endorsement"] is None else status_cycle[idx % 3]
        prior_license_id = f"CL-{app_id.replace('-', '')[-7:]}" if idx % 4 != 1 else None
        issue_options = [None, "prior complaint disclosed", "late bond certificate", "name change"]
        application = {
            "application_id": app_id,
            "applicant_name": applicant_name,
            "trade": cfg["trade"],
            "county": counties[idx % len(counties)],
            "submitted_date": date_between(rng, date(2025, 1, 3), date(2025, 7, 15)),
            "years_experience": max(0, cfg["experience"] + ((idx % 5) - 2)),
            "endorsement_status": endorsement_status,
            "prior_license_id": prior_license_id,
            "requested_class": cfg["requested_class"],
            "self_disclosed_issue": issue_options[idx % len(issue_options)],
            "target_group": target_group if is_target else rng.choice([None, None, None, "audit_pool"]),
        }
        applications.append(application)

        profile = idx % 6
        active_bond_amount = cfg["min_bond"] - 5000 if profile == 1 else cfg["min_bond"] + rng.choice([0, 5000, 15000])
        bond_status = "cancelled" if profile == 4 else "active"
        bonds.append(
            {
                "bond_id": f"BND-{app_id}-A",
                "application_id": app_id,
                "amount": active_bond_amount,
                "status": bond_status,
                "effective_date": date_between(rng, date(2025, 1, 1), date(2025, 4, 20)),
                "cancel_date": "2025-05-30" if bond_status == "cancelled" else None,
                "source_date": date_between(rng, date(2025, 4, 1), date(2025, 7, 20)),
                "surety": rng.choice(sureties),
            }
        )
        bonds.append(
            {
                "bond_id": f"BND-{app_id}-OLD",
                "application_id": app_id,
                "amount": max(10000, cfg["min_bond"] - rng.choice([5000, 10000, 15000])),
                "status": rng.choice(["expired", "cancelled"]),
                "effective_date": date_between(rng, date(2023, 1, 1), date(2024, 6, 30)),
                "cancel_date": date_between(rng, date(2024, 8, 1), date(2024, 12, 31)),
                "source_date": date_between(rng, date(2024, 8, 1), date(2025, 1, 15)),
                "surety": rng.choice(sureties),
            }
        )

        expiration = "2025-04-15" if profile == 2 else date_between(rng, date(2025, 8, 1), date(2026, 7, 1))
        insurance.append(
            {
                "insurance_id": f"INS-{app_id}-A",
                "application_id": app_id,
                "amount": cfg["min_insurance"] - 250000 if profile == 5 else cfg["min_insurance"],
                "status": "active" if profile != 3 else "pending",
                "verified_date": date_between(rng, date(2025, 1, 10), date(2025, 7, 12)),
                "expiration_date": expiration,
                "insurer": rng.choice(insurers),
            }
        )
        insurance.append(
            {
                "insurance_id": f"INS-{app_id}-OLD",
                "application_id": app_id,
                "amount": max(250000, cfg["min_insurance"] - 500000),
                "status": "expired",
                "verified_date": date_between(rng, date(2024, 1, 1), date(2024, 12, 15)),
                "expiration_date": date_between(rng, date(2024, 6, 1), date(2025, 1, 31)),
                "insurer": rng.choice(insurers),
            }
        )

        if prior_license_id:
            license_status = "suspended" if profile == 3 else rng.choice(["active", "expired", "active"])
            histories.append(
                {
                    "license_id": prior_license_id,
                    "applicant_name": applicant_name,
                    "status": license_status,
                    "status_date": date_between(rng, date(2024, 1, 1), date(2025, 6, 30)),
                    "trade": cfg["trade"],
                    "notes": "Active suspension pending board action"
                    if license_status == "suspended"
                    else "Registry history matched by applicant name",
                }
            )

        if profile in {0, 2, 4}:
            violations.append(
                {
                    "violation_id": f"CV-{app_id}-1",
                    "related_application_id": app_id,
                    "license_id": prior_license_id,
                    "violation_date": date_between(rng, date(2023, 6, 1), date(2025, 5, 1)),
                    "severity": rng.choice(["minor", "medium"]),
                    "theme": rng.choice(["advertising", "complaint", "bond lapse"]),
                    "status": "resolved",
                    "resolved_date": date_between(rng, date(2024, 3, 1), date(2025, 6, 1)),
                }
            )
        if profile == 5:
            violations.append(
                {
                    "violation_id": f"CV-{app_id}-S",
                    "related_application_id": app_id,
                    "license_id": prior_license_id,
                    "violation_date": date_between(rng, date(2025, 1, 1), date(2025, 6, 20)),
                    "severity": "serious",
                    "theme": "unpermitted work",
                    "status": "open",
                    "resolved_date": None,
                }
            )

        correspondence.append(
            {
                "correspondence_id": f"COR-{app_id}-1",
                "related_application_id": app_id,
                "received_date": date_between(rng, date(2025, 2, 1), date(2025, 7, 12)),
                "subject": rng.choice(
                    ["experience affidavit", "endorsement certificate", "bond correction", "name match"]
                ),
                "assertion_type": rng.choice(
                    ["experience_update", "endorsement_status", "bond_amount", "prior_license_match"]
                ),
                "assertion_value": rng.choice(
                    ["agency verified", "applicant supplied", "registry corrected", "pending outside agency"]
                ),
                "verified_by_agency": 1 if idx % 3 != 1 else 0,
                "notes": rng.choice(
                    [
                        "Linked to registry case notes",
                        "Applicant copy only; no agency confirmation",
                        "Verified by licensing specialist",
                        "Stale attachment predates application",
                    ]
                ),
            }
        )
        if is_target or idx % 3 == 0:
            inspections.append(
                {
                    "inspection_id": f"CI-{app_id}-1",
                    "related_application_id": app_id,
                    "inspection_date": date_between(rng, date(2025, 2, 15), date(2025, 7, 5)),
                    "result": rng.choice(["pass", "conditional", "fail"]),
                    "finding_code": rng.choice(["NONE", "DOC_GAP", "UNVERIFIED_SITE", "SAFETY_RECHECK"]),
                    "notes": rng.choice(
                        [
                            "Field note matches application trade",
                            "Site visit found incomplete signage",
                            "No adverse field finding",
                            "Follow-up requested by regional inspector",
                        ]
                    ),
                }
            )

    idx = 0
    for target_group, app_ids in CONTRACTOR_TARGETS.items():
        manifest_targets[target_group] = {"contractor_application_ids": list(app_ids)}
        generated_app_ids = app_ids[:6] if target_group == "test_004" else app_ids
        for app_id in generated_app_ids:
            idx += 1
            add_application(app_id, target_group, idx, True)

    distractor_count = 72
    for n in range(1, distractor_count + 1):
        idx += 1
        add_application(f"C-DIS-{n:03d}", None, idx, False)

    while len(histories) < 130:
        cfg = rng.choice(TRADE_CONFIGS)
        n = len(histories) + 1
        histories.append(
            {
                "license_id": f"CL-HIST-{n:04d}",
                "applicant_name": f"{rng.choice(name_roots)} Legacy Licensee {n:03d}",
                "status": rng.choice(["active", "active", "expired", "suspended", "revoked"]),
                "status_date": date_between(rng, date(2022, 1, 1), date(2025, 7, 1)),
                "trade": cfg["trade"],
                "notes": rng.choice(
                    [
                        "Legacy import from prior registry",
                        "Complaint-only match, no application link",
                        "Status verified by board clerk",
                        "Address differs from current application",
                    ]
                ),
            }
        )

    while len(violations) < 190:
        app = rng.choice(applications)
        n = len(violations) + 1
        status = rng.choice(["open", "resolved", "dismissed", "resolved"])
        violations.append(
            {
                "violation_id": f"CV-DIS-{n:04d}",
                "related_application_id": app["application_id"] if rng.random() < 0.7 else None,
                "license_id": app["prior_license_id"]
                if app["prior_license_id"] and rng.random() < 0.6
                else f"CL-HIST-{rng.randint(1, 130):04d}",
                "violation_date": date_between(rng, date(2022, 7, 1), date(2025, 7, 1)),
                "severity": rng.choice(["minor", "medium", "serious"]),
                "theme": rng.choice(["complaint", "unpermitted work", "safety", "advertising", "bond lapse"]),
                "status": status,
                "resolved_date": None if status == "open" else date_between(rng, date(2023, 1, 1), date(2025, 7, 10)),
            }
        )

    while len(correspondence) < 118:
        app = rng.choice(applications)
        n = len(correspondence) + 1
        correspondence.append(
            {
                "correspondence_id": f"COR-DIS-{n:04d}",
                "related_application_id": app["application_id"],
                "received_date": date_between(rng, date(2024, 10, 1), date(2025, 7, 15)),
                "subject": rng.choice(
                    [
                        "bond update",
                        "insurance upload",
                        "experience affidavit",
                        "public complaint",
                        "endorsement correction",
                    ]
                ),
                "assertion_type": rng.choice(
                    [
                        "bond_amount",
                        "insurance_amount",
                        "experience_update",
                        "discipline_response",
                        "endorsement_status",
                    ]
                ),
                "assertion_value": rng.choice(
                    [
                        "verified current",
                        "unverified applicant note",
                        "conflicts with registry",
                        "superseded by later source",
                    ]
                ),
                "verified_by_agency": 1 if rng.random() < 0.55 else 0,
                "notes": rng.choice(
                    ["Office upload", "Email from applicant", "Agency cross-check", "County desk note"]
                ),
            }
        )

    while len(inspections) < 82:
        app = rng.choice(applications)
        n = len(inspections) + 1
        inspections.append(
            {
                "inspection_id": f"CI-DIS-{n:04d}",
                "related_application_id": app["application_id"],
                "inspection_date": date_between(rng, date(2024, 11, 1), date(2025, 7, 15)),
                "result": rng.choice(["pass", "conditional", "fail", "no access"]),
                "finding_code": rng.choice(["NONE", "DOC_GAP", "UNVERIFIED_SITE", "SAFETY_RECHECK", "WRONG_TRADE"]),
                "notes": rng.choice(
                    ["Routine field note", "Potential stale export", "Inspection matched address", "Follow-up pending"]
                ),
            }
        )

    # Append the reworked test_004 expansion after RNG-driven distractors so
    # existing train/liquor/renewal data remains stable across regeneration.
    applications.extend(
        [
            {
                "application_id": "C-TE4-007",
                "applicant_name": "North Terminal Electrical Services LLC",
                "trade": "Electrical",
                "county": "Lake",
                "submitted_date": "2025-05-21",
                "years_experience": 6,
                "endorsement_status": "verified",
                "prior_license_id": "CL-CTE4007",
                "requested_class": "Class A",
                "self_disclosed_issue": None,
                "target_group": "test_004",
            },
            {
                "application_id": "C-TE4-008",
                "applicant_name": "Orchid Plumbing Services LLC",
                "trade": "Plumbing",
                "county": "Canyon",
                "submitted_date": "2025-06-02",
                "years_experience": 3,
                "endorsement_status": "missing",
                "prior_license_id": "CL-CTE4008",
                "requested_class": "Class B",
                "self_disclosed_issue": "prior complaint disclosed",
                "target_group": "test_004",
            },
            {
                "application_id": "C-TE4-009",
                "applicant_name": "Pine State HVAC Services LLC",
                "trade": "HVAC",
                "county": "Redwood",
                "submitted_date": "2025-04-18",
                "years_experience": 3,
                "endorsement_status": "verified",
                "prior_license_id": "CL-CTE4009",
                "requested_class": "Class B",
                "self_disclosed_issue": "late bond certificate",
                "target_group": "test_004",
            },
            {
                "application_id": "C-TE4-010",
                "applicant_name": "Riverview General Building Services LLC",
                "trade": "General Building",
                "county": "Prairie",
                "submitted_date": "2025-05-04",
                "years_experience": 5,
                "endorsement_status": "verified",
                "prior_license_id": "CL-CTE4010",
                "requested_class": "Class A",
                "self_disclosed_issue": "name change",
                "target_group": "test_004",
            },
            {
                "application_id": "C-TE4-011",
                "applicant_name": "Sage Roofing Services LLC",
                "trade": "Roofing",
                "county": "Harbor",
                "submitted_date": "2025-03-27",
                "years_experience": 2,
                "endorsement_status": "not_required",
                "prior_license_id": None,
                "requested_class": "Limited",
                "self_disclosed_issue": None,
                "target_group": "test_004",
            },
            {
                "application_id": "C-TE4-012",
                "applicant_name": "Timber Solar Services LLC",
                "trade": "Solar",
                "county": "Summit",
                "submitted_date": "2025-06-17",
                "years_experience": 3,
                "endorsement_status": "missing",
                "prior_license_id": "CL-CTE4012",
                "requested_class": "Specialty",
                "self_disclosed_issue": "late bond certificate",
                "target_group": "test_004",
            },
            {
                "application_id": "C-TE4-013",
                "applicant_name": "Alder Electrical Services LLC",
                "trade": "Electrical",
                "county": "Lake",
                "submitted_date": "2025-07-01",
                "years_experience": 5,
                "endorsement_status": "verified",
                "prior_license_id": "CL-CTE4013",
                "requested_class": "Class A",
                "self_disclosed_issue": "prior complaint disclosed",
                "target_group": "test_004",
            },
            {
                "application_id": "C-TE4-014",
                "applicant_name": "Blue Ridge Plumbing Services LLC",
                "trade": "Plumbing",
                "county": "Canyon",
                "submitted_date": "2025-04-30",
                "years_experience": 4,
                "endorsement_status": "pending",
                "prior_license_id": "CL-CTE4014",
                "requested_class": "Class B",
                "self_disclosed_issue": "name change",
                "target_group": "test_004",
            },
            {
                "application_id": "C-TE4-015",
                "applicant_name": "Crescent HVAC Services LLC",
                "trade": "HVAC",
                "county": "Redwood",
                "submitted_date": "2025-02-20",
                "years_experience": 2,
                "endorsement_status": "verified",
                "prior_license_id": "CL-CTE4015",
                "requested_class": "Class B",
                "self_disclosed_issue": "prior complaint disclosed",
                "target_group": "test_004",
            },
        ]
    )
    bonds.extend(
        [
            {
                "bond_id": "BND-C-TE4-007-A",
                "application_id": "C-TE4-007",
                "amount": 50000,
                "status": "active",
                "effective_date": "2025-02-01",
                "cancel_date": None,
                "source_date": "2025-06-15",
                "surety": "Union Surety",
            },
            {
                "bond_id": "BND-C-TE4-007-OLD",
                "application_id": "C-TE4-007",
                "amount": 35000,
                "status": "expired",
                "effective_date": "2023-02-01",
                "cancel_date": "2024-08-30",
                "source_date": "2024-09-02",
                "surety": "Civic Bonding",
            },
            {
                "bond_id": "BND-C-TE4-008-A",
                "application_id": "C-TE4-008",
                "amount": 30000,
                "status": "active",
                "effective_date": "2025-02-07",
                "cancel_date": None,
                "source_date": "2025-06-20",
                "surety": "Harbor Surety",
            },
            {
                "bond_id": "BND-C-TE4-008-OLD",
                "application_id": "C-TE4-008",
                "amount": 20000,
                "status": "expired",
                "effective_date": "2023-05-01",
                "cancel_date": "2024-10-19",
                "source_date": "2024-10-20",
                "surety": "Union Surety",
            },
            {
                "bond_id": "BND-C-TE4-009-A",
                "application_id": "C-TE4-009",
                "amount": 20000,
                "status": "active",
                "effective_date": "2025-03-11",
                "cancel_date": None,
                "source_date": "2025-07-02",
                "surety": "Granite Mutual",
            },
            {
                "bond_id": "BND-C-TE4-009-OLD",
                "application_id": "C-TE4-009",
                "amount": 15000,
                "status": "expired",
                "effective_date": "2023-04-01",
                "cancel_date": "2024-11-01",
                "source_date": "2024-11-03",
                "surety": "Civic Bonding",
            },
            {
                "bond_id": "BND-C-TE4-010-A",
                "application_id": "C-TE4-010",
                "amount": 75000,
                "status": "active",
                "effective_date": "2025-01-18",
                "cancel_date": None,
                "source_date": "2025-06-29",
                "surety": "Northwest Indemnity",
            },
            {
                "bond_id": "BND-C-TE4-010-OLD",
                "application_id": "C-TE4-010",
                "amount": 60000,
                "status": "expired",
                "effective_date": "2023-03-01",
                "cancel_date": "2024-10-01",
                "source_date": "2024-10-05",
                "surety": "Harbor Surety",
            },
            {
                "bond_id": "BND-C-TE4-011-A",
                "application_id": "C-TE4-011",
                "amount": 20000,
                "status": "cancelled",
                "effective_date": "2025-01-20",
                "cancel_date": "2025-05-22",
                "source_date": "2025-06-01",
                "surety": "Prairie Shield",
            },
            {
                "bond_id": "BND-C-TE4-011-OLD",
                "application_id": "C-TE4-011",
                "amount": 15000,
                "status": "expired",
                "effective_date": "2023-02-14",
                "cancel_date": "2024-09-21",
                "source_date": "2024-09-24",
                "surety": "Union Surety",
            },
            {
                "bond_id": "BND-C-TE4-012-A",
                "application_id": "C-TE4-012",
                "amount": 30000,
                "status": "active",
                "effective_date": "2025-02-18",
                "cancel_date": None,
                "source_date": "2025-07-08",
                "surety": "Granite Mutual",
            },
            {
                "bond_id": "BND-C-TE4-012-OLD",
                "application_id": "C-TE4-012",
                "amount": 20000,
                "status": "expired",
                "effective_date": "2023-03-19",
                "cancel_date": "2024-12-10",
                "source_date": "2024-12-11",
                "surety": "Northwest Indemnity",
            },
            {
                "bond_id": "BND-C-TE4-013-A",
                "application_id": "C-TE4-013",
                "amount": 50000,
                "status": "active",
                "effective_date": "2025-03-01",
                "cancel_date": None,
                "source_date": "2025-07-11",
                "surety": "Civic Bonding",
            },
            {
                "bond_id": "BND-C-TE4-013-OLD",
                "application_id": "C-TE4-013",
                "amount": 35000,
                "status": "expired",
                "effective_date": "2023-05-03",
                "cancel_date": "2024-11-12",
                "source_date": "2024-11-14",
                "surety": "Harbor Surety",
            },
            {
                "bond_id": "BND-C-TE4-014-A",
                "application_id": "C-TE4-014",
                "amount": 30000,
                "status": "cancelled",
                "effective_date": "2025-01-25",
                "cancel_date": "2025-04-28",
                "source_date": "2025-05-04",
                "surety": "Union Surety",
            },
            {
                "bond_id": "BND-C-TE4-014-OLD",
                "application_id": "C-TE4-014",
                "amount": 20000,
                "status": "expired",
                "effective_date": "2023-01-21",
                "cancel_date": "2024-08-15",
                "source_date": "2024-08-16",
                "surety": "Civic Bonding",
            },
            {
                "bond_id": "BND-C-TE4-015-A",
                "application_id": "C-TE4-015",
                "amount": 25000,
                "status": "active",
                "effective_date": "2025-02-28",
                "cancel_date": None,
                "source_date": "2025-06-23",
                "surety": "Harbor Surety",
            },
            {
                "bond_id": "BND-C-TE4-015-OLD",
                "application_id": "C-TE4-015",
                "amount": 15000,
                "status": "expired",
                "effective_date": "2023-04-27",
                "cancel_date": "2024-12-12",
                "source_date": "2024-12-16",
                "surety": "Granite Mutual",
            },
        ]
    )
    insurance.extend(
        [
            {
                "insurance_id": "INS-C-TE4-007-A",
                "application_id": "C-TE4-007",
                "amount": 1000000,
                "status": "active",
                "verified_date": "2025-06-01",
                "expiration_date": "2026-02-01",
                "insurer": "Civic Risk Pool",
            },
            {
                "insurance_id": "INS-C-TE4-007-OLD",
                "application_id": "C-TE4-007",
                "amount": 500000,
                "status": "expired",
                "verified_date": "2024-06-01",
                "expiration_date": "2024-12-31",
                "insurer": "Northfield Casualty",
            },
            {
                "insurance_id": "INS-C-TE4-008-A",
                "application_id": "C-TE4-008",
                "amount": 750000,
                "status": "active",
                "verified_date": "2025-06-03",
                "expiration_date": "2026-03-01",
                "insurer": "Builders Mutual",
            },
            {
                "insurance_id": "INS-C-TE4-008-OLD",
                "application_id": "C-TE4-008",
                "amount": 250000,
                "status": "expired",
                "verified_date": "2024-05-01",
                "expiration_date": "2024-12-31",
                "insurer": "Prairie Shield",
            },
            {
                "insurance_id": "INS-C-TE4-009-A",
                "application_id": "C-TE4-009",
                "amount": 500000,
                "status": "active",
                "verified_date": "2025-05-30",
                "expiration_date": "2026-02-15",
                "insurer": "Evergreen Commercial",
            },
            {
                "insurance_id": "INS-C-TE4-009-OLD",
                "application_id": "C-TE4-009",
                "amount": 250000,
                "status": "expired",
                "verified_date": "2024-05-10",
                "expiration_date": "2024-11-30",
                "insurer": "Civic Risk Pool",
            },
            {
                "insurance_id": "INS-C-TE4-010-A",
                "application_id": "C-TE4-010",
                "amount": 1000000,
                "status": "pending",
                "verified_date": "2025-06-14",
                "expiration_date": "2026-01-15",
                "insurer": "Northfield Casualty",
            },
            {
                "insurance_id": "INS-C-TE4-010-OLD",
                "application_id": "C-TE4-010",
                "amount": 500000,
                "status": "expired",
                "verified_date": "2024-02-18",
                "expiration_date": "2024-10-31",
                "insurer": "Builders Mutual",
            },
            {
                "insurance_id": "INS-C-TE4-011-A",
                "application_id": "C-TE4-011",
                "amount": 500000,
                "status": "active",
                "verified_date": "2025-03-15",
                "expiration_date": "2025-04-15",
                "insurer": "Prairie Shield",
            },
            {
                "insurance_id": "INS-C-TE4-011-OLD",
                "application_id": "C-TE4-011",
                "amount": 250000,
                "status": "expired",
                "verified_date": "2024-04-10",
                "expiration_date": "2024-10-01",
                "insurer": "Northfield Casualty",
            },
            {
                "insurance_id": "INS-C-TE4-012-A",
                "application_id": "C-TE4-012",
                "amount": 750000,
                "status": "active",
                "verified_date": "2025-06-30",
                "expiration_date": "2026-05-01",
                "insurer": "Civic Risk Pool",
            },
            {
                "insurance_id": "INS-C-TE4-012-OLD",
                "application_id": "C-TE4-012",
                "amount": 250000,
                "status": "expired",
                "verified_date": "2024-06-22",
                "expiration_date": "2024-12-31",
                "insurer": "Builders Mutual",
            },
            {
                "insurance_id": "INS-C-TE4-013-A",
                "application_id": "C-TE4-013",
                "amount": 750000,
                "status": "active",
                "verified_date": "2025-07-05",
                "expiration_date": "2026-04-01",
                "insurer": "Evergreen Commercial",
            },
            {
                "insurance_id": "INS-C-TE4-013-OLD",
                "application_id": "C-TE4-013",
                "amount": 500000,
                "status": "expired",
                "verified_date": "2024-06-15",
                "expiration_date": "2024-12-31",
                "insurer": "Civic Risk Pool",
            },
            {
                "insurance_id": "INS-C-TE4-014-A",
                "application_id": "C-TE4-014",
                "amount": 750000,
                "status": "pending",
                "verified_date": "2025-06-07",
                "expiration_date": "2026-02-20",
                "insurer": "Prairie Shield",
            },
            {
                "insurance_id": "INS-C-TE4-014-OLD",
                "application_id": "C-TE4-014",
                "amount": 250000,
                "status": "expired",
                "verified_date": "2024-06-01",
                "expiration_date": "2024-11-11",
                "insurer": "Builders Mutual",
            },
            {
                "insurance_id": "INS-C-TE4-015-A",
                "application_id": "C-TE4-015",
                "amount": 500000,
                "status": "active",
                "verified_date": "2025-06-21",
                "expiration_date": "2026-06-01",
                "insurer": "Northfield Casualty",
            },
            {
                "insurance_id": "INS-C-TE4-015-OLD",
                "application_id": "C-TE4-015",
                "amount": 250000,
                "status": "expired",
                "verified_date": "2024-06-09",
                "expiration_date": "2024-12-31",
                "insurer": "Civic Risk Pool",
            },
        ]
    )
    histories.extend(
        [
            {
                "license_id": "CL-CTE4007",
                "applicant_name": "North Terminal Electrical Services LLC",
                "status": "active",
                "status_date": "2025-01-10",
                "trade": "Electrical",
                "notes": "Registry history matched by applicant name",
            },
            {
                "license_id": "CL-CTE4008",
                "applicant_name": "Orchid Plumbing Services LLC",
                "status": "active",
                "status_date": "2024-09-03",
                "trade": "Plumbing",
                "notes": "Registry history matched by applicant name",
            },
            {
                "license_id": "CL-CTE4009",
                "applicant_name": "Pine State HVAC Services LLC",
                "status": "active",
                "status_date": "2024-11-16",
                "trade": "HVAC",
                "notes": "Registry history matched by applicant name",
            },
            {
                "license_id": "CL-CTE4010",
                "applicant_name": "Riverview General Building Services LLC",
                "status": "suspended",
                "status_date": "2025-03-18",
                "trade": "General Building",
                "notes": "Active suspension pending board action",
            },
            {
                "license_id": "CL-CTE4012",
                "applicant_name": "Timber Solar Services LLC",
                "status": "active",
                "status_date": "2024-10-25",
                "trade": "Solar",
                "notes": "Registry history matched by applicant name",
            },
            {
                "license_id": "CL-CTE4013",
                "applicant_name": "Alder Electrical Services LLC",
                "status": "active",
                "status_date": "2024-08-09",
                "trade": "Electrical",
                "notes": "Registry history matched by applicant name",
            },
            {
                "license_id": "CL-CTE4014",
                "applicant_name": "Blue Ridge Plumbing Services LLC",
                "status": "active",
                "status_date": "2024-12-13",
                "trade": "Plumbing",
                "notes": "Registry history matched by applicant name",
            },
            {
                "license_id": "CL-CTE4015",
                "applicant_name": "Crescent HVAC Services LLC",
                "status": "active",
                "status_date": "2025-02-02",
                "trade": "HVAC",
                "notes": "Registry history matched by applicant name",
            },
        ]
    )
    violations.extend(
        [
            {
                "violation_id": "CV-C-TE4-003-S",
                "related_application_id": "C-TE4-003",
                "license_id": "CL-CTE4003",
                "violation_date": "2025-05-09",
                "severity": "serious",
                "theme": "unpermitted work",
                "status": "open",
                "resolved_date": None,
            },
            {
                "violation_id": "CV-C-TE4-004-M",
                "related_application_id": "C-TE4-004",
                "license_id": "CL-CTE4004",
                "violation_date": "2025-04-21",
                "severity": "minor",
                "theme": "advertising",
                "status": "open",
                "resolved_date": None,
            },
            {
                "violation_id": "CV-C-TE4-008-CS",
                "related_application_id": "C-TE4-008",
                "license_id": "CL-CTE4008",
                "violation_date": "2024-10-12",
                "severity": "serious",
                "theme": "bond lapse",
                "status": "resolved",
                "resolved_date": "2025-01-14",
            },
            {
                "violation_id": "CV-C-TE4-009-M",
                "related_application_id": "C-TE4-009",
                "license_id": "CL-CTE4009",
                "violation_date": "2025-03-08",
                "severity": "medium",
                "theme": "advertising",
                "status": "open",
                "resolved_date": None,
            },
            {
                "violation_id": "CV-C-TE4-013-S",
                "related_application_id": "C-TE4-013",
                "license_id": "CL-CTE4013",
                "violation_date": "2025-06-11",
                "severity": "serious",
                "theme": "unpermitted work",
                "status": "open",
                "resolved_date": None,
            },
            {
                "violation_id": "CV-C-TE4-015-CS",
                "related_application_id": "C-TE4-015",
                "license_id": "CL-CTE4015",
                "violation_date": "2024-09-19",
                "severity": "serious",
                "theme": "safety",
                "status": "resolved",
                "resolved_date": "2025-02-18",
            },
            {
                "violation_id": "CV-C-TE4-015-M",
                "related_application_id": "C-TE4-015",
                "license_id": "CL-CTE4015",
                "violation_date": "2025-05-07",
                "severity": "minor",
                "theme": "advertising",
                "status": "open",
                "resolved_date": None,
            },
        ]
    )
    correspondence.extend(
        [
            {
                "correspondence_id": "COR-C-TE4-007-1",
                "related_application_id": "C-TE4-007",
                "received_date": "2025-06-20",
                "subject": "name match",
                "assertion_type": "prior_license_match",
                "assertion_value": "agency verified",
                "verified_by_agency": 1,
                "notes": "Verified by licensing specialist",
            },
            {
                "correspondence_id": "COR-C-TE4-008-1",
                "related_application_id": "C-TE4-008",
                "received_date": "2025-06-04",
                "subject": "experience affidavit",
                "assertion_type": "experience_update",
                "assertion_value": "pending outside agency",
                "verified_by_agency": 1,
                "notes": "Linked to registry case notes",
            },
            {
                "correspondence_id": "COR-C-TE4-009-1",
                "related_application_id": "C-TE4-009",
                "received_date": "2025-05-11",
                "subject": "bond correction",
                "assertion_type": "bond_amount",
                "assertion_value": "applicant supplied",
                "verified_by_agency": 1,
                "notes": "Verified by licensing specialist",
            },
            {
                "correspondence_id": "COR-C-TE4-010-1",
                "related_application_id": "C-TE4-010",
                "received_date": "2025-05-24",
                "subject": "discipline response",
                "assertion_type": "discipline_response",
                "assertion_value": "pending outside agency",
                "verified_by_agency": 1,
                "notes": "Linked to registry case notes",
            },
            {
                "correspondence_id": "COR-C-TE4-011-1",
                "related_application_id": "C-TE4-011",
                "received_date": "2025-04-20",
                "subject": "bond correction",
                "assertion_type": "bond_amount",
                "assertion_value": "agency verified",
                "verified_by_agency": 1,
                "notes": "Verified by licensing specialist",
            },
            {
                "correspondence_id": "COR-C-TE4-012-1",
                "related_application_id": "C-TE4-012",
                "received_date": "2025-06-28",
                "subject": "endorsement certificate",
                "assertion_type": "endorsement_status",
                "assertion_value": "applicant supplied",
                "verified_by_agency": 0,
                "notes": "Applicant copy only; no agency confirmation",
            },
            {
                "correspondence_id": "COR-C-TE4-013-1",
                "related_application_id": "C-TE4-013",
                "received_date": "2025-07-10",
                "subject": "insurance upload",
                "assertion_type": "insurance_amount",
                "assertion_value": "agency verified",
                "verified_by_agency": 1,
                "notes": "Verified by licensing specialist",
            },
            {
                "correspondence_id": "COR-C-TE4-014-1",
                "related_application_id": "C-TE4-014",
                "received_date": "2025-03-03",
                "subject": "bond correction",
                "assertion_type": "bond_amount",
                "assertion_value": "registry corrected",
                "verified_by_agency": 0,
                "notes": "Stale attachment predates application",
            },
            {
                "correspondence_id": "COR-C-TE4-015-1",
                "related_application_id": "C-TE4-015",
                "received_date": "2025-06-05",
                "subject": "experience affidavit",
                "assertion_type": "experience_update",
                "assertion_value": "agency verified",
                "verified_by_agency": 1,
                "notes": "Verified by licensing specialist",
            },
        ]
    )
    inspections.extend(
        [
            {
                "inspection_id": "CI-C-TE4-007-1",
                "related_application_id": "C-TE4-007",
                "inspection_date": "2025-06-08",
                "result": "pass",
                "finding_code": "NONE",
                "notes": "Field note matches application trade",
            },
            {
                "inspection_id": "CI-C-TE4-008-1",
                "related_application_id": "C-TE4-008",
                "inspection_date": "2025-05-26",
                "result": "conditional",
                "finding_code": "DOC_GAP",
                "notes": "Follow-up requested by regional inspector",
            },
            {
                "inspection_id": "CI-C-TE4-009-1",
                "related_application_id": "C-TE4-009",
                "inspection_date": "2025-05-01",
                "result": "pass",
                "finding_code": "NONE",
                "notes": "Field note matches application trade",
            },
            {
                "inspection_id": "CI-C-TE4-010-1",
                "related_application_id": "C-TE4-010",
                "inspection_date": "2025-06-18",
                "result": "conditional",
                "finding_code": "UNVERIFIED_SITE",
                "notes": "Follow-up requested by regional inspector",
            },
            {
                "inspection_id": "CI-C-TE4-011-1",
                "related_application_id": "C-TE4-011",
                "inspection_date": "2025-04-30",
                "result": "pass",
                "finding_code": "NONE",
                "notes": "No adverse field finding",
            },
            {
                "inspection_id": "CI-C-TE4-012-1",
                "related_application_id": "C-TE4-012",
                "inspection_date": "2025-06-19",
                "result": "conditional",
                "finding_code": "DOC_GAP",
                "notes": "Site visit found incomplete signage",
            },
            {
                "inspection_id": "CI-C-TE4-013-1",
                "related_application_id": "C-TE4-013",
                "inspection_date": "2025-07-08",
                "result": "fail",
                "finding_code": "SAFETY_RECHECK",
                "notes": "Follow-up requested by regional inspector",
            },
            {
                "inspection_id": "CI-C-TE4-014-1",
                "related_application_id": "C-TE4-014",
                "inspection_date": "2025-05-19",
                "result": "conditional",
                "finding_code": "UNVERIFIED_SITE",
                "notes": "Potential stale export",
            },
            {
                "inspection_id": "CI-C-TE4-015-1",
                "related_application_id": "C-TE4-015",
                "inspection_date": "2025-04-14",
                "result": "pass",
                "finding_code": "NONE",
                "notes": "No adverse field finding",
            },
        ]
    )

    return {
        "contractor_applications": applications,
        "contractor_bonds": bonds,
        "contractor_insurance": insurance,
        "contractor_license_history": histories,
        "contractor_violations": violations,
        "contractor_correspondence": correspondence,
        "contractor_inspections": inspections,
        "manifest_targets": manifest_targets,
    }


def build_liquor_data(rng):
    classes = ["Tavern", "Restaurant", "BeerWine", "Package"]
    posture = ["new", "transfer", "renewal_with_controls", "settlement_review"]
    applicants = [
        "Bridge & Barrel LLC",
        "Crescent Market Group",
        "Eastgate Social House",
        "Foundry Foods Inc",
        "Harbor Night LLC",
        "Lakeview Stores",
        "Mosaic Dining",
        "North Terminal Group",
        "Orchid Hospitality",
        "Pine State Markets",
    ]
    streets = ["Market", "Pine", "Main", "Ferry", "Union", "Water", "Cedar", "Monroe"]
    applications = []
    settlements = []
    incidents = []
    evidence = []
    manifest_targets = {}

    def add_liquor_app(application_id, location_id, target_group, idx, is_target):
        license_class = classes[idx % len(classes)]
        dba = f"{rng.choice(['Copper', 'Station', 'Vista', 'Anchor', 'Corner'])} {rng.choice(['Taproom', 'Market', 'Kitchen', 'Club'])} {idx:02d}"
        address = f"{100 + idx * 7} {streets[idx % len(streets)]} St"
        applications.append(
            {
                "application_id": application_id,
                "agency": "Alcohol Control Board",
                "applicant_name": applicants[idx % len(applicants)],
                "dba": dba,
                "address": address,
                "license_class": license_class,
                "location_id": location_id,
                "submitted_date": date_between(rng, date(2025, 1, 15), date(2025, 7, 10)),
                "requested_posture": posture[idx % len(posture)],
                "target_group": target_group if is_target else rng.choice([None, None, "settlement_watch"]),
            }
        )

        control_sets = [
            ["ID_CHECK", "HOURS"],
            ["SECURITY", "CCTV", "HOURS"],
            ["NOISE", "PATIO"],
            ["FOOD_SERVICE", "ID_CHECK"],
        ]
        for offset in range(2 if not is_target else 4):
            active = offset == 0
            controls = {
                "controls": control_sets[(idx + offset) % len(control_sets)],
                "active": active,
                "review_required": active and (idx + offset) % 2 == 0,
                "expires": "2026-12-31" if active else "2024-12-31",
            }
            settlements.append(
                {
                    "settlement_id": f"SET-{location_id}-{offset + 1}",
                    "location_id": location_id,
                    "effective_date": date_between(
                        rng,
                        date(2022, 1, 1) if offset else date(2024, 1, 1),
                        date(2025, 6, 15),
                    ),
                    "settlement_type": rng.choice(
                        ["restricted", "warning", "conditional approval", "historic refusal"]
                    ),
                    "basis_code": rng.choice(["SAME_PREMISES", "PUBLIC_SAFETY", "NOISE", "SALE_TO_MINOR"]),
                    "controls_json": json.dumps(controls, sort_keys=True),
                    "source_name": rng.choice(["board_order", "settlement_pdf", "legacy_registry"]),
                }
            )

        for offset in range(3 if is_target else 2):
            incidents.append(
                {
                    "incident_id": f"INC-{location_id}-{offset + 1}",
                    "location_id": location_id,
                    "incident_date": date_between(rng, date(2023, 1, 1), date(2025, 7, 1)),
                    "risk_code": rng.choice(["MINOR_SALE", "NOISE", "ASSAULT", "AFTER_HOURS", "TAX_HOLD"]),
                    "severity": rng.choice(["low", "medium", "high"]),
                    "status": rng.choice(["open", "closed", "referred", "dismissed"]),
                    "source_name": rng.choice(["police_feed", "board_order", "complaint_portal", "inspection_log"]),
                }
            )

        for offset in range(2 if is_target else 1):
            evidence.append(
                {
                    "evidence_id": f"EV-{location_id}-{offset + 1}",
                    "location_id": location_id,
                    "evidence_date": date_between(rng, date(2024, 6, 1), date(2025, 7, 5)),
                    "evidence_code": rng.choice(
                        ["SITE_PHOTO", "FLOOR_PLAN", "NEIGHBOR_NOTICE", "CONTROL_SIGNAGE", "POLICE_MEMO"]
                    ),
                    "status": rng.choice(["verified", "stale", "missing", "conflicting"]),
                    "notes": rng.choice(
                        ["Current packet", "Old location name", "Needs follow-up", "Verified by inspector"]
                    ),
                }
            )

    idx = 0
    for group, target in LIQUOR_TARGETS.items():
        idx += 1
        add_liquor_app(target["application_id"], target["location_id"], group, idx, True)
        manifest_targets[group] = dict(target)

    for n in range(1, 31):
        idx += 1
        add_liquor_app(f"L-DIS-{n:03d}", f"LOC-DIS-{n:03d}", None, idx, False)

    while len(incidents) < 128:
        app = rng.choice(applications)
        n = len(incidents) + 1
        incidents.append(
            {
                "incident_id": f"INC-DIS-{n:04d}",
                "location_id": app["location_id"],
                "incident_date": date_between(rng, date(2021, 1, 1), date(2025, 7, 1)),
                "risk_code": rng.choice(
                    ["MINOR_SALE", "NOISE", "ASSAULT", "AFTER_HOURS", "TAX_HOLD", "FOOD_SERVICE_GAP"]
                ),
                "severity": rng.choice(["low", "medium", "high"]),
                "status": rng.choice(["open", "closed", "referred", "dismissed"]),
                "source_name": rng.choice(["police_feed", "legacy_feed", "public_complaint", "board_order"]),
            }
        )

    while len(evidence) < 76:
        app = rng.choice(applications)
        n = len(evidence) + 1
        evidence.append(
            {
                "evidence_id": f"EV-DIS-{n:04d}",
                "location_id": app["location_id"],
                "evidence_date": date_between(rng, date(2023, 1, 1), date(2025, 7, 1)),
                "evidence_code": rng.choice(
                    ["SITE_PHOTO", "FLOOR_PLAN", "NEIGHBOR_NOTICE", "CONTROL_SIGNAGE", "POLICE_MEMO", "TAX_CLEARANCE"]
                ),
                "status": rng.choice(["verified", "stale", "missing", "conflicting"]),
                "notes": rng.choice(
                    ["Field import", "Applicant packet", "Conflicts with settlement order", "Current evidence"]
                ),
            }
        )

    return {
        "liquor_applications": applications,
        "liquor_settlements": settlements,
        "liquor_incidents": incidents,
        "liquor_site_evidence": evidence,
        "manifest_targets": manifest_targets,
    }


def build_alcohol_data(rng):
    agencies = ["City Licensing", "County Licensing", "Alcohol Renewal Unit"]
    channels = ["grocery", "bar", "restaurant", "convenience", "event"]
    streets = ["Oak", "Maple", "Adams", "Lincoln", "River", "Third", "Seventh", "Pearl"]
    themes = ["late renewal", "sale to minor", "unpaid fine", "after hours", "missing posting", "tax hold", "noise"]
    licensees = []
    violations = []
    manifest_targets = {}

    for group, info in RENEWAL_TARGETS.items():
        boundary = date.fromisoformat(info["boundary"])
        license_numbers = []
        non_exact_cases = []
        non_exact_case = RENEWAL_NON_EXACT_CASES.get(group)
        for idx in range(1, info["target_queue_size"] + 1):
            license_no = f"{info['prefix']}-{idx:03d}"
            license_numbers.append(license_no)
            facility_name = f"{group.replace('_', ' ').title()} Facility {idx:02d}"
            address = f"{200 + idx * 11} {streets[idx % len(streets)]} Ave"
            is_non_exact_case = non_exact_case and idx == non_exact_case["current_idx"]
            successor_to = None
            if is_non_exact_case:
                successor_to = non_exact_case["old_license_no"]
            elif idx % 5 == 0:
                successor_to = f"{info['prefix']}-OLD-{idx:03d}"
            licensees.append(
                {
                    "license_no": license_no,
                    "agency": agencies[idx % len(agencies)],
                    "facility_name": facility_name,
                    "address": address,
                    "channel_type": channels[idx % len(channels)],
                    "active": 1,
                    "location_id": f"ALOC-{info['prefix']}-{idx:03d}",
                    "successor_to": successor_to,
                    "target_group": group,
                }
            )

            if is_non_exact_case:
                old_address = non_exact_case.get("old_address", address)
                old_facility_name = f"{facility_name} Former Permit"
                licensees.append(
                    {
                        "license_no": non_exact_case["old_license_no"],
                        "agency": agencies[idx % len(agencies)],
                        "facility_name": old_facility_name,
                        "address": old_address,
                        "channel_type": channels[idx % len(channels)],
                        "active": 0,
                        "location_id": f"ALOC-{info['prefix']}-{idx:03d}-OLD",
                        "successor_to": None,
                        "target_group": group,
                    }
                )
                current_violation_ids = []
                old_violation_ids = []
                for profile in non_exact_case["current_exact_violations"]:
                    violation_id = f"AV-{license_no}-{profile['suffix']}"
                    current_violation_ids.append(violation_id)
                    violations.append(
                        {
                            "violation_id": violation_id,
                            "license_no": license_no,
                            "facility_name": facility_name,
                            "address": address,
                            "violation_date": (boundary - timedelta(days=profile["days_before"])).isoformat(),
                            "theme": profile["theme"],
                            "severity": profile["severity"],
                            "disposition": profile["disposition"],
                            "fine_balance": profile["fine_balance"],
                            "alert_flag": profile["alert_flag"],
                            "source_name": "renewal_case_export",
                        }
                    )
                for profile in non_exact_case["old_violations"]:
                    violation_id = f"AV-{non_exact_case['old_license_no']}-{profile['suffix']}"
                    old_violation_ids.append(violation_id)
                    violations.append(
                        {
                            "violation_id": violation_id,
                            "license_no": non_exact_case["old_license_no"],
                            "facility_name": old_facility_name,
                            "address": old_address,
                            "violation_date": (boundary - timedelta(days=profile["days_before"])).isoformat(),
                            "theme": profile["theme"],
                            "severity": profile["severity"],
                            "disposition": profile["disposition"],
                            "fine_balance": profile["fine_balance"],
                            "alert_flag": profile["alert_flag"],
                            "source_name": "legacy_successor_feed",
                        }
                    )
                non_exact_cases.append(
                    {
                        "current_license_no": license_no,
                        "old_license_no": non_exact_case["old_license_no"],
                        "current_facility_name": facility_name,
                        "old_facility_name": old_facility_name,
                        "current_address": address,
                        "old_address": old_address,
                        "boundary": info["boundary"],
                        "match_basis": non_exact_case["match_basis"],
                        "expected_match_confidence": non_exact_case["expected_match_confidence"],
                        "current_exact_violation_ids": current_violation_ids,
                        "old_or_close_violation_ids": old_violation_ids,
                        "expected_current_only_pre_boundary_count": len(current_violation_ids),
                        "expected_matched_pre_boundary_count": len(current_violation_ids) + len(old_violation_ids),
                        "expected_risk_tier_after_match": "high",
                        "expected_next_step_label_after_match": "board_review",
                    }
                )
            else:
                before_count = 2 + (idx % 3)
                for offset in range(before_count):
                    vdate = boundary - timedelta(days=rng.randint(3, 150))
                    severity = rng.choice(["minor", "medium", "serious"])
                    fine_balance = 0.0 if offset % 2 else float(rng.choice([125, 250, 500, 900]))
                    violations.append(
                        {
                            "violation_id": f"AV-{license_no}-{offset + 1}",
                            "license_no": license_no,
                            "facility_name": facility_name,
                            "address": address,
                            "violation_date": vdate.isoformat(),
                            "theme": rng.choice(themes),
                            "severity": severity,
                            "disposition": rng.choice(["open", "settled", "warning", "paid", "pending"]),
                            "fine_balance": fine_balance,
                            "alert_flag": 1 if severity == "serious" or fine_balance > 0 else 0,
                            "source_name": "renewal_case_export",
                        }
                    )
            violations.append(
                {
                    "violation_id": f"AV-{license_no}-LATE",
                    "license_no": license_no,
                    "facility_name": facility_name,
                    "address": address,
                    "violation_date": (boundary + timedelta(days=rng.randint(2, 45))).isoformat(),
                    "theme": rng.choice(themes),
                    "severity": rng.choice(["minor", "medium", "serious"]),
                    "disposition": rng.choice(["open", "settled", "warning", "pending"]),
                    "fine_balance": float(rng.choice([0, 100, 350])),
                    "alert_flag": rng.choice([0, 1]),
                    "source_name": "post_boundary_feed",
                }
            )
        manifest_targets[group] = {
            "renewal_group_tag": group,
            "target_queue_size": info["target_queue_size"],
            "boundary": info["boundary"],
            "license_numbers": license_numbers,
            "non_exact_match_cases": non_exact_cases,
        }

    distractor_count = 58
    for idx in range(1, distractor_count + 1):
        license_no = f"AL-DIS-{idx:04d}"
        facility_name = f"{rng.choice(['Metro', 'Corner', 'Harbor', 'Prairie', 'Summit'])} {rng.choice(['Market', 'Tavern', 'Cafe', 'Bottle Shop'])} {idx:03d}"
        address = f"{500 + idx * 5} {streets[idx % len(streets)]} Ave"
        licensees.append(
            {
                "license_no": license_no,
                "agency": rng.choice(agencies),
                "facility_name": facility_name,
                "address": address,
                "channel_type": rng.choice(channels),
                "active": 0 if idx % 11 == 0 else 1,
                "location_id": f"ALOC-DIS-{idx:04d}",
                "successor_to": f"AL-DIS-OLD-{idx:04d}" if idx % 9 == 0 else None,
                "target_group": rng.choice([None, None, None, "general_renewal_pool"]),
            }
        )
        for offset in range(rng.randint(1, 4)):
            violations.append(
                {
                    "violation_id": f"AV-DIS-{idx:04d}-{offset + 1}",
                    "license_no": license_no,
                    "facility_name": facility_name,
                    "address": address if rng.random() > 0.1 else address.replace("Ave", "Avenue"),
                    "violation_date": date_between(rng, date(2024, 1, 1), date(2025, 7, 15)),
                    "theme": rng.choice(themes),
                    "severity": rng.choice(["minor", "medium", "serious"]),
                    "disposition": rng.choice(["open", "settled", "warning", "paid", "dismissed"]),
                    "fine_balance": float(rng.choice([0, 0, 100, 250, 750])),
                    "alert_flag": rng.choice([0, 0, 1]),
                    "source_name": rng.choice(
                        ["renewal_case_export", "public_feed", "legacy_feed", "post_boundary_feed"]
                    ),
                }
            )

    while len(violations) < 264:
        licensee = rng.choice(licensees)
        n = len(violations) + 1
        violations.append(
            {
                "violation_id": f"AV-EXTRA-{n:04d}",
                "license_no": licensee["license_no"],
                "facility_name": licensee["facility_name"],
                "address": licensee["address"],
                "violation_date": date_between(rng, date(2023, 8, 1), date(2025, 7, 15)),
                "theme": rng.choice(themes),
                "severity": rng.choice(["minor", "medium", "serious"]),
                "disposition": rng.choice(["open", "settled", "warning", "paid", "dismissed"]),
                "fine_balance": float(rng.choice([0, 0, 125, 450, 1000])),
                "alert_flag": rng.choice([0, 1]),
                "source_name": rng.choice(["renewal_case_export", "public_feed", "legacy_feed"]),
            }
        )

    return {
        "alcohol_licensees": licensees,
        "alcohol_violations": violations,
        "manifest_targets": manifest_targets,
    }


def count_rows(cur):
    counts = {}
    for table in TABLES:
        counts[table] = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return counts


def generate(data_dir=DATA_DIR):
    rng = random.Random(SEED)
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "licensing.db"
    manifest_path = data_dir / "manifest.json"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    create_schema(cur)

    contractor = build_contractor_data(rng)
    liquor = build_liquor_data(rng)
    alcohol = build_alcohol_data(rng)

    table_rows = {
        "policies": build_policy_rows(),
        "contractor_applications": contractor["contractor_applications"],
        "contractor_bonds": contractor["contractor_bonds"],
        "contractor_insurance": contractor["contractor_insurance"],
        "contractor_license_history": contractor["contractor_license_history"],
        "contractor_violations": contractor["contractor_violations"],
        "contractor_correspondence": contractor["contractor_correspondence"],
        "contractor_inspections": contractor["contractor_inspections"],
        "liquor_applications": liquor["liquor_applications"],
        "liquor_settlements": liquor["liquor_settlements"],
        "liquor_privileges": build_privilege_rows(),
        "liquor_incidents": liquor["liquor_incidents"],
        "liquor_site_evidence": liquor["liquor_site_evidence"],
        "alcohol_licensees": alcohol["alcohol_licensees"],
        "alcohol_violations": alcohol["alcohol_violations"],
        "renewal_rules": build_renewal_rules(),
    }

    for table in TABLES:
        insert_many(cur, table, table_rows[table])

    conn.commit()
    counts = count_rows(cur)
    conn.close()

    target_groups = {}
    target_groups.update(contractor["manifest_targets"])
    target_groups.update(liquor["manifest_targets"])
    target_groups.update(alcohol["manifest_targets"])

    manifest = {
        "seed": SEED,
        "generated_at": "2026-07-18T00:00:00Z",
        "database": "data/licensing.db",
        "sql_token": "licensing-review-019",
        "state_mode": "read_only",
        "target_groups": target_groups,
        "counts": counts,
        "notes": [
            "Generated data is shared across contractor, liquor, and alcohol-renewal workflows.",
            "Target groups are construction metadata for task builders, not public task endpoints.",
            "Business endpoints expose normal domain tables with realistic distractors and stale/conflicting records.",
        ],
    }
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return manifest


if __name__ == "__main__":
    result = generate()
    print(json.dumps({"database": str(DB_PATH), "counts": result["counts"]}, sort_keys=True))
