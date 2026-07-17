#!/usr/bin/env python3
"""Generate deterministic shared EHR/referral records for task_group_015."""

from __future__ import annotations

import hashlib
import json
import random
from datetime import date, timedelta
from pathlib import Path


SEED = 15015
DATA_DIR = Path(__file__).resolve().parent / "data"
RECORDS_PATH = DATA_DIR / "records.json"
MANIFEST_PATH = DATA_DIR / "manifest.json"


def iso(days_after: int) -> str:
    return (date(2026, 1, 1) + timedelta(days=days_after)).isoformat()


def stable_id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha1(value.encode()).hexdigest()[:8].upper()}"


def patient_record(
    patient_id: str,
    given: str,
    family: str,
    dob: str,
    sex: str,
    mrn: str,
    phone: str,
    address: str,
    insurance_id: str,
    pcp_id: str,
    status: str = "active",
    canonical_patient_id: str | None = None,
    suffix: str | None = None,
) -> dict:
    return {
        "patient_id": patient_id,
        "given_name": given,
        "family_name": family,
        "suffix": suffix,
        "display_name": " ".join(x for x in [given, family, suffix] if x),
        "dob": dob,
        "sex": sex,
        "enterprise_mrn": mrn,
        "phone": phone,
        "address": address,
        "insurance_id": insurance_id,
        "primary_care_provider_id": pcp_id,
        "canonical_status": status,
        "canonical_patient_id": canonical_patient_id,
    }


def item_id(prefix: str, patient_id: str, label: str) -> str:
    return stable_id(prefix, f"{patient_id}:{label}")


def clinical_item(
    patient_id: str, code: str, description: str, status: str, onset: str, source: str, key: str
) -> dict:
    return {
        "id": item_id("COND", patient_id, f"{code}:{onset}:{source}"),
        "patient_id": patient_id,
        "code": code,
        "description": description,
        "status": status,
        "onset_date": onset,
        "source": source,
        "normalized_key": key,
    }


def medication(
    patient_id: str, name: str, dose: str, route: str, frequency: str, status: str, source: str, key: str
) -> dict:
    return {
        "id": item_id("MED", patient_id, f"{name}:{dose}:{source}"),
        "patient_id": patient_id,
        "medication": name,
        "dose": dose,
        "route": route,
        "frequency": frequency,
        "status": status,
        "source": source,
        "normalized_key": key,
    }


def allergy(patient_id: str, allergen: str, reaction: str, severity: str, status: str, source: str, key: str) -> dict:
    return {
        "id": item_id("ALG", patient_id, f"{allergen}:{reaction}:{source}"),
        "patient_id": patient_id,
        "allergen": allergen,
        "reaction": reaction,
        "severity": severity,
        "status": status,
        "source": source,
        "normalized_key": key,
    }


def provider_records() -> list[dict]:
    return [
        {
            "provider_id": "PRV-PCP-001",
            "name": "Dr. Alina Chow",
            "role": "Primary Care",
            "service_line": "primary_care",
            "facility": "Harborview Primary Care",
            "phone": "555-410-1001",
            "fax": "555-410-1099",
        },
        {
            "provider_id": "PRV-PCP-002",
            "name": "Dr. Marcus Hale",
            "role": "Primary Care",
            "service_line": "primary_care",
            "facility": "Eastlake Family Medicine",
            "phone": "555-410-1002",
            "fax": "555-410-2099",
        },
        {
            "provider_id": "PRV-ORTHO-010",
            "name": "Dr. Priya Nair",
            "role": "Orthopedic Surgeon",
            "service_line": "orthopedics",
            "facility": "Cedar Orthopedic Institute",
            "phone": "555-420-1010",
            "fax": "555-420-1199",
        },
        {
            "provider_id": "PRV-ORTHO-011",
            "name": "Dr. Victor Huang",
            "role": "Orthopedic Surgeon",
            "service_line": "orthopedics",
            "facility": "Cedar Orthopedic Institute",
            "phone": "555-420-1011",
            "fax": "555-420-1299",
        },
        {
            "provider_id": "PRV-CARD-020",
            "name": "Dr. Renee Okafor",
            "role": "Cardiologist",
            "service_line": "cardiology",
            "facility": "Summit Heart Center",
            "phone": "555-430-2020",
            "fax": "555-430-2299",
        },
        {
            "provider_id": "PRV-PULM-030",
            "name": "Dr. Leo Navarro",
            "role": "Pulmonologist",
            "service_line": "pulmonology",
            "facility": "Northgate Pulmonary Clinic",
            "phone": "555-440-3030",
            "fax": "555-440-3399",
        },
        {
            "provider_id": "PRV-NEURO-040",
            "name": "Dr. Hannah Stern",
            "role": "Neurologist",
            "service_line": "neurology",
            "facility": "Lakeside Neurology",
            "phone": "555-450-4040",
            "fax": "555-450-4499",
        },
        {
            "provider_id": "PRV-SNF-050",
            "name": "Kelsey Morgan, RN",
            "role": "SNF Intake Coordinator",
            "service_line": "skilled_nursing",
            "facility": "Meadowbrook Skilled Nursing",
            "phone": "555-460-5050",
            "fax": "555-460-5599",
        },
        {
            "provider_id": "PRV-ONC-060",
            "name": "Dr. Isabel Becker",
            "role": "Oncologist",
            "service_line": "oncology",
            "facility": "Evergreen Oncology",
            "phone": "555-470-6060",
            "fax": "555-470-6699",
        },
    ]


