#!/usr/bin/env python3
import json
import random
from pathlib import Path


SEED = 15026
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"


def clinical_item(item_id, code, label, status="active", **extra):
    item = {"id": item_id, "code": code, "label": label, "status": status}
    item.update(extra)
    return item


def patient(patient_id, first, last, dob, mrn, **extra):
    base = {
        "patient_id": patient_id,
        "first_name": first,
        "last_name": last,
        "dob": dob,
        "enterprise_mrn": mrn,
        "phone": extra.pop("phone", "(555) 010-0000"),
        "email": extra.pop("email", f"{first.lower()}.{last.lower()}@example.test"),
        "address": extra.pop("address", "100 Clinic Way, Springfield, KS 66000"),
        "primary_provider_id": extra.pop("primary_provider_id", "PROV-001"),
        "problems": extra.pop("problems", []),
        "medications": extra.pop("medications", []),
        "allergies": extra.pop("allergies", []),
        "encounters": extra.pop("encounters", []),
        "immunizations": extra.pop("immunizations", []),
        "disclosures": extra.pop("disclosures", []),
        "documents": extra.pop("documents", []),
    }
    base.update(extra)
    return base


def referral(
    ref_id,
    batch_id,
    last,
    first,
    dob,
    insurance_provider,
    insurance_id,
    physician,
    practice,
    fax,
    code,
    diagnosis,
    urgency="Routine",
    records="Yes",
    imaging="Yes",
    auth_required="Yes",
    auth_status="Pending",
    scheduled="No",
    appt_date="",
    assigned="",
    notes="",
    reason="Orthopedic evaluation",
):
    return {
        "referral_id": ref_id,
        "batch_id": batch_id,
        "date_received": "2026-03-10" if "TR" in ref_id else "2026-04-10",
        "patient_last_name": last,
        "patient_first_name": first,
        "patient_dob": dob,
        "insurance_provider": insurance_provider,
        "insurance_id": insurance_id,
        "referring_physician": physician,
        "referring_practice": practice,
        "referring_fax": fax,
        "icd10_code": code,
        "diagnosis_description": diagnosis,
        "referral_reason": reason,
        "urgency": urgency,
        "records_received": records,
        "imaging_received": imaging,
        "auth_required": auth_required,
        "auth_status": auth_status,
        "appointment_scheduled": scheduled,
        "appointment_date": appt_date,
        "assigned_physician": assigned,
        "notes": notes,
    }


def build_codebook():
    rows = [
        ("M17.11", "Primary osteoarthritis, right knee", "M", "right", "knee"),
        ("M17.12", "Primary osteoarthritis, left knee", "M", "left", "knee"),
        ("M16.11", "Unilateral primary osteoarthritis, right hip", "M", "right", "hip"),
        ("M16.12", "Unilateral primary osteoarthritis, left hip", "M", "left", "hip"),
        ("M75.121", "Complete rotator cuff tear or rupture of right shoulder", "M", "right", "shoulder"),
        ("M75.122", "Complete rotator cuff tear or rupture of left shoulder", "M", "left", "shoulder"),
        ("M76.61", "Achilles tendinitis, right leg", "M", "right", "achilles"),
        ("M76.62", "Achilles tendinitis, left leg", "M", "left", "achilles"),
        ("M84.451A", "Pathological fracture, right femur, initial encounter", "M", "right", "femur"),
        ("M84.452A", "Pathological fracture, left femur, initial encounter", "M", "left", "femur"),
        ("M25.561", "Pain in right knee", "M", "right", "knee"),
        ("M25.562", "Pain in left knee", "M", "left", "knee"),
        ("M48.062", "Spinal stenosis, lumbar region with neurogenic claudication", "M", "", "spine"),
        ("M19.011", "Primary osteoarthritis, right shoulder", "M", "right", "shoulder"),
        ("M24.271", "Disorder of ligament, right ankle", "M", "right", "ankle"),
        ("M24.272", "Disorder of ligament, left ankle", "M", "left", "ankle"),
        ("M70.21", "Olecranon bursitis, right elbow", "M", "right", "elbow"),
        ("M70.22", "Olecranon bursitis, left elbow", "M", "left", "elbow"),
        ("M79.3", "Panniculitis, unspecified", "M", "", "soft tissue"),
        (
            "S82.001A",
            "Unspecified fracture of right patella, initial encounter for closed fracture",
            "S",
            "right",
            "patella",
        ),
        ("S83.512A", "Sprain of anterior cruciate ligament of left knee, initial encounter", "S", "left", "knee"),
        ("G89.29", "Other chronic pain", "G", "", "pain"),
        ("C79.51", "Secondary malignant neoplasm of bone", "C", "", "oncology"),
        ("I50.22", "Chronic systolic congestive heart failure", "I", "", "heart"),
        ("J44.9", "Chronic obstructive pulmonary disease, unspecified", "J", "", "lung"),
        ("N18.32", "Chronic kidney disease, stage 3b", "N", "", "kidney"),
    ]
    return [
        {
            "code": code,
            "description": desc,
            "chapter_prefix": chapter,
            "in_musculoskeletal_tracking_range": chapter == "M",
            "laterality": laterality,
            "body_site": body_site,
        }
        for code, desc, chapter, laterality, body_site in rows
    ]


