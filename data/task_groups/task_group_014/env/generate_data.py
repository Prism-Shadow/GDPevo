#!/usr/bin/env python3
"""Generate deterministic Northstar payer-operations SQLite data."""

from __future__ import annotations

import json
import random
import sqlite3
from pathlib import Path


SEED = 140417
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "northstar_pa.sqlite"
MANIFEST_PATH = ROOT / "manifest.json"


SCHEMA = [
    """
    CREATE TABLE members(
        member_id TEXT PRIMARY KEY,
        patient_name TEXT NOT NULL,
        dob TEXT NOT NULL,
        plan_id TEXT NOT NULL,
        plan_type TEXT NOT NULL,
        product TEXT NOT NULL,
        employer_group TEXT,
        member_status TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE plans(
        plan_id TEXT PRIMARY KEY,
        payer_name TEXT NOT NULL,
        plan_type TEXT NOT NULL,
        state TEXT NOT NULL,
        network TEXT NOT NULL,
        effective_start TEXT NOT NULL,
        effective_end TEXT NOT NULL,
        notes TEXT
    )
    """,
    """
    CREATE TABLE providers(
        provider_id TEXT PRIMARY KEY,
        provider_name TEXT NOT NULL,
        specialty TEXT NOT NULL,
        npi TEXT NOT NULL,
        phone TEXT,
        fax TEXT,
        organization TEXT
    )
    """,
    """
    CREATE TABLE cases(
        case_id TEXT PRIMARY KEY,
        member_id TEXT NOT NULL,
        provider_id TEXT NOT NULL,
        request_type TEXT NOT NULL,
        service_domain TEXT NOT NULL,
        policy_id TEXT NOT NULL,
        request_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        current_stage TEXT NOT NULL,
        current_status TEXT NOT NULL,
        urgency TEXT NOT NULL,
        summary TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE request_lines(
        line_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        cpt_code TEXT NOT NULL,
        modifier TEXT,
        service_name TEXT NOT NULL,
        requested_units INTEGER NOT NULL,
        requested_start TEXT,
        requested_end TEXT,
        diagnosis_codes TEXT,
        billed_charge REAL NOT NULL
    )
    """,
    """
    CREATE TABLE documents(
        document_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        document_type TEXT NOT NULL,
        document_date TEXT NOT NULL,
        received_date TEXT NOT NULL,
        source_system TEXT NOT NULL,
        is_current INTEGER NOT NULL,
        title TEXT NOT NULL,
        summary TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE document_facts(
        fact_id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        case_id TEXT NOT NULL,
        fact_key TEXT NOT NULL,
        fact_value TEXT NOT NULL,
        numeric_value REAL,
        unit TEXT,
        supports_criteria TEXT
    )
    """,
    """
    CREATE TABLE policies(
        policy_id TEXT PRIMARY KEY,
        policy_name TEXT NOT NULL,
        version TEXT NOT NULL,
        effective_start TEXT NOT NULL,
        effective_end TEXT NOT NULL,
        precedence INTEGER NOT NULL,
        summary TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE policy_criteria(
        criterion_id TEXT PRIMARY KEY,
        policy_id TEXT NOT NULL,
        criterion_key TEXT NOT NULL,
        criterion_text TEXT NOT NULL,
        approval_required INTEGER NOT NULL,
        result_if_missing TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE case_criteria(
        case_id TEXT NOT NULL,
        criterion_id TEXT NOT NULL,
        result TEXT NOT NULL,
        evidence_fact_ids TEXT,
        gap_description TEXT,
        reviewer_scope TEXT,
        PRIMARY KEY(case_id, criterion_id)
    )
    """,
    """
    CREATE TABLE p2p_events(
        p2p_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        scheduled_at TEXT NOT NULL,
        duration_minutes INTEGER NOT NULL,
        provider_argument TEXT,
        new_information TEXT,
        outcome TEXT,
        final_status TEXT,
        reviewer TEXT,
        notes TEXT
    )
    """,
    """
    CREATE TABLE appeals(
        appeal_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        denial_date TEXT NOT NULL,
        received_date TEXT NOT NULL,
        appeal_type_requested TEXT NOT NULL,
        appeal_path TEXT NOT NULL,
        expedited_attestation TEXT NOT NULL,
        appeal_deadline TEXT NOT NULL,
        outcome TEXT,
        owner TEXT,
        notes TEXT
    )
    """,
    """
    CREATE TABLE drug_trials(
        trial_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        medication TEXT NOT NULL,
        outcome TEXT NOT NULL,
        documented INTEGER NOT NULL,
        start_date TEXT,
        end_date TEXT,
        notes TEXT
    )
    """,
    """
    CREATE TABLE assistance_screen(
        case_id TEXT PRIMARY KEY,
        program_name TEXT NOT NULL,
        income_percent_fpl REAL,
        insurance_type TEXT NOT NULL,
        denial_required INTEGER NOT NULL,
        denial_on_file INTEGER NOT NULL,
        missing_fields TEXT,
        assistance_status TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE claims(
        claim_id TEXT PRIMARY KEY,
        member_id TEXT NOT NULL,
        case_id TEXT,
        payer TEXT NOT NULL,
        received_date TEXT NOT NULL,
        claim_status TEXT NOT NULL,
        auth_number TEXT,
        billed_total REAL NOT NULL,
        paid_total REAL NOT NULL
    )
    """,
    """
    CREATE TABLE claim_lines(
        claim_line_id TEXT PRIMARY KEY,
        claim_id TEXT NOT NULL,
        line_number INTEGER NOT NULL,
        cpt_code TEXT NOT NULL,
        modifier TEXT,
        units INTEGER NOT NULL,
        billed_amount REAL NOT NULL,
        paid_amount REAL NOT NULL,
        denial_code TEXT,
        service_date TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE authorizations(
        auth_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        auth_number TEXT,
        status TEXT NOT NULL,
        approved_units INTEGER,
        approved_start TEXT,
        approved_end TEXT,
        approved_cpt TEXT,
        approved_modifier TEXT,
        denial_reason TEXT
    )
    """,
    """
    CREATE TABLE payment_benchmarks(
        benchmark_id TEXT PRIMARY KEY,
        payer TEXT NOT NULL,
        plan_type TEXT NOT NULL,
        service_domain TEXT NOT NULL,
        cpt_code TEXT NOT NULL,
        modifier TEXT,
        effective_start TEXT NOT NULL,
        effective_end TEXT NOT NULL,
        allowed_amount REAL NOT NULL,
        source_name TEXT NOT NULL,
        source_version TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE service_margin(
        month_id TEXT PRIMARY KEY,
        period TEXT NOT NULL,
        payer TEXT NOT NULL,
        payer_segment TEXT NOT NULL,
        service_domain TEXT NOT NULL,
        cpt_code TEXT NOT NULL,
        visits INTEGER NOT NULL,
        net_revenue REAL NOT NULL,
        variable_cost REAL NOT NULL,
        fixed_cost_allocated REAL NOT NULL,
        charge_sensitive INTEGER NOT NULL
    )
    """,
]


def insert_many(cur: sqlite3.Cursor, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in keys)
    columns = ", ".join(keys)
    cur.executemany(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
        [[row.get(key) for key in keys] for row in rows],
    )