def code_records() -> tuple[list[dict], list[dict]]:
    icd10 = [
        ("E11.9", "Endocrine", False, ["type 2 diabetes", "diabetes"]),
        ("G20.A1", "Nervous system", False, ["parkinson", "parkinsonism"]),
        ("I10", "Circulatory", False, ["hypertension"]),
        ("I25.10", "Circulatory", False, ["coronary artery disease", "cad"]),
        ("I50.32", "Circulatory", False, ["chronic diastolic heart failure", "heart failure"]),
        ("J44.9", "Respiratory", False, ["copd", "chronic obstructive pulmonary disease"]),
        ("J45.40", "Respiratory", False, ["moderate persistent asthma", "asthma"]),
        ("M16.11", "Musculoskeletal", True, ["right hip osteoarthritis", "right hip"]),
        ("M16.12", "Musculoskeletal", True, ["left hip osteoarthritis", "left hip"]),
        ("M17.11", "Musculoskeletal", True, ["right knee osteoarthritis", "right knee"]),
        ("M17.12", "Musculoskeletal", True, ["left knee osteoarthritis", "left knee"]),
        ("M25.561", "Musculoskeletal", True, ["right knee pain"]),
        ("M25.562", "Musculoskeletal", True, ["left knee pain"]),
        ("M54.16", "Musculoskeletal", False, ["lumbar radiculopathy"]),
        ("R06.02", "Symptoms", False, ["shortness of breath", "dyspnea"]),
        ("R41.3", "Symptoms", False, ["memory loss", "cognitive impairment"]),
        ("S83.241A", "Injury", True, ["right medial meniscus tear"]),
        ("S83.242A", "Injury", True, ["left medial meniscus tear"]),
        ("Z01.818", "Factors influencing health status", False, ["pre-operative examination", "preop"]),
        ("C34.91", "Neoplasms", True, ["malignant neoplasm right lung", "right lung cancer"]),
    ]
    icd = [
        {"code": c, "chapter": ch, "requires_laterality": laterality, "expected_terms": terms}
        for c, ch, laterality, terms in icd10
    ]
    services = [
        ("CARD-CONSULT", "Cardiology consultation", "cardiology", "consultation"),
        ("ORTHO-CONSULT", "Orthopedic surgery consultation", "orthopedics", "consultation"),
        ("PULM-CONSULT", "Pulmonology consultation", "pulmonology", "consultation"),
        ("NEURO-CONSULT", "Neurology consultation", "neurology", "consultation"),
        ("SNF-HANDOFF", "Skilled nursing transition packet", "skilled_nursing", "handoff"),
        ("ONC-CONSULT", "Oncology co-management consultation", "oncology", "consultation"),
    ]
    svc = [
        {"code": c, "display": d, "service_line": line, "order_kind": kind, "active": True}
        for c, d, line, kind in services
    ]
    return icd, svc


def focal_patients() -> list[dict]:
    return [
        patient_record(
            "P-31014",
            "Samuel",
            "Rivera",
            "1958-04-12",
            "M",
            "E10031014",
            "555-201-3014",
            "14 Alder St, Seattle, WA",
            "INS-771900",
            "PRV-PCP-001",
        ),
        patient_record(
            "P-88420",
            "Sam",
            "Rivera",
            "1958-04-12",
            "M",
            "E10088420",
            "555-201-3014",
            "14 Alder Street, Seattle, WA",
            "INS-771900",
            "PRV-PCP-001",
            "duplicate",
            "P-31014",
        ),
        patient_record(
            "P-20177",
            "Marisol",
            "Kim",
            "1966-11-03",
            "F",
            "E10020177",
            "555-202-0177",
            "88 Union Ave, Tacoma, WA",
            "INS-234510",
            "PRV-PCP-002",
        ),
        patient_record(
            "P-44702",
            "Thomas",
            "Bennett",
            "1949-02-27",
            "M",
            "E10044702",
            "555-204-4702",
            "220 Pine Rd, Bellevue, WA",
            "INS-552812",
            "PRV-PCP-001",
        ),
        patient_record(
            "P-55218",
            "Nadia",
            "Patel",
            "1975-07-19",
            "F",
            "E10055218",
            "555-205-5218",
            "415 Hillcrest Way, Renton, WA",
            "INS-881144",
            "PRV-PCP-002",
        ),
        patient_record(
            "P-55281",
            "Nadine",
            "Patel",
            "1975-07-19",
            "F",
            "E10055281",
            "555-205-9281",
            "415 Hillcrest Wy, Renton, WA",
            "INS-881144",
            "PRV-PCP-002",
            "possible_duplicate",
            None,
        ),
        patient_record(
            "P-73008",
            "Eleanor",
            "Watkins",
            "1944-09-08",
            "F",
            "E10073008",
            "555-207-3008",
            "7 Madrona Ln, Olympia, WA",
            "INS-663020",
            "PRV-PCP-001",
            suffix="Jr",
        ),
        patient_record(
            "P-11964",
            "Ellen",
            "Watkins",
            "1944-09-08",
            "F",
            "E10011964",
            "555-207-3008",
            "7 Madrona Lane, Olympia, WA",
            "INS-663020",
            "PRV-PCP-001",
            "duplicate",
            "P-73008",
        ),
        patient_record(
            "P-66591",
            "Darius",
            "Cole",
            "1960-05-30",
            "M",
            "E10066591",
            "555-206-6591",
            "91 Harbor Pl, Kent, WA",
            "INS-441290",
            "PRV-PCP-002",
        ),
        patient_record(
            "P-50831",
            "Helena",
            "Ortiz",
            "1937-01-18",
            "F",
            "E10050831",
            "555-205-0831",
            "303 Lakeview Dr, Everett, WA",
            "INS-901245",
            "PRV-PCP-001",
        ),
        patient_record(
            "P-91804",
            "Owen",
            "Mercer",
            "1970-12-06",
            "M",
            "E10091804",
            "555-209-1804",
            "612 Ravenna Blvd, Seattle, WA",
            "INS-779013",
            "PRV-PCP-002",
        ),
    ]


