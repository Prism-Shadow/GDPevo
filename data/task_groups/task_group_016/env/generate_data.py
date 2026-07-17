#!/usr/bin/env python3
"""Generate the Harborview Synthetic Clinic SQLite environment."""

from __future__ import annotations

import argparse
import json
import os
import random
import sqlite3
from pathlib import Path


SEED = 16016
SCHEMA_VERSION = "harborview-synthetic-clinic-v1"
DEFAULT_DB_PATH = Path(__file__).resolve().parent / "generated" / "clinic.sqlite3"


TARGET_CASES = [
    "CASE-RESP-102",
    "CASE-HEAD-207",
    "CASE-K-303",
    "CASE-CM-411",
    "CASE-LAB-518",
    "CASE-RESP-914",
    "CASE-HEAD-822",
    "CASE-K-919",
    "CASE-CM-908",
    "CASE-LAB-927",
]

TARGET_PATIENTS = [
    "PAT-1002",
    "PAT-2207",
    "PAT-3303",
    "PAT-4411",
    "PAT-5518",
    "PAT-1914",
    "PAT-2822",
    "PAT-3919",
    "PAT-4908",
    "PAT-5927",
]

PROTOCOL_IDS = [
    "RESP-CAP-2026",
    "PEDS-HEAD-2026",
    "K-REPLETION-2026",
    "OBS-WINDOW-2026",
    "CM-HIGH-RISK-2026",
]


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS sdoh;
        DROP TABLE IF EXISTS care_registry;
        DROP TABLE IF EXISTS imaging;
        DROP TABLE IF EXISTS observations;
        DROP TABLE IF EXISTS medications;
        DROP TABLE IF EXISTS problems;
        DROP TABLE IF EXISTS allergies;
        DROP TABLE IF EXISTS case_findings;
        DROP TABLE IF EXISTS protocols;
        DROP TABLE IF EXISTS cases;
        DROP TABLE IF EXISTS patients;

        CREATE TABLE patients (
            patient_id TEXT PRIMARY KEY,
            fhir_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            sex TEXT NOT NULL,
            birth_date TEXT NOT NULL
        );

        CREATE TABLE cases (
            case_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL REFERENCES patients(patient_id),
            case_type TEXT NOT NULL,
            service_date TEXT NOT NULL,
            status TEXT NOT NULL,
            summary TEXT NOT NULL
        );

        CREATE TABLE case_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL REFERENCES cases(case_id),
            finding_key TEXT NOT NULL,
            finding_value TEXT NOT NULL,
            source_id TEXT NOT NULL
        );

        CREATE TABLE allergies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL REFERENCES patients(patient_id),
            allergen TEXT NOT NULL,
            reaction TEXT NOT NULL,
            status TEXT NOT NULL
        );

        CREATE TABLE problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL REFERENCES patients(patient_id),
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            onset_date TEXT
        );

        CREATE TABLE medications (
            medication_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL REFERENCES patients(patient_id),
            name TEXT NOT NULL,
            code TEXT NOT NULL,
            status TEXT NOT NULL,
            dose TEXT NOT NULL,
            route TEXT NOT NULL,
            frequency TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            source TEXT NOT NULL
        );

        CREATE TABLE observations (
            observation_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL REFERENCES patients(patient_id),
            case_id TEXT REFERENCES cases(case_id),
            code TEXT NOT NULL,
            display TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL,
            effective_time TEXT NOT NULL,
            value_text TEXT,
            value_number REAL,
            unit TEXT,
            interpretation TEXT,
            source TEXT NOT NULL
        );

        CREATE TABLE imaging (
            imaging_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL REFERENCES patients(patient_id),
            case_id TEXT REFERENCES cases(case_id),
            study TEXT NOT NULL,
            status TEXT NOT NULL,
            performed_at TEXT NOT NULL,
            impression TEXT NOT NULL
        );

        CREATE TABLE care_registry (
            case_id TEXT PRIMARY KEY REFERENCES cases(case_id),
            patient_id TEXT NOT NULL REFERENCES patients(patient_id),
            risk_score REAL NOT NULL,
            program_hint TEXT NOT NULL,
            recent_admission_date TEXT,
            dialysis_schedule TEXT,
            chronic_condition_count INTEGER NOT NULL,
            medication_count INTEGER NOT NULL
        );

        CREATE TABLE sdoh (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL REFERENCES patients(patient_id),
            domain TEXT NOT NULL,
            severity TEXT NOT NULL,
            evidence TEXT NOT NULL,
            source TEXT NOT NULL
        );

        CREATE TABLE protocols (
            protocol_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            version TEXT NOT NULL,
            body_json TEXT NOT NULL
        );

        CREATE INDEX idx_cases_patient ON cases(patient_id);
        CREATE INDEX idx_findings_case ON case_findings(case_id);
        CREATE INDEX idx_observations_case ON observations(case_id);
        CREATE INDEX idx_observations_patient_code_time
            ON observations(patient_id, code, effective_time);
        CREATE INDEX idx_medications_patient ON medications(patient_id);
        CREATE INDEX idx_allergies_patient ON allergies(patient_id);
        CREATE INDEX idx_problems_patient ON problems(patient_id);
        CREATE INDEX idx_imaging_case ON imaging(case_id);
        CREATE INDEX idx_sdoh_patient ON sdoh(patient_id);
        """
    )


def add_patient(conn: sqlite3.Connection, row: tuple) -> None:
    conn.execute(
        """
        INSERT INTO patients(patient_id, fhir_id, name, age, sex, birth_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        row,
    )