def base_rows() -> dict[str, list[dict]]:
    plans = [
        {
            "plan_id": "NHP-COM-NY",
            "payer_name": "Northstar Health Plan",
            "plan_type": "commercial",
            "state": "NY",
            "network": "PrimePlus",
            "effective_start": "2026-01-01",
            "effective_end": "2026-12-31",
            "notes": "Commercial plan with standard prior authorization and internal appeal rules.",
        },
        {
            "plan_id": "NHP-MCD-NY",
            "payer_name": "Northstar Health Plan",
            "plan_type": "medicaid",
            "state": "NY",
            "network": "CommunityCare",
            "effective_start": "2026-01-01",
            "effective_end": "2026-12-31",
            "notes": "Medicaid managed care plan with tighter therapy margin thresholds.",
        },
        {
            "plan_id": "NHP-MCR-NJ",
            "payer_name": "Northstar Health Plan",
            "plan_type": "medicare_advantage",
            "state": "NJ",
            "network": "SeniorChoice",
            "effective_start": "2026-01-01",
            "effective_end": "2026-12-31",
            "notes": "Medicare Advantage plan; expedited appeals require attestation.",
        },
        {
            "plan_id": "NHP-WC-PA",
            "payer_name": "Northstar Health Plan",
            "plan_type": "workers_comp",
            "state": "PA",
            "network": "OccupationalDirect",
            "effective_start": "2026-01-01",
            "effective_end": "2026-12-31",
            "notes": "Workers compensation product with charge-sensitive outlier review.",
        },
        {
            "plan_id": "NHP-COM-OLD",
            "payer_name": "Northstar Health Plan",
            "plan_type": "commercial",
            "state": "NY",
            "network": "PrimePlus",
            "effective_start": "2025-01-01",
            "effective_end": "2025-12-31",
            "notes": "Expired plan left in exports as a stale distractor.",
        },
    ]
    providers = [
        {
            "provider_id": "PRV-PT-001",
            "provider_name": "Summit Spine Physical Therapy",
            "specialty": "physical_therapy",
            "npi": "1487629011",
            "phone": "212-555-0114",
            "fax": "212-555-0199",
            "organization": "Summit Rehab Network",
        },
        {
            "provider_id": "PRV-CARD-001",
            "provider_name": "Hudson Cardiology Associates",
            "specialty": "cardiology",
            "npi": "1770542219",
            "phone": "212-555-0140",
            "fax": "212-555-0141",
            "organization": "Hudson Heart Group",
        },
        {
            "provider_id": "PRV-RAD-001",
            "provider_name": "Metro Nuclear Imaging",
            "specialty": "nuclear_medicine",
            "npi": "1215987042",
            "phone": "646-555-0123",
            "fax": "646-555-0160",
            "organization": "Metro Diagnostics",
        },
        {
            "provider_id": "PRV-PEDS-001",
            "provider_name": "Bright Steps Pediatric Therapy",
            "specialty": "speech_therapy",
            "npi": "1306208876",
            "phone": "718-555-0155",
            "fax": "718-555-0156",
            "organization": "Bright Steps Care",
        },
        {
            "provider_id": "PRV-DERM-001",
            "provider_name": "North Ridge Dermatology",
            "specialty": "dermatology",
            "npi": "1982014652",
            "phone": "973-555-0177",
            "fax": "973-555-0188",
            "organization": "North Ridge Medical",
        },
        {
            "provider_id": "PRV-ORTHO-001",
            "provider_name": "Keystone Orthopedic Center",
            "specialty": "orthopedics",
            "npi": "1548396629",
            "phone": "215-555-0135",
            "fax": "215-555-0136",
            "organization": "Keystone Surgical Partners",
        },
    ]
    policies = [
        {
            "policy_id": "POL-PT-LUMBAR-2026",
            "policy_name": "Lumbar Physical Therapy Medical Necessity",
            "version": "2026.2",
            "effective_start": "2026-01-01",
            "effective_end": "2026-12-31",
            "precedence": 10,
            "summary": "Approve therapy when a current plan of care documents lumbar diagnosis, functional deficit, skilled intervention, and requested units within policy limits.",
        },
        {
            "policy_id": "POL-ST-PEDS-2026",
            "policy_name": "Pediatric Speech Therapy Prior Authorization",
            "version": "2026.1",
            "effective_start": "2026-01-01",
            "effective_end": "2026-12-31",
            "precedence": 11,
            "summary": "A current plan of care must state frequency and duration without conflict with current clinical notes.",
        },
        {
            "policy_id": "POL-DRUG-EXC-2026",
            "policy_name": "Specialty Drug Coverage Exception Appeal",
            "version": "2026.3",
            "effective_start": "2026-01-01",
            "effective_end": "2026-12-31",
            "precedence": 20,
            "summary": "Internal drug appeals require denial notice, member authorization, prescriber rationale, formulary failure evidence, and relevant assistance packet materials.",
        },
        {
            "policy_id": "POL-PET-MPI-2026",
            "policy_name": "PET Myocardial Perfusion Imaging Medical Necessity",
            "version": "2026.4",
            "effective_start": "2026-01-01",
            "effective_end": "2026-12-31",
            "precedence": 30,
            "summary": "PET MPI needs a covered cardiac indication and at least one PET-over-SPECT factor such as prior equivocal SPECT, BMI limitation, or attenuation artifact.",
        },
        {
            "policy_id": "POL-CLAIM-RATE-2026",
            "policy_name": "Outpatient Imaging and Surgery Payment Benchmark",
            "version": "2026.2",
            "effective_start": "2026-01-01",
            "effective_end": "2026-12-31",
            "precedence": 40,
            "summary": "Payment corrections compare claim lines against current benchmark schedules by payer, plan type, CPT, and modifier.",
        },
    ]
    criteria = [
        (
            "PT-ACTIVE",
            "POL-PT-LUMBAR-2026",
            "active_coverage",
            "Member has active plan coverage on requested service dates.",
            1,
            "pend",
        ),
        (
            "PT-DX",
            "POL-PT-LUMBAR-2026",
            "lumbar_diagnosis",
            "Documentation supports lumbar spine diagnosis related to requested therapy.",
            1,
            "deny",
        ),
        (
            "PT-DEFICIT",
            "POL-PT-LUMBAR-2026",
            "functional_deficit",
            "Objective functional deficit or baseline limitation is documented.",
            1,
            "pend",
        ),
        (
            "PT-POC",
            "POL-PT-LUMBAR-2026",
            "current_plan_of_care",
            "Current plan of care includes frequency, duration, and skilled goals.",
            1,
            "pend",
        ),
        (
            "PT-UNITS",
            "POL-PT-LUMBAR-2026",
            "unit_limit",
            "Requested units do not exceed 24 units for initial nurse review.",
            1,
            "deny",
        ),
        (
            "ST-POC",
            "POL-ST-PEDS-2026",
            "current_plan_of_care",
            "Current plan of care states speech therapy frequency and duration.",
            1,
            "pend",
        ),
        (
            "ST-CONFLICT",
            "POL-ST-PEDS-2026",
            "no_current_conflict",
            "Current clinical note and plan of care agree on frequency.",
            1,
            "pend",
        ),
        (
            "DRUG-DENIAL",
            "POL-DRUG-EXC-2026",
            "denial_notice",
            "Denial notice or adverse determination is included.",
            1,
            "pend",
        ),
        (
            "DRUG-AUTH",
            "POL-DRUG-EXC-2026",
            "member_authorization",
            "Member authorization or representative form is included.",
            1,
            "pend",
        ),
        (
            "DRUG-RATIONALE",
            "POL-DRUG-EXC-2026",
            "prescriber_rationale",
            "Prescriber rationale connects requested drug to diagnosis and history.",
            1,
            "pend",
        ),
        (
            "DRUG-FAILURES",
            "POL-DRUG-EXC-2026",
            "formulary_failures",
            "Required formulary failures or contraindications are documented.",
            1,
            "deny",
        ),
        (
            "PET-IND",
            "POL-PET-MPI-2026",
            "covered_cad_indication",
            "Covered coronary artery disease indication is present.",
            1,
            "deny",
        ),
        (
            "PET-FACTOR",
            "POL-PET-MPI-2026",
            "pet_over_spect_factor",
            "At least one PET-over-SPECT factor is documented.",
            1,
            "deny",
        ),
        (
            "PET-NEWINFO",
            "POL-PET-MPI-2026",
            "new_p2p_information",
            "P2P information materially changes the original review.",
            0,
            "uphold",
        ),
        (
            "CLAIM-SCHED",
            "POL-CLAIM-RATE-2026",
            "current_schedule",
            "Use current benchmark schedule rather than stale export.",
            1,
            "correct",
        ),
    ]
    policy_criteria = [
        {
            "criterion_id": criterion_id,
            "policy_id": policy_id,
            "criterion_key": key,
            "criterion_text": text,
            "approval_required": required,
            "result_if_missing": missing,
        }
        for criterion_id, policy_id, key, text, required, missing in criteria
    ]
    return {
        "plans": plans,
        "providers": providers,
        "policies": policies,
        "policy_criteria": policy_criteria,
    }


def add_doc(
    rows: dict[str, list[dict]],
    document_id: str,
    case_id: str,
    doc_type: str,
    doc_date: str,
    received: str,
    source: str,
    current: int,
    title: str,
    summary: str,
    facts: list[tuple[str, str, float | None, str | None, str | None]],
) -> None:
    rows["documents"].append(
        {
            "document_id": document_id,
            "case_id": case_id,
            "document_type": doc_type,
            "document_date": doc_date,
            "received_date": received,
            "source_system": source,
            "is_current": current,
            "title": title,
            "summary": summary,
        }
    )
    for idx, (key, value, numeric, unit, supports) in enumerate(facts, start=1):
        rows["document_facts"].append(
            {
                "fact_id": f"FACT-{document_id}-{idx:02d}",
                "document_id": document_id,
                "case_id": case_id,
                "fact_key": key,
                "fact_value": value,
                "numeric_value": numeric,
                "unit": unit,
                "supports_criteria": supports,
            }
        )


