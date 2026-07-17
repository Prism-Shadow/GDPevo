#!/usr/bin/env python3
"""Generate deterministic Cedar Ridge intake coordination data."""

from __future__ import annotations

import json
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path


SEED = 13013
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "clinic.db"
MANIFEST_PATH = DATA_DIR / "manifest.json"


FIRST_NAMES = [
    "Avery",
    "Blake",
    "Carmen",
    "Dana",
    "Elliot",
    "Finley",
    "Gabriel",
    "Harper",
    "Imani",
    "Jordan",
    "Kai",
    "Logan",
    "Morgan",
    "Noel",
    "Parker",
    "Quinn",
    "Reese",
    "Sawyer",
    "Taylor",
    "Val",
]
LAST_NAMES = [
    "Adams",
    "Bennett",
    "Chen",
    "Diaz",
    "Ellis",
    "Foster",
    "Garcia",
    "Hughes",
    "Iqbal",
    "Jones",
    "Kim",
    "Lopez",
    "Mason",
    "Nguyen",
    "Ortiz",
    "Patel",
    "Reed",
    "Singh",
    "Turner",
    "Wright",
]
PAYERS = ["Aetna", "BlueCross", "Cigna", "Humana", "Medicare", "United"]
SERVICE_LINES = ["primary_care", "orthopedics", "dialysis", "pulmonary", "cardiology", "chronic_care"]


TASK_ROSTERS = {
    "NPI-JUN-01": ["P001", "P002", "P003", "P004", "P005", "P006"],
    "NPI-JUL-02": ["P007", "P008", "P009", "P010", "P011", "P012", "P013"],
}

TRANSFER_BATCHES = {
    "DIAL-WINTER-01": ["P014", "P015", "P016", "P017", "P018", "P019"],
    "DIAL-SUMMER-02": ["P020", "P021", "P022", "P023", "P024", "P025"],
}

PROGRAMS = {
    "DMHTN-2026A": ["P026", "P027", "P028", "P029", "P030", "P031", "P032"],
    "RENAL-DM-2026B": ["P033", "P034", "P035", "P036", "P037", "P038", "P039"],
}

REFERRAL_BATCHES = {
    "ORTHO-JUN-01": ("orthopedics", ["P040", "P041", "P042", "P043", "P044", "P045", "P046", "P047"]),
    "PULM-JUN-02": ("pulmonary", ["P048", "P049", "P050", "P051", "P052", "P053"]),
    "ORTHO-JUL-04": ("orthopedics", ["P054", "P055", "P056", "P057", "P058", "P059", "P060"]),
    "CARD-JUL-03": ("cardiology", ["P061", "P062", "P063", "P064", "P065", "P066"]),
}