def add_case(conn: sqlite3.Connection, row: tuple) -> None:
    conn.execute(
        """
        INSERT INTO cases(case_id, patient_id, case_type, service_date, status, summary)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        row,
    )


def add_finding(conn: sqlite3.Connection, case_id: str, key: str, value, source: str) -> None:
    conn.execute(
        """
        INSERT INTO case_findings(case_id, finding_key, finding_value, source_id)
        VALUES (?, ?, ?, ?)
        """,
        (case_id, key, str(value), source),
    )


def add_allergy(conn: sqlite3.Connection, patient_id: str, allergen: str, reaction: str, status: str) -> None:
    conn.execute(
        """
        INSERT INTO allergies(patient_id, allergen, reaction, status)
        VALUES (?, ?, ?, ?)
        """,
        (patient_id, allergen, reaction, status),
    )


def add_problem(
    conn: sqlite3.Connection,
    patient_id: str,
    code: str,
    name: str,
    status: str,
    onset_date: str | None,
) -> None:
    conn.execute(
        """
        INSERT INTO problems(patient_id, code, name, status, onset_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (patient_id, code, name, status, onset_date),
    )


def add_medication(
    conn: sqlite3.Connection,
    medication_id: str,
    patient_id: str,
    name: str,
    code: str,
    status: str,
    dose: str,
    route: str,
    frequency: str,
    start_date: str | None,
    end_date: str | None,
    source: str,
) -> None:
    conn.execute(
        """
        INSERT INTO medications(
            medication_id, patient_id, name, code, status, dose, route,
            frequency, start_date, end_date, source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            medication_id,
            patient_id,
            name,
            code,
            status,
            dose,
            route,
            frequency,
            start_date,
            end_date,
            source,
        ),
    )


def add_observation(
    conn: sqlite3.Connection,
    observation_id: str,
    patient_id: str,
    case_id: str | None,
    code: str,
    display: str,
    category: str,
    status: str,
    effective_time: str,
    value_text: str | None,
    value_number: float | None,
    unit: str | None,
    interpretation: str | None,
    source: str,
) -> None:
    conn.execute(
        """
        INSERT INTO observations(
            observation_id, patient_id, case_id, code, display, category, status,
            effective_time, value_text, value_number, unit, interpretation, source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            observation_id,
            patient_id,
            case_id,
            code,
            display,
            category,
            status,
            effective_time,
            value_text,
            value_number,
            unit,
            interpretation,
            source,
        ),
    )


def add_imaging(
    conn: sqlite3.Connection,
    imaging_id: str,
    patient_id: str,
    case_id: str | None,
    study: str,
    status: str,
    performed_at: str,
    impression: str,
) -> None:
    conn.execute(
        """
        INSERT INTO imaging(imaging_id, patient_id, case_id, study, status, performed_at, impression)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (imaging_id, patient_id, case_id, study, status, performed_at, impression),
    )


def add_registry(
    conn: sqlite3.Connection,
    case_id: str,
    patient_id: str,
    risk_score: float,
    program_hint: str,
    recent_admission_date: str | None,
    dialysis_schedule: str | None,
    chronic_condition_count: int,
    medication_count: int,
) -> None:
    conn.execute(
        """
        INSERT INTO care_registry(
            case_id, patient_id, risk_score, program_hint, recent_admission_date,
            dialysis_schedule, chronic_condition_count, medication_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case_id,
            patient_id,
            risk_score,
            program_hint,
            recent_admission_date,
            dialysis_schedule,
            chronic_condition_count,
            medication_count,
        ),
    )


def add_sdoh(
    conn: sqlite3.Connection,
    patient_id: str,
    domain: str,
    severity: str,
    evidence: str,
    source: str,
) -> None:
    conn.execute(
        """
        INSERT INTO sdoh(patient_id, domain, severity, evidence, source)
        VALUES (?, ?, ?, ?, ?)
        """,
        (patient_id, domain, severity, evidence, source),
    )


def add_protocol(conn: sqlite3.Connection, protocol_id: str, title: str, body: dict) -> None:
    conn.execute(
        """
        INSERT INTO protocols(protocol_id, title, version, body_json)
        VALUES (?, ?, ?, ?)
        """,
        (protocol_id, title, "2026.1", json.dumps(body, sort_keys=True)),
    )


def load_protocols(conn: sqlite3.Connection) -> None:
    add_protocol(
        conn,
        "RESP-CAP-2026",
        "Adult Respiratory Infection and CAP Assessment",
        {
            "scope": "Synthetic adult acute respiratory clinic cases.",
            "authoritative_statuses": ["final"],
            "controlled_codes": {
                "oxygen_saturation": "59408-5",
                "respiratory_rate": "9279-1",
                "temperature": "8310-5",
                "chest_xray": "CXR-2V",
                "respiratory_viral_pcr": "SARS_FLU_RSV_PCR",
                "pulse_ox_recheck": "PULSE_OX_RECHECK",
                "basic_cbc": "CBC_BASIC",
            },
            "ed_escalation": {
                "oxygen_saturation_room_air_less_than": 90,
                "respiratory_rate_at_least": 30,
                "systolic_bp_less_than": 90,
                "other_red_flags": [
                    "confusion",
                    "sepsis_concern",
                    "immunocompromise",
                    "multilobar_disease",
                ],
            },
            "outpatient_follow_up_hours": 48,
            "allergy_rule": "Use active allergies and avoid implicated medication classes.",
            "return_precaution_codes": [
                "worsening_dyspnea",
                "oxygen_below_90",
                "confusion",
                "persistent_fever",
                "chest_pain",
            ],
        },
    )
    add_protocol(
        conn,
        "PEDS-HEAD-2026",
        "Pediatric Head Injury Clinic Triage",
        {
            "scope": "Synthetic pediatric head injury and concussion assessments.",
            "authoritative_statuses": ["final"],
            "urgent_route_triggers": [
                "repeated_vomiting",
                "worsening_severe_headache",
                "seizure",
                "basilar_skull_signs",
                "focal_neurologic_deficit",
                "gcs_below_15",
                "prolonged_loss_of_consciousness",
            ],
            "mild_tbi_support": [
                "brief_confusion_or_symptoms",
                "normal_or_near_normal_neurologic_exam",
                "no_protocol_urgent_trigger",
            ],
            "restrictions": {
                "return_to_play": "no same-day return; graded return after symptom resolution and clearance",
                "driving": "avoid driving while symptomatic or using sedating medicine",
                "school": "short cognitive rest with gradual return and accommodations",
            },
            "follow_up_hours": [24, 48],
        },
    )
    add_protocol(
        conn,
        "K-REPLETION-2026",
        "Potassium Replacement and Escalation",
        {
            "scope": "Synthetic outpatient potassium replacement support.",
            "authoritative_statuses": ["final"],
            "controlled_codes": {
                "serum_potassium": "K",
                "follow_up_lab": "2823-3",
                "routine_oral_potassium_ndc": "40032-917-01",
                "ecg_summary": "ECG-SUMMARY",
                "egfr": "33914-3",
            },
            "target_potassium_mmol_l": 3.5,
            "routine_dose_rule": {
                "mEq_per_0_1_mmol_l_below_target": 10,
                "round_to_nearest_mEq": 10,
                "applies_only_when_urgent_branch_false": True,
            },
            "urgent_branch": {
                "potassium_less_than": 3.0,
                "symptoms": ["palpitations", "syncope", "weakness_with_arrhythmia_concern"],
                "ecg_abnormality": True,
                "dialysis_dependent_esrd": True,
                "severe_renal_contraindication": True,
            },
            "routine_follow_up": "next morning final serum potassium",
        },
    )
    add_protocol(
        conn,
        "OBS-WINDOW-2026",
        "Observation Window Interpretation",
        {
            "scope": "Synthetic FHIR-like Observation retrieval tasks.",
            "status_rule": "Only status=final observations satisfy protocol gates.",
            "excluded_statuses": ["preliminary", "entered-in-error", "canceled"],
            "same_code_selection": "Choose the latest final effective_time within the target window.",
            "ordering": ["effective_time ascending", "observation_id ascending"],
            "controlled_codes": {
                "serum_potassium": "K",
                "respiratory_viral_pcr": "SARS_FLU_RSV_PCR",
                "chest_xray": "CXR-2V",
            },
        },
    )
    add_protocol(
        conn,
        "CM-HIGH-RISK-2026",
        "High-Risk Care-Management Routing",
        {
            "scope": "Synthetic complex-care registry routing.",
            "high_predictive_risk_min": 0.75,
            "complex_care_supporting_triggers": [
                "chronic_condition_count_at_least_3",
                "recent_admission",
                "dialysis_or_advanced_ckd",
                "heart_failure",
                "uncontrolled_diabetes",
            ],
            "pharmacist_referral_triggers": [
                "active_medication_count_at_least_10",
                "insulin_safety",
                "high_risk_diuretic_or_electrolyte_regimen",
            ],
            "social_work_referral": {
                "moderate_or_severe_domains_at_least": 2,
                "domains": ["transportation", "financial", "food", "housing"],
            },
            "outreach": "Use permission-based outreach when the member is reluctant or refusing.",
            "care_plan_minima": [
                "weekly_contact_initially",
                "medication_reconciliation",
                "barrier_resolution",
                "clear_escalation_conditions",
            ],
        },
    )


def load_target_patients(conn: sqlite3.Connection) -> None:
    target_patient_rows = [
        ("PAT-1002", "FHIR-PAT-1002", "Olivia Harper", 47, "female", "1978-08-12"),
        ("PAT-2207", "FHIR-PAT-2207", "Mason Fields", 14, "male", "2011-07-04"),
        ("PAT-3303", "FHIR-PAT-3303", "Noah Singh", 62, "male", "1963-03-17"),
        ("PAT-4411", "FHIR-PAT-4411", "Denise Coleman", 58, "female", "1967-11-21"),
        ("PAT-5518", "FHIR-PAT-5518", "Grace Lin", 53, "female", "1972-06-03"),
        ("PAT-1914", "FHIR-PAT-1914", "Mateo Rivera", 69, "male", "1956-10-29"),
        ("PAT-2822", "FHIR-PAT-2822", "Avery Thompson", 16, "female", "2009-12-08"),
        ("PAT-3919", "FHIR-PAT-3919", "Priya Desai", 71, "female", "1954-04-19"),
        ("PAT-4908", "FHIR-PAT-4908", "Leon Brooks", 64, "male", "1961-01-15"),
        ("PAT-5927", "FHIR-PAT-5927", "Hannah Kim", 36, "female", "1989-09-27"),
    ]
    for row in target_patient_rows:
        add_patient(conn, row)


def load_respiratory_cases(conn: sqlite3.Connection) -> None:
    add_case(
        conn,
        (
            "CASE-RESP-102",
            "PAT-1002",
            "acute_respiratory",
            "2026-01-14",
            "active",
            "Adult with fever, productive cough, and focal right lower-lobe consolidation.",
        ),
    )
    for key, value, source in [
        ("current_time", "2026-01-14T10:00:00Z", "VISIT-RESP-102"),
        ("chief_complaint", "Fever and productive cough for four days", "VISIT-RESP-102"),
        ("cough", "productive yellow sputum", "VISIT-RESP-102"),
        ("oxygen_room_air_range", "92-93%", "OBS-RESP-102-SPO2"),
        ("dyspnea", "mild on stairs only", "VISIT-RESP-102"),
        ("pleuritic_chest_pain", "mild right-sided pleuritic chest pain with cough", "VISIT-RESP-102"),
        ("confusion", "absent", "VISIT-RESP-102"),
        ("occupational_exposure", "works in a senior center cafeteria", "VISIT-RESP-102"),
        ("allergy_constraint", "active penicillin and sulfonamide allergies", "ALG-RESP-102"),
    ]:
        add_finding(conn, "CASE-RESP-102", key, value, source)
    add_allergy(conn, "PAT-1002", "penicillin", "hives and throat tightness", "active")
    add_allergy(conn, "PAT-1002", "sulfonamide antibiotics", "diffuse rash", "active")
    add_allergy(conn, "PAT-1002", "codeine", "nausea", "inactive")
    add_problem(conn, "PAT-1002", "J45.30", "mild persistent asthma", "active", "2020-02-11")
    add_medication(
        conn,
        "MED-RESP-102-ALB",
        "PAT-1002",
        "albuterol HFA inhaler",
        "RXNORM-435",
        "active",
        "2 puffs",
        "inhalation",
        "every 4 hours as needed",
        "2025-08-02",
        None,
        "medication reconciliation",
    )
    add_observation(
        conn,
        "OBS-RESP-102-SPO2",
        "PAT-1002",
        "CASE-RESP-102",
        "59408-5",
        "Oxygen saturation in Arterial blood by Pulse oximetry",
        "vital-sign",
        "final",
        "2026-01-14T09:10:00Z",
        "93% on room air",
        93.0,
        "%",
        "borderline_low",
        "rooming vitals",
    )
    add_observation(
        conn,
        "OBS-RESP-102-PULSE-OX-RECHECK",
        "PAT-1002",
        "CASE-RESP-102",
        "PULSE_OX_RECHECK",
        "Pulse oximetry recheck",
        "vital-sign",
        "final",
        "2026-01-14T09:36:00Z",
        "92% on room air after walking from imaging",
        92.0,
        "%",
        "borderline_low",
        "repeat vital",
    )
    add_observation(
        conn,
        "OBS-RESP-102-RR",
        "PAT-1002",
        "CASE-RESP-102",
        "9279-1",
        "Respiratory rate",
        "vital-sign",
        "final",
        "2026-01-14T09:10:00Z",
        None,
        24.0,
        "/min",
        "high",
        "rooming vitals",
    )
    add_observation(
        conn,
        "OBS-RESP-102-TEMP",
        "PAT-1002",
        "CASE-RESP-102",
        "8310-5",
        "Body temperature",
        "vital-sign",
        "final",
        "2026-01-14T09:10:00Z",
        None,
        38.3,
        "Cel",
        "high",
        "rooming vitals",
    )
    add_observation(
        conn,
        "OBS-RESP-102-SBP",
        "PAT-1002",
        "CASE-RESP-102",
        "8480-6",
        "Systolic blood pressure",
        "vital-sign",
        "final",
        "2026-01-14T09:10:00Z",
        None,
        118.0,
        "mmHg",
        "normal",
        "rooming vitals",
    )
    add_observation(
        conn,
        "OBS-RESP-102-SARSFLURSV",
        "PAT-1002",
        "CASE-RESP-102",
        "SARS_FLU_RSV_PCR",
        "SARS/Flu/RSV PCR",
        "laboratory",
        "final",
        "2026-01-14T09:31:00Z",
        "not detected",
        None,
        None,
        "negative",
        "rapid respiratory swab",
    )
    add_imaging(
        conn,
        "IMG-RESP-102-CXR",
        "PAT-1002",
        "CASE-RESP-102",
        "Chest radiograph, two views",
        "final",
        "2026-01-14T09:42:00Z",
        "Right lower-lobe airspace consolidation. No pleural effusion. No multilobar disease.",
    )
    add_observation(
        conn,
        "OBS-RESP-102-CXR-IMP",
        "PAT-1002",
        "CASE-RESP-102",
        "CXR-2V",
        "Chest x-ray two-view impression",
        "imaging",
        "final",
        "2026-01-14T09:42:00Z",
        "right lower-lobe consolidation without multilobar disease",
        None,
        None,
        "abnormal",
        "radiology interface",
    )

    add_case(
        conn,
        (
            "CASE-RESP-914",
            "PAT-1914",
            "acute_respiratory",
            "2026-04-03",
            "active",
            "Adult with dyspnea, hypoxemia, and left lower-lobe consolidation.",
        ),
    )
    for key, value, source in [
        ("current_time", "2026-04-03T15:20:00Z", "VISIT-RESP-914"),
        ("chief_complaint", "Fever, cough, and worsening shortness of breath", "VISIT-RESP-914"),
        ("oxygen_room_air", "89%", "OBS-RESP-914-SPO2"),
        ("dyspnea", "present at rest while speaking in short phrases", "VISIT-RESP-914"),
        ("pleuritic_chest_pain", "left-sided pleuritic pain with deep cough", "VISIT-RESP-914"),
        ("confusion", "absent", "VISIT-RESP-914"),
        ("allergy_constraint", "active beta-lactam allergy recorded as amoxicillin angioedema", "ALG-RESP-914"),
    ]:
        add_finding(conn, "CASE-RESP-914", key, value, source)
    add_allergy(conn, "PAT-1914", "amoxicillin", "angioedema", "active")
    add_allergy(conn, "PAT-1914", "cephalexin", "generalized urticaria", "active")
    add_problem(conn, "PAT-1914", "J44.9", "chronic obstructive pulmonary disease", "active", "2019-05-10")
    add_problem(conn, "PAT-1914", "E11.9", "type 2 diabetes mellitus", "active", "2016-03-20")
    add_medication(
        conn,
        "MED-RESP-914-TIO",
        "PAT-1914",
        "tiotropium inhaler",
        "RXNORM-1442131",
        "active",
        "18 mcg",
        "inhalation",
        "daily",
        "2025-11-15",
        None,
        "medication list",
    )
    add_observation(
        conn,
        "OBS-RESP-914-SPO2",
        "PAT-1914",
        "CASE-RESP-914",
        "59408-5",
        "Oxygen saturation in Arterial blood by Pulse oximetry",
        "vital-sign",
        "final",
        "2026-04-03T14:58:00Z",
        "89% on room air",
        89.0,
        "%",
        "low",
        "rooming vitals",
    )
    add_observation(
        conn,
        "OBS-RESP-914-RR",
        "PAT-1914",
        "CASE-RESP-914",
        "9279-1",
        "Respiratory rate",
        "vital-sign",
        "final",
        "2026-04-03T14:58:00Z",
        None,
        28.0,
        "/min",
        "high",
        "rooming vitals",
    )
    add_observation(
        conn,
        "OBS-RESP-914-TEMP",
        "PAT-1914",
        "CASE-RESP-914",
        "8310-5",
        "Body temperature",
        "vital-sign",
        "final",
        "2026-04-03T14:58:00Z",
        None,
        38.8,
        "Cel",
        "high",
        "rooming vitals",
    )
    add_observation(
        conn,
        "OBS-RESP-914-SBP",
        "PAT-1914",
        "CASE-RESP-914",
        "8480-6",
        "Systolic blood pressure",
        "vital-sign",
        "final",
        "2026-04-03T14:58:00Z",
        None,
        104.0,
        "mmHg",
        "normal",
        "rooming vitals",
    )
    add_observation(
        conn,
        "OBS-RESP-914-SARSFLURSV-PRELIM",
        "PAT-1914",
        "CASE-RESP-914",
        "SARS_FLU_RSV_PCR",
        "SARS/Flu/RSV PCR",
        "laboratory",
        "preliminary",
        "2026-04-03T15:12:00Z",
        "pending",
        None,
        None,
        "preliminary",
        "rapid respiratory swab",
    )
    add_observation(
        conn,
        "OBS-RESP-914-PULSE-OX-RECHECK",
        "PAT-1914",
        "CASE-RESP-914",
        "PULSE_OX_RECHECK",
        "Pulse oximetry recheck",
        "vital-sign",
        "final",
        "2026-04-03T15:13:00Z",
        "88% on room air",
        88.0,
        "%",
        "low",
        "repeat vital",
    )
    add_imaging(
        conn,
        "IMG-RESP-914-CXR",
        "PAT-1914",
        "CASE-RESP-914",
        "Portable chest radiograph",
        "final",
        "2026-04-03T15:16:00Z",
        "Left lower-lobe consolidation. No pneumothorax. No multilobar infiltrates.",
    )
    add_observation(
        conn,
        "OBS-RESP-914-CXR-IMP",
        "PAT-1914",
        "CASE-RESP-914",
        "CXR-2V",
        "Chest x-ray two-view impression",
        "imaging",
        "final",
        "2026-04-03T15:16:00Z",
        "left lower-lobe consolidation",
        None,
        None,
        "abnormal",
        "radiology interface",
    )


def load_head_injury_cases(conn: sqlite3.Connection) -> None:
    add_case(
        conn,
        (
            "CASE-HEAD-207",
            "PAT-2207",
            "pediatric_head_injury",
            "2026-01-22",
            "active",
            "Skateboard fall with stable mild symptoms and no vomiting or loss of consciousness.",
        ),
    )
    for key, value, source in [
        ("current_time", "2026-01-22T18:10:00Z", "VISIT-HEAD-207"),
        ("mechanism", "fell from skateboard while turning; helmet worn", "VISIT-HEAD-207"),
        ("loss_of_consciousness", "absent", "VISIT-HEAD-207"),
        ("vomiting", "absent", "VISIT-HEAD-207"),
        ("nausea", "mild", "VISIT-HEAD-207"),
        ("headache", "mild and stable", "VISIT-HEAD-207"),
        ("broken_glasses", "present; small cheek abrasion from frame", "VISIT-HEAD-207"),
        ("coordination", "mild heel-walk coordination issue, no focal weakness", "OBS-HEAD-207-NEURO"),
        ("gcs", "15", "OBS-HEAD-207-GCS"),
    ]:
        add_finding(conn, "CASE-HEAD-207", key, value, source)
    add_problem(conn, "PAT-2207", "F90.9", "attention deficit hyperactivity disorder", "active", "2022-09-12")
    add_medication(
        conn,
        "MED-HEAD-207-MPH",
        "PAT-2207",
        "methylphenidate extended release",
        "RXNORM-1806189",
        "active",
        "18 mg",
        "oral",
        "each morning on school days",
        "2025-09-01",
        None,
        "parent medication list",
    )
    add_observation(
        conn,
        "OBS-HEAD-207-GCS",
        "PAT-2207",
        "CASE-HEAD-207",
        "9269-2",
        "Glasgow coma score total",
        "exam",
        "final",
        "2026-01-22T17:52:00Z",
        None,
        15.0,
        "score",
        "normal",
        "neuro exam",
    )
    add_observation(
        conn,
        "OBS-HEAD-207-VOMIT",
        "PAT-2207",
        "CASE-HEAD-207",
        "HEAD-VOMIT-COUNT",
        "Vomiting episodes after head injury",
        "exam",
        "final",
        "2026-01-22T17:52:00Z",
        None,
        0.0,
        "episodes",
        "normal",
        "history",
    )
    add_observation(
        conn,
        "OBS-HEAD-207-LOC",
        "PAT-2207",
        "CASE-HEAD-207",
        "HEAD-LOC-SECONDS",
        "Loss of consciousness duration",
        "exam",
        "final",
        "2026-01-22T17:52:00Z",
        "none reported",
        0.0,
        "seconds",
        "normal",
        "history",
    )
    add_observation(
        conn,
        "OBS-HEAD-207-NEURO",
        "PAT-2207",
        "CASE-HEAD-207",
        "NEURO-COORD",
        "Coordination exam summary",
        "exam",
        "final",
        "2026-01-22T17:56:00Z",
        "mild difficulty with heel walking; finger-nose normal; no focal weakness",
        None,
        None,
        "mild_abnormal",
        "neuro exam",
    )

    add_case(
        conn,
        (
            "CASE-HEAD-822",
            "PAT-2822",
            "pediatric_head_injury",
            "2026-04-21",
            "active",
            "Sports head injury with repeated vomiting, worsening headache, and brief loss of consciousness.",
        ),
    )
    for key, value, source in [
        ("current_time", "2026-04-21T20:05:00Z", "VISIT-HEAD-822"),
        ("mechanism", "head-to-head collision during soccer match", "VISIT-HEAD-822"),
        ("loss_of_consciousness", "brief, about 20 seconds", "VISIT-HEAD-822"),
        ("vomiting", "three episodes after injury", "OBS-HEAD-822-VOMIT"),
        ("headache", "worsening severe frontal headache", "VISIT-HEAD-822"),
        ("seizure", "absent", "VISIT-HEAD-822"),
        ("focal_neurologic_deficit", "absent on clinic exam", "EXAM-HEAD-822"),
        ("gcs", "15", "OBS-HEAD-822-GCS"),
    ]:
        add_finding(conn, "CASE-HEAD-822", key, value, source)
    add_observation(
        conn,
        "OBS-HEAD-822-GCS",
        "PAT-2822",
        "CASE-HEAD-822",
        "9269-2",
        "Glasgow coma score total",
        "exam",
        "final",
        "2026-04-21T19:46:00Z",
        None,
        15.0,
        "score",
        "normal",
        "neuro exam",
    )
    add_observation(
        conn,
        "OBS-HEAD-822-VOMIT",
        "PAT-2822",
        "CASE-HEAD-822",
        "HEAD-VOMIT-COUNT",
        "Vomiting episodes after head injury",
        "exam",
        "final",
        "2026-04-21T19:46:00Z",
        None,
        3.0,
        "episodes",
        "high",
        "history",
    )
    add_observation(
        conn,
        "OBS-HEAD-822-LOC",
        "PAT-2822",
        "CASE-HEAD-822",
        "HEAD-LOC-SECONDS",
        "Loss of consciousness duration",
        "exam",
        "final",
        "2026-04-21T19:46:00Z",
        "brief",
        20.0,
        "seconds",
        "abnormal",
        "history",
    )
    add_observation(
        conn,
        "OBS-HEAD-822-NEURO",
        "PAT-2822",
        "CASE-HEAD-822",
        "NEURO-FOCAL",
        "Focal neurologic deficit screen",
        "exam",
        "final",
        "2026-04-21T19:50:00Z",
        "no focal weakness, normal pupils, no basilar skull signs",
        None,
        None,
        "normal",
        "neuro exam",
    )


def load_potassium_cases(conn: sqlite3.Connection) -> None:
    add_case(
        conn,
        (
            "CASE-K-303",
            "PAT-3303",
            "potassium_repletion",
            "2026-02-10",
            "active",
            "Outpatient potassium review with same-day serum electrolyte and renal-function records.",
        ),
    )
    for key, value, source in [
        ("current_time", "2026-02-10T10:15:00Z", "TASK-CLOCK-K-303"),
        ("symptoms", "no palpitations, syncope, or severe weakness", "VISIT-K-303"),
        ("ecg", "normal sinus rhythm", "OBS-K-303-ECG"),
        ("renal_contraindication", "absent; eGFR 64 mL/min/1.73m2", "OBS-EGFR-303-20260209"),
    ]:
        add_finding(conn, "CASE-K-303", key, value, source)
    add_problem(conn, "PAT-3303", "I10", "essential hypertension", "active", "2018-04-05")
    add_medication(
        conn,
        "MED-K-303-HCTZ",
        "PAT-3303",
        "hydrochlorothiazide",
        "RXNORM-5487",
        "active",
        "25 mg",
        "oral",
        "daily",
        "2025-01-15",
        None,
        "medication list",
    )
    add_observation(
        conn,
        "OBS-K-303-20260209-0730",
        "PAT-3303",
        "CASE-K-303",
        "K",
        "Potassium [Moles/volume] in Serum or Plasma",
        "laboratory",
        "final",
        "2026-02-09T07:30:00Z",
        None,
        3.4,
        "mmol/L",
        "low",
        "chemistry analyzer",
    )
    add_observation(
        conn,
        "OBS-K-303-20260210-0620",
        "PAT-3303",
        "CASE-K-303",
        "K",
        "Potassium [Moles/volume] in Serum or Plasma",
        "laboratory",
        "final",
        "2026-02-10T06:20:00Z",
        None,
        3.2,
        "mmol/L",
        "low",
        "chemistry analyzer",
    )
    add_observation(
        conn,
        "OBS-K-303-20260210-0810-PRELIM",
        "PAT-3303",
        "CASE-K-303",
        "K",
        "Potassium [Moles/volume] in Serum or Plasma",
        "laboratory",
        "preliminary",
        "2026-02-10T08:10:00Z",
        None,
        3.1,
        "mmol/L",
        "low",
        "chemistry analyzer",
    )
    add_observation(
        conn,
        "OBS-K-303-WHOLE-BLOOD",
        "PAT-3303",
        "CASE-K-303",
        "6298-4",
        "Potassium [Moles/volume] in Blood",
        "laboratory",
        "final",
        "2026-02-10T08:22:00Z",
        None,
        3.0,
        "mmol/L",
        "low",
        "point-of-care cartridge",
    )
    add_observation(
        conn,
        "OBS-EGFR-303-20260209",
        "PAT-3303",
        "CASE-K-303",
        "33914-3",
        "eGFR",
        "laboratory",
        "final",
        "2026-02-09T07:35:00Z",
        None,
        64.0,
        "mL/min/1.73m2",
        "mildly_low",
        "chemistry analyzer",
    )
    add_observation(
        conn,
        "OBS-K-303-ECG",
        "PAT-3303",
        "CASE-K-303",
        "ECG-SUMMARY",
        "ECG summary",
        "procedure",
        "final",
        "2026-02-10T09:12:00Z",
        "normal sinus rhythm; no U waves or acute arrhythmia",
        None,
        None,
        "normal",
        "ECG interface",
    )

    add_case(
        conn,
        (
            "CASE-K-919",
            "PAT-3919",
            "potassium_repletion",
            "2026-04-18",
            "active",
            "Potassium review with low same-day serum electrolyte result and phone-triage symptoms.",
        ),
    )
    for key, value, source in [
        ("current_time", "2026-04-18T14:35:00Z", "TASK-CLOCK-K-919"),
        ("symptoms", "palpitations and lightheadedness reported by phone triage", "TRIAGE-K-919"),
        ("ecg", "sinus tachycardia with prominent U waves", "OBS-K-919-ECG"),
        ("renal_context", "eGFR 58 mL/min/1.73m2; not dialysis dependent", "OBS-EGFR-919-20260417"),
    ]:
        add_finding(conn, "CASE-K-919", key, value, source)
    add_problem(conn, "PAT-3919", "N18.31", "chronic kidney disease stage 3a", "active", "2021-08-12")
    add_problem(conn, "PAT-3919", "I48.0", "paroxysmal atrial fibrillation", "active", "2024-02-18")
    add_medication(
        conn,
        "MED-K-919-FURO",
        "PAT-3919",
        "furosemide",
        "RXNORM-4603",
        "active",
        "40 mg",
        "oral",
        "daily",
        "2025-10-11",
        None,
        "medication list",
    )
    add_observation(
        conn,
        "OBS-K-919-20260417-0800",
        "PAT-3919",
        "CASE-K-919",
        "K",
        "Potassium [Moles/volume] in Serum or Plasma",
        "laboratory",
        "final",
        "2026-04-17T08:00:00Z",
        None,
        3.4,
        "mmol/L",
        "low",
        "chemistry analyzer",
    )
    add_observation(
        conn,
        "OBS-K-919-20260418-1240-PRELIM",
        "PAT-3919",
        "CASE-K-919",
        "K",
        "Potassium [Moles/volume] in Serum or Plasma",
        "laboratory",
        "preliminary",
        "2026-04-18T12:40:00Z",
        None,
        2.9,
        "mmol/L",
        "critical_low",
        "chemistry analyzer",
    )
    add_observation(
        conn,
        "OBS-K-919-20260418-1320",
        "PAT-3919",
        "CASE-K-919",
        "K",
        "Potassium [Moles/volume] in Serum or Plasma",
        "laboratory",
        "final",
        "2026-04-18T13:20:00Z",
        None,
        2.8,
        "mmol/L",
        "critical_low",
        "chemistry analyzer",
    )
    add_observation(
        conn,
        "OBS-EGFR-919-20260417",
        "PAT-3919",
        "CASE-K-919",
        "33914-3",
        "eGFR",
        "laboratory",
        "final",
        "2026-04-17T08:05:00Z",
        None,
        58.0,
        "mL/min/1.73m2",
        "mildly_low",
        "chemistry analyzer",
    )
    add_observation(
        conn,
        "OBS-K-919-ECG",
        "PAT-3919",
        "CASE-K-919",
        "ECG-SUMMARY",
        "ECG summary",
        "procedure",
        "final",
        "2026-04-18T14:05:00Z",
        "sinus tachycardia with prominent U waves; no ST elevation",
        None,
        None,
        "abnormal",
        "ECG interface",
    )


def load_care_management_cases(conn: sqlite3.Connection) -> None:
    add_case(
        conn,
        (
            "CASE-CM-411",
            "PAT-4411",
            "care_management",
            "2026-02-27",
            "active",
            "ESRD and diabetes registry review after recent volume-overload admission.",
        ),
    )
    for key, value, source in [
        ("registry_risk_score", "0.84", "REG-CM-411"),
        ("dialysis_schedule", "Tuesday/Thursday/Saturday", "REG-CM-411"),
        ("recent_admission", "volume overload admission on 2026-02-12", "REG-CM-411"),
        ("hba1c", "9.4%", "OBS-CM-411-A1C"),
        ("phosphorus", "7.1 mg/dL", "OBS-CM-411-PHOS"),
        ("blood_pressure", "152/88 mmHg", "OBS-CM-411-BP-SBP"),
        ("active_medications", "21", "REG-CM-411"),
        ("sdoh_barriers", "transportation and financial barriers disclosed by member", "SDOH-CM-411"),
        ("dialysis_fatigue", "member reports fatigue after Tue/Thu/Sat dialysis sessions", "CALL-CM-411"),
        (
            "outreach_posture",
            "engaged but wants calls after dialysis; permission-based outreach still required",
            "CALL-CM-411",
        ),
    ]:
        add_finding(conn, "CASE-CM-411", key, value, source)
    add_registry(
        conn, "CASE-CM-411", "PAT-4411", 0.84, "complex_care_esrd_diabetes", "2026-02-12", "Tue/Thu/Sat", 5, 21
    )
    for code, name, onset in [
        ("N18.6", "end stage renal disease on dialysis", "2020-01-03"),
        ("E11.65", "type 2 diabetes mellitus with hyperglycemia", "2014-06-01"),
        ("I10", "essential hypertension", "2013-11-20"),
        ("E83.39", "hyperphosphatemia", "2024-09-18"),
        ("I50.32", "chronic diastolic heart failure", "2022-04-10"),
    ]:
        add_problem(conn, "PAT-4411", code, name, "active", onset)
    active_meds_411 = [
        ("insulin glargine", "RXNORM-274783", "36 units", "subcutaneous", "nightly"),
        ("insulin lispro", "RXNORM-86009", "8 units", "subcutaneous", "with meals"),
        ("sevelamer carbonate", "RXNORM-749206", "800 mg", "oral", "three times daily with meals"),
        ("carvedilol", "RXNORM-20352", "12.5 mg", "oral", "twice daily"),
        ("amlodipine", "RXNORM-17767", "10 mg", "oral", "daily"),
        ("hydralazine", "RXNORM-5470", "50 mg", "oral", "three times daily"),
        ("torsemide", "RXNORM-38413", "40 mg", "oral", "daily"),
        ("atorvastatin", "RXNORM-83367", "40 mg", "oral", "nightly"),
        ("aspirin", "RXNORM-1191", "81 mg", "oral", "daily"),
        ("gabapentin", "RXNORM-25480", "300 mg", "oral", "nightly"),
        ("pantoprazole", "RXNORM-40790", "40 mg", "oral", "daily"),
        ("renal multivitamin", "RXNORM-RENALVITE", "1 tablet", "oral", "daily"),
        ("calcitriol", "RXNORM-1894", "0.25 mcg", "oral", "Mon/Wed/Fri"),
        ("epoetin alfa", "RXNORM-205923", "per protocol", "injection", "at dialysis"),
        ("cinacalcet", "RXNORM-349345", "30 mg", "oral", "daily"),
        ("lisinopril", "RXNORM-29046", "5 mg", "oral", "daily"),
        ("ondansetron", "RXNORM-26225", "4 mg", "oral", "as needed"),
        ("polyethylene glycol", "RXNORM-8516", "17 g", "oral", "daily"),
        ("acetaminophen", "RXNORM-161", "650 mg", "oral", "as needed"),
        ("fluticasone nasal", "RXNORM-41126", "1 spray", "nasal", "daily"),
        ("albuterol HFA", "RXNORM-435", "2 puffs", "inhalation", "as needed"),
    ]
    for idx, (name, code, dose, route, freq) in enumerate(active_meds_411, start=1):
        add_medication(
            conn,
            f"MED-CM-411-{idx:02d}",
            "PAT-4411",
            name,
            code,
            "active",
            dose,
            route,
            freq,
            "2025-01-01",
            None,
            "dialysis medication reconciliation",
        )
    add_observation(
        conn,
        "OBS-CM-411-A1C",
        "PAT-4411",
        "CASE-CM-411",
        "4548-4",
        "Hemoglobin A1c/Hemoglobin.total in Blood",
        "laboratory",
        "final",
        "2026-02-24T08:15:00Z",
        None,
        9.4,
        "%",
        "high",
        "lab feed",
    )
    add_observation(
        conn,
        "OBS-CM-411-PHOS",
        "PAT-4411",
        "CASE-CM-411",
        "2777-1",
        "Phosphate [Mass/volume] in Serum or Plasma",
        "laboratory",
        "final",
        "2026-02-24T08:15:00Z",
        None,
        7.1,
        "mg/dL",
        "high",
        "dialysis lab feed",
    )
    add_observation(
        conn,
        "OBS-CM-411-BP-SBP",
        "PAT-4411",
        "CASE-CM-411",
        "8480-6",
        "Systolic blood pressure",
        "vital-sign",
        "final",
        "2026-02-27T10:30:00Z",
        None,
        152.0,
        "mmHg",
        "high",
        "clinic vitals",
    )
    add_observation(
        conn,
        "OBS-CM-411-BP-DBP",
        "PAT-4411",
        "CASE-CM-411",
        "8462-4",
        "Diastolic blood pressure",
        "vital-sign",
        "final",
        "2026-02-27T10:30:00Z",
        None,
        88.0,
        "mmHg",
        "high",
        "clinic vitals",
    )
    add_observation(
        conn,
        "OBS-CM-411-PHQ9",
        "PAT-4411",
        "CASE-CM-411",
        "PHQ-9",
        "Patient Health Questionnaire 9 item total score",
        "survey",
        "final",
        "2026-02-27T10:35:00Z",
        None,
        7.0,
        "score",
        "mild",
        "care management screen",
    )
    add_sdoh(
        conn,
        "PAT-4411",
        "transportation",
        "moderate",
        "missed one dialysis-adjacent clinic visit when paratransit ride failed",
        "member-disclosed",
    )
    add_sdoh(
        conn,
        "PAT-4411",
        "financial",
        "moderate",
        "reports choosing between renal diet foods and utility bill",
        "member-disclosed",
    )
    add_sdoh(
        conn,
        "PAT-4411",
        "housing",
        "mild",
        "stable apartment but elevator outages complicate dialysis travel",
        "care-manager note",
    )

    add_case(
        conn,
        (
            "CASE-CM-908",
            "PAT-4908",
            "care_management",
            "2026-05-12",
            "active",
            "Post-heart-failure admission registry case with diabetes, CKD, barriers, and initial reluctance.",
        ),
    )
    for key, value, source in [
        ("registry_risk_score", "0.79", "REG-CM-908"),
        ("recent_admission", "heart-failure exacerbation discharge on 2026-05-02", "REG-CM-908"),
        ("hba1c", "9.1%", "OBS-CM-908-A1C"),
        ("egfr", "28 mL/min/1.73m2", "OBS-CM-908-EGFR"),
        ("blood_pressure", "158/92 mmHg", "OBS-CM-908-BP-SBP"),
        ("active_medications", "14", "REG-CM-908"),
        ("sdoh_barriers", "transportation, financial, and food barriers", "SDOH-CM-908"),
        ("outreach_posture", "initially reluctant and asks not to be pushed into another program", "CALL-CM-908"),
    ]:
        add_finding(conn, "CASE-CM-908", key, value, source)
    add_registry(conn, "CASE-CM-908", "PAT-4908", 0.79, "complex_care_hf_diabetes_ckd", "2026-05-02", None, 4, 14)
    for code, name, onset in [
        ("I50.23", "acute on chronic systolic heart failure", "2022-10-12"),
        ("E11.65", "type 2 diabetes mellitus with hyperglycemia", "2017-03-22"),
        ("N18.4", "chronic kidney disease stage 4", "2024-06-04"),
        ("I10", "essential hypertension", "2015-09-14"),
    ]:
        add_problem(conn, "PAT-4908", code, name, "active", onset)
    active_meds_908 = [
        ("insulin glargine", "RXNORM-274783", "28 units", "subcutaneous", "nightly"),
        ("insulin aspart", "RXNORM-51428", "sliding scale", "subcutaneous", "with meals"),
        ("torsemide", "RXNORM-38413", "60 mg", "oral", "daily"),
        ("spironolactone", "RXNORM-9997", "25 mg", "oral", "daily"),
        ("sacubitril-valsartan", "RXNORM-1656340", "49/51 mg", "oral", "twice daily"),
        ("metoprolol succinate", "RXNORM-866427", "100 mg", "oral", "daily"),
        ("hydralazine", "RXNORM-5470", "25 mg", "oral", "three times daily"),
        ("isosorbide dinitrate", "RXNORM-6058", "20 mg", "oral", "three times daily"),
        ("atorvastatin", "RXNORM-83367", "80 mg", "oral", "nightly"),
        ("aspirin", "RXNORM-1191", "81 mg", "oral", "daily"),
        ("ferrous sulfate", "RXNORM-24947", "325 mg", "oral", "daily"),
        ("pantoprazole", "RXNORM-40790", "40 mg", "oral", "daily"),
        ("albuterol HFA", "RXNORM-435", "2 puffs", "inhalation", "as needed"),
        ("acetaminophen", "RXNORM-161", "650 mg", "oral", "as needed"),
    ]
    for idx, (name, code, dose, route, freq) in enumerate(active_meds_908, start=1):
        add_medication(
            conn,
            f"MED-CM-908-{idx:02d}",
            "PAT-4908",
            name,
            code,
            "active",
            dose,
            route,
            freq,
            "2025-03-01",
            None,
            "post-discharge medication reconciliation",
        )
    add_observation(
        conn,
        "OBS-CM-908-A1C",
        "PAT-4908",
        "CASE-CM-908",
        "4548-4",
        "Hemoglobin A1c/Hemoglobin.total in Blood",
        "laboratory",
        "final",
        "2026-05-09T09:00:00Z",
        None,
        9.1,
        "%",
        "high",
        "lab feed",
    )
    add_observation(
        conn,
        "OBS-CM-908-EGFR",
        "PAT-4908",
        "CASE-CM-908",
        "33914-3",
        "eGFR",
        "laboratory",
        "final",
        "2026-05-09T09:00:00Z",
        None,
        28.0,
        "mL/min/1.73m2",
        "low",
        "lab feed",
    )
    add_observation(
        conn,
        "OBS-CM-908-BP-SBP",
        "PAT-4908",
        "CASE-CM-908",
        "8480-6",
        "Systolic blood pressure",
        "vital-sign",
        "final",
        "2026-05-12T11:18:00Z",
        None,
        158.0,
        "mmHg",
        "high",
        "clinic vitals",
    )
    add_observation(
        conn,
        "OBS-CM-908-BP-DBP",
        "PAT-4908",
        "CASE-CM-908",
        "8462-4",
        "Diastolic blood pressure",
        "vital-sign",
        "final",
        "2026-05-12T11:18:00Z",
        None,
        92.0,
        "mmHg",
        "high",
        "clinic vitals",
    )
    add_sdoh(
        conn, "PAT-4908", "transportation", "moderate", "no reliable ride to cardiology follow-up", "member-disclosed"
    )
    add_sdoh(
        conn,
        "PAT-4908",
        "financial",
        "moderate",
        "skipped copays after discharge due to rent pressure",
        "member-disclosed",
    )
    add_sdoh(
        conn, "PAT-4908", "food", "moderate", "runs out of low-sodium foods near end of month", "member-disclosed"
    )


def load_observation_window_cases(conn: sqlite3.Connection) -> None:
    add_case(
        conn,
        (
            "CASE-LAB-518",
            "PAT-5518",
            "observation_window",
            "2026-04-01",
            "active",
            "March 2026 serum potassium observation-window review with final and distractor observations.",
        ),
    )
    for key, value, source in [
        ("target_patient_id", "PAT-5518", "CASE-LAB-518"),
        ("target_code", "K", "OBS-WINDOW-2026"),
        ("window_start", "2026-03-01T00:00:00Z", "CASE-LAB-518"),
        ("window_end", "2026-04-01T00:00:00Z", "CASE-LAB-518"),
        ("status_rule", "final observations only", "OBS-WINDOW-2026"),
        ("nearby_non_target_lab", "NA sodium observation appears in the same month", "OBS-NA-518-20260315"),
    ]:
        add_finding(conn, "CASE-LAB-518", key, value, source)
    add_problem(conn, "PAT-5518", "E87.6", "hypokalemia history", "active", "2025-12-02")
    add_observation(
        conn,
        "OBS-K-518-20260227-0900",
        "PAT-5518",
        "CASE-LAB-518",
        "K",
        "Potassium [Moles/volume] in Serum or Plasma",
        "laboratory",
        "final",
        "2026-02-27T09:00:00Z",
        None,
        3.4,
        "mmol/L",
        "low",
        "chemistry analyzer",
    )
    add_observation(
        conn,
        "OBS-K-518-20260305-0810",
        "PAT-5518",
        "CASE-LAB-518",
        "K",
        "Potassium [Moles/volume] in Serum or Plasma",
        "laboratory",
        "final",
        "2026-03-05T08:10:00Z",
        None,
        3.5,
        "mmol/L",
        "normal",
        "chemistry analyzer",
    )
    add_observation(
        conn,
        "OBS-K-518-20260320-0745",
        "PAT-5518",
        "CASE-LAB-518",
        "K",
        "Potassium [Moles/volume] in Serum or Plasma",
        "laboratory",
        "final",
        "2026-03-20T07:45:00Z",
        None,
        3.6,
        "mmol/L",
        "normal",
        "chemistry analyzer",
    )
    add_observation(
        conn,
        "OBS-K-518-PRELIM-20260328",
        "PAT-5518",
        "CASE-LAB-518",
        "K",
        "Potassium [Moles/volume] in Serum or Plasma",
        "laboratory",
        "preliminary",
        "2026-03-28T11:00:00Z",
        None,
        3.2,
        "mmol/L",
        "low",
        "chemistry analyzer",
    )
    add_observation(
        conn,
        "OBS-NA-518-20260315",
        "PAT-5518",
        "CASE-LAB-518",
        "NA",
        "Sodium [Moles/volume] in Serum or Plasma",
        "laboratory",
        "final",
        "2026-03-15T08:00:00Z",
        None,
        139.0,
        "mmol/L",
        "normal",
        "chemistry analyzer",
    )
    add_observation(
        conn,
        "OBS-K-518-WRONGPAT-20260321",
        "PAT-3303",
        "CASE-LAB-518",
        "K",
        "Potassium [Moles/volume] in Serum or Plasma",
        "laboratory",
        "final",
        "2026-03-21T08:00:00Z",
        None,
        3.1,
        "mmol/L",
        "low",
        "chemistry analyzer",
    )

    add_case(
        conn,
        (
            "CASE-LAB-927",
            "PAT-5927",
            "observation_window",
            "2026-05-08",
            "active",
            "Respiratory observation-window review for final viral PCR and CXR observations.",
        ),
    )
    for key, value, source in [
        ("target_patient_id", "PAT-5927", "CASE-LAB-927"),
        ("window_start", "2026-05-01T00:00:00Z", "CASE-LAB-927"),
        ("window_end", "2026-05-04T00:00:00Z", "CASE-LAB-927"),
        ("viral_code", "SARS_FLU_RSV_PCR", "OBS-WINDOW-2026"),
        ("cxr_observation_code", "CXR-2V", "OBS-WINDOW-2026"),
        ("status_rule", "final observations only", "OBS-WINDOW-2026"),
        ("respiratory_context", "cough, fever, and focal crackles during target window", "VISIT-LAB-927"),
    ]:
        add_finding(conn, "CASE-LAB-927", key, value, source)
    add_observation(
        conn,
        "OBS-CXR-927-20260429",
        "PAT-5927",
        "CASE-LAB-927",
        "CXR-2V",
        "Chest x-ray two-view impression",
        "imaging",
        "final",
        "2026-04-29T16:20:00Z",
        "no acute cardiopulmonary process",
        None,
        None,
        "normal",
        "outside-window radiology",
    )
    add_observation(
        conn,
        "OBS-VIRAL-927-20260502-1035",
        "PAT-5927",
        "CASE-LAB-927",
        "SARS_FLU_RSV_PCR",
        "SARS/Flu/RSV PCR",
        "laboratory",
        "final",
        "2026-05-02T10:35:00Z",
        "negative",
        None,
        None,
        "negative",
        "respiratory swab",
    )
    add_observation(
        conn,
        "OBS-VIRAL-927-PRELIM-20260502",
        "PAT-5927",
        "CASE-LAB-927",
        "SARS_FLU_RSV_PCR",
        "SARS/Flu/RSV PCR",
        "laboratory",
        "preliminary",
        "2026-05-02T10:10:00Z",
        "pending",
        None,
        None,
        "preliminary",
        "respiratory swab",
    )
    add_observation(
        conn,
        "OBS-CXR-927-20260502-1110",
        "PAT-5927",
        "CASE-LAB-927",
        "CXR-2V",
        "Chest x-ray two-view impression",
        "imaging",
        "final",
        "2026-05-02T11:10:00Z",
        "right_middle_lobe_infiltrate",
        None,
        None,
        "abnormal",
        "radiology interface",
    )
    add_observation(
        conn,
        "OBS-CBC-927-20260502",
        "PAT-5927",
        "CASE-LAB-927",
        "CBC_BASIC",
        "Basic complete blood count",
        "laboratory",
        "final",
        "2026-05-02T11:00:00Z",
        "white blood cell count 12.4 K/uL",
        12.4,
        "10*3/uL",
        "high",
        "hematology analyzer",
    )
    add_observation(
        conn,
        "OBS-CXR-927-20260505-FOLLOWUP",
        "PAT-5927",
        "CASE-LAB-927",
        "CXR-2V",
        "Chest x-ray two-view impression",
        "imaging",
        "final",
        "2026-05-05T09:00:00Z",
        "improving right middle-lobe infiltrate",
        None,
        None,
        "abnormal",
        "outside-window radiology",
    )
    add_imaging(
        conn,
        "IMG-LAB-927-CXR",
        "PAT-5927",
        "CASE-LAB-927",
        "Chest radiograph, two views",
        "final",
        "2026-05-02T11:10:00Z",
        "Right middle-lobe infiltrate consistent with pneumonia.",
    )


def load_targets(conn: sqlite3.Connection) -> None:
    load_target_patients(conn)
    load_respiratory_cases(conn)
    load_head_injury_cases(conn)
    load_potassium_cases(conn)
    load_care_management_cases(conn)
    load_observation_window_cases(conn)


def random_date(rng: random.Random, year: int = 2026, month: int | None = None) -> str:
    months = [month] if month else list(range(1, 7))
    selected_month = rng.choice(months)
    day = rng.randint(1, 28)
    hour = rng.randint(6, 20)
    minute = rng.choice([0, 5, 10, 15, 20, 30, 40, 45, 50])
    return f"{year:04d}-{selected_month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00Z"


def load_distractors(conn: sqlite3.Connection) -> None:
    rng = random.Random(SEED)
    first_names = [
        "Alex",
        "Jordan",
        "Casey",
        "Taylor",
        "Morgan",
        "Riley",
        "Jamie",
        "Quinn",
        "Rowan",
        "Sam",
    ]
    last_names = [
        "Allen",
        "Baker",
        "Carter",
        "Diaz",
        "Evans",
        "Foster",
        "Garcia",
        "Hughes",
        "Irwin",
        "Jones",
    ]
    case_types = [
        "acute_respiratory",
        "pediatric_head_injury",
        "potassium_repletion",
        "care_management",
        "observation_window",
    ]
    allergy_pool = [
        ("penicillin", "rash"),
        ("sulfonamide antibiotics", "hives"),
        ("azithromycin", "nausea"),
        ("latex", "contact dermatitis"),
        ("ibuprofen", "wheezing"),
    ]
    med_pool = [
        ("metformin", "RXNORM-6809", "500 mg", "oral", "twice daily"),
        ("lisinopril", "RXNORM-29046", "10 mg", "oral", "daily"),
        ("atorvastatin", "RXNORM-83367", "20 mg", "oral", "nightly"),
        ("albuterol HFA", "RXNORM-435", "2 puffs", "inhalation", "as needed"),
        ("omeprazole", "RXNORM-7646", "20 mg", "oral", "daily"),
    ]
    problem_pool = [
        ("I10", "essential hypertension"),
        ("E11.9", "type 2 diabetes mellitus"),
        ("J45.20", "mild intermittent asthma"),
        ("N18.31", "chronic kidney disease stage 3a"),
        ("F41.9", "anxiety disorder"),
    ]
    patient_ids = []
    for idx in range(80):
        patient_id = f"PAT-D{2000 + idx}"
        patient_ids.append(patient_id)
        name = f"{rng.choice(first_names)} {rng.choice(last_names)}"
        age = rng.randint(7, 86)
        sex = rng.choice(["female", "male", "nonbinary"])
        birth_year = 2026 - age
        add_patient(
            conn,
            (
                patient_id,
                f"FHIR-{patient_id}",
                name,
                age,
                sex,
                f"{birth_year:04d}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
            ),
        )
        if rng.random() < 0.65:
            code, name_problem = rng.choice(problem_pool)
            add_problem(
                conn,
                patient_id,
                code,
                name_problem,
                rng.choice(["active", "active", "resolved"]),
                f"{rng.randint(2010, 2025)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
            )

    for idx in range(50):
        patient_id = rng.choice(patient_ids)
        allergen, reaction = rng.choice(allergy_pool)
        add_allergy(conn, patient_id, allergen, reaction, rng.choice(["active", "active", "inactive"]))

    for idx in range(60):
        patient_id = rng.choice(patient_ids)
        med_name, code, dose, route, freq = rng.choice(med_pool)
        status = rng.choice(["active", "active", "historical"])
        end_date = None if status == "active" else f"2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
        add_medication(
            conn,
            f"MED-D{idx:03d}",
            patient_id,
            med_name,
            code,
            status,
            dose,
            route,
            freq,
            "2024-01-01",
            end_date,
            "distractor medication reconciliation",
        )

    obs_codes = [
        ("K", "Potassium [Moles/volume] in Serum or Plasma", "laboratory", "mmol/L", (3.0, 4.8)),
        ("6298-4", "Potassium [Moles/volume] in Blood", "laboratory", "mmol/L", (3.0, 4.8)),
        ("59408-5", "Oxygen saturation in Arterial blood by Pulse oximetry", "vital-sign", "%", (88, 99)),
        ("9279-1", "Respiratory rate", "vital-sign", "/min", (14, 32)),
        ("4548-4", "Hemoglobin A1c/Hemoglobin.total in Blood", "laboratory", "%", (5.2, 11.2)),
        ("33914-3", "eGFR", "laboratory", "mL/min/1.73m2", (18, 105)),
    ]
    for idx in range(40):
        patient_id = rng.choice(patient_ids)
        case_id = f"CASE-D{3000 + idx}"
        case_type = rng.choice(case_types)
        add_case(
            conn,
            (
                case_id,
                patient_id,
                case_type,
                f"2026-{rng.randint(1, 6):02d}-{rng.randint(1, 28):02d}",
                rng.choice(["active", "closed", "active"]),
                f"Synthetic distractor {case_type.replace('_', ' ')} record with mixed source quality.",
            ),
        )
        add_finding(
            conn,
            case_id,
            "distractor_note",
            "Record is clinically plausible but not one of the target cases.",
            f"VISIT-{case_id}",
        )
        if case_type == "care_management":
            add_registry(
                conn,
                case_id,
                patient_id,
                round(rng.uniform(0.2, 0.93), 2),
                rng.choice(["routine_outreach", "complex_care_review", "pharmacy_only"]),
                f"2026-{rng.randint(1, 6):02d}-{rng.randint(1, 28):02d}" if rng.random() < 0.4 else None,
                rng.choice([None, "Mon/Wed/Fri", "Tue/Thu/Sat"]),
                rng.randint(1, 6),
                rng.randint(2, 18),
            )
        if case_type == "acute_respiratory":
            add_imaging(
                conn,
                f"IMG-D{idx:03d}-CXR",
                patient_id,
                case_id,
                "Chest radiograph",
                rng.choice(["final", "preliminary", "canceled"]),
                random_date(rng),
                rng.choice(
                    [
                        "No acute cardiopulmonary process.",
                        "Patchy right basilar opacity, atelectasis favored.",
                        "Subtle left lower-lobe opacity; correlate clinically.",
                    ]
                ),
            )
        for obs_idx in range(4):
            code, display, category, unit, bounds = rng.choice(obs_codes)
            value = round(rng.uniform(bounds[0], bounds[1]), 1)
            status = rng.choice(["final", "final", "preliminary", "canceled", "entered-in-error"])
            add_observation(
                conn,
                f"OBS-D{idx:03d}-{obs_idx:02d}",
                patient_id,
                case_id,
                code,
                display,
                category,
                status,
                random_date(rng),
                None,
                value,
                unit,
                rng.choice(["normal", "low", "high", "borderline", None]),
                "generated distractor feed",
            )


def write_manifests(conn: sqlite3.Connection, db_path: Path) -> None:
    manifest_path = db_path.parent / "manifest.json"
    seed_manifest_path = db_path.parent / "seed_manifest.json"
    tables = [
        "patients",
        "cases",
        "case_findings",
        "allergies",
        "problems",
        "medications",
        "observations",
        "imaging",
        "care_registry",
        "sdoh",
        "protocols",
    ]
    counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "seed": SEED,
        "database": db_path.name,
        "counts": counts,
        "target_case_ids": TARGET_CASES,
        "target_patient_ids": TARGET_PATIENTS,
        "protocol_ids": PROTOCOL_IDS,
        "distractor_minimums": {
            "patients": 80,
            "cases": 40,
            "observations": 160,
            "medication_allergy_records": 40,
        },
    }
    seed_manifest = {
        "seed": SEED,
        "random_generator": "python random.Random",
        "schema_version": SCHEMA_VERSION,
        "notes": [
            "Target records are authored deterministically.",
            "Distractor records are generated from the fixed seed.",
            "Generated files are environment-internal and not solver inputs.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    seed_manifest_path.write_text(json.dumps(seed_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def generate(db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()
    conn = connect(db_path)
    try:
        init_schema(conn)
        load_protocols(conn)
        load_targets(conn)
        load_distractors(conn)
        conn.commit()
        write_manifests(conn, db_path)
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Harborview Synthetic Clinic data.")
    parser.add_argument(
        "--db", default=os.environ.get("TASK_ENV_DB", str(DEFAULT_DB_PATH)), help="SQLite database path"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate(Path(args.db))


if __name__ == "__main__":
    main()