def target_rows() -> dict[str, list[dict]]:
    rows: dict[str, list[dict]] = {
        "members": [],
        "cases": [],
        "request_lines": [],
        "documents": [],
        "document_facts": [],
        "case_criteria": [],
        "p2p_events": [],
        "appeals": [],
        "drug_trials": [],
        "assistance_screen": [],
        "claims": [],
        "claim_lines": [],
        "authorizations": [],
        "payment_benchmarks": [],
        "service_margin": [],
    }
    members = [
        (
            "M-TR-001",
            "Amelia Ramos",
            "1981-04-18",
            "NHP-COM-NY",
            "commercial",
            "PrimePlus PPO",
            "BriarWorks",
            "active",
        ),
        (
            "M-TR-002",
            "Jonah Patel",
            "1979-09-03",
            "NHP-COM-NY",
            "commercial",
            "PrimePlus PPO",
            "Mercer Foods",
            "active",
        ),
        ("M-TR-003", "Victor Nguyen", "1966-11-27", "NHP-COM-NY", "commercial", "PrimePlus PPO", "Portline", "active"),
        (
            "M-TR-004",
            "Marta De Leon",
            "1958-02-14",
            "NHP-MCR-NJ",
            "medicare_advantage",
            "SeniorChoice HMO",
            None,
            "active",
        ),
        (
            "M-TR-005",
            "Northstar Finance Queue",
            "1970-01-01",
            "NHP-MCD-NY",
            "medicaid",
            "CommunityCare",
            None,
            "active",
        ),
        (
            "M-TE-001",
            "Leo Bouchard",
            "2018-08-09",
            "NHP-COM-NY",
            "commercial",
            "PrimePlus PPO",
            "North Pier",
            "active",
        ),
        (
            "M-TE-002",
            "Elena Torres",
            "1992-06-22",
            "NHP-MCR-NJ",
            "medicare_advantage",
            "SeniorChoice HMO",
            None,
            "active",
        ),
        (
            "M-TE-003",
            "Keisha Bryant",
            "1971-10-10",
            "NHP-WC-PA",
            "workers_comp",
            "OccupationalDirect",
            "Keystone Transit",
            "active",
        ),
        (
            "M-TE-004",
            "Robert Chan",
            "1963-03-19",
            "NHP-COM-NY",
            "commercial",
            "PrimePlus PPO",
            "Eastline Labs",
            "active",
        ),
        (
            "M-TE-005",
            "Northstar Mixed Queue",
            "1970-01-01",
            "NHP-COM-NY",
            "commercial",
            "PrimePlus PPO",
            None,
            "active",
        ),
    ]
    rows["members"].extend(
        {
            "member_id": mid,
            "patient_name": name,
            "dob": dob,
            "plan_id": plan_id,
            "plan_type": plan_type,
            "product": product,
            "employer_group": group,
            "member_status": status,
        }
        for mid, name, dob, plan_id, plan_type, product, group, status in members
    )

    def case(case_id, member_id, provider_id, request_type, domain, policy, req, due, stage, status, urgency, summary):
        rows["cases"].append(
            {
                "case_id": case_id,
                "member_id": member_id,
                "provider_id": provider_id,
                "request_type": request_type,
                "service_domain": domain,
                "policy_id": policy,
                "request_date": req,
                "due_date": due,
                "current_stage": stage,
                "current_status": status,
                "urgency": urgency,
                "summary": summary,
            }
        )

    case(
        "CASE-TR-001",
        "M-TR-001",
        "PRV-PT-001",
        "prior_authorization",
        "physical_therapy",
        "POL-PT-LUMBAR-2026",
        "2026-05-02",
        "2026-05-07",
        "nurse_review",
        "ready_for_determination",
        "routine",
        "Initial lumbar PT request queued for nurse determination.",
    )
    rows["request_lines"].extend(
        [
            {
                "line_id": "RL-TR-001-1",
                "case_id": "CASE-TR-001",
                "cpt_code": "97110",
                "modifier": "GP",
                "service_name": "Therapeutic exercise",
                "requested_units": 12,
                "requested_start": "2026-05-06",
                "requested_end": "2026-07-05",
                "diagnosis_codes": "M54.50,M62.81",
                "billed_charge": 1680.0,
            },
            {
                "line_id": "RL-TR-001-2",
                "case_id": "CASE-TR-001",
                "cpt_code": "97112",
                "modifier": "GP",
                "service_name": "Neuromuscular re-education",
                "requested_units": 8,
                "requested_start": "2026-05-06",
                "requested_end": "2026-07-05",
                "diagnosis_codes": "M54.50,M62.81",
                "billed_charge": 1240.0,
            },
            {
                "line_id": "RL-TR-001-3",
                "case_id": "CASE-TR-001",
                "cpt_code": "97530",
                "modifier": "GP",
                "service_name": "Therapeutic activities",
                "requested_units": 4,
                "requested_start": "2026-05-06",
                "requested_end": "2026-07-05",
                "diagnosis_codes": "M54.50,M62.81",
                "billed_charge": 700.0,
            },
        ]
    )
    add_doc(
        rows,
        "DOC-TR-001-POC",
        "CASE-TR-001",
        "plan_of_care",
        "2026-05-01",
        "2026-05-02",
        "CarePort",
        1,
        "Lumbar PT plan of care",
        "Frequency twice weekly for six weeks with measurable lumbar mobility and lifting goals.",
        [
            ("frequency_per_week", "2", 2, "visits", "PT-POC"),
            ("duration_weeks", "6", 6, "weeks", "PT-POC"),
            ("requested_units_total", "24", 24, "units", "PT-UNITS"),
        ],
    )
    add_doc(
        rows,
        "DOC-TR-001-EVAL",
        "CASE-TR-001",
        "clinical_eval",
        "2026-04-30",
        "2026-05-02",
        "ProviderFax",
        1,
        "Initial PT evaluation",
        "Documents low back pain, reduced flexion, Oswestry 42 percent, and skilled therapy goals.",
        [
            ("diagnosis", "lumbar pain with weakness", None, None, "PT-DX"),
            ("oswestry_score", "42", 42, "percent", "PT-DEFICIT"),
            ("coverage_verified", "active on 2026-05-06", None, None, "PT-ACTIVE"),
        ],
    )
    add_doc(
        rows,
        "DOC-TR-001-STALE",
        "CASE-TR-001",
        "stale_export",
        "2026-03-12",
        "2026-05-02",
        "LegacyUM",
        0,
        "Prior therapy export",
        "Older export shows a closed knee therapy episode; not current for lumbar request.",
        [("stale_episode", "closed knee PT episode from March", None, None, None)],
    )
    for cid in ["PT-ACTIVE", "PT-DX", "PT-DEFICIT", "PT-POC", "PT-UNITS"]:
        rows["case_criteria"].append(
            {
                "case_id": "CASE-TR-001",
                "criterion_id": cid,
                "result": "met",
                "evidence_fact_ids": "current clinical and POC facts",
                "gap_description": "",
                "reviewer_scope": "nurse",
            }
        )
    rows["authorizations"].append(
        {
            "auth_id": "AUTH-TR-001",
            "case_id": "CASE-TR-001",
            "auth_number": "NPA-2405014",
            "status": "recommended_approval",
            "approved_units": 24,
            "approved_start": "2026-05-06",
            "approved_end": "2026-07-05",
            "approved_cpt": "97110,97112,97530",
            "approved_modifier": "GP",
            "denial_reason": "",
        }
    )

    case(
        "APPEAL-TR-002",
        "M-TR-002",
        "PRV-DERM-001",
        "coverage_exception",
        "specialty_drug",
        "POL-DRUG-EXC-2026",
        "2026-05-08",
        "2026-06-07",
        "appeals",
        "packet_incomplete",
        "standard",
        "Vraylar coverage exception appeal packet queued for pharmacy appeals review.",
    )
    rows["appeals"].append(
        {
            "appeal_id": "APL-TR-002",
            "case_id": "APPEAL-TR-002",
            "denial_date": "2026-05-01",
            "received_date": "2026-05-08",
            "appeal_type_requested": "coverage_exception",
            "appeal_path": "standard_internal",
            "expedited_attestation": "not_requested",
            "appeal_deadline": "2026-06-07",
            "outcome": "open",
            "owner": "appeals-rx",
            "notes": "Required packet: denial notice, member authorization, prescriber rationale, formulary failure evidence, household income proof.",
        }
    )
    add_doc(
        rows,
        "DOC-TR-002-DENIAL",
        "APPEAL-TR-002",
        "denial_notice",
        "2026-05-01",
        "2026-05-08",
        "RxPortal",
        1,
        "Vraylar denial",
        "Initial denial for non-formulary Vraylar.",
        [("packet_item", "denial notice present", None, None, "DRUG-DENIAL")],
    )
    add_doc(
        rows,
        "DOC-TR-002-LETTER",
        "APPEAL-TR-002",
        "prescriber_letter",
        "2026-05-07",
        "2026-05-08",
        "ProviderFax",
        1,
        "Prescriber appeal letter",
        "Prescriber documents bipolar depression history and intolerance to quetiapine.",
        [
            ("packet_item", "prescriber rationale present", None, None, "DRUG-RATIONALE"),
            ("formulary_failure", "quetiapine intolerance", None, None, "DRUG-FAILURES"),
        ],
    )
    add_doc(
        rows,
        "DOC-TR-002-AUTH",
        "APPEAL-TR-002",
        "member_authorization",
        "2026-05-06",
        "2026-05-08",
        "MemberUpload",
        1,
        "Member authorization",
        "Signed appeal authorization received.",
        [("packet_item", "member authorization present", None, None, "DRUG-AUTH")],
    )
    rows["drug_trials"].extend(
        [
            {
                "trial_id": "TRIAL-TR-002-1",
                "case_id": "APPEAL-TR-002",
                "medication": "quetiapine",
                "outcome": "intolerable sedation",
                "documented": 1,
                "start_date": "2026-01-02",
                "end_date": "2026-02-10",
                "notes": "Prescriber letter.",
            },
            {
                "trial_id": "TRIAL-TR-002-2",
                "case_id": "APPEAL-TR-002",
                "medication": "lurasidone",
                "outcome": "partial response",
                "documented": 0,
                "start_date": "2026-02-20",
                "end_date": "2026-04-05",
                "notes": "Mentioned but pharmacy fill missing.",
            },
        ]
    )
    rows["assistance_screen"].append(
        {
            "case_id": "APPEAL-TR-002",
            "program_name": "Vraylar Connect",
            "income_percent_fpl": None,
            "insurance_type": "commercial",
            "denial_required": 1,
            "denial_on_file": 1,
            "missing_fields": "household_income_proof",
            "assistance_status": "pending_missing_income_proof",
        }
    )
    for cid, result, gap in [
        ("DRUG-DENIAL", "met", ""),
        ("DRUG-AUTH", "met", ""),
        ("DRUG-RATIONALE", "met", ""),
        ("DRUG-FAILURES", "partial", "One failure documented; second referenced without fill record."),
    ]:
        rows["case_criteria"].append(
            {
                "case_id": "APPEAL-TR-002",
                "criterion_id": cid,
                "result": result,
                "evidence_fact_ids": "appeal packet documents",
                "gap_description": gap,
                "reviewer_scope": "appeals",
            }
        )

    case(
        "CLAIM-TR-003",
        "M-TR-003",
        "PRV-CARD-001",
        "claim_payment_review",
        "cardiac_imaging",
        "POL-CLAIM-RATE-2026",
        "2026-05-12",
        "2026-05-17",
        "payment_integrity",
        "needs_repricing",
        "routine",
        "Cardiac SPECT claim queued for payment integrity schedule review.",
    )
    rows["claims"].append(
        {
            "claim_id": "CLAIM-TR-003",
            "member_id": "M-TR-003",
            "case_id": "CLAIM-TR-003",
            "payer": "Northstar Health Plan",
            "received_date": "2026-05-12",
            "claim_status": "paid_stale_schedule",
            "auth_number": "NPA-2404980",
            "billed_total": 2850.0,
            "paid_total": 940.0,
        }
    )
    rows["claim_lines"].extend(
        [
            {
                "claim_line_id": "CL-TR-003-1",
                "claim_id": "CLAIM-TR-003",
                "line_number": 1,
                "cpt_code": "78452",
                "modifier": "TC",
                "units": 1,
                "billed_amount": 1900.0,
                "paid_amount": 608.0,
                "denial_code": None,
                "service_date": "2026-05-03",
            },
            {
                "claim_line_id": "CL-TR-003-2",
                "claim_id": "CLAIM-TR-003",
                "line_number": 2,
                "cpt_code": "A9500",
                "modifier": None,
                "units": 2,
                "billed_amount": 720.0,
                "paid_amount": 288.0,
                "denial_code": None,
                "service_date": "2026-05-03",
            },
            {
                "claim_line_id": "CL-TR-003-3",
                "claim_id": "CLAIM-TR-003",
                "line_number": 3,
                "cpt_code": "93016",
                "modifier": None,
                "units": 1,
                "billed_amount": 230.0,
                "paid_amount": 44.0,
                "denial_code": None,
                "service_date": "2026-05-03",
            },
        ]
    )
    rows["payment_benchmarks"].extend(
        [
            {
                "benchmark_id": "BM-TR-003-78452",
                "payer": "Northstar Health Plan",
                "plan_type": "commercial",
                "service_domain": "cardiac_imaging",
                "cpt_code": "78452",
                "modifier": "TC",
                "effective_start": "2026-04-01",
                "effective_end": "2026-12-31",
                "allowed_amount": 760.0,
                "source_name": "Northstar Commercial Imaging Schedule",
                "source_version": "2026Q2",
            },
            {
                "benchmark_id": "BM-TR-003-A9500",
                "payer": "Northstar Health Plan",
                "plan_type": "commercial",
                "service_domain": "cardiac_imaging",
                "cpt_code": "A9500",
                "modifier": None,
                "effective_start": "2026-04-01",
                "effective_end": "2026-12-31",
                "allowed_amount": 180.0,
                "source_name": "Northstar Commercial Imaging Schedule",
                "source_version": "2026Q2",
            },
            {
                "benchmark_id": "BM-TR-003-93016",
                "payer": "Northstar Health Plan",
                "plan_type": "commercial",
                "service_domain": "cardiac_imaging",
                "cpt_code": "93016",
                "modifier": None,
                "effective_start": "2026-04-01",
                "effective_end": "2026-12-31",
                "allowed_amount": 55.0,
                "source_name": "Northstar Commercial Imaging Schedule",
                "source_version": "2026Q2",
            },
            {
                "benchmark_id": "BM-OLD-78452",
                "payer": "Northstar Health Plan",
                "plan_type": "commercial",
                "service_domain": "cardiac_imaging",
                "cpt_code": "78452",
                "modifier": "TC",
                "effective_start": "2025-01-01",
                "effective_end": "2026-03-31",
                "allowed_amount": 608.0,
                "source_name": "Legacy Imaging Export",
                "source_version": "2025Q4",
            },
        ]
    )
    add_doc(
        rows,
        "DOC-TR-003-EOB",
        "CLAIM-TR-003",
        "remittance",
        "2026-05-13",
        "2026-05-13",
        "ClaimsCore",
        1,
        "SPECT remittance",
        "Remittance lists paid line amounts from an older imaging schedule; compare with the effective benchmark schedule.",
        [
            ("paid_total", "940.00", 940, "USD", "CLAIM-SCHED"),
            ("schedule_used", "legacy imaging export", None, None, "CLAIM-SCHED"),
        ],
    )
    rows["case_criteria"].append(
        {
            "case_id": "CLAIM-TR-003",
            "criterion_id": "CLAIM-SCHED",
            "result": "stale_schedule_used",
            "evidence_fact_ids": "DOC-TR-003-EOB",
            "gap_description": "Reprice to current 2026Q2 commercial imaging benchmark.",
            "reviewer_scope": "payment_integrity",
        }
    )

    case(
        "P2P-TR-004",
        "M-TR-004",
        "PRV-RAD-001",
        "peer_to_peer",
        "cardiac_imaging",
        "POL-PET-MPI-2026",
        "2026-05-09",
        "2026-05-14",
        "medical_director",
        "p2p_complete",
        "routine",
        "PET MPI peer-to-peer record queued for final authorization-file closure.",
    )
    rows["request_lines"].append(
        {
            "line_id": "RL-TR-004-1",
            "case_id": "P2P-TR-004",
            "cpt_code": "78431",
            "modifier": None,
            "service_name": "PET myocardial perfusion imaging",
            "requested_units": 1,
            "requested_start": "2026-05-20",
            "requested_end": "2026-05-20",
            "diagnosis_codes": "I25.10,R07.9",
            "billed_charge": 4200.0,
        }
    )
    add_doc(
        rows,
        "DOC-TR-004-CARD",
        "P2P-TR-004",
        "cardiology_note",
        "2026-05-03",
        "2026-05-09",
        "ProviderFax",
        1,
        "CAD cardiology note",
        "Known CAD and chest pain; no prior equivocal SPECT, BMI limitation, or attenuation artifact.",
        [
            ("covered_cad_indication", "known CAD with chest pain", None, None, "PET-IND"),
            ("pet_over_spect_factor", "not documented", None, None, "PET-FACTOR"),
        ],
    )
    rows["case_criteria"].extend(
        [
            {
                "case_id": "P2P-TR-004",
                "criterion_id": "PET-IND",
                "result": "met",
                "evidence_fact_ids": "FACT-DOC-TR-004-CARD-01",
                "gap_description": "",
                "reviewer_scope": "medical_director",
            },
            {
                "case_id": "P2P-TR-004",
                "criterion_id": "PET-FACTOR",
                "result": "not_met",
                "evidence_fact_ids": "FACT-DOC-TR-004-CARD-02",
                "gap_description": "No PET-over-SPECT factor documented.",
                "reviewer_scope": "medical_director",
            },
        ]
    )
    rows["p2p_events"].append(
        {
            "p2p_id": "P2P-TR-004-E1",
            "case_id": "P2P-TR-004",
            "scheduled_at": "2026-05-13T15:00:00Z",
            "duration_minutes": 18,
            "provider_argument": "PET has better image quality for CAD.",
            "new_information": "No prior equivocal SPECT, BMI limitation, or attenuation artifact supplied.",
            "outcome": "uphold_intended_adverse_decision",
            "final_status": "denied",
            "reviewer": "Dr. Imani Wells",
            "notes": "Covered indication met; PET-specific factor absent.",
        }
    )
    rows["authorizations"].append(
        {
            "auth_id": "AUTH-TR-004",
            "case_id": "P2P-TR-004",
            "auth_number": None,
            "status": "denied",
            "approved_units": 0,
            "approved_start": None,
            "approved_end": None,
            "approved_cpt": "78431",
            "approved_modifier": None,
            "denial_reason": "PET-over-SPECT factor not met",
        }
    )

    case(
        "QUEUE-TR-005",
        "M-TR-005",
        "PRV-PT-001",
        "queue_analysis",
        "therapy_margin",
        "POL-CLAIM-RATE-2026",
        "2026-05-31",
        "2026-06-05",
        "finance_queue",
        "monthly_review",
        "routine",
        "May therapy margin rows queued for payer-service review.",
    )
    rows["service_margin"].extend(
        [
            {
                "month_id": "SM-TR-005-MCD",
                "period": "2026-05",
                "payer": "Northstar Health Plan",
                "payer_segment": "medicaid",
                "service_domain": "physical_therapy",
                "cpt_code": "97110",
                "visits": 412,
                "net_revenue": 23690.0,
                "variable_cost": 21140.0,
                "fixed_cost_allocated": 5100.0,
                "charge_sensitive": 0,
            },
            {
                "month_id": "SM-TR-005-COM",
                "period": "2026-05",
                "payer": "Northstar Health Plan",
                "payer_segment": "commercial",
                "service_domain": "physical_therapy",
                "cpt_code": "97530",
                "visits": 288,
                "net_revenue": 45270.0,
                "variable_cost": 24100.0,
                "fixed_cost_allocated": 7600.0,
                "charge_sensitive": 1,
            },
            {
                "month_id": "SM-TR-005-WC",
                "period": "2026-05",
                "payer": "Northstar Health Plan",
                "payer_segment": "workers_comp",
                "service_domain": "physical_therapy",
                "cpt_code": "97112",
                "visits": 96,
                "net_revenue": 25760.0,
                "variable_cost": 10420.0,
                "fixed_cost_allocated": 3100.0,
                "charge_sensitive": 1,
            },
        ]
    )

    case(
        "CASE-TE-001",
        "M-TE-001",
        "PRV-PEDS-001",
        "prior_authorization",
        "speech_therapy",
        "POL-ST-PEDS-2026",
        "2026-06-04",
        "2026-06-09",
        "nurse_review",
        "needs_information",
        "routine",
        "Pediatric speech therapy request queued for nurse documentation review.",
    )
    rows["request_lines"].append(
        {
            "line_id": "RL-TE-001-1",
            "case_id": "CASE-TE-001",
            "cpt_code": "92507",
            "modifier": "GN",
            "service_name": "Speech therapy treatment",
            "requested_units": 16,
            "requested_start": "2026-06-10",
            "requested_end": "2026-08-09",
            "diagnosis_codes": "F80.2",
            "billed_charge": 2400.0,
        }
    )
    add_doc(
        rows,
        "DOC-TE-001-POC",
        "CASE-TE-001",
        "plan_of_care",
        "2026-06-01",
        "2026-06-04",
        "CarePort",
        1,
        "Speech plan of care",
        "Plan says 1-2 visits weekly; duration is not explicit.",
        [
            ("frequency_per_week", "1-2 ambiguous", None, "visits", "ST-POC"),
            ("duration_weeks", "not stated", None, "weeks", "ST-POC"),
        ],
    )
    add_doc(
        rows,
        "DOC-TE-001-NOTE",
        "CASE-TE-001",
        "clinical_note",
        "2026-06-03",
        "2026-06-04",
        "ProviderFax",
        1,
        "Current speech note",
        "Current note requests three visits weekly, conflicting with plan of care.",
        [("frequency_per_week", "3", 3, "visits", "ST-CONFLICT")],
    )
    add_doc(
        rows,
        "DOC-TE-001-STALE",
        "CASE-TE-001",
        "stale_export",
        "2026-04-20",
        "2026-06-04",
        "LegacyUM",
        0,
        "Old speech export",
        "Old export shows once weekly therapy approved in April.",
        [("stale_frequency", "1 weekly", 1, "visits", None)],
    )
    rows["case_criteria"].extend(
        [
            {
                "case_id": "CASE-TE-001",
                "criterion_id": "ST-POC",
                "result": "not_met",
                "evidence_fact_ids": "DOC-TE-001-POC",
                "gap_description": "Plan-of-care frequency and duration are ambiguous.",
                "reviewer_scope": "nurse",
            },
            {
                "case_id": "CASE-TE-001",
                "criterion_id": "ST-CONFLICT",
                "result": "not_met",
                "evidence_fact_ids": "DOC-TE-001-NOTE",
                "gap_description": "Current note conflicts with plan-of-care frequency.",
                "reviewer_scope": "nurse",
            },
        ]
    )
    rows["authorizations"].append(
        {
            "auth_id": "AUTH-TE-001",
            "case_id": "CASE-TE-001",
            "auth_number": None,
            "status": "pended",
            "approved_units": 0,
            "approved_start": None,
            "approved_end": None,
            "approved_cpt": "92507",
            "approved_modifier": "GN",
            "denial_reason": "Need clarified frequency and duration",
        }
    )

    case(
        "APPEAL-TE-002",
        "M-TE-002",
        "PRV-DERM-001",
        "coverage_exception",
        "specialty_drug",
        "POL-DRUG-EXC-2026",
        "2026-06-06",
        "2026-06-09",
        "appeals",
        "packet_incomplete",
        "expedited",
        "Dupixent coverage exception appeal packet queued for pharmacy appeals review.",
    )
    rows["appeals"].append(
        {
            "appeal_id": "APL-TE-002",
            "case_id": "APPEAL-TE-002",
            "denial_date": "2026-06-02",
            "received_date": "2026-06-06",
            "appeal_type_requested": "coverage_exception",
            "appeal_path": "expedited_internal",
            "expedited_attestation": "provider_attested_serious_health_risk",
            "appeal_deadline": "2026-06-09",
            "outcome": "open",
            "owner": "appeals-rx",
            "notes": "Dupixent appeal packet otherwise complete; household income proof absent for manufacturer assistance.",
        }
    )
    rows["drug_trials"].extend(
        [
            {
                "trial_id": "TRIAL-TE-002-1",
                "case_id": "APPEAL-TE-002",
                "medication": "topical tacrolimus",
                "outcome": "failed",
                "documented": 1,
                "start_date": "2026-02-01",
                "end_date": "2026-03-01",
                "notes": "Dermatology note.",
            },
            {
                "trial_id": "TRIAL-TE-002-2",
                "case_id": "APPEAL-TE-002",
                "medication": "phototherapy",
                "outcome": "failed",
                "documented": 1,
                "start_date": "2026-03-15",
                "end_date": "2026-05-15",
                "notes": "Treatment log.",
            },
        ]
    )
    rows["assistance_screen"].append(
        {
            "case_id": "APPEAL-TE-002",
            "program_name": "Dupixent MyWay",
            "income_percent_fpl": None,
            "insurance_type": "medicare_advantage",
            "denial_required": 1,
            "denial_on_file": 1,
            "missing_fields": "household_income_proof",
            "assistance_status": "pending_missing_income_proof",
        }
    )

    case(
        "CLAIM-TE-003",
        "M-TE-003",
        "PRV-ORTHO-001",
        "claim_payment_review",
        "outpatient_surgery",
        "POL-CLAIM-RATE-2026",
        "2026-06-08",
        "2026-06-13",
        "payment_integrity",
        "needs_repricing",
        "routine",
        "Knee arthroscopy claim queued for payment integrity schedule and modifier review.",
    )
    rows["claims"].append(
        {
            "claim_id": "CLAIM-TE-003",
            "member_id": "M-TE-003",
            "case_id": "CLAIM-TE-003",
            "payer": "Northstar Health Plan",
            "received_date": "2026-06-08",
            "claim_status": "paid_review",
            "auth_number": "NPA-2406121",
            "billed_total": 3950.0,
            "paid_total": 2010.0,
        }
    )
    rows["claim_lines"].extend(
        [
            {
                "claim_line_id": "CL-TE-003-1",
                "claim_id": "CLAIM-TE-003",
                "line_number": 1,
                "cpt_code": "29881",
                "modifier": "RT",
                "units": 1,
                "billed_amount": 3200.0,
                "paid_amount": 1660.0,
                "denial_code": None,
                "service_date": "2026-06-02",
            },
            {
                "claim_line_id": "CL-TE-003-2",
                "claim_id": "CLAIM-TE-003",
                "line_number": 2,
                "cpt_code": "29881",
                "modifier": "59",
                "units": 1,
                "billed_amount": 750.0,
                "paid_amount": 350.0,
                "denial_code": None,
                "service_date": "2026-06-02",
            },
        ]
    )
    rows["payment_benchmarks"].extend(
        [
            {
                "benchmark_id": "BM-TE-003-29881RT",
                "payer": "Northstar Health Plan",
                "plan_type": "workers_comp",
                "service_domain": "outpatient_surgery",
                "cpt_code": "29881",
                "modifier": "RT",
                "effective_start": "2026-01-01",
                "effective_end": "2026-12-31",
                "allowed_amount": 2420.0,
                "source_name": "Northstar WC Surgery Schedule",
                "source_version": "2026",
            },
            {
                "benchmark_id": "BM-TE-003-2988159",
                "payer": "Northstar Health Plan",
                "plan_type": "workers_comp",
                "service_domain": "outpatient_surgery",
                "cpt_code": "29881",
                "modifier": "59",
                "effective_start": "2026-01-01",
                "effective_end": "2026-12-31",
                "allowed_amount": 0.0,
                "source_name": "Northstar WC Surgery Schedule",
                "source_version": "2026",
            },
        ]
    )
    add_doc(
        rows,
        "DOC-TE-003-EOB",
        "CLAIM-TE-003",
        "remittance",
        "2026-06-09",
        "2026-06-09",
        "ClaimsCore",
        1,
        "Knee arthroscopy remittance",
        "Remittance lists two arthroscopy lines for comparison against the current workers-comp surgery schedule and modifier policy.",
        [
            ("paid_total", "2010.00", 2010, "USD", "CLAIM-SCHED"),
            ("schedule_used", "workers comp surgery schedule review needed", None, None, "CLAIM-SCHED"),
        ],
    )

    case(
        "P2P-TE-004",
        "M-TE-004",
        "PRV-RAD-001",
        "peer_to_peer",
        "cardiac_imaging",
        "POL-PET-MPI-2026",
        "2026-06-07",
        "2026-06-12",
        "medical_director",
        "p2p_complete",
        "routine",
        "PET MPI peer-to-peer record queued for final authorization-file closure.",
    )
    rows["request_lines"].append(
        {
            "line_id": "RL-TE-004-1",
            "case_id": "P2P-TE-004",
            "cpt_code": "78431",
            "modifier": None,
            "service_name": "PET myocardial perfusion imaging",
            "requested_units": 1,
            "requested_start": "2026-06-18",
            "requested_end": "2026-06-18",
            "diagnosis_codes": "I25.118,R94.39,Z68.41",
            "billed_charge": 4200.0,
        }
    )
    add_doc(
        rows,
        "DOC-TE-004-P2P",
        "P2P-TE-004",
        "p2p_addendum",
        "2026-06-10",
        "2026-06-10",
        "P2PDesk",
        1,
        "PET MPI P2P addendum",
        "New documentation: prior SPECT was equivocal due attenuation and BMI 42 limits SPECT quality.",
        [
            ("covered_cad_indication", "known CAD with angina", None, None, "PET-IND"),
            ("prior_equivocal_spect", "yes", 1, None, "PET-FACTOR"),
            ("bmi", "42", 42, "kg/m2", "PET-FACTOR"),
        ],
    )
    rows["p2p_events"].append(
        {
            "p2p_id": "P2P-TE-004-E1",
            "case_id": "P2P-TE-004",
            "scheduled_at": "2026-06-10T16:30:00Z",
            "duration_minutes": 22,
            "provider_argument": "Prior SPECT was equivocal and BMI limits SPECT accuracy.",
            "new_information": "Equivocal SPECT report and BMI 42 supplied during P2P.",
            "outcome": "overturn_to_approval",
            "final_status": "approved",
            "reviewer": "Dr. Imani Wells",
            "notes": "Covered indication and PET-over-SPECT factors met.",
        }
    )
    rows["authorizations"].append(
        {
            "auth_id": "AUTH-TE-004",
            "case_id": "P2P-TE-004",
            "auth_number": "NPA-2406199",
            "status": "approved",
            "approved_units": 1,
            "approved_start": "2026-06-18",
            "approved_end": "2026-06-18",
            "approved_cpt": "78431",
            "approved_modifier": None,
            "denial_reason": "",
        }
    )

    case(
        "QUEUE-TE-005",
        "M-TE-005",
        "PRV-CARD-001",
        "queue_analysis",
        "mixed_um_finance",
        "POL-CLAIM-RATE-2026",
        "2026-06-11",
        "2026-06-12",
        "operations_queue",
        "needs_triage",
        "mixed",
        "Mixed UM-finance queue containing appeal, clinical-review, and payment-integrity work items.",
    )
    rows["appeals"].append(
        {
            "appeal_id": "APL-TE-005-DEADLINE",
            "case_id": "QUEUE-TE-005",
            "denial_date": "2026-05-13",
            "received_date": "2026-05-16",
            "appeal_type_requested": "standard",
            "appeal_path": "standard_internal",
            "expedited_attestation": "not_requested",
            "appeal_deadline": "2026-06-12",
            "outcome": "open",
            "owner": "appeals-um",
            "notes": "Deadline item for mixed queue triage.",
        }
    )
    rows["request_lines"].extend(
        [
            {
                "line_id": "RL-TE-005-MD",
                "case_id": "QUEUE-TE-005",
                "cpt_code": "78431",
                "modifier": None,
                "service_name": "PET myocardial perfusion imaging escalation",
                "requested_units": 1,
                "requested_start": "2026-06-20",
                "requested_end": "2026-06-20",
                "diagnosis_codes": "I25.118,R07.9",
                "billed_charge": 4200.0,
            },
            {
                "line_id": "RL-TE-005-CLAIM",
                "case_id": "QUEUE-TE-005",
                "cpt_code": "78452",
                "modifier": "TC",
                "service_name": "Claim correction review line",
                "requested_units": 1,
                "requested_start": "2026-06-03",
                "requested_end": "2026-06-03",
                "diagnosis_codes": "I25.10",
                "billed_charge": 1900.0,
            },
        ]
    )
    add_doc(
        rows,
        "DOC-TE-005-APPEAL",
        "QUEUE-TE-005",
        "queue_note",
        "2026-06-11",
        "2026-06-11",
        "OpsQueue",
        1,
        "Appeal deadline queue item",
        "Standard internal appeal has an open deadline on 2026-06-12.",
        [("work_item_type", "appeal", None, None, None), ("appeal_deadline", "2026-06-12", None, "date", None)],
    )
    add_doc(
        rows,
        "DOC-TE-005-MD",
        "QUEUE-TE-005",
        "clinical_escalation",
        "2026-06-11",
        "2026-06-11",
        "UMWorkbench",
        1,
        "Clinical review queue item",
        "PET MPI request has covered CAD symptoms; PET-over-SPECT factor evidence is not documented in the current clinical item.",
        [
            ("work_item_type", "clinical_review", None, None, None),
            ("covered_cad_indication", "known CAD with angina symptoms", None, None, "PET-IND"),
            ("pet_over_spect_factor", "not documented", None, None, "PET-FACTOR"),
        ],
    )
    add_doc(
        rows,
        "DOC-TE-005-CLAIM",
        "QUEUE-TE-005",
        "claim_correction",
        "2026-06-11",
        "2026-06-11",
        "ClaimsCore",
        1,
        "Claim payment queue item",
        "Commercial imaging claim line paid from a legacy schedule and requires comparison with the current benchmark schedule.",
        [
            ("work_item_type", "claim_payment_review", None, None, None),
            ("paid_total", "608.00", 608, "USD", "CLAIM-SCHED"),
            ("schedule_used", "legacy imaging export", None, None, "CLAIM-SCHED"),
        ],
    )
    rows["case_criteria"].extend(
        [
            {
                "case_id": "QUEUE-TE-005",
                "criterion_id": "PET-IND",
                "result": "met",
                "evidence_fact_ids": "FACT-DOC-TE-005-MD-02",
                "gap_description": "",
                "reviewer_scope": "medical_director",
            },
            {
                "case_id": "QUEUE-TE-005",
                "criterion_id": "PET-FACTOR",
                "result": "not_met",
                "evidence_fact_ids": "FACT-DOC-TE-005-MD-03",
                "gap_description": "PET-over-SPECT factor is absent from the current clinical item.",
                "reviewer_scope": "medical_director",
            },
            {
                "case_id": "QUEUE-TE-005",
                "criterion_id": "CLAIM-SCHED",
                "result": "stale_schedule_used",
                "evidence_fact_ids": "DOC-TE-005-CLAIM",
                "gap_description": "Current benchmark schedule comparison is required for this queue item.",
                "reviewer_scope": "payment_integrity",
            },
        ]
    )
    rows["claims"].append(
        {
            "claim_id": "CLAIM-TE-005-CORR",
            "member_id": "M-TE-005",
            "case_id": "QUEUE-TE-005",
            "payer": "Northstar Health Plan",
            "received_date": "2026-06-11",
            "claim_status": "needs_correction",
            "auth_number": "NPA-2406344",
            "billed_total": 1900.0,
            "paid_total": 608.0,
        }
    )
    rows["claim_lines"].append(
        {
            "claim_line_id": "CL-TE-005-CORR-1",
            "claim_id": "CLAIM-TE-005-CORR",
            "line_number": 1,
            "cpt_code": "78452",
            "modifier": "TC",
            "units": 1,
            "billed_amount": 1900.0,
            "paid_amount": 608.0,
            "denial_code": None,
            "service_date": "2026-06-03",
        }
    )
    rows["payment_benchmarks"].append(
        {
            "benchmark_id": "BM-TE-005-78452TC",
            "payer": "Northstar Health Plan",
            "plan_type": "commercial",
            "service_domain": "cardiac_imaging",
            "cpt_code": "78452",
            "modifier": "TC",
            "effective_start": "2026-04-01",
            "effective_end": "2026-12-31",
            "allowed_amount": 760.0,
            "source_name": "Northstar Commercial Imaging Schedule",
            "source_version": "2026Q2",
        }
    )
    return rows