def build_distractor_patients(rng: random.Random, count: int) -> list[dict]:
    given = [
        "Alice",
        "Brian",
        "Carmen",
        "Devon",
        "Elise",
        "Frank",
        "Grace",
        "Iris",
        "Jonas",
        "Lena",
        "Mason",
        "Noor",
        "Paula",
        "Quinn",
        "Rosa",
        "Silas",
        "Tara",
        "Uma",
        "Vera",
        "Wesley",
    ]
    family = [
        "Adams",
        "Brooks",
        "Chen",
        "Diaz",
        "Evans",
        "Foster",
        "Garcia",
        "Howard",
        "Ito",
        "Jones",
        "Klein",
        "Lopez",
        "Miller",
        "Nguyen",
        "Price",
        "Reed",
        "Shah",
        "Turner",
        "Voss",
        "Young",
    ]
    rows = []
    for i in range(count):
        pid = f"P-{40000 + i * 137 + rng.randint(0, 88):05d}"
        g = given[i % len(given)]
        f = family[(i * 3) % len(family)]
        dob = f"{rng.randint(1935, 1987)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
        rows.append(
            patient_record(
                pid,
                g,
                f,
                dob,
                rng.choice(["F", "M"]),
                f"E9{i:07d}",
                f"555-29{i:03d}",
                f"{100 + i} Clinic View Rd, Seattle, WA",
                f"INS-{rng.randint(200000, 999999)}",
                rng.choice(["PRV-PCP-001", "PRV-PCP-002"]),
            )
        )
    rows[5]["insurance_id"] = "INS-663020"
    rows[6]["family_name"] = "Watkins"
    rows[6]["display_name"] = f"{rows[6]['given_name']} Watkins"
    return rows


def add_patient_baseline(data: dict, patient: dict, rng: random.Random) -> None:
    pid = patient["patient_id"]
    chronic = [
        ("I10", "Essential hypertension", "hypertension"),
        ("E11.9", "Type 2 diabetes mellitus without complications", "diabetes_type_2"),
        ("M17.11", "Unilateral primary osteoarthritis, right knee", "right_knee_oa"),
        ("J44.9", "Chronic obstructive pulmonary disease, unspecified", "copd"),
    ]
    for code, desc, key in rng.sample(chronic, k=2):
        data["conditions"].append(
            clinical_item(pid, code, desc, "active", iso(rng.randint(-1600, -200)), "problem_list", key)
        )
    data["medications"].append(
        medication(
            pid,
            rng.choice(["lisinopril", "metformin", "atorvastatin", "albuterol inhaler"]),
            rng.choice(["5 mg", "10 mg", "500 mg", "2 puffs"]),
            rng.choice(["oral", "inhaled"]),
            rng.choice(["daily", "twice daily", "as needed"]),
            "active",
            "medication_reconciliation",
            "baseline_med",
        )
    )
    if rng.random() < 0.35:
        data["allergies"].append(
            allergy(
                pid,
                rng.choice(["penicillin", "sulfa", "latex"]),
                rng.choice(["rash", "hives", "wheezing"]),
                rng.choice(["mild", "moderate"]),
                "active",
                "patient_reported",
                "baseline_allergy",
            )
        )
    for n in range(3):
        data["encounters"].append(
            {
                "encounter_id": item_id("ENC", pid, str(n)),
                "patient_id": pid,
                "date": iso(rng.randint(0, 100)),
                "type": rng.choice(["office_visit", "telehealth", "urgent_care"]),
                "provider_id": patient["primary_care_provider_id"],
                "diagnoses": rng.sample([x["code"] for x in data["icd10"]], k=2),
                "medications_mentioned": [],
                "care_plan_notes": rng.choice(
                    ["continue current therapy", "follow up in 3 months", "referred for specialty evaluation"]
                ),
                "signed_status": rng.choice(["signed", "signed", "amended"]),
            }
        )
    data["immunizations"].append(
        {
            "id": item_id("IMM", pid, "flu"),
            "patient_id": pid,
            "vaccine": "influenza high-dose",
            "date": iso(rng.randint(10, 80)),
        }
    )
    data["documents"].append(
        {
            "document_id": item_id("DOC", pid, "summary"),
            "patient_id": pid,
            "type": "chart_summary",
            "date": iso(rng.randint(20, 95)),
            "status": "final",
            "source": "ehr_export",
        }
    )


