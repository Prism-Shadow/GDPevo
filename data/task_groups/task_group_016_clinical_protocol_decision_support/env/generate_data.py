#!/usr/bin/env python3
"""Generate deterministic synthetic clinic data for the shared environment."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path


SEED = 16016
SYNTHETIC_CLOCK = "2026-07-06T09:00:00-05:00"
GENERATED_AT = "2026-07-06T14:00:00Z"
TIMEZONE = "America/Chicago"

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CLINIC_DATA_PATH = DATA_DIR / "clinic_data.json"
MANIFEST_PATH = DATA_DIR / "manifest.json"


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S-05:00")


def date(days_back: int, hour: int = 9, minute: int = 0) -> str:
    base = datetime(2026, 7, 6, hour, minute, 0)
    return iso(base - timedelta(days=days_back))


def patient(
    patient_id: str,
    identifier: str,
    given: str,
    family: str,
    birth_date: str,
    sex: str,
    phone: str,
    risk_band: str,
    allergies: list[dict],
    active_problems: list[dict],
    medication_summary: list[dict],
    address: dict | None = None,
) -> dict:
    return {
        "patient_id": patient_id,
        "identifier": identifier,
        "name": {"given": given, "family": family, "text": f"{given} {family}"},
        "birth_date": birth_date,
        "sex": sex,
        "phone": phone,
        "address": address
        or {
            "line": "100 Clinic Way",
            "city": "Madison",
            "state": "WI",
            "postal_code": "53703",
        },
        "allergies": allergies,
        "active_problems": active_problems,
        "medication_summary": medication_summary,
    }


def encounter(
    encounter_id: str,
    patient_id: str,
    kind: str,
    start: str,
    reason: str,
    clinician: str,
    facts: dict,
    status: str = "in-progress",
) -> dict:
    return {
        "encounter_id": encounter_id,
        "patient_id": patient_id,
        "kind": kind,
        "status": status,
        "start": start,
        "timezone": TIMEZONE,
        "reason": reason,
        "clinician": clinician,
        "facts": facts,
    }


def observation(
    obs_id: str,
    patient_id: str,
    code: str,
    display: str,
    category: str,
    status: str,
    effective: str,
    value=None,
    unit: str | None = None,
    encounter_id: str | None = None,
    interpretation: str | None = None,
    notes: str | None = None,
    panel_header: bool = False,
) -> dict:
    item = {
        "resourceType": "Observation",
        "id": obs_id,
        "patient_id": patient_id,
        "encounter_id": encounter_id,
        "code": code,
        "display": display,
        "category": category,
        "status": status,
        "effectiveDateTime": effective,
        "panel_header": panel_header,
    }
    if value is not None:
        item["value"] = value
    if unit is not None:
        item["unit"] = unit
    if interpretation is not None:
        item["interpretation"] = interpretation
    if notes is not None:
        item["notes"] = notes
    return item


def medication_request(
    med_id: str,
    patient_id: str,
    medication: str,
    category: str,
    status: str,
    authored_on: str,
    dose: str,
    prescriber: str,
    ndc: str | None = None,
    notes: str | None = None,
) -> dict:
    item = {
        "id": med_id,
        "patient_id": patient_id,
        "medication": medication,
        "category": category,
        "status": status,
        "authored_on": authored_on,
        "dose": dose,
        "prescriber": prescriber,
    }
    if ndc is not None:
        item["ndc"] = ndc
    if notes is not None:
        item["notes"] = notes
    return item


def care_case(
    case_id: str,
    patient_id: str,
    risk_band: str,
    risk_score: float,
    status: str,
    opened_on: str,
    referral_reason: str,
    persona: str,
    chart_concerns: list[str],
    admissions: list[dict],
    sdoh_flags: list[str],
    medication_burden: int,
) -> dict:
    return {
        "case_id": case_id,
        "patient_id": patient_id,
        "risk_score": risk_score,
        "status": status,
        "opened_on": opened_on,
        "referral_reason": referral_reason,
        "member_persona": persona,
        "chart_concerns": chart_concerns,
        "recent_admissions": admissions,
        "sdoh_flags": sdoh_flags,
        "medication_burden": medication_burden,
        "service_context": {
            "available_disciplines": [
                "RN care manager",
                "clinical pharmacist",
                "social worker",
                "behavioral health consultant",
                "respiratory therapist",
                "primary care provider",
            ],
            "assignment_status": "not_assigned_until_intake_decision",
        },
    }


def protocol_cards() -> list[dict]:
    return [
        {
            "protocol_id": "HEAD_INJURY_2026",
            "title": "Head Injury Routing and Activity Restriction",
            "version": "2026.1",
            "effective": "2026-01-01",
            "local_rules": [
                "urgent_ed when the current encounter includes repeated vomiting, worsening headache, seizure, focal weakness, slurred speech, increasing drowsiness, confusion, amnesia over 30 minutes, anticoagulant use, abnormal gait or coordination, or deteriorating mental status.",
                "same_day_clinic for low-risk symptoms that need clinician review but no urgent red flag.",
                "home_observation only when no red flags, normal neuro exam, and reliable adult observation.",
                "CT recommendation is urgent for urgent_ed, consider for same_day_clinic with persistent symptoms or unreliable observation, otherwise not_required.",
                "No same-day return to play. No high-risk activity until symptom-free and medically cleared. No driving if symptoms or neurologic concerns are present.",
                "Follow-up timing is 24 hours for urgent or red-flag cases, 48-72 hours for same-day clinic, and 72 hours for home observation.",
            ],
            "outputs": {
                "routes": ["urgent_ed", "same_day_clinic", "home_observation"],
                "ct_recommendations": ["urgent", "consider", "not_required"],
            },
        },
        {
            "protocol_id": "RESP_ACUTE_2026",
            "title": "Acute Respiratory Infection and Pneumonia",
            "version": "2026.2",
            "effective": "2026-02-15",
            "local_rules": [
                "community_acquired_pneumonia when fever and cough are accompanied by focal crackles or chest x-ray infiltrate or consolidation.",
                "ed_evaluation for oxygen saturation below 92 percent on room air, confusion, hypotension, respiratory rate at least 24, or pleuritic chest pain with hypoxia.",
                "outpatient_treatment when stable, O2 saturation is at least 92 percent, and no ED criteria are present.",
                "Controlled antibiotic choices are doxycycline, respiratory_fluoroquinolone, azithromycin, and no_antibiotic_protocol.",
                "Avoid penicillin class with penicillin allergy, sulfonamide class with sulfa allergy, and macrolide or fluoroquinolone when a local QT-risk medication is active unless ED route supersedes outpatient selection.",
                "Required tests may include chest_xray, pulse_ox_recheck, covid_flu_testing, basic_metabolic_panel, or blood_culture_if_ed.",
            ],
            "outputs": {
                "routes": ["ed_evaluation", "outpatient_treatment", "supportive_care"],
                "antibiotic_plan_choices": [
                    "doxycycline",
                    "respiratory_fluoroquinolone",
                    "azithromycin",
                    "no_antibiotic_protocol",
                ],
                "test_options": [
                    "chest_xray",
                    "pulse_ox_recheck",
                    "covid_flu_testing",
                    "basic_metabolic_panel",
                    "blood_culture_if_ed",
                ],
            },
        },
        {
            "protocol_id": "POTASSIUM_REPLETION_2026",
            "title": "Oral Potassium Repletion",
            "version": "2026.1",
            "effective": "2026-01-01",
            "local_rules": [
                "Use the most recent final serum potassium Observation with code K.",
                "Target potassium is 3.5 mEq/L.",
                "If below target, order oral potassium chloride using NDC 40032-917-01.",
                "Dose is 10 mEq per 0.1 mEq/L below target, rounded up to the next 10 mEq.",
                "Follow-up serum potassium LOINC is 2823-3.",
                "Follow-up occurrence is the next calendar day at 08:00 in the local encounter timezone.",
            ],
            "outputs": {
                "target_mEq_per_L": 3.5,
                "potassium_code": "K",
                "follow_up_loinc": "2823-3",
                "ndc": "40032-917-01",
            },
        },
        {
            "protocol_id": "FHIR_LAB_RETRIEVAL_2026",
            "title": "FHIR Observation Lab Retrieval",
            "version": "2026.1",
            "effective": "2026-01-01",
            "local_rules": [
                "Match Observation resources by exact patient id and exact code.",
                "Date windows use Observation effectiveDateTime.",
                "Month windows include all instants from the first day at 00:00:00 through the last day at 23:59:59.",
                "Count only final resources.",
                "Exclude panel headers, preliminary records, cancelled records, entered-in-error records, and records for linked but different patients.",
                "Matched resource ids should be returned sorted lexicographically unless chronological order is explicitly requested.",
            ],
            "outputs": {
                "default_sort": "lexicographic_resource_id",
                "accepted_status": "final",
            },
        },
        {
            "protocol_id": "COMPLEX_CARE_2026",
            "title": "Complex Care Outreach and Care Plan",
            "version": "2026.3",
            "effective": "2026-03-01",
            "local_rules": [
                "complex_care program when registry risk score is at least 0.75 or there is a recent high-acuity admission plus uncontrolled chronic disease.",
                "Required chart concerns include active disease metrics, recent admissions, medication burden, and SDoH flags when present.",
                "Initial refusal is not final when the persona is initially_refuses; use low-pressure, permission-based explanation of voluntary scope.",
                "Do not guarantee lower costs, ride availability, dialysis-slot flexibility, or approval of assistance.",
                "Assessment domains must be grounded in chart or referral cues and member-confirmed barriers.",
                "Complex-care plan requires at least 3 problem areas, at least 2 disciplines, weekly follow-up, and escalation conditions covering clinical plus behavioral or SDoH risk when indicated.",
            ],
            "outputs": {
                "minimum_problem_areas": 3,
                "minimum_disciplines": 2,
                "follow_up_cadence": "weekly",
            },
        },
    ]


def build_targets() -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
    patients: list[dict] = []
    encounters: list[dict] = []
    observations: list[dict] = []
    medication_requests: list[dict] = []
    care_cases: list[dict] = []

    patients.extend(
        [
            patient(
                "PAT-H-T001",
                "MRN-H-61001",
                "Maya",
                "Rios",
                "2009-04-12",
                "female",
                "608-555-0114",
                "low",
                [
                    {
                        "substance": "amoxicillin",
                        "category": "medication",
                        "reaction": "hives",
                        "severity": "moderate",
                        "status": "active",
                    }
                ],
                [
                    {
                        "code": "CONCUSSION-HX",
                        "display": "Concussion in 2023",
                        "status": "inactive",
                        "recorded": date(900),
                        "notes": "Stale problem-list item from soccer season.",
                    }
                ],
                [{"medication": "ibuprofen", "status": "active", "category": "analgesic"}],
            ),
            patient(
                "PAT-R-T001",
                "MRN-R-62001",
                "Gordon",
                "Patel",
                "1968-11-22",
                "male",
                "608-555-0121",
                "moderate",
                [
                    {
                        "substance": "penicillin",
                        "category": "medication",
                        "reaction": "angioedema",
                        "severity": "severe",
                        "status": "active",
                    }
                ],
                [
                    {"code": "HTN", "display": "Hypertension", "status": "active", "recorded": date(1200)},
                    {
                        "code": "COPD-OLD",
                        "display": "COPD noted by outside clinic",
                        "status": "inactive",
                        "recorded": date(1450),
                        "notes": "Patient denies COPD; no current inhalers.",
                    },
                ],
                [
                    {"medication": "lisinopril", "status": "active", "category": "antihypertensive"},
                    {"medication": "sertraline", "status": "active", "category": "qt_risk"},
                ],
            ),
            patient(
                "PAT-K-T001",
                "MRN-K-63001",
                "Elena",
                "Santos",
                "1955-08-03",
                "female",
                "608-555-0130",
                "moderate",
                [],
                [
                    {
                        "code": "HF",
                        "display": "Heart failure with preserved EF",
                        "status": "active",
                        "recorded": date(820),
                    },
                    {
                        "code": "CKD2",
                        "display": "Chronic kidney disease stage 2",
                        "status": "active",
                        "recorded": date(500),
                    },
                ],
                [
                    {"medication": "furosemide", "status": "active", "category": "diuretic"},
                    {"medication": "metoprolol", "status": "active", "category": "cardiac"},
                ],
            ),
            patient(
                "PAT-L-T001",
                "MRN-L-64001",
                "Noah",
                "Kim",
                "1982-01-30",
                "male",
                "608-555-0140",
                "low",
                [],
                [{"code": "DM2", "display": "Type 2 diabetes mellitus", "status": "active", "recorded": date(700)}],
                [{"medication": "metformin", "status": "active", "category": "diabetes"}],
            ),
            patient(
                "PAT-CM-T001",
                "MRN-CM-65001",
                "Linda",
                "Washington",
                "1951-06-09",
                "female",
                "608-555-0150",
                "high",
                [
                    {
                        "substance": "sulfonamide antibiotics",
                        "category": "medication",
                        "reaction": "rash",
                        "severity": "moderate",
                        "status": "active",
                    }
                ],
                [
                    {
                        "code": "DM2",
                        "display": "Type 2 diabetes mellitus, uncontrolled",
                        "status": "active",
                        "recorded": date(1100),
                    },
                    {
                        "code": "CKD4",
                        "display": "Chronic kidney disease stage 4",
                        "status": "active",
                        "recorded": date(300),
                    },
                    {"code": "MDD", "display": "Major depressive disorder", "status": "active", "recorded": date(600)},
                ],
                [
                    {"medication": "insulin glargine", "status": "active", "category": "diabetes"},
                    {"medication": "insulin lispro", "status": "active", "category": "diabetes"},
                    {"medication": "torsemide", "status": "active", "category": "diuretic"},
                    {"medication": "apixaban", "status": "active", "category": "anticoagulant"},
                    {"medication": "sertraline", "status": "active", "category": "behavioral_health"},
                    {"medication": "atorvastatin", "status": "active", "category": "lipid"},
                    {"medication": "amlodipine", "status": "active", "category": "antihypertensive"},
                    {"medication": "gabapentin", "status": "active", "category": "pain"},
                ],
                {"line": "423 North Wingra Ave Apt 12", "city": "Madison", "state": "WI", "postal_code": "53704"},
            ),
            patient(
                "PAT-H-X001",
                "MRN-H-71001",
                "Elliot",
                "Nguyen",
                "1976-10-18",
                "male",
                "608-555-0214",
                "low",
                [],
                [
                    {"code": "AFIB", "display": "Atrial fibrillation", "status": "active", "recorded": date(400)},
                    {
                        "code": "DIZZINESS-OLD",
                        "display": "Vertigo episode in 2022",
                        "status": "inactive",
                        "recorded": date(1400),
                    },
                ],
                [{"medication": "warfarin", "status": "active", "category": "anticoagulant"}],
            ),
            patient(
                "PAT-R-X001",
                "MRN-R-72001",
                "Simone",
                "Grant",
                "1989-05-17",
                "female",
                "608-555-0221",
                "low",
                [
                    {
                        "substance": "sulfonamide antibiotics",
                        "category": "medication",
                        "reaction": "anaphylaxis",
                        "severity": "severe",
                        "status": "active",
                    }
                ],
                [{"code": "ASTHMA", "display": "Mild intermittent asthma", "status": "active", "recorded": date(900)}],
                [
                    {"medication": "albuterol inhaler", "status": "active", "category": "respiratory"},
                    {"medication": "escitalopram", "status": "active", "category": "qt_risk"},
                ],
            ),
            patient(
                "PAT-K-X001",
                "MRN-K-73001",
                "Arthur",
                "Bennett",
                "1949-02-25",
                "male",
                "608-555-0230",
                "high",
                [],
                [
                    {
                        "code": "HFREF",
                        "display": "Heart failure with reduced EF",
                        "status": "active",
                        "recorded": date(760),
                    },
                    {
                        "code": "CKD3",
                        "display": "Chronic kidney disease stage 3",
                        "status": "active",
                        "recorded": date(510),
                    },
                ],
                [
                    {"medication": "bumetanide", "status": "active", "category": "diuretic"},
                    {"medication": "sacubitril-valsartan", "status": "active", "category": "cardiac"},
                ],
            ),
            patient(
                "PAT-L-X001",
                "MRN-L-74001",
                "Priya",
                "Shah",
                "1974-09-07",
                "female",
                "608-555-0240",
                "moderate",
                [],
                [
                    {"code": "RA", "display": "Rheumatoid arthritis", "status": "active", "recorded": date(1300)},
                    {"code": "ANEMIA", "display": "Iron deficiency anemia", "status": "active", "recorded": date(620)},
                ],
                [{"medication": "methotrexate", "status": "active", "category": "immunomodulator"}],
            ),
            patient(
                "PAT-CM-X001",
                "MRN-CM-75001",
                "Harold",
                "Martinez",
                "1962-12-01",
                "male",
                "608-555-0250",
                "high",
                [
                    {
                        "substance": "iodinated contrast",
                        "category": "medication",
                        "reaction": "wheezing",
                        "severity": "severe",
                        "status": "active",
                    }
                ],
                [
                    {
                        "code": "COPD",
                        "display": "COPD with frequent exacerbations",
                        "status": "active",
                        "recorded": date(1000),
                    },
                    {
                        "code": "HFREF",
                        "display": "Heart failure with reduced EF",
                        "status": "active",
                        "recorded": date(700),
                    },
                    {
                        "code": "OUD",
                        "display": "Opioid use disorder in remission",
                        "status": "active",
                        "recorded": date(900),
                    },
                ],
                [
                    {"medication": "tiotropium", "status": "active", "category": "respiratory"},
                    {"medication": "budesonide-formoterol", "status": "active", "category": "respiratory"},
                    {"medication": "furosemide", "status": "active", "category": "diuretic"},
                    {"medication": "carvedilol", "status": "active", "category": "cardiac"},
                    {"medication": "buprenorphine-naloxone", "status": "active", "category": "behavioral_health"},
                    {"medication": "mirtazapine", "status": "active", "category": "behavioral_health"},
                    {"medication": "aspirin", "status": "active", "category": "antiplatelet"},
                ],
                {"line": "88 Yahara Landing", "city": "Madison", "state": "WI", "postal_code": "53714"},
            ),
        ]
    )

    encounters.extend(
        [
            encounter(
                "ENC-H-T001",
                "PAT-H-T001",
                "urgent_care",
                date(0, 8, 10),
                "Head injury during basketball practice",
                "NP Avery Nolan",
                {
                    "mechanism": "Elbow to right temple, fell backward, no helmet.",
                    "symptoms": ["headache", "nausea", "vomited twice", "drowsy in waiting room"],
                    "vomiting_episode_count": 2,
                    "waiting_room_observation": "Caregiver reports the patient became hard to keep awake while waiting.",
                    "neuro_exam": {
                        "gait": "steady",
                        "speech": "clear",
                        "focal_weakness": False,
                        "glasgow_coma_scale": 15,
                    },
                    "loss_of_consciousness": "none witnessed",
                    "amnesia_minutes": 10,
                    "reliable_observer": True,
                    "current_anticoagulant_use": False,
                    "stale_conflict": "Old concussion problem is inactive and not the current event.",
                },
            ),
            encounter(
                "ENC-R-T001",
                "PAT-R-T001",
                "same_day_clinic",
                date(0, 8, 35),
                "Fever, cough, and shortness of breath",
                "Dr. Celia Brooks",
                {
                    "symptoms": ["fever", "productive cough", "pleuritic chest pain", "fatigue"],
                    "vitals": {
                        "temperature_f": 101.8,
                        "heart_rate": 108,
                        "respiratory_rate": 26,
                        "blood_pressure": "118/72",
                        "oxygen_saturation_room_air": 90,
                    },
                    "exam": {"lung": "focal crackles right lower lobe", "mental_status": "alert"},
                    "imaging": {"chest_xray": "right lower lobe infiltrate"},
                    "current_qt_risk_medication": "sertraline",
                    "stale_conflict": "Outside COPD label is inactive; current hypoxia is documented today.",
                },
            ),
            encounter(
                "ENC-H-X001",
                "PAT-H-X001",
                "telephone_triage",
                date(0, 7, 55),
                "Fall with head strike",
                "RN Jo Mendes",
                {
                    "mechanism": "Slipped on wet step and struck occiput.",
                    "symptoms": ["worsening headache", "mild nausea", "unsteady when walking to bathroom"],
                    "headache_course": "worse since the call started according to spouse",
                    "walking_observation": "Spouse reports the patient was unsteady walking to the bathroom.",
                    "neuro_exam": {
                        "gait": "abnormal by spouse report",
                        "speech": "clear",
                        "focal_weakness": False,
                        "glasgow_coma_scale": "not assessed by phone",
                    },
                    "loss_of_consciousness": "unknown for less than one minute",
                    "amnesia_minutes": 5,
                    "reliable_observer": True,
                    "current_anticoagulant_use": True,
                },
            ),
            encounter(
                "ENC-R-X001",
                "PAT-R-X001",
                "same_day_clinic",
                date(0, 8, 50),
                "Cough and fever",
                "PA Jordan Ellis",
                {
                    "symptoms": ["fever", "cough", "chills", "mild dyspnea"],
                    "vitals": {
                        "temperature_f": 100.9,
                        "heart_rate": 96,
                        "respiratory_rate": 20,
                        "blood_pressure": "124/78",
                        "oxygen_saturation_room_air": 95,
                    },
                    "exam": {"lung": "focal crackles left base", "mental_status": "alert"},
                    "imaging": {"chest_xray": "left lower lobe consolidation"},
                    "current_qt_risk_medication": "escitalopram",
                },
            ),
        ]
    )

    observations.extend(
        [
            observation(
                "OBS-H-T001-GCS",
                "PAT-H-T001",
                "GCS",
                "Glasgow coma score",
                "vital_signs",
                "final",
                date(0, 8, 18),
                15,
                "score",
                "ENC-H-T001",
            ),
            observation(
                "OBS-H-T001-HR",
                "PAT-H-T001",
                "8867-4",
                "Heart rate",
                "vital_signs",
                "final",
                date(0, 8, 18),
                92,
                "beats/min",
                "ENC-H-T001",
            ),
            observation(
                "OBS-H-X001-INR",
                "PAT-H-X001",
                "6301-6",
                "INR",
                "laboratory",
                "final",
                date(2, 10, 0),
                2.4,
                "ratio",
                None,
                "therapeutic",
            ),
            observation(
                "OBS-R-T001-O2",
                "PAT-R-T001",
                "59408-5",
                "Oxygen saturation in arterial blood by pulse oximetry",
                "vital_signs",
                "final",
                date(0, 8, 40),
                90,
                "%",
                "ENC-R-T001",
                "low",
            ),
            observation(
                "OBS-R-T001-CXR",
                "PAT-R-T001",
                "36643-5",
                "Chest x-ray impression",
                "imaging",
                "final",
                date(0, 8, 52),
                "Right lower lobe infiltrate",
                None,
                "ENC-R-T001",
            ),
            observation(
                "OBS-R-T001-O2-OLD",
                "PAT-R-T001",
                "59408-5",
                "Oxygen saturation in arterial blood by pulse oximetry",
                "vital_signs",
                "final",
                date(95, 9, 0),
                97,
                "%",
                None,
                notes="Stale primary-care value.",
            ),
            observation(
                "OBS-R-X001-O2",
                "PAT-R-X001",
                "59408-5",
                "Oxygen saturation in arterial blood by pulse oximetry",
                "vital_signs",
                "final",
                date(0, 8, 56),
                95,
                "%",
                "ENC-R-X001",
            ),
            observation(
                "OBS-R-X001-CXR",
                "PAT-R-X001",
                "36643-5",
                "Chest x-ray impression",
                "imaging",
                "final",
                date(0, 9, 8),
                "Left lower lobe consolidation",
                None,
                "ENC-R-X001",
            ),
            observation(
                "OBS-K-T001-OLD-FINAL",
                "PAT-K-T001",
                "K",
                "Serum potassium",
                "laboratory",
                "final",
                date(8, 7, 30),
                3.7,
                "mEq/L",
                None,
                notes="Stale normal potassium.",
            ),
            observation(
                "OBS-K-T001-PRELIM",
                "PAT-K-T001",
                "K",
                "Serum potassium",
                "laboratory",
                "preliminary",
                date(0, 7, 45),
                3.1,
                "mEq/L",
                None,
                notes="Preliminary duplicate before final verification.",
            ),
            observation(
                "OBS-K-T001-FINAL",
                "PAT-K-T001",
                "K",
                "Serum potassium",
                "laboratory",
                "final",
                date(0, 8, 5),
                3.2,
                "mEq/L",
                None,
                "low",
            ),
            observation(
                "OBS-K-T001-ERR",
                "PAT-K-T001",
                "K",
                "Serum potassium",
                "laboratory",
                "entered-in-error",
                date(0, 8, 20),
                2.7,
                "mEq/L",
                None,
            ),
            observation(
                "OBS-K-T001-LOINC",
                "PAT-K-T001",
                "2823-3",
                "Potassium [Moles/volume] in Serum or Plasma",
                "laboratory",
                "final",
                date(30, 8, 0),
                3.4,
                "mEq/L",
                None,
                notes="Older LOINC-coded result, not the local K code for dose selection.",
            ),
            observation(
                "OBS-K-X001-OLD-FINAL",
                "PAT-K-X001",
                "K",
                "Serum potassium",
                "laboratory",
                "final",
                date(4, 9, 15),
                3.4,
                "mEq/L",
                None,
            ),
            observation(
                "OBS-K-X001-CANCELLED",
                "PAT-K-X001",
                "K",
                "Serum potassium",
                "laboratory",
                "cancelled",
                date(0, 7, 50),
                3.0,
                "mEq/L",
                None,
            ),
            observation(
                "OBS-K-X001-FINAL",
                "PAT-K-X001",
                "K",
                "Serum potassium",
                "laboratory",
                "final",
                date(0, 8, 15),
                2.9,
                "mEq/L",
                None,
                "critical-low",
            ),
            observation(
                "OBS-L-T001-A1C-2026-05-A",
                "PAT-L-T001",
                "4548-4",
                "Hemoglobin A1c",
                "laboratory",
                "final",
                "2026-05-02T08:10:00-05:00",
                7.8,
                "%",
            ),
            observation(
                "OBS-L-T001-A1C-2026-05-B",
                "PAT-L-T001",
                "4548-4",
                "Hemoglobin A1c",
                "laboratory",
                "final",
                "2026-05-31T23:30:00-05:00",
                8.1,
                "%",
            ),
            observation(
                "OBS-L-T001-A1C-PRELIM",
                "PAT-L-T001",
                "4548-4",
                "Hemoglobin A1c",
                "laboratory",
                "preliminary",
                "2026-05-18T10:15:00-05:00",
                8.0,
                "%",
            ),
            observation(
                "OBS-L-T001-A1C-PANEL",
                "PAT-L-T001",
                "4548-4",
                "Hemoglobin A1c panel",
                "panel_header",
                "final",
                "2026-05-18T10:00:00-05:00",
                None,
                None,
                panel_header=True,
            ),
            observation(
                "OBS-L-T001-A1C-APRIL",
                "PAT-L-T001",
                "4548-4",
                "Hemoglobin A1c",
                "laboratory",
                "final",
                "2026-04-30T23:59:00-05:00",
                7.6,
                "%",
            ),
            observation(
                "OBS-L-T001-CREAT-MAY",
                "PAT-L-T001",
                "2160-0",
                "Creatinine",
                "laboratory",
                "final",
                "2026-05-20T11:00:00-05:00",
                0.9,
                "mg/dL",
            ),
            observation(
                "OBS-L-T001-LINKED",
                "PAT-L-T01",
                "4548-4",
                "Hemoglobin A1c",
                "laboratory",
                "final",
                "2026-05-12T09:00:00-05:00",
                9.4,
                "%",
                notes="Close but wrong patient id.",
            ),
            observation(
                "OBS-L-X001-ESR-JUN-A",
                "PAT-L-X001",
                "4537-7",
                "Erythrocyte sedimentation rate",
                "laboratory",
                "final",
                "2026-06-01T00:00:00-05:00",
                34,
                "mm/h",
            ),
            observation(
                "OBS-L-X001-ESR-JUN-B",
                "PAT-L-X001",
                "4537-7",
                "Erythrocyte sedimentation rate",
                "laboratory",
                "final",
                "2026-06-22T14:25:00-05:00",
                41,
                "mm/h",
            ),
            observation(
                "OBS-L-X001-ESR-JULY",
                "PAT-L-X001",
                "4537-7",
                "Erythrocyte sedimentation rate",
                "laboratory",
                "final",
                "2026-07-01T08:00:00-05:00",
                39,
                "mm/h",
            ),
            observation(
                "OBS-L-X001-ESR-CANCEL",
                "PAT-L-X001",
                "4537-7",
                "Erythrocyte sedimentation rate",
                "laboratory",
                "cancelled",
                "2026-06-10T08:40:00-05:00",
                37,
                "mm/h",
            ),
            observation(
                "OBS-L-X001-ESR-PANEL",
                "PAT-L-X001",
                "4537-7",
                "Sedimentation rate panel",
                "panel_header",
                "final",
                "2026-06-10T08:30:00-05:00",
                None,
                None,
                panel_header=True,
            ),
            observation(
                "OBS-L-X001-CRP-JUN",
                "PAT-L-X001",
                "1988-5",
                "C reactive protein",
                "laboratory",
                "final",
                "2026-06-22T14:25:00-05:00",
                12.2,
                "mg/L",
            ),
            observation(
                "OBS-L-X001-WRONGPAT",
                "PAT-L-X01",
                "4537-7",
                "Erythrocyte sedimentation rate",
                "laboratory",
                "final",
                "2026-06-12T08:00:00-05:00",
                88,
                "mm/h",
                notes="Linked chart, wrong patient id.",
            ),
            observation(
                "OBS-CM-T001-A1C",
                "PAT-CM-T001",
                "4548-4",
                "Hemoglobin A1c",
                "laboratory",
                "final",
                date(15, 9, 20),
                10.4,
                "%",
                None,
                "high",
            ),
            observation(
                "OBS-CM-T001-EGFR",
                "PAT-CM-T001",
                "33914-3",
                "eGFR",
                "laboratory",
                "final",
                date(15, 9, 20),
                24,
                "mL/min/1.73m2",
                None,
                "low",
            ),
            observation(
                "OBS-CM-X001-FEV1",
                "PAT-CM-X001",
                "20150-9",
                "FEV1 percent predicted",
                "pulmonary_function",
                "final",
                date(18, 11, 0),
                42,
                "% predicted",
                None,
                "low",
            ),
            observation(
                "OBS-CM-X001-BNP",
                "PAT-CM-X001",
                "30934-4",
                "BNP",
                "laboratory",
                "final",
                date(11, 13, 30),
                840,
                "pg/mL",
                None,
                "high",
            ),
        ]
    )

    medication_requests.extend(
        [
            medication_request(
                "MEDREQ-R-T001-CEF",
                "PAT-R-T001",
                "ceftriaxone",
                "antibiotic",
                "cancelled",
                date(0, 9, 5),
                "1 g IM once",
                "Dr. Celia Brooks",
                notes="Cancelled after penicillin allergy review.",
            ),
            medication_request(
                "MEDREQ-R-T001-SERTRALINE",
                "PAT-R-T001",
                "sertraline",
                "behavioral_health",
                "active",
                date(150, 10, 0),
                "50 mg daily",
                "Dr. Omar Vale",
            ),
            medication_request(
                "MEDREQ-R-X001-ESCITALOPRAM",
                "PAT-R-X001",
                "escitalopram",
                "behavioral_health",
                "active",
                date(230, 10, 0),
                "10 mg daily",
                "Dr. Mari Ives",
            ),
            medication_request(
                "MEDREQ-K-T001-FUROSEMIDE",
                "PAT-K-T001",
                "furosemide",
                "diuretic",
                "active",
                date(120, 9, 0),
                "40 mg each morning",
                "Dr. Noah Green",
            ),
            medication_request(
                "MEDREQ-K-X001-BUMETANIDE",
                "PAT-K-X001",
                "bumetanide",
                "diuretic",
                "active",
                date(95, 9, 0),
                "1 mg twice daily",
                "Dr. Noah Green",
            ),
            medication_request(
                "MEDREQ-CM-T001-INSULIN",
                "PAT-CM-T001",
                "insulin glargine",
                "diabetes",
                "active",
                date(210, 9, 0),
                "32 units nightly",
                "Endocrinology Clinic",
            ),
            medication_request(
                "MEDREQ-CM-X001-TIOTROPIUM",
                "PAT-CM-X001",
                "tiotropium",
                "respiratory",
                "active",
                date(180, 9, 0),
                "18 mcg inhaled daily",
                "Pulmonary Clinic",
            ),
        ]
    )

    care_cases.extend(
        [
            care_case(
                "CASE-CM-T001",
                "PAT-CM-T001",
                "high",
                0.86,
                "open",
                "2026-07-01",
                "Two admissions in 60 days with uncontrolled diabetes, CKD progression, missed nephrology visit, food insecurity, and medication complexity.",
                "initially_refuses",
                [
                    "A1c 10.4 percent despite basal-bolus insulin",
                    "eGFR 24 with missed nephrology follow-up",
                    "Two high-acuity admissions since May 2026",
                    "Eight active chronic medications with refill gaps",
                    "Food insecurity and utility shutoff notice documented by discharge planner",
                ],
                [
                    {
                        "facility": "Meridian Medical Center",
                        "admit": "2026-05-16",
                        "discharge": "2026-05-20",
                        "reason": "Hyperglycemia and dehydration",
                        "acuity": "high",
                    },
                    {
                        "facility": "Meridian Medical Center",
                        "admit": "2026-06-18",
                        "discharge": "2026-06-23",
                        "reason": "Heart failure exacerbation and AKI",
                        "acuity": "high",
                    },
                ],
                ["food_insecurity", "utility_risk", "transportation_barrier"],
                8,
            ),
            care_case(
                "CASE-CM-X001",
                "PAT-CM-X001",
                "high",
                0.79,
                "open",
                "2026-07-02",
                "COPD and heart failure admissions with unstable housing, missed pulmonary rehab, and difficulty affording inhalers.",
                "guarded_but_willing",
                [
                    "FEV1 42 percent predicted and three steroid bursts in 90 days",
                    "BNP 840 after recent heart failure admission",
                    "Seven active chronic medications with inhaler affordability concern",
                    "Unstable housing reported after discharge",
                    "Behavioral health history with OUD in remission",
                ],
                [
                    {
                        "facility": "East Bay Hospital",
                        "admit": "2026-04-28",
                        "discharge": "2026-05-02",
                        "reason": "COPD exacerbation",
                        "acuity": "high",
                    },
                    {
                        "facility": "East Bay Hospital",
                        "admit": "2026-06-11",
                        "discharge": "2026-06-15",
                        "reason": "Heart failure exacerbation",
                        "acuity": "high",
                    },
                ],
                ["housing_instability", "medication_cost", "transportation_barrier"],
                7,
            ),
        ]
    )

    return patients, encounters, observations, medication_requests, care_cases


def build_distractors(rng: random.Random) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
    first_names = [
        "Alicia",
        "Ben",
        "Carla",
        "Damon",
        "Eva",
        "Felix",
        "Grace",
        "Hannah",
        "Ian",
        "Jada",
        "Keiko",
        "Leo",
        "Marta",
        "Nolan",
        "Olivia",
        "Peter",
        "Quinn",
        "Rosa",
        "Samir",
        "Talia",
        "Uma",
        "Victor",
        "Wendy",
        "Xavier",
        "Yara",
        "Zane",
        "Maya",
        "Noel",
        "Simona",
        "Priyanka",
        "Harriet",
        "Gordon",
        "Elise",
        "Arthur",
        "Linda",
        "Elliott",
        "Nora",
        "Hugo",
        "Celine",
        "Marcus",
    ]
    last_names = [
        "Reed",
        "Morgan",
        "Diaz",
        "Cole",
        "Shaw",
        "Ali",
        "Brooks",
        "Chen",
        "Vega",
        "Stone",
        "Park",
        "Blake",
        "Ng",
        "Santos",
        "Rios",
        "Grant",
        "Kim",
        "Shah",
        "Martens",
        "Washington",
        "Bennett",
        "Patel",
        "Nguyen",
        "Martinez",
    ]
    problem_pool = [
        ("HTN", "Hypertension"),
        ("DM2", "Type 2 diabetes mellitus"),
        ("ASTHMA", "Asthma"),
        ("CKD3", "Chronic kidney disease stage 3"),
        ("MDD", "Major depressive disorder"),
        ("CHF", "Congestive heart failure"),
        ("MIGRAINE", "Migraine"),
        ("AFIB", "Atrial fibrillation"),
        ("COPD", "COPD"),
        ("GERD", "GERD"),
    ]
    med_pool = [
        ("lisinopril", "antihypertensive"),
        ("metformin", "diabetes"),
        ("atorvastatin", "lipid"),
        ("albuterol inhaler", "respiratory"),
        ("omeprazole", "gastrointestinal"),
        ("hydrochlorothiazide", "diuretic"),
        ("amiodarone", "qt_risk"),
        ("apixaban", "anticoagulant"),
        ("fluoxetine", "qt_risk"),
        ("gabapentin", "pain"),
    ]
    allergy_pool = [
        ("penicillin", "rash", "moderate"),
        ("sulfonamide antibiotics", "hives", "moderate"),
        ("azithromycin", "nausea", "mild"),
        ("latex", "contact dermatitis", "mild"),
        ("iodinated contrast", "wheezing", "severe"),
    ]
    patients: list[dict] = []
    encounters: list[dict] = []
    observations: list[dict] = []
    medication_requests: list[dict] = []
    care_cases: list[dict] = []

    for idx in range(1, 41):
        patient_id = f"PAT-D-{idx:03d}"
        given = first_names[idx - 1]
        family = rng.choice(last_names)
        year = rng.randint(1942, 2007)
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)
        risk = rng.choices(["low", "moderate", "high"], weights=[0.46, 0.39, 0.15], k=1)[0]
        problems = [
            {
                "code": code,
                "display": display,
                "status": "active",
                "recorded": date(rng.randint(60, 1600), rng.randint(7, 16), 0),
            }
            for code, display in rng.sample(problem_pool, rng.randint(1, 3))
        ]
        if idx % 9 == 0:
            problems.append(
                {
                    "code": "OLD-PE",
                    "display": "Pulmonary embolism noted in imported chart",
                    "status": "inactive",
                    "recorded": date(1800, 8, 0),
                    "notes": "Stale problem-list fact not confirmed in current chart.",
                }
            )
        meds = [
            {"medication": medication, "status": "active", "category": category}
            for medication, category in rng.sample(med_pool, rng.randint(1, 4))
        ]
        allergies = []
        if rng.random() < 0.45:
            substance, reaction, severity = rng.choice(allergy_pool)
            allergies.append(
                {
                    "substance": substance,
                    "category": "medication" if substance != "latex" else "environment",
                    "reaction": reaction,
                    "severity": severity,
                    "status": "active",
                }
            )
        patients.append(
            patient(
                patient_id,
                f"MRN-D-{81000 + idx}",
                given,
                family,
                f"{year:04d}-{month:02d}-{day:02d}",
                rng.choice(["female", "male", "nonbinary"]),
                f"608-555-{3000 + idx:04d}",
                risk,
                allergies,
                problems,
                meds,
            )
        )

        if idx % 4 == 0:
            kind = "same_day_clinic"
            reason = "Cough and fever"
            o2 = rng.choice([93, 94, 95, 96, 97])
            if idx % 16 == 0:
                o2 = 91
            encounters.append(
                encounter(
                    f"ENC-D-{idx:03d}-RESP",
                    patient_id,
                    kind,
                    date(rng.randint(1, 45), rng.randint(8, 15), rng.choice([0, 15, 30, 45])),
                    reason,
                    rng.choice(["Dr. Celia Brooks", "PA Jordan Ellis", "NP Avery Nolan"]),
                    {
                        "symptoms": rng.sample(
                            ["cough", "fever", "nasal congestion", "fatigue", "sore throat", "dyspnea"], 3
                        ),
                        "vitals": {
                            "temperature_f": round(rng.uniform(98.7, 101.9), 1),
                            "heart_rate": rng.randint(78, 112),
                            "respiratory_rate": rng.randint(16, 26),
                            "blood_pressure": f"{rng.randint(102, 138)}/{rng.randint(62, 86)}",
                            "oxygen_saturation_room_air": o2,
                        },
                        "exam": {
                            "lung": rng.choice(
                                ["clear", "scattered wheeze", "focal crackles left base", "coarse breath sounds"]
                            )
                        },
                    },
                    status="finished",
                )
            )
            observations.append(
                observation(
                    f"OBS-D-{idx:03d}-O2",
                    patient_id,
                    "59408-5",
                    "Oxygen saturation in arterial blood by pulse oximetry",
                    "vital_signs",
                    "final",
                    date(rng.randint(1, 45), rng.randint(8, 15), 0),
                    o2,
                    "%",
                )
            )
        elif idx % 4 == 1:
            encounters.append(
                encounter(
                    f"ENC-D-{idx:03d}-HEAD",
                    patient_id,
                    "urgent_care",
                    date(rng.randint(1, 60), rng.randint(8, 15), rng.choice([0, 20, 40])),
                    "Minor head bump",
                    "NP Avery Nolan",
                    {
                        "mechanism": rng.choice(
                            ["Cabinet door strike", "Low-speed bike fall", "Bumped head standing up"]
                        ),
                        "symptoms": rng.sample(["mild headache", "brief dizziness", "scalp tenderness", "nausea"], 2),
                        "neuro_exam": {
                            "gait": "steady",
                            "speech": "clear",
                            "focal_weakness": False,
                            "glasgow_coma_scale": 15,
                        },
                        "reliable_observer": rng.choice([True, True, False]),
                        "current_anticoagulant_use": any(m["category"] == "anticoagulant" for m in meds),
                    },
                    status="finished",
                )
            )
            observations.append(
                observation(
                    f"OBS-D-{idx:03d}-GCS",
                    patient_id,
                    "GCS",
                    "Glasgow coma score",
                    "vital_signs",
                    "final",
                    date(rng.randint(1, 60), 9, 0),
                    15,
                    "score",
                )
            )
        else:
            observations.append(
                observation(
                    f"OBS-D-{idx:03d}-K-FINAL",
                    patient_id,
                    "K",
                    "Serum potassium",
                    "laboratory",
                    "final",
                    date(rng.randint(1, 90), rng.randint(6, 14), 0),
                    round(rng.uniform(3.1, 4.8), 1),
                    "mEq/L",
                )
            )
            if idx % 7 == 0:
                observations.append(
                    observation(
                        f"OBS-D-{idx:03d}-K-PRELIM",
                        patient_id,
                        "K",
                        "Serum potassium",
                        "laboratory",
                        "preliminary",
                        date(rng.randint(1, 90), rng.randint(6, 14), 30),
                        round(rng.uniform(2.9, 4.6), 1),
                        "mEq/L",
                    )
                )

        observations.append(
            observation(
                f"OBS-D-{idx:03d}-CBC-PANEL",
                patient_id,
                "CBC",
                "Complete blood count panel",
                "panel_header",
                "final",
                date(rng.randint(3, 180), 7, 0),
                None,
                None,
                panel_header=True,
            )
        )
        observations.append(
            observation(
                f"OBS-D-{idx:03d}-A1C",
                patient_id,
                "4548-4",
                "Hemoglobin A1c",
                "laboratory",
                rng.choice(["final", "final", "preliminary", "cancelled"]),
                date(rng.randint(1, 210), rng.randint(7, 15), rng.choice([0, 15, 30])),
                round(rng.uniform(5.2, 9.8), 1),
                "%",
            )
        )

        for med_idx, med in enumerate(meds, 1):
            medication_requests.append(
                medication_request(
                    f"MEDREQ-D-{idx:03d}-{med_idx:02d}",
                    patient_id,
                    med["medication"],
                    med["category"],
                    "active",
                    date(rng.randint(15, 500), 9, 0),
                    rng.choice(["daily", "twice daily", "as needed", "nightly"]),
                    rng.choice(["Dr. Omar Vale", "Dr. Noah Green", "Clinic refill protocol"]),
                )
            )

        if risk in {"moderate", "high"} and idx % 5 == 0:
            score = round(rng.uniform(0.55, 0.82), 2)
            care_cases.append(
                care_case(
                    f"CASE-D-{idx:03d}",
                    patient_id,
                    risk,
                    score,
                    rng.choice(["open", "monitoring", "closed"]),
                    f"2026-0{rng.randint(4, 7)}-{rng.randint(1, 28):02d}",
                    rng.choice(
                        [
                            "Moderate registry risk with medication gaps.",
                            "Recent ED use with uncontrolled chronic disease.",
                            "Referral for care coordination after discharge.",
                        ]
                    ),
                    rng.choice(["engaged", "initially_refuses", "difficult_to_reach"]),
                    rng.sample(
                        [
                            "Medication refill gaps",
                            "Recent ED visit",
                            "A1c above goal",
                            "Missed specialist visit",
                            "Transportation concern",
                            "Caregiver stress",
                        ],
                        3,
                    ),
                    [
                        {
                            "facility": rng.choice(
                                ["Meridian Medical Center", "East Bay Hospital", "St. Anne Campus"]
                            ),
                            "admit": f"2026-0{rng.randint(4, 6)}-{rng.randint(1, 24):02d}",
                            "discharge": f"2026-0{rng.randint(4, 6)}-{rng.randint(2, 28):02d}",
                            "reason": rng.choice(["Pneumonia", "Heart failure", "Hyperglycemia", "COPD exacerbation"]),
                            "acuity": rng.choice(["moderate", "high"]),
                        }
                    ],
                    rng.sample(
                        ["transportation_barrier", "food_insecurity", "medication_cost", "housing_instability"],
                        rng.randint(0, 2),
                    ),
                    rng.randint(4, 11),
                )
            )

    patients.append(
        patient(
            "PAT-L-T01",
            "MRN-L-64001-LINK",
            "Noel",
            "Kim",
            "1982-01-31",
            "male",
            "608-555-0141",
            "low",
            [],
            [{"code": "PREDM", "display": "Prediabetes", "status": "active", "recorded": date(400)}],
            [{"medication": "none", "status": "active", "category": "administrative"}],
        )
    )
    patients.append(
        patient(
            "PAT-L-X01",
            "MRN-L-74001-LINK",
            "Priyanka",
            "Shah",
            "1975-09-07",
            "female",
            "608-555-0241",
            "moderate",
            [],
            [{"code": "RA", "display": "Rheumatoid arthritis", "status": "active", "recorded": date(1200)}],
            [{"medication": "prednisone", "status": "active", "category": "immunomodulator"}],
        )
    )

    return patients, encounters, observations, medication_requests, care_cases


def build_data() -> dict:
    rng = random.Random(SEED)
    patients, encounters, observations, medication_requests, care_cases = build_targets()
    d_patients, d_encounters, d_observations, d_medication_requests, d_care_cases = build_distractors(rng)
    patients.extend(d_patients)
    encounters.extend(d_encounters)
    observations.extend(d_observations)
    medication_requests.extend(d_medication_requests)
    care_cases.extend(d_care_cases)

    data = {
        "metadata": {
            "seed": SEED,
            "synthetic_clock": SYNTHETIC_CLOCK,
            "timezone": TIMEZONE,
            "generated_at": GENERATED_AT,
        },
        "protocols": protocol_cards(),
        "patients": sorted(patients, key=lambda item: item["patient_id"]),
        "encounters": sorted(encounters, key=lambda item: item["encounter_id"]),
        "observations": sorted(observations, key=lambda item: item["id"]),
        "medication_requests": sorted(medication_requests, key=lambda item: item["id"]),
        "care_cases": sorted(care_cases, key=lambda item: item["case_id"]),
    }
    return data


def build_manifest(data: dict) -> dict:
    target_ids = {
        "patients": [
            "PAT-H-T001",
            "PAT-R-T001",
            "PAT-K-T001",
            "PAT-L-T001",
            "PAT-CM-T001",
            "PAT-H-X001",
            "PAT-R-X001",
            "PAT-K-X001",
            "PAT-L-X001",
            "PAT-CM-X001",
        ],
        "encounters": ["ENC-H-T001", "ENC-R-T001", "ENC-H-X001", "ENC-R-X001"],
        "care_cases": ["CASE-CM-T001", "CASE-CM-X001"],
    }
    counts = {
        "protocols": len(data["protocols"]),
        "patients": len(data["patients"]),
        "encounters": len(data["encounters"]),
        "observations": len(data["observations"]),
        "medication_requests": len(data["medication_requests"]),
        "care_cases": len(data["care_cases"]),
    }
    distractor_count = counts["patients"] - len(target_ids["patients"])
    return {
        "seed": SEED,
        "synthetic_clock": SYNTHETIC_CLOCK,
        "timezone": TIMEZONE,
        "counts": counts,
        "target_ids": target_ids,
        "distractor_patient_count": distractor_count,
        "notes": [
            "Manifest is for construction and calibration only.",
            "The HTTP API does not label train/test cases or expose answers.",
        ],
    }


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = build_data()
    manifest = build_manifest(data)
    CLINIC_DATA_PATH.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "Generated clinic_data.json with "
        f"{manifest['counts']['patients']} patients, "
        f"{manifest['counts']['encounters']} encounters, "
        f"{manifest['counts']['observations']} observations."
    )
    print(f"Seed: {SEED}")


if __name__ == "__main__":
    main()