def build_target_patients():
    return [
        patient(
            "PAT-TR-001A",
            "Amelia",
            "Navarro",
            "1968-04-14",
            "EHR-10234",
            phone="(555) 210-1130",
            address="19 Aspen Drive, Lawrence, KS 66044",
            problems=[
                clinical_item("PR-TR001-01", "J44.9", "Chronic obstructive pulmonary disease"),
                clinical_item("PR-TR001-02", "E11.9", "Type 2 diabetes mellitus"),
            ],
            medications=[
                clinical_item(
                    "MED-TR001-01", "RXN-6918", "Tiotropium 18 mcg inhalation capsule daily", dose="18 mcg daily"
                ),
                clinical_item("MED-TR001-02", "RXN-6809", "Metformin 500 mg tablet twice daily", dose="500 mg BID"),
            ],
            allergies=[
                clinical_item("ALG-TR001-01", "ALG-PEN", "Penicillin", reaction="Rash", severity="Moderate"),
            ],
            disclosures=[
                {
                    "id": "DISC-TR001-01",
                    "recipient": "Dr. Erin Mercer",
                    "purpose": "Care Coordination",
                    "date": "2026-03-01",
                    "status": "active",
                }
            ],
        ),
        patient(
            "PAT-TR-001B",
            "Amelia",
            "Navarro",
            "1968-04-14",
            "EHR-90882",
            phone="(555) 210-1130",
            address="19 Aspen Drive, Lawrence, KS 66044",
            problems=[clinical_item("PR-TR001-03", "J45.909", "Unspecified asthma, uncomplicated")],
            medications=[
                clinical_item("MED-TR001-03", "RXN-435", "Albuterol 90 mcg inhaler as needed", dose="2 puffs PRN")
            ],
            allergies=[
                clinical_item(
                    "ALG-TR001-02", "ALG-SULFA", "Sulfonamide antibiotics", reaction="Hives", severity="Moderate"
                )
            ],
        ),
        patient(
            "PAT-TE-001A",
            "Jonas",
            "Bellamy",
            "1959-08-22",
            "EHR-11840",
            phone="(555) 310-4410",
            address="244 North Oak Street, Topeka, KS 66603",
            problems=[
                clinical_item("PR-TE001-01", "N18.32", "Chronic kidney disease, stage 3b"),
                clinical_item("PR-TE001-02", "I10", "Essential hypertension"),
            ],
            medications=[clinical_item("MED-TE001-01", "RXN-29046", "Lisinopril 20 mg daily", dose="20 mg daily")],
            allergies=[
                clinical_item(
                    "ALG-TE001-01", "ALG-NSAID", "NSAIDs", reaction="Renal function decline", severity="Severe"
                )
            ],
            disclosures=[
                {
                    "id": "DISC-TE001-01",
                    "recipient": "Dr. Noura Haddad",
                    "purpose": "Nephrology consult",
                    "date": "2026-04-02",
                    "status": "active",
                }
            ],
        ),
        patient(
            "PAT-TE-001B",
            "Jonas",
            "Bellamy",
            "1959-08-22",
            "EHR-93221",
            phone="(555) 310-4410",
            address="911 Elm Terrace, Topeka, KS 66603",
            problems=[
                clinical_item("PR-TE001-03", "E11.22", "Type 2 diabetes mellitus with diabetic chronic kidney disease")
            ],
            medications=[
                clinical_item(
                    "MED-TE001-02", "RXN-274783", "Insulin glargine 18 units nightly", dose="18 units nightly"
                )
            ],
            allergies=[
                clinical_item(
                    "ALG-TE001-02",
                    "ALG-CONTRAST",
                    "Iodinated contrast media",
                    reaction="Acute kidney injury after exposure",
                    severity="Severe",
                ),
                clinical_item(
                    "ALG-TE001-03",
                    "ALG-SHELL",
                    "Shellfish",
                    status="inactive",
                    reaction="Historical nausea",
                    severity="Mild",
                ),
            ],
            disclosures=[
                {
                    "id": "DISC-TE001-02",
                    "recipient": "County Records Request",
                    "purpose": "Address verification",
                    "date": "2025-11-14",
                    "status": "expired",
                }
            ],
        ),
        patient(
            "PAT-TR-003",
            "Marisol",
            "Keene",
            "1947-02-19",
            "EHR-23003",
            problems=[
                clinical_item("PR-TR003-01", "I50.22", "Chronic systolic heart failure"),
                clinical_item("PR-TR003-02", "J44.9", "Chronic obstructive pulmonary disease"),
                clinical_item("PR-TR003-03", "I48.91", "Atrial fibrillation"),
                clinical_item("PR-TR003-04", "M54.50", "Low back pain", status="inactive"),
            ],
            medications=[
                clinical_item("MED-TR003-01", "RXN-4603", "Furosemide 40 mg daily", dose="40 mg daily"),
                clinical_item("MED-TR003-02", "RXN-35208", "Apixaban 5 mg twice daily", dose="5 mg BID"),
            ],
            allergies=[
                clinical_item("ALG-TR003-01", "ALG-ACE", "ACE inhibitors", reaction="Angioedema", severity="Severe")
            ],
            encounters=[
                {
                    "id": "ENC-TR003-01",
                    "date": "2026-05-29",
                    "diagnoses": ["I50.22"],
                    "care_plan": "Adjust diuretic and monitor weight trend.",
                },
                {
                    "id": "ENC-TR003-02",
                    "date": "2026-05-17",
                    "diagnoses": ["J44.9"],
                    "care_plan": "Continue inhaler regimen; review oxygen saturation log.",
                },
                {
                    "id": "ENC-TR003-03",
                    "date": "2026-04-28",
                    "diagnoses": ["I48.91"],
                    "care_plan": "Continue anticoagulation; fall precautions.",
                },
                {
                    "id": "ENC-TR003-04",
                    "date": "2026-04-10",
                    "diagnoses": ["I50.22", "J44.9"],
                    "care_plan": "Home health nurse follow-up.",
                },
                {
                    "id": "ENC-TR003-05",
                    "date": "2025-11-12",
                    "diagnoses": ["M54.50"],
                    "care_plan": "Resolved back strain.",
                },
            ],
            immunizations=[
                {"id": "IMM-TR003-01", "name": "Pneumococcal conjugate PCV20", "date": "2024-09-18"},
                {"id": "IMM-TR003-02", "name": "Influenza high-dose", "date": "2025-10-04"},
            ],
            disclosures=[
                {
                    "id": "DISC-TR003-01",
                    "recipient": "Lakeside Skilled Nursing",
                    "purpose": "Care Transition",
                    "date": "2026-05-30",
                    "status": "active",
                }
            ],
        ),
        patient(
            "PAT-TE-003",
            "Helena",
            "Rowe",
            "1952-12-03",
            "EHR-24014",
            problems=[
                clinical_item("PR-TE003-01", "M16.12", "Unilateral primary osteoarthritis, left hip"),
                clinical_item("PR-TE003-02", "Z96.642", "Presence of left artificial hip joint"),
                clinical_item("PR-TE003-03", "E11.9", "Type 2 diabetes mellitus"),
                clinical_item("PR-TE003-04", "M25.552", "Pain in left hip", status="inactive"),
            ],
            medications=[
                clinical_item(
                    "MED-TE003-01", "RXN-7052", "Acetaminophen 650 mg every 6 hours as needed", dose="650 mg q6h PRN"
                ),
                clinical_item("MED-TE003-02", "RXN-6809", "Metformin 500 mg twice daily", dose="500 mg BID"),
                clinical_item("MED-TE003-03", "RXN-435", "Albuterol inhaler", status="inactive", dose="PRN"),
            ],
            allergies=[
                clinical_item("ALG-TE003-01", "ALG-LATEX", "Latex", reaction="Contact dermatitis", severity="Moderate")
            ],
            encounters=[
                {
                    "id": "ENC-TE003-01",
                    "date": "2026-06-08",
                    "diagnoses": ["Z47.1", "Z96.642"],
                    "care_plan": "Post-operative wound check and rehab progression.",
                },
                {
                    "id": "ENC-TE003-02",
                    "date": "2026-06-03",
                    "diagnoses": ["M16.12"],
                    "care_plan": "Left total hip arthroplasty discharge planning.",
                },
                {
                    "id": "ENC-TE003-03",
                    "date": "2026-05-21",
                    "diagnoses": ["E11.9"],
                    "care_plan": "Perioperative glucose plan reviewed.",
                },
                {
                    "id": "ENC-TE003-04",
                    "date": "2026-04-30",
                    "diagnoses": ["M16.12"],
                    "care_plan": "Pre-op physical therapy goals set.",
                },
                {
                    "id": "ENC-TE003-05",
                    "date": "2025-08-01",
                    "diagnoses": ["M25.552"],
                    "care_plan": "Old conservative-care note.",
                },
            ],
            immunizations=[
                {"id": "IMM-TE003-01", "name": "COVID-19 booster", "date": "2025-09-22"},
                {"id": "IMM-TE003-02", "name": "Influenza standard-dose", "date": "2025-10-12"},
            ],
            disclosures=[
                {
                    "id": "DISC-TE003-01",
                    "recipient": "Prairie Post-Acute Rehab",
                    "purpose": "Care Transition",
                    "date": "2026-06-09",
                    "status": "active",
                },
                {
                    "id": "DISC-TE003-00",
                    "recipient": "Prairie Post-Acute Rehab",
                    "purpose": "Care Transition",
                    "date": "2025-05-01",
                    "status": "expired",
                },
            ],
        ),
        patient(
            "PAT-TR-004",
            "Cedric",
            "Malo",
            "1984-01-30",
            "EHR-30044",
            problems=[clinical_item("PR-TR004-01", "M75.122", "Complete left rotator cuff tear")],
            encounters=[
                {
                    "id": "ENC-TR004-01",
                    "date": "2026-03-18",
                    "diagnoses": ["M75.122"],
                    "care_plan": "MRI confirms full-thickness left rotator cuff tear after work injury.",
                }
            ],
        ),
        patient(
            "PAT-TE-004",
            "Rina",
            "Patel",
            "1961-05-11",
            "EHR-30077",
            problems=[
                clinical_item("PR-TE004-01", "M84.452A", "Pathological fracture, left femur, initial encounter")
            ],
            encounters=[
                {
                    "id": "ENC-TE004-01",
                    "date": "2026-04-18",
                    "diagnoses": ["M84.452A"],
                    "care_plan": "Left femur lesion concerning for malignancy; oncology coordination requested.",
                }
            ],
        ),
        patient(
            "PAT-TR-005A",
            "Dorthea",
            "Lin",
            "1955-11-26",
            "EHR-41005",
            problems=[
                clinical_item("PR-TR005-01", "I50.22", "Chronic systolic congestive heart failure"),
                clinical_item("PR-TR005-02", "E78.5", "Hyperlipidemia"),
            ],
            medications=[clinical_item("MED-TR005-01", "RXN-4603", "Furosemide 20 mg daily", dose="20 mg daily")],
            allergies=[],
            encounters=[
                {
                    "id": "ENC-TR005-01",
                    "date": "2026-03-20",
                    "diagnoses": ["I50.22"],
                    "care_plan": "Reduced ejection fraction on echo; cardiology referral discussed.",
                },
                {
                    "id": "ENC-TR005-02",
                    "date": "2026-03-05",
                    "diagnoses": ["R06.09"],
                    "care_plan": "Progressive dyspnea on exertion.",
                },
                {"id": "ENC-TR005-03", "date": "2026-02-11", "diagnoses": ["E78.5"], "care_plan": "Continue statin."},
            ],
        ),
    ]