def add_focal_clinical_data(data: dict) -> None:
    c = data["conditions"]
    m = data["medications"]
    a = data["allergies"]
    e = data["encounters"]
    imm = data["immunizations"]
    docs = data["documents"]
    disc = data["disclosures"]
    audit = data["audit_logs"]
    sr = data["service_requests"]

    for pid in ["P-31014", "P-88420"]:
        c.append(
            clinical_item(pid, "I10", "Essential hypertension", "active", "2017-05-02", "problem_list", "hypertension")
        )
    c += [
        clinical_item(
            "P-31014",
            "E11.9",
            "Type 2 diabetes mellitus without complications",
            "active",
            "2019-08-16",
            "pcp_note",
            "diabetes_type_2",
        ),
        clinical_item(
            "P-88420",
            "I25.10",
            "Coronary artery disease without angina",
            "active",
            "2024-10-09",
            "cardiology_import",
            "coronary_artery_disease",
        ),
        clinical_item(
            "P-88420", "M17.12", "Left knee osteoarthritis", "inactive", "2021-04-03", "legacy_import", "left_knee_oa"
        ),
    ]
    m += [
        medication(
            "P-31014", "metformin", "500 mg", "oral", "twice daily", "active", "medication_reconciliation", "metformin"
        ),
        medication("P-88420", "aspirin", "81 mg", "oral", "daily", "active", "cardiology_import", "aspirin"),
        medication("P-88420", "naproxen", "250 mg", "oral", "twice daily", "inactive", "legacy_import", "naproxen"),
    ]
    a += [
        allergy("P-31014", "penicillin", "hives", "moderate", "active", "patient_reported", "penicillin"),
        allergy(
            "P-88420", "iodinated contrast", "wheezing", "severe", "active", "cardiology_import", "iodinated_contrast"
        ),
    ]
    docs += [
        {
            "document_id": "DOC-MERGE-TR-001-A",
            "patient_id": "P-31014",
            "type": "identity_verification",
            "date": "2026-02-03",
            "status": "final",
            "source": "registration",
        },
        {
            "document_id": "DOC-CARD-TR-001",
            "patient_id": "P-88420",
            "type": "external_cardiology_note",
            "date": "2026-01-18",
            "status": "final",
            "source": "summit_heart_center",
        },
    ]
    audit += [
        {
            "audit_id": "AUD-TR-001-A",
            "patient_id": "P-31014",
            "event": "identity_review",
            "date": "2026-02-05",
            "actor": "ehr_quality",
            "summary": "Matched phone, DOB, insurer, and cardiology import from P-88420.",
        },
        {
            "audit_id": "AUD-TR-001-B",
            "patient_id": "P-88420",
            "event": "external_import",
            "date": "2026-01-20",
            "actor": "interface_engine",
            "summary": "Cardiology continuity document added to possible duplicate shell.",
        },
    ]

    c += [
        clinical_item(
            "P-20177",
            "I50.32",
            "Chronic diastolic heart failure",
            "active",
            "2024-09-01",
            "problem_list",
            "heart_failure_diastolic",
        ),
        clinical_item(
            "P-20177", "I10", "Essential hypertension", "active", "2018-06-14", "problem_list", "hypertension"
        ),
        clinical_item(
            "P-20177", "R06.02", "Shortness of breath", "active", "2026-02-09", "referral_intake", "dyspnea"
        ),
    ]
    m += [
        medication("P-20177", "furosemide", "20 mg", "oral", "daily", "active", "cardiology_med_list", "furosemide"),
        medication("P-20177", "lisinopril", "10 mg", "oral", "daily", "active", "pcp_note", "lisinopril"),
    ]
    a.append(
        allergy("P-20177", "sulfa antibiotics", "rash", "moderate", "active", "referral_form", "sulfa_antibiotics")
    )
    e += [
        {
            "encounter_id": "ENC-20177-20260211",
            "patient_id": "P-20177",
            "date": "2026-02-11",
            "type": "office_visit",
            "provider_id": "PRV-PCP-002",
            "diagnoses": ["I50.32", "R06.02"],
            "medications_mentioned": ["furosemide"],
            "care_plan_notes": "cardiology referral for exertional dyspnea and HFpEF review",
            "signed_status": "signed",
        },
        {
            "encounter_id": "ENC-20177-20260118",
            "patient_id": "P-20177",
            "date": "2026-01-18",
            "type": "telephone",
            "provider_id": "PRV-PCP-002",
            "diagnoses": ["I10"],
            "medications_mentioned": ["lisinopril"],
            "care_plan_notes": "blood pressure log reviewed",
            "signed_status": "signed",
        },
    ]
    docs.append(
        {
            "document_id": "DOC-ECHO-20177",
            "patient_id": "P-20177",
            "type": "echocardiogram",
            "date": "2025-11-12",
            "status": "final",
            "source": "imaging_archive",
        }
    )

    c += [
        clinical_item(
            "P-44702", "M16.11", "Right hip osteoarthritis", "active", "2022-03-04", "orthopedics", "right_hip_oa"
        ),
        clinical_item(
            "P-44702",
            "E11.9",
            "Type 2 diabetes mellitus without complications",
            "active",
            "2016-11-20",
            "problem_list",
            "diabetes_type_2",
        ),
        clinical_item(
            "P-44702", "R41.3", "Memory loss", "active", "2025-12-01", "geriatric_assessment", "memory_loss"
        ),
    ]
    m += [
        medication(
            "P-44702",
            "insulin glargine",
            "12 units",
            "subcutaneous",
            "nightly",
            "active",
            "med_rec",
            "insulin_glargine",
        ),
        medication(
            "P-44702",
            "acetaminophen",
            "650 mg",
            "oral",
            "every 8 hours as needed",
            "active",
            "orthopedics",
            "acetaminophen",
        ),
    ]
    a.append(allergy("P-44702", "latex", "contact dermatitis", "mild", "active", "patient_reported", "latex"))
    for idx, day in enumerate(["2026-03-01", "2026-02-14", "2026-01-29", "2026-01-02", "2025-10-10"]):
        e.append(
            {
                "encounter_id": f"ENC-44702-{idx}",
                "patient_id": "P-44702",
                "date": day,
                "type": "care_transition" if idx == 0 else "office_visit",
                "provider_id": "PRV-PCP-001",
                "diagnoses": ["M16.11", "E11.9"],
                "medications_mentioned": ["insulin glargine", "acetaminophen"],
                "care_plan_notes": "orthopedic surgery packet requires glucose plan and fall-risk note"
                if idx == 0
                else "stable chronic care follow-up",
                "signed_status": "signed",
            }
        )
    imm += [
        {"id": "IMM-44702-FLU", "patient_id": "P-44702", "vaccine": "influenza high-dose", "date": "2025-10-02"},
        {"id": "IMM-44702-COVID", "patient_id": "P-44702", "vaccine": "COVID-19 booster", "date": "2025-09-14"},
    ]
    disc.append(
        {
            "disclosure_id": "DISC-44702-ORTHO",
            "patient_id": "P-44702",
            "recipient": "Cedar Orthopedic Institute",
            "recipient_provider_id": "PRV-ORTHO-010",
            "purpose": "surgical handoff",
            "date": "2026-03-02",
            "status": "permitted",
        }
    )

    c += [
        clinical_item(
            "P-55218", "M17.11", "Right knee osteoarthritis", "active", "2023-05-07", "problem_list", "right_knee_oa"
        ),
        clinical_item(
            "P-55218",
            "S83.241A",
            "Right medial meniscus tear",
            "active",
            "2026-02-28",
            "mri_report",
            "right_medial_meniscus_tear",
        ),
        clinical_item(
            "P-55281", "M17.12", "Left knee osteoarthritis", "active", "2023-05-07", "external_note", "left_knee_oa"
        ),
    ]
    sr.append(
        {
            "service_request_id": "SR-TR-004",
            "patient_id": "P-55218",
            "status": "draft",
            "intent": "order",
            "priority": "routine",
            "service_code": "ORTHO-CONSULT",
            "authored_on": "2026-03-04",
            "occurrence_date": "2026-03-20",
            "requester_id": "PRV-PCP-002",
            "performer_id": "PRV-ORTHO-011",
            "reason_codes": ["M17.11", "S83.241A"],
            "sbar": {
                "situation": "Right knee pain after twisting injury.",
                "background": "Known right knee OA with new MRI report.",
                "assessment": "Possible medial meniscus tear with functional limitation.",
                "recommendation": "Orthopedic consultation for treatment options.",
            },
        }
    )

    c += [
        clinical_item(
            "P-73008", "I10", "Essential hypertension", "active", "2015-01-04", "problem_list", "hypertension"
        ),
        clinical_item(
            "P-11964",
            "J44.9",
            "Chronic obstructive pulmonary disease",
            "active",
            "2024-08-12",
            "pulmonary_import",
            "copd",
        ),
        clinical_item(
            "P-11964", "M17.11", "Right knee osteoarthritis", "inactive", "2020-05-01", "legacy_note", "right_knee_oa"
        ),
    ]
    m += [
        medication("P-73008", "amlodipine", "5 mg", "oral", "daily", "active", "pcp_note", "amlodipine"),
        medication("P-11964", "tiotropium", "18 mcg", "inhaled", "daily", "active", "pulmonary_import", "tiotropium"),
        medication("P-11964", "prednisone", "20 mg", "oral", "daily", "inactive", "legacy_note", "prednisone"),
    ]
    a += [
        allergy("P-73008", "codeine", "nausea", "moderate", "active", "patient_reported", "codeine"),
        allergy("P-11964", "shellfish", "anaphylaxis", "severe", "active", "pulmonary_import", "shellfish"),
    ]
    audit += [
        {
            "audit_id": "AUD-TE-001-A",
            "patient_id": "P-73008",
            "event": "identity_review",
            "date": "2026-04-12",
            "actor": "ehr_quality",
            "summary": "Duplicate review opened for P-73008 and P-11964; suffix and nickname discrepancy noted.",
        },
        {
            "audit_id": "AUD-OTHER-MERGE",
            "patient_id": "P-73008",
            "event": "merge_completed",
            "date": "2026-04-10",
            "actor": "ehr_quality",
            "summary": "Unrelated merge with historical pediatric chart P-73080 completed.",
        },
    ]
    docs.append(
        {
            "document_id": "DOC-PULM-11964",
            "patient_id": "P-11964",
            "type": "external_pulmonology_note",
            "date": "2026-03-25",
            "status": "final",
            "source": "northgate_pulmonary",
        }
    )

    c += [
        clinical_item(
            "P-66591", "J44.9", "Chronic obstructive pulmonary disease", "active", "2018-04-10", "problem_list", "copd"
        ),
        clinical_item(
            "P-66591",
            "J45.40",
            "Moderate persistent asthma",
            "active",
            "2023-09-13",
            "pulmonary_note",
            "asthma_moderate_persistent",
        ),
        clinical_item(
            "P-66591", "R06.02", "Shortness of breath", "active", "2026-04-05", "referral_intake", "dyspnea"
        ),
    ]
    m += [
        medication(
            "P-66591",
            "fluticasone/salmeterol",
            "250/50 mcg",
            "inhaled",
            "twice daily",
            "active",
            "med_rec",
            "fluticasone_salmeterol",
        ),
        medication(
            "P-66591", "albuterol inhaler", "2 puffs", "inhaled", "as needed", "active", "med_rec", "albuterol"
        ),
    ]
    a.append(allergy("P-66591", "levofloxacin", "tendon pain", "moderate", "active", "referral_form", "levofloxacin"))
    e.append(
        {
            "encounter_id": "ENC-66591-20260406",
            "patient_id": "P-66591",
            "date": "2026-04-06",
            "type": "office_visit",
            "provider_id": "PRV-PCP-002",
            "diagnoses": ["J44.9", "R06.02"],
            "medications_mentioned": ["fluticasone/salmeterol", "albuterol inhaler"],
            "care_plan_notes": "pulmonology referral; spirometry result not found in chart",
            "signed_status": "signed",
        }
    )
    docs.append(
        {
            "document_id": "DOC-CXR-66591",
            "patient_id": "P-66591",
            "type": "chest_xray",
            "date": "2026-03-30",
            "status": "final",
            "source": "imaging_archive",
        }
    )

    c += [
        clinical_item(
            "P-50831",
            "I50.32",
            "Chronic diastolic heart failure",
            "active",
            "2021-06-09",
            "problem_list",
            "heart_failure_diastolic",
        ),
        clinical_item("P-50831", "R41.3", "Memory loss", "active", "2025-08-22", "geriatrics", "memory_loss"),
        clinical_item(
            "P-50831", "M54.16", "Lumbar radiculopathy", "active", "2025-11-15", "problem_list", "lumbar_radiculopathy"
        ),
    ]
    m += [
        medication("P-50831", "donepezil", "5 mg", "oral", "nightly", "active", "geriatrics", "donepezil"),
        medication("P-50831", "furosemide", "20 mg", "oral", "daily", "active", "cardiology", "furosemide"),
    ]
    for idx, day in enumerate(["2026-04-18", "2026-04-14", "2026-04-08", "2026-03-29", "2026-03-22", "2025-12-31"]):
        e.append(
            {
                "encounter_id": f"ENC-50831-{idx}",
                "patient_id": "P-50831",
                "date": day,
                "type": "care_transition" if idx == 0 else "office_visit",
                "provider_id": "PRV-PCP-001",
                "diagnoses": ["I50.32", "R41.3"],
                "medications_mentioned": ["donepezil", "furosemide"],
                "care_plan_notes": "SNF packet: walker required, medication supervision, mild cognitive impairment"
                if idx < 2
                else "routine follow-up",
                "signed_status": "signed",
            }
        )
    imm.append(
        {"id": "IMM-50831-FLU", "patient_id": "P-50831", "vaccine": "influenza high-dose", "date": "2025-10-18"}
    )
    disc.append(
        {
            "disclosure_id": "DISC-50831-SNF",
            "patient_id": "P-50831",
            "recipient": "Meadowbrook Skilled Nursing",
            "recipient_provider_id": "PRV-SNF-050",
            "purpose": "post-acute care transition",
            "date": "2026-04-18",
            "status": "permitted",
        }
    )

    c += [
        clinical_item(
            "P-91804",
            "G20.A1",
            "Parkinson disease without dyskinesia",
            "active",
            "2025-07-08",
            "neurology_screen",
            "parkinson_disease",
        ),
        clinical_item("P-91804", "R41.3", "Memory loss", "active", "2026-03-28", "pcp_note", "memory_loss"),
    ]
    m.append(
        medication(
            "P-91804",
            "carbidopa/levodopa",
            "25/100 mg",
            "oral",
            "three times daily",
            "active",
            "med_rec",
            "carbidopa_levodopa",
        )
    )
    e.append(
        {
            "encounter_id": "ENC-91804-20260409",
            "patient_id": "P-91804",
            "date": "2026-04-09",
            "type": "office_visit",
            "provider_id": "PRV-PCP-002",
            "diagnoses": ["G20.A1", "R41.3"],
            "medications_mentioned": ["carbidopa/levodopa"],
            "care_plan_notes": "neurology referral requested for worsening tremor and gait freezing",
            "signed_status": "signed",
        }
    )
    sr.append(
        {
            "service_request_id": "SR-TE-004",
            "patient_id": "P-91804",
            "status": "draft",
            "intent": "order",
            "priority": "routine",
            "service_code": "NEURO-CONSULT",
            "authored_on": "2026-04-10",
            "occurrence_date": "2026-04-28",
            "requester_id": "PRV-PCP-002",
            "performer_id": "PRV-NEURO-040",
            "reason_codes": ["G20.A1", "R41.3"],
            "sbar": {
                "situation": "Progressive tremor and gait freezing.",
                "background": "Started carbidopa/levodopa after abnormal screen.",
                "assessment": "Possible Parkinson disease with cognitive concerns.",
                "recommendation": "Neurology evaluation and medication guidance.",
            },
        }
    )