def distractor_rows(rng: random.Random) -> dict[str, list[dict]]:
    first = [
        "Avery",
        "Blake",
        "Casey",
        "Dana",
        "Elliot",
        "Finley",
        "Harper",
        "Jordan",
        "Kai",
        "Logan",
        "Morgan",
        "Noel",
        "Parker",
        "Quinn",
        "Riley",
        "Sawyer",
        "Taylor",
    ]
    last = [
        "Bennett",
        "Carter",
        "Diaz",
        "Evans",
        "Foster",
        "Garcia",
        "Hayes",
        "Irwin",
        "Jensen",
        "Kim",
        "Lewis",
        "Miller",
        "Owens",
        "Price",
        "Reed",
        "Singh",
        "Young",
    ]
    plan_ids = ["NHP-COM-NY", "NHP-MCD-NY", "NHP-MCR-NJ", "NHP-WC-PA", "NHP-COM-OLD"]
    provider_ids = ["PRV-PT-001", "PRV-CARD-001", "PRV-RAD-001", "PRV-PEDS-001", "PRV-DERM-001", "PRV-ORTHO-001"]
    policies = [
        "POL-PT-LUMBAR-2026",
        "POL-ST-PEDS-2026",
        "POL-DRUG-EXC-2026",
        "POL-PET-MPI-2026",
        "POL-CLAIM-RATE-2026",
    ]
    domains = {
        "POL-PT-LUMBAR-2026": "physical_therapy",
        "POL-ST-PEDS-2026": "speech_therapy",
        "POL-DRUG-EXC-2026": "specialty_drug",
        "POL-PET-MPI-2026": "cardiac_imaging",
        "POL-CLAIM-RATE-2026": "payment_review",
    }
    rows: dict[str, list[dict]] = {
        "members": [],
        "cases": [],
        "request_lines": [],
        "documents": [],
        "document_facts": [],
        "case_criteria": [],
        "p2p_events": [],
        "appeals": [],
        "drug_trials": [],
        "assistance_screen": [],
        "claims": [],
        "claim_lines": [],
        "authorizations": [],
        "payment_benchmarks": [],
        "service_margin": [],
    }
    for idx in range(1, 151):
        member_id = f"M-D-{idx:04d}"
        plan_id = rng.choice(plan_ids)
        plan_type = {
            "NHP-COM-NY": "commercial",
            "NHP-MCD-NY": "medicaid",
            "NHP-MCR-NJ": "medicare_advantage",
            "NHP-WC-PA": "workers_comp",
            "NHP-COM-OLD": "commercial",
        }[plan_id]
        status = "active" if plan_id != "NHP-COM-OLD" and rng.random() > 0.08 else "inactive"
        rows["members"].append(
            {
                "member_id": member_id,
                "patient_name": f"{rng.choice(first)} {rng.choice(last)}",
                "dob": f"{rng.randint(1950, 2018):04d}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
                "plan_id": plan_id,
                "plan_type": plan_type,
                "product": rng.choice(["PrimePlus PPO", "CommunityCare", "SeniorChoice HMO", "OccupationalDirect"]),
                "employer_group": rng.choice(
                    ["BriarWorks", "Mercer Foods", "Eastline Labs", "Keystone Transit", None]
                ),
                "member_status": status,
            }
        )
        policy_id = rng.choice(policies)
        case_id = f"CASE-D-{idx:04d}"
        stage = rng.choice(
            ["intake", "nurse_review", "medical_director", "appeals", "payment_integrity", "finance_queue"]
        )
        current_status = rng.choice(
            ["open", "ready_for_determination", "needs_information", "denied", "approved", "paid_review", "closed"]
        )
        rows["cases"].append(
            {
                "case_id": case_id,
                "member_id": member_id,
                "provider_id": rng.choice(provider_ids),
                "request_type": rng.choice(
                    [
                        "prior_authorization",
                        "claim_payment_review",
                        "coverage_exception",
                        "peer_to_peer",
                        "queue_analysis",
                    ]
                ),
                "service_domain": domains[policy_id],
                "policy_id": policy_id,
                "request_date": f"2026-{rng.randint(1, 6):02d}-{rng.randint(1, 28):02d}",
                "due_date": f"2026-{rng.randint(6, 7):02d}-{rng.randint(1, 28):02d}",
                "current_stage": stage,
                "current_status": current_status,
                "urgency": rng.choice(["routine", "standard", "expedited"]),
                "summary": rng.choice(
                    [
                        "Distractor record with similar but non-target therapy documentation.",
                        "Older export conflicts with current document and requires source-date review.",
                        "Payment review item with unrelated CPT mix.",
                        "Appeal packet has partial documentation for an unrelated queue item.",
                    ]
                ),
            }
        )
        line_count = rng.randint(1, 3)
        cpts = ["97110", "97112", "97530", "92507", "78431", "78452", "A9500", "93016", "29881"]
        for line_no in range(1, line_count + 1):
            cpt = rng.choice(cpts)
            rows["request_lines"].append(
                {
                    "line_id": f"RL-D-{idx:04d}-{line_no}",
                    "case_id": case_id,
                    "cpt_code": cpt,
                    "modifier": rng.choice(["GP", "GN", "TC", "RT", "59", None]),
                    "service_name": rng.choice(
                        ["Therapy service", "Imaging service", "Surgical service", "Drug review"]
                    ),
                    "requested_units": rng.randint(1, 24),
                    "requested_start": f"2026-{rng.randint(4, 7):02d}-{rng.randint(1, 28):02d}",
                    "requested_end": f"2026-{rng.randint(7, 9):02d}-{rng.randint(1, 28):02d}",
                    "diagnosis_codes": rng.choice(["M54.50", "F80.2", "I25.10", "L20.9", "S83.241A"]),
                    "billed_charge": round(rng.uniform(120.0, 4200.0), 2),
                }
            )
        for doc_no in range(1, rng.randint(2, 4)):
            is_current = 0 if doc_no == 2 and rng.random() < 0.22 else 1
            doc_id = f"DOC-D-{idx:04d}-{doc_no}"
            rows["documents"].append(
                {
                    "document_id": doc_id,
                    "case_id": case_id,
                    "document_type": rng.choice(
                        ["clinical_note", "plan_of_care", "stale_export", "remittance", "appeal_letter"]
                    ),
                    "document_date": f"2026-{rng.randint(1, 6):02d}-{rng.randint(1, 28):02d}",
                    "received_date": f"2026-{rng.randint(4, 6):02d}-{rng.randint(1, 28):02d}",
                    "source_system": rng.choice(["CarePort", "ProviderFax", "LegacyUM", "ClaimsCore", "RxPortal"]),
                    "is_current": is_current,
                    "title": f"Distractor document {doc_no} for {case_id}",
                    "summary": rng.choice(
                        [
                            "Current note has limited details.",
                            "Stale export should not control the decision.",
                            "Partial packet item.",
                            "Payment detail references old schedule.",
                        ]
                    ),
                }
            )
            rows["document_facts"].append(
                {
                    "fact_id": f"FACT-{doc_id}-01",
                    "document_id": doc_id,
                    "case_id": case_id,
                    "fact_key": rng.choice(
                        ["frequency_per_week", "requested_units_total", "paid_total", "packet_item", "clinical_status"]
                    ),
                    "fact_value": rng.choice(["not stated", "current", "partial", "closed", "requires review"]),
                    "numeric_value": rng.choice([None, 1.0, 2.0, 12.0, 24.0, round(rng.uniform(100, 1500), 2)]),
                    "unit": rng.choice([None, "units", "USD", "visits"]),
                    "supports_criteria": rng.choice([None, "PT-POC", "ST-POC", "CLAIM-SCHED", "DRUG-RATIONALE"]),
                }
            )
        if policy_id == "POL-PET-MPI-2026" and rng.random() < 0.35:
            rows["p2p_events"].append(
                {
                    "p2p_id": f"P2P-D-{idx:04d}",
                    "case_id": case_id,
                    "scheduled_at": f"2026-06-{rng.randint(1, 28):02d}T{rng.randint(13, 18):02d}:00:00Z",
                    "duration_minutes": rng.randint(10, 25),
                    "provider_argument": "Provider requested reconsideration.",
                    "new_information": rng.choice(
                        ["No new information.", "BMI limitation supplied.", "Prior SPECT report supplied."]
                    ),
                    "outcome": rng.choice(["uphold_intended_adverse_decision", "overturn_to_approval", "reschedule"]),
                    "final_status": rng.choice(["denied", "approved", "pending"]),
                    "reviewer": rng.choice(["Dr. Imani Wells", "Dr. Samuel Ortiz"]),
                    "notes": "Distractor P2P record.",
                }
            )
        if policy_id == "POL-DRUG-EXC-2026" and rng.random() < 0.45:
            rows["appeals"].append(
                {
                    "appeal_id": f"APL-D-{idx:04d}",
                    "case_id": case_id,
                    "denial_date": f"2026-05-{rng.randint(1, 28):02d}",
                    "received_date": f"2026-06-{rng.randint(1, 12):02d}",
                    "appeal_type_requested": rng.choice(["coverage_exception", "standard", "expedited"]),
                    "appeal_path": rng.choice(["standard_internal", "expedited_internal", "external_review"]),
                    "expedited_attestation": rng.choice(
                        ["not_requested", "provider_attested_serious_health_risk", "missing"]
                    ),
                    "appeal_deadline": f"2026-06-{rng.randint(10, 28):02d}",
                    "outcome": rng.choice(["open", "upheld", "overturned", "withdrawn"]),
                    "owner": rng.choice(["appeals-rx", "appeals-um"]),
                    "notes": "Distractor appeal.",
                }
            )
        if rng.random() < 0.55:
            claim_id = f"CLAIM-D-{idx:04d}"
            paid = round(rng.uniform(120.0, 2600.0), 2)
            rows["claims"].append(
                {
                    "claim_id": claim_id,
                    "member_id": member_id,
                    "case_id": case_id,
                    "payer": "Northstar Health Plan",
                    "received_date": f"2026-{rng.randint(1, 6):02d}-{rng.randint(1, 28):02d}",
                    "claim_status": rng.choice(["paid", "denied", "paid_stale_schedule", "adjusted"]),
                    "auth_number": rng.choice([None, f"NPA-{rng.randint(2400000, 2409999)}"]),
                    "billed_total": round(paid * rng.uniform(1.2, 2.6), 2),
                    "paid_total": paid,
                }
            )
            for line_no in range(1, rng.randint(2, 4)):
                rows["claim_lines"].append(
                    {
                        "claim_line_id": f"CL-D-{idx:04d}-{line_no}",
                        "claim_id": claim_id,
                        "line_number": line_no,
                        "cpt_code": rng.choice(cpts),
                        "modifier": rng.choice(["GP", "GN", "TC", "RT", "59", None]),
                        "units": rng.randint(1, 4),
                        "billed_amount": round(rng.uniform(100.0, 1800.0), 2),
                        "paid_amount": round(rng.uniform(0.0, 900.0), 2),
                        "denial_code": rng.choice([None, None, "CO-45", "PI-204", "N30"]),
                        "service_date": f"2026-{rng.randint(1, 6):02d}-{rng.randint(1, 28):02d}",
                    }
                )
    for idx, (payer, domain, cpt) in enumerate(
        [
            ("Northstar Health Plan", "physical_therapy", "97110"),
            ("Northstar Health Plan", "speech_therapy", "92507"),
            ("Northstar Health Plan", "cardiac_imaging", "78431"),
            ("Northstar Health Plan", "outpatient_surgery", "29881"),
        ],
        start=1,
    ):
        for plan_type in ["commercial", "medicaid", "medicare_advantage", "workers_comp"]:
            rows["payment_benchmarks"].append(
                {
                    "benchmark_id": f"BM-D-{idx}-{plan_type}",
                    "payer": payer,
                    "plan_type": plan_type,
                    "service_domain": domain,
                    "cpt_code": cpt,
                    "modifier": rng.choice([None, "GP", "GN", "TC", "RT"]),
                    "effective_start": "2026-01-01",
                    "effective_end": "2026-12-31",
                    "allowed_amount": round(rng.uniform(65.0, 2400.0), 2),
                    "source_name": "Northstar Distractor Schedule",
                    "source_version": "2026",
                }
            )
    for idx in range(1, 25):
        rows["service_margin"].append(
            {
                "month_id": f"SM-D-{idx:03d}",
                "period": rng.choice(["2026-04", "2026-05", "2026-06"]),
                "payer": "Northstar Health Plan",
                "payer_segment": rng.choice(["commercial", "medicaid", "medicare_advantage", "workers_comp"]),
                "service_domain": rng.choice(["physical_therapy", "speech_therapy", "cardiac_imaging"]),
                "cpt_code": rng.choice(["97110", "97112", "97530", "92507", "78431"]),
                "visits": rng.randint(25, 600),
                "net_revenue": round(rng.uniform(4000.0, 65000.0), 2),
                "variable_cost": round(rng.uniform(2500.0, 42000.0), 2),
                "fixed_cost_allocated": round(rng.uniform(1000.0, 13000.0), 2),
                "charge_sensitive": rng.choice([0, 1]),
            }
        )
    return rows