def build_referrals():
    refs = []
    refs.extend(
        [
            referral(
                "REF-TR-0301",
                "BATCH-ORTHO-2026-03",
                "Harris",
                "Paula",
                "1972-03-02",
                "Blue Cross",
                "BC-301",
                "Dr. Robert Chen",
                "Lakewood Family Medicine",
                "(555) 200-1101",
                "M17.11",
                "Primary osteoarthritis right knee",
            ),
            referral(
                "REF-TR-0302",
                "BATCH-ORTHO-2026-03",
                "Price",
                "Nathan",
                "1964-07-19",
                "Aetna",
                "AET-3001",
                "Dr. Sarah Patel",
                "Riverside Internal Medicine",
                "(555) 300-2201",
                "M75.122",
                "Complete rotator cuff tear left shoulder",
                "Urgent",
                auth_required="No",
                auth_status="N/A",
            ),
            referral(
                "REF-TR-0303",
                "BATCH-ORTHO-2026-03",
                "Price",
                "Nathan",
                "1964-07-19",
                "Aetna",
                "AET-3001",
                "Dr. Robert Chen",
                "Lakewood Family Medicine",
                "(555) 200-1101",
                "M75.122",
                "Complete rotator cuff tear left shoulder",
                notes="Second referral for same patient and condition.",
            ),
            referral(
                "REF-TR-0304",
                "BATCH-ORTHO-2026-03",
                "Boone",
                "Carla",
                "1980-10-03",
                "Humana",
                "HUM-3004",
                "Dr. Amanda Foster",
                "Greenfield Primary Care",
                "(555) 500-4401",
                "M76.61",
                "Achilles tendinitis left ankle",
                imaging="No",
            ),
            referral(
                "REF-TR-0305",
                "BATCH-ORTHO-2026-03",
                "Reyes",
                "Sofia",
                "1988-12-05",
                "Medicaid",
                "MCD-3005",
                "Dr. Robert Chen",
                "Lakewood Family Medicine",
                "(555) 200-1101",
                "S82.001A",
                "Fracture of right patella initial encounter",
                "Urgent",
                auth_required="No",
                auth_status="N/A",
                notes="ER records included.",
            ),
            referral(
                "REF-TR-0306",
                "BATCH-ORTHO-2026-03",
                "Wallace",
                "Brenda",
                "1977-06-14",
                "United",
                "UHC-3006",
                "Dr. Amanda Foster",
                "Greenfield Primary Care",
                "(555) 500-4401",
                "M79.3",
                "Olecranon bursitis right elbow",
                "Urgent",
                imaging="No",
                notes="Narrative does not match code.",
            ),
            referral(
                "REF-TR-0307",
                "BATCH-ORTHO-2026-03",
                "Sato",
                "Kenji",
                "1973-01-09",
                "Aetna",
                "AET-3001",
                "Dr. James Whitfield",
                "Prairie Health Associates",
                "(555) 400-3301",
                "M17.12",
                "Primary osteoarthritis left knee",
            ),
            referral(
                "REF-TR-0308",
                "BATCH-ORTHO-2026-03",
                "Morgan",
                "Iris",
                "1962-04-20",
                "Cigna",
                "CIG-3008",
                "Dr. Sarah Patel",
                "Riverside Internal Medicine",
                "(555) 300-2201",
                "M84.451A",
                "Pathological fracture left femur",
                "Urgent",
                auth_required="No",
                auth_status="N/A",
                notes="PRIORITY: oncology coordination requested.",
            ),
            referral(
                "REF-TR-0309",
                "BATCH-ORTHO-2026-03",
                "Brooks",
                "Angela",
                "1983-05-03",
                "United",
                "UHC-3009",
                "Dr. Robert Chen",
                "Lakewood Family Medicine",
                "(555) 200-1101",
                "M25.561",
                "Pain in right knee",
                auth_status="Not Submitted",
                notes="Patient called to reschedule and prefers April dates.",
            ),
            referral(
                "REF-TR-0310",
                "BATCH-ORTHO-2026-03",
                "Kim",
                "David",
                "1971-03-27",
                "Blue Cross",
                "BC-3010",
                "Dr. Amanda Foster",
                "Greenfield Primary Care",
                "(555) 500-4401",
                "M19.011",
                "Primary osteoarthritis right shoulder",
                records="No",
                imaging="No",
                auth_status="Not Submitted",
                notes="Missing office notes and X-ray images.",
            ),
            referral(
                "REF-TR-0311",
                "BATCH-ORTHO-2026-03",
                "Anders",
                "Robert",
                "1952-04-09",
                "Medicare",
                "MCR-3011",
                "Dr. James Whitfield",
                "Prairie Health Associates",
                "(555) 400-3301",
                "M48.062",
                "Lumbar spinal stenosis with neurogenic claudication",
            ),
            referral(
                "REF-TR-0312",
                "BATCH-ORTHO-2026-03",
                "Hernandez",
                "Carlos",
                "1973-06-20",
                "Blue Cross",
                "BC-3012",
                "Dr. James Whitfield",
                "Prairie Health Associates",
                "(555) 400-3301",
                "G89.29",
                "Chronic bilateral knee pain with gait abnormality",
                notes="ICD code may need review.",
            ),
        ]
    )
    refs.extend(
        [
            referral(
                "REF-TE-0401",
                "BATCH-ORTHO-2026-04",
                "Mendez",
                "Laura",
                "1978-04-15",
                "Blue Cross",
                "BC-401",
                "Dr. Robert Chen",
                "Lakewood Family Medicine",
                "(555) 200-1101",
                "M17.12",
                "Primary osteoarthritis left knee",
            ),
            referral(
                "REF-TE-0402",
                "BATCH-ORTHO-2026-04",
                "Evans",
                "Thomas",
                "1965-11-22",
                "Aetna",
                "AET-9902",
                "Dr. Sarah Patel",
                "Riverside Internal Medicine",
                "(555) 300-2201",
                "M75.121",
                "Complete rotator cuff tear right shoulder",
                "Urgent",
                auth_required="No",
                auth_status="N/A",
            ),
            referral(
                "REF-TE-0403",
                "BATCH-ORTHO-2026-04",
                "Norris",
                "Gail",
                "1981-08-21",
                "Humana",
                "HUM-403",
                "Dr. Amanda Foster",
                "Greenfield Primary Care",
                "(555) 500-4401",
                "M24.271",
                "Disorder of ligament left ankle",
                imaging="No",
            ),
            referral(
                "REF-TE-0404",
                "BATCH-ORTHO-2026-04",
                "Ramirez",
                "Julio",
                "1990-12-05",
                "Medicaid",
                "MCD-404",
                "Dr. Robert Chen",
                "Lakewood Family Medicine",
                "(555) 200-1101",
                "S83.512A",
                "ACL sprain left knee initial encounter",
                "Urgent",
                auth_required="No",
                auth_status="N/A",
            ),
            referral(
                "REF-TE-0405",
                "BATCH-ORTHO-2026-04",
                "Olsen",
                "Mira",
                "1955-01-30",
                "Medicare",
                "MCR-405",
                "Dr. James Whitfield",
                "Prairie Health Associates",
                "(555) 400-3301",
                "M16.11",
                "Primary osteoarthritis right hip",
            ),
            referral(
                "REF-TE-0406",
                "BATCH-ORTHO-2026-04",
                "Cole",
                "Denise",
                "1970-09-18",
                "Cigna",
                "CIG-406",
                "Dr. Sarah Patel",
                "Riverside Internal Medicine",
                "(555) 300-2201",
                "M79.3",
                "Olecranon bursitis left elbow",
                "Urgent",
                imaging="No",
            ),
            referral(
                "REF-TE-0407",
                "BATCH-ORTHO-2026-04",
                "Patel",
                "Rina",
                "1961-05-11",
                "Aetna",
                "AET-407",
                "Dr. Sarah Patel",
                "Riverside Internal Medicine",
                "(555) 300-2201",
                "M84.451A",
                "Pathological fracture left femur",
                "Urgent",
                auth_required="No",
                auth_status="N/A",
                notes="Coordinate with oncology at Regional Medical Center.",
            ),
            referral(
                "REF-TE-0408",
                "BATCH-ORTHO-2026-04",
                "Hart",
                "Ellen",
                "1987-11-14",
                "Humana",
                "HUM-408",
                "Dr. Robert Chen",
                "Lakewood Family Medicine",
                "(555) 200-1101",
                "M24.272",
                "Disorder of ligament left ankle",
                records="No",
                imaging="No",
                auth_status="Not Submitted",
            ),
            referral(
                "REF-TE-0409",
                "BATCH-ORTHO-2026-04",
                "Wright",
                "Omar",
                "1973-06-20",
                "Blue Cross",
                "BC-409",
                "Dr. James Whitfield",
                "Prairie Health Associates",
                "(555) 400-3301",
                "M48.062",
                "Lumbar spinal stenosis with neurogenic claudication",
            ),
            referral(
                "REF-TE-0410",
                "BATCH-ORTHO-2026-04",
                "Evans",
                "Thomas",
                "1965-11-22",
                "Aetna",
                "AET-9902",
                "Dr. James Whitfield",
                "Prairie Health Associates",
                "(555) 400-3301",
                "M75.121",
                "Complete rotator cuff tear right shoulder",
                notes="Second opinion requested; same condition as REF-TE-0402.",
            ),
            referral(
                "REF-TE-0411",
                "BATCH-ORTHO-2026-04",
                "Brooks",
                "Maya",
                "1984-03-03",
                "United",
                "UHC-411",
                "Dr. Robert Chen",
                "Lakewood Family Medicine",
                "(555) 200-1101",
                "M25.562",
                "Pain in left knee",
                auth_status="Not Submitted",
                notes="Patient requested May scheduling window.",
            ),
            referral(
                "REF-TE-0412",
                "BATCH-ORTHO-2026-04",
                "Baker",
                "Leon",
                "1969-10-16",
                "Cigna",
                "CIG-412",
                "Dr. James Whitfield",
                "Prairie Health Associates",
                "(555) 400-3301",
                "M84.452A",
                "Pathological fracture right femur",
                "Urgent",
                imaging="No",
                auth_required="No",
                auth_status="N/A",
                notes="Possible malignancy; oncology consult requested.",
            ),
            referral(
                "REF-TE-0413",
                "BATCH-ORTHO-2026-04",
                "Ibrahim",
                "Nadia",
                "1980-09-02",
                "Aetna",
                "AET-9902",
                "Dr. Amanda Foster",
                "Greenfield Primary Care",
                "(555) 500-4401",
                "M70.22",
                "Olecranon bursitis left elbow",
                imaging="No",
            ),
            referral(
                "REF-TE-0414",
                "BATCH-ORTHO-2026-04",
                "Hart",
                "Ellen",
                "1987-11-14",
                "Humana",
                "HUM-408",
                "Dr. Amanda Foster",
                "Greenfield Primary Care",
                "(555) 500-4401",
                "M24.272",
                "Disorder of ligament left ankle",
                notes="Duplicate from different referrer.",
            ),
            referral(
                "REF-TE-0415",
                "BATCH-ORTHO-2026-04",
                "Quinn",
                "Peter",
                "1975-02-01",
                "Blue Cross",
                "BC-415",
                "Dr. James Whitfield",
                "Prairie Health Associates",
                "(555) 400-3301",
                "G89.29",
                "Chronic right knee pain from meniscal tear",
                records="No",
            ),
            referral(
                "REF-TE-0416",
                "BATCH-ORTHO-2026-04",
                "Yang",
                "Ivy",
                "1991-07-07",
                "Medicare",
                "MCR-416",
                "Dr. Amanda Foster",
                "Greenfield Primary Care",
                "(555) 500-4401",
                "M70.21",
                "Olecranon bursitis right elbow",
                scheduled="Yes",
                appt_date="2026-04-29",
                assigned="Dr. R. Mitchell",
            ),
            referral(
                "REF-TR-005",
                "BATCH-CARD-2026-03",
                "Lin",
                "Dorthea",
                "1955-11-26",
                "Medicare",
                "MCR-5005",
                "Dr. Rebecca Lindstrom",
                "Hingham Senior Care",
                "(555) 610-2201",
                "I50.22",
                "Chronic systolic congestive heart failure",
                reason="Progressive dyspnea on exertion with reduced ejection fraction; cardiology referral",
                urgency="Routine",
                records="Yes",
                imaging="Yes",
                auth_required="No",
                auth_status="N/A",
                notes="Add severe iodinated contrast allergy before sending.",
            ),
        ]
    )
    return refs