def referral_row(
    referral_id: str,
    batch: str,
    patient_id: str,
    service_line: str,
    provider_id: str,
    code: str,
    narrative: str,
    urgency: str,
    status: str,
    docs: list[str],
    auth: str,
    note: str,
) -> dict:
    return {
        "referral_id": referral_id,
        "batch_id": batch,
        "patient_id": patient_id,
        "service_line": service_line,
        "receiving_provider_id": provider_id,
        "diagnosis_code": code,
        "diagnosis_narrative": narrative,
        "urgency": urgency,
        "status": status,
        "documents_received": docs,
        "authorization_status": auth,
        "requested_date": "2026-03-15" if "MAR26" in batch else "2026-04-15" if "APR26" in batch else "2026-02-15",
        "coordination_note": note,
    }


def add_referrals(data: dict, rng: random.Random) -> None:
    refs = data["referrals"]
    refs += [
        referral_row(
            "REF-FEB-CARD-007",
            "FEB26-CARD",
            "P-20177",
            "cardiology",
            "PRV-CARD-020",
            "I50.32",
            "HFpEF with exertional dyspnea",
            "routine",
            "open",
            ["echocardiogram", "office_note"],
            "approved",
            "confirm sulfa allergy details before letter",
        ),
        referral_row(
            "REF-APR-PULM-004",
            "APR26-PULM",
            "P-66591",
            "pulmonology",
            "PRV-PULM-030",
            "J44.9",
            "COPD with worsening dyspnea; spirometry missing",
            "urgent",
            "open",
            ["chest_xray", "office_note"],
            "pending",
            "needs spirometry and active allergy confirmation",
        ),
    ]
    ortho_codes = ["M17.11", "M17.12", "M16.11", "M16.12", "M25.561", "M25.562", "S83.241A", "S83.242A", "M54.16"]
    patient_ids = [p["patient_id"] for p in data["patients"] if p["patient_id"] not in {"P-88420", "P-11964"}]
    for i in range(18):
        pid = "P-55218" if i == 3 else patient_ids[(i * 2) % len(patient_ids)]
        code = rng.choice(ortho_codes)
        narrative = rng.choice(
            ["right knee pain", "left knee osteoarthritis", "hip arthritis", "lumbar radiculopathy", "meniscus tear"]
        )
        if i == 5:
            code = "J44.9"
            narrative = "right knee pain"
        if i == 8:
            code = "M17.12"
            narrative = "right knee osteoarthritis"
        docs = rng.sample(["office_note", "xray", "mri", "insurance_card"], k=rng.randint(1, 3))
        if i in {2, 9, 14}:
            docs = ["office_note"]
        auth = "approved" if i % 4 else "missing"
        urgency = "urgent" if i in {3, 8, 14} else "routine"
        refs.append(
            referral_row(
                f"REF-MAR-{i + 1:03d}",
                "MAR26-ORTHO-A",
                pid,
                "orthopedics",
                rng.choice(["PRV-ORTHO-010", "PRV-ORTHO-011"]),
                code,
                narrative,
                urgency,
                "open",
                docs,
                auth,
                rng.choice(
                    ["patient ready to schedule", "imaging pending", "clinical concern unresolved", "routine review"]
                ),
            )
        )
    refs.append(
        referral_row(
            "REF-MAR-019-DUP",
            "MAR26-ORTHO-A",
            "P-55218",
            "orthopedics",
            "PRV-ORTHO-011",
            "S83.241A",
            "right medial meniscus tear",
            "urgent",
            "open",
            ["office_note", "mri"],
            "approved",
            "duplicate resubmission from same clinic",
        )
    )
    for i in range(22):
        pid = "P-73008" if i == 4 else "P-50831" if i == 10 else patient_ids[(i * 3 + 7) % len(patient_ids)]
        code = rng.choice(ortho_codes + ["C34.91"])
        narrative = rng.choice(
            [
                "right knee osteoarthritis",
                "left knee pain",
                "right hip osteoarthritis",
                "back pain",
                "oncology co-management before joint injection",
            ]
        )
        if i == 6:
            code = "M17.11"
            narrative = "left knee osteoarthritis"
        if i == 11:
            code = "I25.10"
            narrative = "right knee pain"
        docs = rng.sample(
            ["office_note", "xray", "mri", "physical_therapy_note", "insurance_card"], k=rng.randint(1, 4)
        )
        if i in {1, 12, 19}:
            docs = ["insurance_card"]
        auth = "approved" if i % 5 not in {0, 2} else "pending" if i % 5 == 2 else "missing"
        urgency = "urgent" if i in {6, 10, 15} else "routine"
        refs.append(
            referral_row(
                f"REF-APR-{i + 1:03d}",
                "APR26-ORTHO-B",
                pid,
                "orthopedics",
                rng.choice(["PRV-ORTHO-010", "PRV-ORTHO-011"]),
                code,
                narrative,
                urgency,
                "open",
                docs,
                auth,
                rng.choice(
                    [
                        "requested delay by patient",
                        "clinical concern unresolved",
                        "routine review",
                        "authorization queue",
                    ]
                ),
            )
        )
    refs.append(
        referral_row(
            "REF-APR-023-DUP",
            "APR26-ORTHO-B",
            "P-73008",
            "orthopedics",
            "PRV-ORTHO-010",
            "M17.11",
            "right knee osteoarthritis",
            "routine",
            "open",
            ["office_note", "xray"],
            "approved",
            "same patient duplicate with changed referring physician",
        )
    )