SCHEMA = """
PRAGMA journal_mode = DELETE;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS intake_rosters;
DROP TABLE IF EXISTS coverage;
DROP TABLE IF EXISTS pbm;
DROP TABLE IF EXISTS pharmacies;
DROP TABLE IF EXISTS patient_pharmacy;
DROP TABLE IF EXISTS lifestyle;
DROP TABLE IF EXISTS clinical_history;
DROP TABLE IF EXISTS referrals;
DROP TABLE IF EXISTS icd_codes;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS transfer_requests;
DROP TABLE IF EXISTS facility_capacity;
DROP TABLE IF EXISTS chart_artifacts;
DROP TABLE IF EXISTS program_candidates;

CREATE TABLE patients (
    patient_id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    dob TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    language TEXT NOT NULL,
    address TEXT,
    existing_chart INTEGER NOT NULL,
    preferred_contact TEXT,
    emergency_contact_present INTEGER NOT NULL
);

CREATE TABLE intake_rosters (
    roster_id TEXT NOT NULL,
    patient_id TEXT NOT NULL,
    requested_service_date TEXT NOT NULL,
    service_line TEXT NOT NULL,
    source_note TEXT,
    PRIMARY KEY (roster_id, patient_id)
);

CREATE TABLE coverage (
    coverage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    payer TEXT NOT NULL,
    policy_number TEXT,
    group_number TEXT,
    effective_date TEXT,
    termination_date TEXT,
    network_status TEXT NOT NULL,
    service_lines TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE pbm (
    pbm_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    payer TEXT NOT NULL,
    policy_number TEXT,
    active INTEGER NOT NULL,
    formulary_status TEXT NOT NULL,
    specialty_required INTEGER NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE pharmacies (
    pharmacy_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    phone TEXT,
    network_status TEXT NOT NULL
);

CREATE TABLE patient_pharmacy (
    patient_id TEXT NOT NULL,
    pharmacy_id TEXT NOT NULL,
    preference_rank INTEGER NOT NULL,
    PRIMARY KEY (patient_id, pharmacy_id)
);

CREATE TABLE lifestyle (
    patient_id TEXT PRIMARY KEY,
    smoking_status TEXT,
    alcohol_use TEXT,
    exercise_frequency TEXT,
    sleep_hours REAL
);

CREATE TABLE clinical_history (
    patient_id TEXT PRIMARY KEY,
    chronic_conditions TEXT,
    surgeries TEXT,
    medication_count INTEGER NOT NULL,
    allergy_count INTEGER NOT NULL,
    recent_hospitalization INTEGER NOT NULL,
    risk_flags TEXT
);

CREATE TABLE referrals (
    referral_id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    service_line TEXT NOT NULL,
    date_received TEXT NOT NULL,
    patient_id TEXT NOT NULL,
    payer TEXT,
    insurance_id TEXT,
    referring_physician TEXT,
    referring_practice TEXT,
    referring_phone TEXT,
    referring_fax TEXT,
    icd10_code TEXT,
    diagnosis_description TEXT,
    referral_reason TEXT,
    urgency TEXT,
    records_received INTEGER NOT NULL,
    imaging_received INTEGER NOT NULL,
    auth_required INTEGER NOT NULL,
    auth_status TEXT NOT NULL,
    appointment_scheduled INTEGER NOT NULL,
    appointment_date TEXT,
    assigned_physician TEXT,
    notes TEXT
);

CREATE TABLE icd_codes (
    code TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    chapter TEXT NOT NULL,
    service_family TEXT NOT NULL,
    laterality TEXT
);

CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    referral_id TEXT,
    transfer_id TEXT,
    doc_type TEXT NOT NULL,
    status TEXT NOT NULL,
    finalized INTEGER NOT NULL,
    received_date TEXT,
    service_date TEXT,
    content_tag TEXT,
    notes TEXT
);

CREATE TABLE transfer_requests (
    transfer_id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    patient_id TEXT NOT NULL,
    referring_facility TEXT NOT NULL,
    requested_start_date TEXT NOT NULL,
    requested_end_date TEXT,
    modality TEXT NOT NULL,
    days_requested TEXT,
    chair_window TEXT,
    transportation TEXT,
    status_note TEXT
);

CREATE TABLE facility_capacity (
    location_id TEXT NOT NULL,
    date TEXT NOT NULL,
    modality TEXT NOT NULL,
    open_chairs INTEGER NOT NULL,
    PRIMARY KEY (location_id, date, modality)
);

CREATE TABLE chart_artifacts (
    artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    status TEXT NOT NULL,
    last_updated TEXT,
    value_summary TEXT
);

CREATE TABLE program_candidates (
    program_code TEXT NOT NULL,
    patient_id TEXT NOT NULL,
    candidate_date TEXT NOT NULL,
    source TEXT NOT NULL,
    consent_status TEXT NOT NULL,
    preferred_outreach TEXT,
    adherence_score INTEGER,
    target_condition TEXT NOT NULL,
    PRIMARY KEY (program_code, patient_id)
);
"""


def iso(d: date) -> str:
    return d.isoformat()