def build_data():
    random.seed(SEED)
    patients = build_target_patients()
    providers = [
        {
            "provider_id": "PROV-001",
            "name": "Dr. Janet Crooks",
            "specialty": "Internal Medicine",
            "fax": "(555) 100-1001",
        },
        {
            "provider_id": "PROV-002",
            "name": "Dr. Gertrud Kuhic",
            "specialty": "Orthopedic Surgery",
            "fax": "(555) 100-1002",
        },
        {"provider_id": "PROV-003", "name": "Dr. Noura Haddad", "specialty": "Nephrology", "fax": "(555) 100-1003"},
        {
            "provider_id": "PROV-004",
            "name": "Dr. Hiroshi Tanaka",
            "specialty": "Advanced Heart Failure",
            "fax": "(555) 100-1004",
        },
        {
            "provider_id": "PROV-005",
            "name": "Dr. R. James Mitchell",
            "specialty": "Orthopedic Surgery",
            "fax": "(620) 555-0148",
        },
        {"provider_id": "PROV-006", "name": "Dr. Priya Raman", "specialty": "Oncology", "fax": "(555) 100-1006"},
    ]

    first_names = [
        "Alice",
        "Ben",
        "Cora",
        "Diego",
        "Elise",
        "Farah",
        "Gina",
        "Hugo",
        "Iris",
        "Jalen",
        "Kira",
        "Lena",
        "Marco",
        "Nell",
        "Oscar",
        "Priya",
        "Quincy",
        "Rosa",
        "Sam",
        "Talia",
        "Uma",
        "Victor",
        "Willa",
        "Xavier",
        "Yara",
        "Zane",
    ]
    last_names = [
        "Alden",
        "Bishop",
        "Carver",
        "Diaz",
        "Ellis",
        "Frost",
        "Garza",
        "Hale",
        "Irwin",
        "Jensen",
        "Klein",
        "Lopez",
        "Mason",
        "Novak",
        "Ortiz",
        "Perry",
        "Quade",
        "Reed",
        "Stone",
        "Torres",
        "Usher",
        "Vale",
        "West",
        "Young",
        "Zimmer",
    ]
    codes = ["M17.11", "M17.12", "M16.11", "M75.121", "M25.562", "M48.062", "J44.9", "I50.22"]
    for i in range(42):
        fn = first_names[i % len(first_names)]
        ln = last_names[(i * 3) % len(last_names)]
        yr = random.randint(1940, 1998)
        pcode = random.choice(codes)
        patients.append(
            patient(
                f"PAT-FILL-{i + 1:03d}",
                fn,
                ln,
                f"{yr}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
                f"EHR-{50000 + i}",
                problems=[clinical_item(f"PR-FILL-{i + 1:03d}", pcode, f"Generated active condition {pcode}")],
                medications=[
                    clinical_item(
                        f"MED-FILL-{i + 1:03d}", "RXN-GEN", "Generated maintenance medication", dose="as directed"
                    )
                ],
                encounters=[
                    {
                        "id": f"ENC-FILL-{i + 1:03d}",
                        "date": "2026-02-01",
                        "diagnoses": [pcode],
                        "care_plan": "Routine follow-up.",
                    }
                ],
            )
        )

    duplicate_candidates = [
        {
            "candidate_id": "DUP-TR-001",
            "patient_ids": ["PAT-TR-001A", "PAT-TR-001B"],
            "match_reasons": ["same legal name", "same DOB", "same phone", "overlapping respiratory history"],
            "risk_flags": [],
            "suggested_action": "review_for_merge",
        },
        {
            "candidate_id": "DUP-TE-001",
            "patient_ids": ["PAT-TE-001A", "PAT-TE-001B"],
            "match_reasons": ["same legal name", "same DOB", "same phone", "renal/diabetes overlap"],
            "risk_flags": ["conflicting_current_address", "expired_disclosure_on_source"],
            "suggested_action": "clarify_before_merge",
        },
        {
            "candidate_id": "DUP-DIST-001",
            "patient_ids": ["PAT-FILL-001", "PAT-FILL-014"],
            "match_reasons": ["similar name only"],
            "risk_flags": ["different DOB"],
            "suggested_action": "do_not_merge",
        },
    ]

    handoff_packets = [
        {
            "packet_id": "HANDOFF-TR-003",
            "patient_id": "PAT-TR-003",
            "sending_provider_id": "PROV-001",
            "receiving_provider_id": "PROV-002",
            "receiving_facility": "Lakeside Skilled Nursing",
            "created_date": "2026-05-30",
            "included_sections": [
                "demographics",
                "active_problems",
                "active_medications",
                "allergies",
                "recent_encounters",
                "immunizations",
                "functional_status",
                "transfer_plan",
                "disclosure",
            ],
            "functional_status": "Ambulates 40 feet with rolling walker; requires standby assistance for transfers.",
            "cognitive_status": "",
            "transfer_reason": "Heart failure/COPD recovery support and medication monitoring after hospitalization.",
            "notes": "Cognitive status is omitted from the packet draft.",
        },
        {
            "packet_id": "HANDOFF-TE-003",
            "patient_id": "PAT-TE-003",
            "sending_provider_id": "PROV-005",
            "receiving_provider_id": "PROV-002",
            "receiving_facility": "Prairie Post-Acute Rehab",
            "created_date": "2026-06-09",
            "included_sections": [
                "demographics",
                "active_problems",
                "active_medications",
                "allergies",
                "recent_encounters",
                "immunizations",
                "functional_status",
                "cognitive_status",
                "transfer_plan",
                "disclosure",
            ],
            "functional_status": "Weight bearing as tolerated with walker; requires assistance with stairs and lower-body dressing.",
            "cognitive_status": "Alert and oriented x4; understands hip precautions.",
            "transfer_reason": "Post-operative rehabilitation after left total hip arthroplasty.",
            "notes": "One inactive albuterol medication appears in source chart but should not be treated as current.",
        },
    ]

    service_requests = [
        {
            "request_id": "SR-TR-004",
            "patient_id": "PAT-TR-004",
            "status": "draft",
            "intent": "order",
            "priority": "routine",
            "service_code": "306181000000106",
            "service_display": "Referral to orthopedic surgery service",
            "specialty": "Orthopedic Surgery",
            "authored_on": "2026-03-18T14:20:00Z",
            "occurrence_datetime": "2026-03-25T09:00:00Z",
            "note_text": "Situation: left shoulder work injury. Background: MRI confirms full-thickness rotator cuff tear. Assessment: complete left rotator cuff tear. Recommendation:",
            "linked_encounter_ids": ["ENC-TR004-01"],
        },
        {
            "request_id": "SR-TE-004",
            "patient_id": "PAT-TE-004",
            "status": "draft",
            "intent": "order",
            "priority": "stat",
            "service_code": "306181000000106",
            "service_display": "Referral to orthopedic surgery service",
            "specialty": "Orthopedic Surgery",
            "authored_on": "2026-04-18T10:15:00Z",
            "occurrence_datetime": "2026-04-19T08:00:00Z",
            "note_text": "Situation: painful left femur lesion with suspected pathological fracture. Background: imaging suggests left femur fracture and oncology referral is pending. Assessment: coded draft lists right femur. Recommendation: urgent orthopedic evaluation and oncology coordination.",
            "linked_encounter_ids": ["ENC-TE004-01"],
        },
    ]

    referrals = build_referrals()
    data = {
        "seed": SEED,
        "patients": patients,
        "providers": providers,
        "codebook_icd10": build_codebook(),
        "duplicate_candidates": duplicate_candidates,
        "referrals": referrals,
        "referral_batches": [
            {"batch_id": "BATCH-ORTHO-2026-03", "month": "2026-03", "service_line": "Orthopedics"},
            {"batch_id": "BATCH-ORTHO-2026-04", "month": "2026-04", "service_line": "Orthopedics"},
            {"batch_id": "BATCH-CARD-2026-03", "month": "2026-03", "service_line": "Cardiology"},
        ],
        "handoff_packets": handoff_packets,
        "service_requests": service_requests,
        "documents": [
            {
                "document_id": "DOC-HIPAA-001",
                "title": "HIPAA Authorization Release Form Reference",
                "document_type": "authorization_template",
            },
            {
                "document_id": "DOC-REF-001",
                "title": "CRMC Orthopedic Referral Form Layout Reference",
                "document_type": "referral_form",
            },
            {
                "document_id": "DOC-Q005-001",
                "title": "Integrated Queue Extract Q-TE-005",
                "document_type": "quality_queue_scope",
                "related_ids": ["DUP-TE-001", "REF-TE-0407", "REF-TE-0411", "REF-TE-0413", "REF-TR-005"],
            },
        ],
        "audit_log": [
            {
                "event_id": "AUD-TR001-01",
                "event_type": "duplicate_review",
                "patient_ids": ["PAT-TR-001A", "PAT-TR-001B"],
                "timestamp": "2026-03-22T09:44:00Z",
                "user": "ehr_quality_admin",
                "status": "ready_for_merge",
            },
            {
                "event_id": "AUD-TE001-01",
                "event_type": "duplicate_review",
                "patient_ids": ["PAT-TE-001A", "PAT-TE-001B"],
                "timestamp": "2026-04-21T11:15:00Z",
                "user": "ehr_quality_admin",
                "status": "blocked_address_conflict",
            },
        ],
    }
    return data


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = build_data()
    write_json(DATA_DIR / "ehr_quality_data.json", data)
    public_manifest = {
        "seed": SEED,
        "patients": len(data["patients"]),
        "providers": len(data["providers"]),
        "referrals": len(data["referrals"]),
        "duplicate_candidates": len(data["duplicate_candidates"]),
        "handoff_packets": len(data["handoff_packets"]),
        "service_requests": len(data["service_requests"]),
        "endpoint_families": [
            "patients",
            "duplicate-candidates",
            "referrals",
            "referral-batches",
            "handoff-packets",
            "service-requests",
            "providers",
            "codebook/icd10",
            "documents",
            "audit-log",
        ],
    }
    write_json(DATA_DIR / "public_manifest.json", public_manifest)
    construction_manifest = {
        "target_ids": {
            "train_001": ["DUP-TR-001"],
            "train_002": ["BATCH-ORTHO-2026-03"],
            "train_003": ["HANDOFF-TR-003"],
            "train_004": ["SR-TR-004"],
            "train_005": ["REF-TR-005", "PAT-TR-005A"],
            "test_001": ["DUP-TE-001"],
            "test_002": ["BATCH-ORTHO-2026-04"],
            "test_003": ["HANDOFF-TE-003"],
            "test_004": ["SR-TE-004"],
            "test_005": ["DUP-TE-001", "REF-TE-0407", "REF-TE-0411", "REF-TE-0413", "REF-TR-005"],
        },
        "issue_labels": {
            "BATCH-ORTHO-2026-03": [
                "laterality",
                "out_of_range",
                "duplicate",
                "insurance_collision",
                "missing_documents",
                "reschedule",
            ],
            "BATCH-ORTHO-2026-04": [
                "laterality",
                "out_of_range",
                "narrative_mismatch",
                "duplicate",
                "insurance_collision",
                "missing_documents",
                "oncology_coordination",
                "reschedule",
            ],
        },
    }
    write_json(DATA_DIR / "construction_manifest.json", construction_manifest)


if __name__ == "__main__":
    main()