def build_data() -> dict:
    rng = random.Random(SEED)
    icd10, service_codes = code_records()
    data = {
        "meta": {
            "seed": SEED,
            "version": "task_group_015_env_v1",
            "generated_on": "2026-07-17",
            "state_mode": "read_only",
        },
        "providers": provider_records(),
        "icd10": icd10,
        "service_codes": service_codes,
        "patients": focal_patients() + build_distractor_patients(rng, 38),
        "conditions": [],
        "medications": [],
        "allergies": [],
        "encounters": [],
        "immunizations": [],
        "documents": [],
        "disclosures": [],
        "service_requests": [],
        "audit_logs": [],
        "duplicate_candidates": [],
        "referrals": [],
    }
    for patient in data["patients"]:
        add_patient_baseline(data, patient, rng)
    add_focal_clinical_data(data)
    add_referrals(data, rng)
    data["duplicate_candidates"] = [
        {
            "candidate_id": "DUP-TR-001",
            "patient_ids": ["P-31014", "P-88420"],
            "status": "open",
            "match_signals": [
                "same_dob",
                "same_phone",
                "same_insurance",
                "name_variant",
                "shared_external_cardiology_document",
            ],
            "conflict_signals": ["address_abbreviation"],
            "merge_preview": {
                "preferred_target_patient_id": "P-31014",
                "source_patient_id": "P-88420",
                "active_condition_keys": ["coronary_artery_disease", "diabetes_type_2", "hypertension"],
                "active_medication_keys": ["aspirin", "metformin"],
                "active_allergy_keys": ["iodinated_contrast", "penicillin"],
            },
        },
        {
            "candidate_id": "DUP-TR-004",
            "patient_ids": ["P-55218", "P-55281"],
            "status": "needs_review",
            "match_signals": ["same_dob", "same_insurance", "similar_address"],
            "conflict_signals": ["different_given_name", "different_phone", "opposite_laterality_problem"],
            "merge_preview": {
                "preferred_target_patient_id": None,
                "source_patient_id": None,
                "active_condition_keys": ["right_knee_oa", "right_medial_meniscus_tear", "left_knee_oa"],
                "active_medication_keys": [],
                "active_allergy_keys": [],
            },
        },
        {
            "candidate_id": "DUP-TE-001",
            "patient_ids": ["P-73008", "P-11964"],
            "status": "open",
            "match_signals": ["same_dob", "same_phone", "same_insurance", "name_variant", "same_address_normalized"],
            "conflict_signals": ["suffix_discrepancy"],
            "merge_preview": {
                "preferred_target_patient_id": "P-73008",
                "source_patient_id": "P-11964",
                "active_condition_keys": ["copd", "hypertension"],
                "active_medication_keys": ["amlodipine", "tiotropium"],
                "active_allergy_keys": ["codeine", "shellfish"],
            },
        },
    ]
    return data


def manifest_for(data: dict) -> dict:
    counts = {k: len(v) for k, v in data.items() if isinstance(v, list)}
    focal = {
        "patients": [
            "P-31014",
            "P-88420",
            "P-20177",
            "P-44702",
            "P-55218",
            "P-73008",
            "P-11964",
            "P-66591",
            "P-50831",
            "P-91804",
        ],
        "duplicate_candidates": ["DUP-TR-001", "DUP-TR-004", "DUP-TE-001"],
        "referral_batches": ["FEB26-CARD", "APR26-PULM", "MAR26-ORTHO-A", "APR26-ORTHO-B"],
        "service_requests": ["SR-TR-004", "SR-TE-004"],
    }
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    return {
        "version": data["meta"]["version"],
        "seed": SEED,
        "generated_on": data["meta"]["generated_on"],
        "state_mode": data["meta"]["state_mode"],
        "record_counts": counts,
        "focal_ids": focal,
        "records_sha256": digest,
        "files": ["data/records.json", "data/manifest.json"],
    }


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = build_data()
    manifest = manifest_for(data)
    RECORDS_PATH.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {RECORDS_PATH}")
    print(f"wrote {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