def choose(rng: random.Random, values: list[str]) -> str:
    return values[rng.randrange(len(values))]


def patient_name(index: int, rng: random.Random) -> tuple[str, str]:
    if index <= 66:
        first = FIRST_NAMES[(index - 1) % len(FIRST_NAMES)]
        last = LAST_NAMES[((index - 1) // len(FIRST_NAMES) + index) % len(LAST_NAMES)]
    else:
        first = choose(rng, FIRST_NAMES)
        last = choose(rng, LAST_NAMES)
    return first, last


def insert_many(conn: sqlite3.Connection, sql: str, rows: list[tuple]) -> None:
    conn.executemany(sql, rows)


def generate() -> dict:
    rng = random.Random(SEED)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    patients: list[tuple] = []
    for idx in range(1, 111):
        pid = f"P{idx:03d}"
        first, last = patient_name(idx, rng)
        dob = date(1942 + (idx * 7) % 55, 1 + idx % 12, 1 + (idx * 3) % 27)
        phone = None if idx in {4, 11, 31, 58, 89} else f"555-013-{idx:04d}"
        email = None if idx in {2, 12, 29, 64, 101} else f"{first.lower()}.{last.lower()}{idx}@example.test"
        address = None if idx in {5, 13, 37, 77} else f"{100 + idx} Cedar Ridge Ave"
        patients.append(
            (
                pid,
                first,
                last,
                iso(dob),
                phone,
                email,
                choose(rng, ["English", "Spanish", "Vietnamese", "Arabic"]),
                address,
                1 if idx % 3 != 1 else 0,
                choose(rng, ["phone", "email", "portal", "sms"]),
                0 if idx in {6, 28, 35, 55, 92} else 1,
            )
        )

    insert_many(
        conn,
        """INSERT INTO patients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        patients,
    )

    roster_rows: list[tuple] = []
    for roster_id, ids in TASK_ROSTERS.items():
        requested = "2026-06-18" if roster_id == "NPI-JUN-01" else "2026-07-09"
        for pid in ids:
            roster_rows.append((roster_id, pid, requested, "primary_care", "new patient intake roster"))
    insert_many(conn, "INSERT INTO intake_rosters VALUES (?, ?, ?, ?, ?)", roster_rows)

    pharmacies: list[tuple] = []
    for idx in range(1, 36):
        network = "in_network" if idx % 5 not in {0, 4} else "out_of_network"
        phone = None if idx in {7, 22, 31} else f"555-019-{idx:04d}"
        pharmacies.append((f"RX{idx:03d}", f"Cedar Pharmacy {idx}", f"{700 + idx} Wellness Pkwy", phone, network))
    insert_many(conn, "INSERT INTO pharmacies VALUES (?, ?, ?, ?, ?)", pharmacies)

    patient_pharmacies: list[tuple] = []
    for idx in range(1, 111):
        primary = f"RX{1 + ((idx * 3) % 35):03d}"
        backup = f"RX{1 + ((idx * 5 + 2) % 35):03d}"
        patient_pharmacies.append((f"P{idx:03d}", primary, 1))
        if idx % 4 == 0 and backup != primary:
            patient_pharmacies.append((f"P{idx:03d}", backup, 2))
    insert_many(conn, "INSERT INTO patient_pharmacy VALUES (?, ?, ?)", patient_pharmacies)

    coverage_rows: list[tuple] = []
    pbm_rows: list[tuple] = []
    for idx in range(1, 91):
        pid = f"P{idx:03d}"
        payer = PAYERS[idx % len(PAYERS)]
        service_lines = ",".join(rng.sample(SERVICE_LINES, k=3 + idx % 3))
        if idx in {3, 8, 22, 43, 59, 74}:
            status = "expired"
            termination = "2026-05-31"
        elif idx in {5, 12, 36, 66}:
            status = "pending"
            termination = None
        else:
            status = "active"
            termination = "2026-12-31" if idx % 11 else "2026-06-30"
        network = "in_network" if idx % 7 else "out_of_network"
        policy = f"POL{(idx * 917) % 100000:05d}"
        if idx in {44, 45, 56, 57}:
            policy = "SHARED-ORTHO-4457"
        coverage_rows.append(
            (
                pid,
                payer,
                policy,
                f"GRP{idx % 12:02d}",
                "2025-01-01",
                termination,
                network,
                service_lines,
                status,
            )
        )
        pbm_status = "approved"
        active = 1
        formulary = "covered"
        if idx in {2, 9, 27, 48, 62}:
            pbm_status = "rejected"
            active = 0
            formulary = "not_found"
        elif idx in {4, 10, 52, 68}:
            pbm_status = "pending"
            formulary = "review"
        pbm_rows.append(
            (
                pid,
                payer,
                policy if idx not in {6, 13} else f"PBM-MISMATCH-{idx}",
                active,
                formulary,
                idx % 6 == 0,
                pbm_status,
            )
        )

    insert_many(
        conn,
        """INSERT INTO coverage
           (patient_id, payer, policy_number, group_number, effective_date, termination_date, network_status, service_lines, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        coverage_rows,
    )
    insert_many(
        conn,
        """INSERT INTO pbm
           (patient_id, payer, policy_number, active, formulary_status, specialty_required, status)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        pbm_rows,
    )

    lifestyle_rows: list[tuple] = []
    history_rows: list[tuple] = []
    condition_pool = ["diabetes", "hypertension", "ckd", "copd", "cad", "asthma", "osteoarthritis"]
    for idx in range(1, 111):
        pid = f"P{idx:03d}"
        lifestyle_rows.append(
            (
                pid,
                choose(rng, ["Never", "Former", "Current"]),
                choose(rng, ["None", "Occasional", "Moderate", "Heavy"]),
                choose(rng, ["5+", "3-4", "1-2", "None", None]),
                None if idx in {7, 32, 81} else round(rng.uniform(4.5, 8.5), 1),
            )
        )
        conditions = rng.sample(condition_pool, k=1 + idx % 4)
        if idx in range(26, 40):
            conditions = sorted(set(conditions + ["diabetes", "hypertension"]))
        risk_flags = []
        if idx % 10 == 0:
            risk_flags.append("recent_ed_visit")
        if idx % 17 == 0:
            risk_flags.append("fall_risk")
        if idx in {6, 10, 16, 24, 35, 63}:
            risk_flags.append("complex_medication_reconciliation")
        history_rows.append(
            (
                pid,
                ",".join(conditions),
                "none" if idx % 9 else "joint replacement",
                1 + idx % 12,
                idx % 5,
                1 if idx % 13 == 0 else 0,
                ",".join(risk_flags),
            )
        )
    insert_many(conn, "INSERT INTO lifestyle VALUES (?, ?, ?, ?, ?)", lifestyle_rows)
    insert_many(conn, "INSERT INTO clinical_history VALUES (?, ?, ?, ?, ?, ?, ?)", history_rows)

    icd_rows = [
        ("M54.16", "Radiculopathy, lumbar region", "M00-M99", "orthopedics", None),
        ("M25.561", "Pain in right knee", "M00-M99", "orthopedics", "right"),
        ("M25.562", "Pain in left knee", "M00-M99", "orthopedics", "left"),
        ("S83.512A", "Sprain of anterior cruciate ligament of left knee", "S00-T88", "orthopedics", "left"),
        ("J44.9", "Chronic obstructive pulmonary disease", "J00-J99", "pulmonary", None),
        ("J45.40", "Moderate persistent asthma", "J00-J99", "pulmonary", None),
        ("I25.10", "Atherosclerotic heart disease", "I00-I99", "cardiology", None),
        ("I48.91", "Unspecified atrial fibrillation", "I00-I99", "cardiology", None),
        ("E11.9", "Type 2 diabetes mellitus", "E00-E89", "chronic_care", None),
        ("I10", "Essential hypertension", "I00-I99", "chronic_care", None),
        ("N18.32", "Chronic kidney disease stage 3b", "N00-N99", "chronic_care", None),
        ("Z99.2", "Dependence on renal dialysis", "Z00-Z99", "dialysis", None),
        ("R06.02", "Shortness of breath", "R00-R99", "pulmonary", None),
    ]
    insert_many(conn, "INSERT INTO icd_codes VALUES (?, ?, ?, ?, ?)", icd_rows)

    referral_rows: list[tuple] = []
    referral_id_counter = 1
    for batch_id, (service_line, ids) in REFERRAL_BATCHES.items():
        for pos, pid in enumerate(ids, 1):
            code = {
                "orthopedics": choose(rng, ["M54.16", "M25.561", "M25.562", "S83.512A", "J44.9"]),
                "pulmonary": choose(rng, ["J44.9", "J45.40", "R06.02", "I25.10"]),
                "cardiology": choose(rng, ["I25.10", "I48.91", "R06.02", "M54.16"]),
            }[service_line]
            desc = "right knee pain" if code == "M25.562" and pos == 2 else "specialty consultation"
            insurance_id = (
                "DUP-INS-ORTHO" if batch_id in {"ORTHO-JUN-01", "ORTHO-JUL-04"} and pos in {4, 5} else f"INS-{pid}"
            )
            referral_rows.append(
                (
                    f"REF{referral_id_counter:04d}",
                    batch_id,
                    service_line,
                    "2026-06-03" if "JUN" in batch_id else "2026-07-02",
                    pid,
                    PAYERS[(referral_id_counter + 2) % len(PAYERS)],
                    insurance_id,
                    choose(rng, ["Dr. Lane", "Dr. Morris", "Dr. Patel", "Dr. Stone"]),
                    choose(rng, ["Harbor Family", "Northside Clinic", "Bayview Medical", "Cedar Ridge PCP"]),
                    f"555-020-{referral_id_counter:04d}",
                    f"555-021-{referral_id_counter:04d}",
                    code,
                    desc,
                    choose(rng, ["pain evaluation", "previsit clearance", "transfer of care", "worsening symptoms"]),
                    "urgent" if pos in {1, 5} else "routine",
                    0 if pos in {3, 6} else 1,
                    0 if service_line == "orthopedics" and pos in {2, 6} else 1,
                    1 if pos % 3 == 0 else 0,
                    "approved" if pos % 3 != 0 else choose(rng, ["pending", "denied"]),
                    1 if pos == len(ids) else 0,
                    "2026-07-22" if pos == len(ids) else None,
                    choose(rng, ["A. Nguyen", "B. Holt", "C. Singh"]),
                    "possible duplicate" if pos in {4, 5} else "batch intake",
                )
            )
            referral_id_counter += 1
        if service_line == "orthopedics":
            original = referral_rows[-2]
            dup = list(original)
            dup[0] = f"REF{referral_id_counter:04d}"
            dup[8] = "Duplicate Orthopedic Associates"
            dup[21] = "duplicate faxed by second practice"
            referral_rows.append(tuple(dup))
            referral_id_counter += 1

    for _ in range(52):
        pid = f"P{rng.randint(1, 110):03d}"
        service_line = choose(rng, ["orthopedics", "pulmonary", "cardiology", "dermatology", "neurology"])
        code = choose(rng, [row[0] for row in icd_rows])
        referral_rows.append(
            (
                f"REF{referral_id_counter:04d}",
                choose(rng, ["GEN-JUN-A", "GEN-JUL-B", "ADMIN-REWORK", "COMMUNITY-Q3"]),
                service_line,
                iso(date(2026, 5, 15) + timedelta(days=rng.randint(0, 70))),
                pid,
                choose(rng, PAYERS),
                f"INS-{rng.randint(10000, 99999)}",
                choose(rng, ["Dr. Lane", "Dr. Morris", "Dr. Patel", "Dr. Stone"]),
                choose(rng, ["Harbor Family", "Northside Clinic", "Bayview Medical", "Cedar Ridge PCP"]),
                None if rng.random() < 0.08 else f"555-030-{referral_id_counter:04d}",
                f"555-031-{referral_id_counter:04d}",
                code,
                "general specialty referral",
                choose(rng, ["pain evaluation", "consult", "follow-up", "second opinion"]),
                choose(rng, ["routine", "urgent", "admin"]),
                int(rng.random() > 0.18),
                int(rng.random() > 0.25),
                int(rng.random() > 0.5),
                choose(rng, ["approved", "pending", "denied", "not_required"]),
                int(rng.random() > 0.85),
                None,
                choose(rng, ["A. Nguyen", "B. Holt", "C. Singh"]),
                "distractor referral",
            )
        )
        referral_id_counter += 1

    insert_many(
        conn,
        """INSERT INTO referrals VALUES
           (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        referral_rows,
    )

    transfer_rows: list[tuple] = []
    transfer_id_counter = 1
    for batch_id, ids in TRANSFER_BATCHES.items():
        start_base = date(2026, 12, 8) if "WINTER" in batch_id else date(2026, 7, 14)
        for pos, pid in enumerate(ids):
            transfer_rows.append(
                (
                    f"TR{transfer_id_counter:04d}",
                    batch_id,
                    pid,
                    choose(rng, ["Gulf Coast Dialysis", "Seaside Renal", "Lakeside Kidney Center"]),
                    iso(start_base + timedelta(days=pos * 2)),
                    iso(start_base + timedelta(days=pos * 2 + 28)),
                    "in_center_hemodialysis",
                    choose(rng, ["Mon/Wed/Fri", "Tue/Thu/Sat"]),
                    choose(rng, ["morning", "midday", "evening"]),
                    None if pos == 3 else choose(rng, ["family", "ride_share", "medical_transport"]),
                    "seasonal visitor packet",
                )
            )
            transfer_id_counter += 1
    for _ in range(14):
        pid = f"P{rng.randint(1, 110):03d}"
        start = date(2026, 6, 1) + timedelta(days=rng.randint(0, 210))
        transfer_rows.append(
            (
                f"TR{transfer_id_counter:04d}",
                choose(rng, ["DIAL-MISC-01", "DIAL-FALL-03"]),
                pid,
                choose(rng, ["Metro Dialysis", "Seaside Renal", "Desert Renal"]),
                iso(start),
                iso(start + timedelta(days=21)),
                "in_center_hemodialysis",
                choose(rng, ["Mon/Wed/Fri", "Tue/Thu/Sat"]),
                choose(rng, ["morning", "midday", "evening"]),
                choose(rng, ["family", "ride_share", "medical_transport", None]),
                "distractor transfer",
            )
        )
        transfer_id_counter += 1
    insert_many(conn, "INSERT INTO transfer_requests VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", transfer_rows)

    cap_rows: list[tuple] = []
    for loc in ["CRIC-MAIN", "CRIC-NORTH"]:
        for offset in range(0, 240):
            d = date(2026, 6, 1) + timedelta(days=offset)
            if d.weekday() in {0, 2, 4}:
                open_chairs = 0 if offset % 17 == 0 else 1 + (offset + len(loc)) % 4
                cap_rows.append((loc, iso(d), "in_center_hemodialysis", open_chairs))
    insert_many(conn, "INSERT INTO facility_capacity VALUES (?, ?, ?, ?)", cap_rows)

    chart_rows: list[tuple] = []
    artifact_types = [
        "demographics",
        "active_problems",
        "vitals",
        "labs",
        "medications",
        "allergies",
        "consent",
        "care_plan",
        "outreach_preference",
    ]
    for idx in range(1, 111):
        pid = f"P{idx:03d}"
        if 26 <= idx <= 39:
            patient_artifacts = ["active_problems", "vitals", "labs", "medications", "consent"]
            if idx % 4 == 0:
                patient_artifacts.append("care_plan")
        elif 48 <= idx <= 66:
            patient_artifacts = ["demographics", "active_problems"]
            if idx % 3 == 0:
                patient_artifacts.append("medications")
        elif 1 <= idx <= 25:
            patient_artifacts = ["vitals"] if idx % 5 == 0 else []
        elif 67 <= idx <= 76:
            patient_artifacts = [choose(rng, artifact_types)]
        else:
            patient_artifacts = []
        for artifact in patient_artifacts:
            if idx % 11 == 0 and artifact in {"consent", "care_plan"}:
                continue
            updated = date(2026, 6, 30) - timedelta(days=(idx * 7 + len(artifact)) % 520)
            status = "current"
            if (date(2026, 7, 15) - updated).days > 365:
                status = "stale"
            if idx % 19 == 0 and artifact in {"labs", "vitals"}:
                status = "draft"
            chart_rows.append((pid, artifact, status, iso(updated), f"{artifact} summary for {pid}"))
    insert_many(
        conn,
        "INSERT INTO chart_artifacts (patient_id, artifact_type, status, last_updated, value_summary) VALUES (?, ?, ?, ?, ?)",
        chart_rows,
    )

    candidate_rows: list[tuple] = []
    for program_code, ids in PROGRAMS.items():
        target = "diabetes_hypertension" if program_code == "DMHTN-2026A" else "renal_diabetes"
        for pos, pid in enumerate(ids):
            candidate_rows.append(
                (
                    program_code,
                    pid,
                    "2026-06-20" if program_code == "DMHTN-2026A" else "2026-07-08",
                    choose(rng, ["registry", "provider_panel", "payer_file"]),
                    "signed" if pos not in {2, 5} else choose(rng, ["missing", "declined"]),
                    choose(rng, ["phone", "portal", "sms", "email"]),
                    40 + (pos * 9) % 60,
                    target,
                )
            )
    for _ in range(18):
        program_code = choose(rng, ["DMHTN-2026A", "RENAL-DM-2026B", "COPD-2026C", "CAD-2026D"])
        candidate_rows.append(
            (
                program_code,
                f"P{rng.randint(1, 110):03d}",
                iso(date(2026, 5, 1) + timedelta(days=rng.randint(0, 90))),
                choose(rng, ["registry", "provider_panel", "payer_file"]),
                choose(rng, ["signed", "missing", "declined"]),
                choose(rng, ["phone", "portal", "sms", "email"]),
                rng.randint(20, 98),
                choose(rng, ["diabetes_hypertension", "renal_diabetes", "copd", "cardiac"]),
            )
        )
    conn.executemany(
        """INSERT OR IGNORE INTO program_candidates VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        candidate_rows,
    )

    doc_rows: list[tuple] = []
    doc_id_counter = 1
    required_transfer_docs = [
        "face_sheet",
        "insurance_proof",
        "hbsag",
        "hep_b_antibody_core",
        "monthly_labs",
        "flu_vaccine",
        "pneumonia_vaccine",
        "ppd_or_cxr",
        "history_physical",
        "medication_list",
        "allergy_list",
        "physician_orders",
        "vascular_access_report",
        "treatment_flowsheets",
    ]
    for transfer_id, batch_id, pid, *_rest in transfer_rows:
        if batch_id in {"DIAL-WINTER-01", "DIAL-SUMMER-02"}:
            start = date.fromisoformat(_rest[1])
            for doc_type in required_transfer_docs:
                if pid in {"P017", "P022"} and doc_type in {"flu_vaccine", "pneumonia_vaccine"}:
                    continue
                skip = (
                    pid in {"P016", "P023"} and doc_type in {"vascular_access_report", "treatment_flowsheets"}
                ) or (pid in {"P018", "P024"} and doc_type in {"transportation"})
                if skip:
                    continue
                age = rng.randint(2, 420)
                if pid in {"P015", "P021"} and doc_type in {"hbsag", "monthly_labs", "ppd_or_cxr"}:
                    age = 65
                status = "final" if rng.random() > 0.08 else "draft"
                finalized = 1 if status == "final" else 0
                doc_rows.append(
                    (
                        f"DOC{doc_id_counter:05d}",
                        pid,
                        None,
                        transfer_id,
                        doc_type,
                        status,
                        finalized,
                        iso(start - timedelta(days=age)),
                        None,
                        "transfer_packet",
                        "generated transfer document",
                    )
                )
                doc_id_counter += 1
    for referral in referral_rows:
        referral_id, _batch, _service, received, pid = referral[:5]
        if _batch not in set(REFERRAL_BATCHES) and rng.random() < 0.95:
            continue
        for doc_type in ["referral_form", "office_notes", "imaging_report"]:
            if rng.random() < 0.96:
                continue
            doc_rows.append(
                (
                    f"DOC{doc_id_counter:05d}",
                    pid,
                    referral_id,
                    None,
                    doc_type,
                    choose(rng, ["final", "final", "draft", "voided"]),
                    1 if rng.random() > 0.16 else 0,
                    received,
                    None,
                    "referral_packet",
                    "referral support document",
                )
            )
            doc_id_counter += 1
    while len(doc_rows) < 150:
        pid = f"P{rng.randint(1, 110):03d}"
        doc_rows.append(
            (
                f"DOC{doc_id_counter:05d}",
                pid,
                None,
                None,
                choose(rng, ["lab", "insurance_card", "consent", "medication_list", "historical_note"]),
                choose(rng, ["final", "draft", "voided"]),
                int(rng.random() > 0.2),
                iso(date(2025, 7, 1) + timedelta(days=rng.randint(0, 380))),
                None,
                "general_chart",
                "distractor document",
            )
        )
        doc_id_counter += 1
    insert_many(conn, "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", doc_rows)

    conn.commit()

    table_counts = {}
    for table in [
        "patients",
        "intake_rosters",
        "coverage",
        "pbm",
        "pharmacies",
        "patient_pharmacy",
        "lifestyle",
        "clinical_history",
        "referrals",
        "icd_codes",
        "documents",
        "transfer_requests",
        "facility_capacity",
        "chart_artifacts",
        "program_candidates",
    ]:
        table_counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    manifest = {
        "task_group_id": "task_group_013",
        "seed": SEED,
        "database": "data/clinic.db",
        "record_counts": table_counts,
        "task_relevant_seed_objects": {
            "train_001": {"roster_id": "NPI-JUN-01", "patients": TASK_ROSTERS["NPI-JUN-01"]},
            "train_002": {"batch_id": "ORTHO-JUN-01"},
            "train_003": {"batch_id": "DIAL-WINTER-01"},
            "train_004": {"program_code": "DMHTN-2026A"},
            "train_005": {"batch_id": "PULM-JUN-02"},
            "test_001": {"roster_id": "NPI-JUL-02", "patients": TASK_ROSTERS["NPI-JUL-02"]},
            "test_002": {"batch_id": "ORTHO-JUL-04"},
            "test_003": {"batch_id": "DIAL-SUMMER-02"},
            "test_004": {"program_code": "RENAL-DM-2026B"},
            "test_005": {"batch_id": "CARD-JUL-03"},
        },
        "noise_included": [
            "duplicate referrals",
            "shared insurance ids",
            "stale and draft documents",
            "expired and pending coverage",
            "PBM policy mismatches",
            "out-of-network pharmacies",
            "missing contact data",
            "stale chart artifacts",
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    conn.close()
    return manifest


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2, sort_keys=True))