def generate_database(db_path: Path = DB_PATH, overwrite: bool = True) -> dict:
    rng = random.Random(SEED)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if overwrite and db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=DELETE")
    cur.execute("PRAGMA foreign_keys=OFF")
    for statement in SCHEMA:
        cur.execute(statement)
    base = base_rows()
    for table in ["plans", "providers", "policies", "policy_criteria"]:
        insert_many(cur, table, base[table])
    targets = target_rows()
    distractors = distractor_rows(rng)
    ordered_tables = [
        "members",
        "cases",
        "request_lines",
        "documents",
        "document_facts",
        "case_criteria",
        "p2p_events",
        "appeals",
        "drug_trials",
        "assistance_screen",
        "claims",
        "claim_lines",
        "authorizations",
        "payment_benchmarks",
        "service_margin",
    ]
    for table in ordered_tables:
        insert_many(cur, table, targets.get(table, []))
        insert_many(cur, table, distractors.get(table, []))
    conn.commit()
    cur.execute("VACUUM")
    conn.close()
    manifest = {
        "service": "northstar-payer-operations",
        "task_group": "task_group_014",
        "seed": SEED,
        "database": "data/northstar_pa.sqlite",
        "generated_at": "2026-07-18T00:00:00Z",
        "state_mode": "read_only",
        "target_record_count": 10,
        "distractors": {
            "cases": 150,
            "notes": "Generated distractors include expired plans, stale exports, duplicate-like documents, unrelated claims, multiple plan types, and overlapping service lines.",
        },
        "tables": {},
    }
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    table_names = [
        row[0]
        for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]
    for table_name in table_names:
        count = cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        manifest["tables"][table_name] = count
    conn.close()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    result = generate_database()
    print(
        json.dumps(
            {"ok": True, "database": str(DB_PATH), "seed": SEED, "tables": result["tables"]}, indent=2, sort_keys=True
        )
    )
