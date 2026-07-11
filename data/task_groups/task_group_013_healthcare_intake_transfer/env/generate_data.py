#!/usr/bin/env python3
"""Generate deterministic Northstar Care Intake Portal data."""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path


SEED = 130726
GENERATED_AT = "2026-07-07T00:00:00Z"
BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
DATA_FILE = DATA_DIR / "generated_data.json"
MANIFEST_FILE = BASE / "manifest.json"

TARGET_IDS = {
    "registration_train": ["NSP-1008", "NSP-1014", "NSP-1022", "NSP-1031"],
    "transfer_train": ["TR-2604", "TR-2611", "TR-2620", "TR-2635"],
    "referral_train": ["REF-3106", "REF-3118", "REF-3124", "REF-3139", "REF-3142"],
    "chart_train": ["CHR-2040", "CHR-2058", "CHR-2077"],
    "chronic_train": ["CCP-4107", "CCP-4116", "CCP-4133", "CCP-4144"],
    "registration_test": ["NSP-1042", "NSP-1057", "NSP-1073", "NSP-1088", "NSP-1096"],
    "transfer_test": ["TR-2644", "TR-2659", "TR-2671", "TR-2688", "TR-2693"],
    "referral_test": ["REF-3151", "REF-3167", "REF-3175", "REF-3182", "REF-3190", "REF-3196"],
    "chronic_chart_test": ["CCP-4158", "CCP-4162", "CCP-4179", "CCP-4185", "CHR-2094"],
    "queue_test": ["Q-5203", "Q-5219", "Q-5226", "Q-5237", "Q-5241", "Q-5255"],
}

FIRST_NAMES = [
    "Avery",
    "Maya",
    "Jordan",
    "Elias",
    "Naomi",
    "Victor",
    "Priya",
    "Caleb",
    "Leah",
    "Mateo",
    "Nora",
    "Iris",
    "Owen",
    "Amara",
    "Samuel",
    "Lena",
    "Grace",
    "Jonah",
    "Mina",
    "Diego",
    "Harper",
    "Theo",
    "Sofia",
    "Andre",
    "Renee",
    "Talia",
    "Felix",
    "Nadia",
    "Elena",
    "Miles",
]
LAST_NAMES = [
    "Nguyen",
    "Patel",
    "Martinez",
    "Chen",
    "Johnson",
    "Garcia",
    "Williams",
    "Brown",
    "Kim",
    "Singh",
    "Rivera",
    "Thompson",
    "Wilson",
    "Clark",
    "Morris",
    "Ali",
    "Reed",
    "Bennett",
    "Morgan",
    "Khan",
]
LANGUAGES = ["English", "Spanish", "Vietnamese", "Mandarin", "Arabic", "Hindi", "Korean", "English"]
SERVICE_LINES = ["Primary Care", "Endocrinology", "Cardiology", "Renal Care", "Orthopedics", "Behavioral Health"]
REQUESTED_SERVICES = {
    "Primary Care": ["new patient intake", "preventive visit", "complex care intake"],
    "Endocrinology": ["diabetes program intake", "thyroid consultation", "medication-managed intake"],
    "Cardiology": ["hypertension care intake", "post-discharge intake", "medication-managed intake"],
    "Renal Care": ["dialysis transfer intake", "renal risk program", "medication-managed intake"],
    "Orthopedics": ["joint pain referral", "sports injury referral", "spine referral"],
    "Behavioral Health": ["therapy intake", "medication review", "care navigation"],
}
PAYERS = [
    "Aetna Choice",
    "BlueCross PPO",
    "Cigna Open Access",
    "Humana HMO",
    "United Healthcare",
    "Medicare Advantage",
]
PBMS = ["CareScript", "MedPoint Rx", "PrimeWell", "ClearDose", "Northstar PBM"]
PHARMACY_NAMES = [
    "Cedar Grove Pharmacy",
    "Lakeview Rx",
    "Summit Specialty",
    "Northstar Campus Pharmacy",
    "Valley Community Drug",
    "MetroCare Pharmacy",
    "Harbor Mail Order",
    "Greenline Pharmacy",
]
CONDITIONS = [
    "Type 2 diabetes",
    "Hypertension",
    "Chronic kidney disease",
    "Asthma",
    "Hyperlipidemia",
    "Osteoarthritis",
    "Depression",
    "Heart failure",
    "None reported",
]
MEDICATIONS = [
    "metformin",
    "lisinopril",
    "atorvastatin",
    "amlodipine",
    "insulin glargine",
    "albuterol",
    "sertraline",
    "furosemide",
    "none listed",
]
ALLERGIES = ["NKDA", "penicillin", "sulfa", "latex", "shellfish", "iodine contrast"]


def d(day: date) -> str:
    return day.isoformat()


def pick(rng: random.Random, values):
    return rng.choice(values)


def make_name(rng: random.Random, idx: int) -> str:
    # A few repeated last names and duplicate-like names make search/cross-checking realistic.
    if idx in (7, 38):
        return "Jordan Rivera"
    if idx in (12, 52):
        return "Maya Chen"
    return f"{pick(rng, FIRST_NAMES)} {pick(rng, LAST_NAMES)}"


def patient_ids() -> list[str]:
    ids = []
    ids.extend(TARGET_IDS["registration_train"])
    ids.extend(TARGET_IDS["registration_test"])
    ids.extend(TARGET_IDS["chart_train"])
    ids.append("CHR-2094")
    ids.extend(TARGET_IDS["chronic_train"])
    ids.extend(["CCP-4158", "CCP-4162", "CCP-4179", "CCP-4185"])
    ids.extend([f"NDT-{n}" for n in range(2601, 2610)])
    ids.extend([f"NOR-{n}" for n in range(3101, 3113)])
    while len(ids) < 78:
        ids.append(f"NSP-{1100 + len(ids)}")
    return ids


def build_patients(rng: random.Random) -> list[dict]:
    patients = []
    for idx, pid in enumerate(patient_ids()):
        service = "Renal Care" if pid.startswith("NDT") else pick(rng, SERVICE_LINES)
        if pid.startswith("CHR"):
            service = "Primary Care"
        if pid.startswith("CCP"):
            service = pick(rng, ["Endocrinology", "Cardiology", "Renal Care"])
        requested = pick(rng, REQUESTED_SERVICES[service])
        if "medication" in requested or service in ("Endocrinology", "Cardiology", "Renal Care"):
            medication_managed = True
        else:
            medication_managed = rng.random() < 0.35
        birth_year = rng.randint(1944, 2002)
        patient = {
            "patient_id": pid,
            "name": make_name(rng, idx),
            "dob": d(date(birth_year, rng.randint(1, 12), rng.randint(1, 28))),
            "language": pick(rng, LANGUAGES),
            "service_line": service,
            "requested_service": requested,
            "medication_managed": medication_managed,
            "demographics": {
                "identity_verified": rng.random() > 0.08,
                "address_complete": rng.random() > 0.10,
                "phone_verified": rng.random() > 0.12,
                "emergency_contact": rng.random() > 0.20,
                "consent_signed": rng.random() > 0.13,
            },
            "clinical": {
                "conditions": rng.sample(CONDITIONS[:-1], rng.randint(1, 3))
                if rng.random() > 0.10
                else ["None reported"],
                "medications": rng.sample(MEDICATIONS[:-1], rng.randint(1, 3))
                if rng.random() > 0.12
                else ["none listed"],
                "allergies": [pick(rng, ALLERGIES)],
                "smoking": pick(rng, ["never", "former", "current", "unknown"]),
                "alcohol": pick(rng, ["none", "occasional", "weekly", "daily", "unknown"]),
                "exercise": pick(rng, ["150+ min/week", "60-149 min/week", "<60 min/week", "unknown"]),
                "vaccination_status": pick(rng, ["current", "due for seasonal", "declined", "unknown"]),
            },
            "registration_links": {
                "benefits": f"BEN-{pid}",
                "pbm": f"PBM-{pid}",
                "pharmacy": f"PHR-{pid}",
                "chart": pid,
            },
        }
        patients.append(patient)
    return patients


def build_benefits(rng: random.Random, patients: list[dict]) -> list[dict]:
    benefits = []
    review = date(2026, 7, 7)
    for idx, p in enumerate(patients):
        active = rng.random() > 0.12
        if p["patient_id"] in {"NSP-1014", "NSP-1057", "NSP-1088"}:
            active = False
        verified = "portal-verified eligibility"
        benefits.append(
            {
                "benefit_id": f"BEN-{p['patient_id']}",
                "patient_id": p["patient_id"],
                "coverage_status": "active" if active else pick(rng, ["inactive", "pending COB", "terminated"]),
                "effective_date": d(review - timedelta(days=rng.randint(45, 900))),
                "termination_date": "" if active else d(review - timedelta(days=rng.randint(1, 60))),
                "payer": pick(rng, PAYERS),
                "network_status": "in network"
                if rng.random() > 0.15
                else pick(rng, ["out of network", "network exception needed"]),
                "authorization_required": rng.random() < 0.45,
                "pbm_status": "active" if rng.random() > 0.13 else pick(rng, ["inactive", "not located", "pending"]),
                "pbm_name": pick(rng, PBMS),
                "pharmacy_network_status": "in network" if rng.random() > 0.12 else "out of network",
                "preferred_pharmacy": pick(rng, PHARMACY_NAMES),
                "special_handling": pick(
                    rng, ["none", "specialty medication review", "mail order only", "prior auth history attached"]
                ),
                "snapshot_date": d(review - timedelta(days=rng.randint(0, 14))),
                "source_label": verified,
                "card_image_status": pick(rng, ["not present", "stale unverified upload", "matches portal snapshot"]),
                "review_date": d(review),
            }
        )
    return benefits


def build_transfers(rng: random.Random, transfer_patient_ids: list[str]) -> list[dict]:
    transfer_ids = TARGET_IDS["transfer_train"] + TARGET_IDS["transfer_test"] + [f"TR-{n}" for n in range(2698, 2710)]
    facilities = [
        "Eastlake Dialysis",
        "Ridgeview Renal",
        "Mercy Acute Dialysis",
        "St. Anne Transitional",
        "Central Kidney Care",
    ]
    modalities = ["in-center hemodialysis", "peritoneal dialysis", "home hemodialysis"]
    docs = [
        "labs",
        "infection screen",
        "dialysis prescription",
        "medication list",
        "allergy list",
        "authorization",
        "confidentiality statement",
        "referring contact",
        "transport note",
    ]
    transfers = []
    for idx, tid in enumerate(transfer_ids):
        requested = date(2026, 7, 15) + timedelta(days=rng.randint(0, 30))
        status_map = {}
        for name in docs:
            state = pick(rng, ["final", "received", "draft", "missing", "expired"])
            if name in ("medication list", "allergy list", "referring contact") and rng.random() > 0.2:
                state = "received"
            if name == "dialysis prescription" and rng.random() > 0.28:
                state = "final"
            if name == "labs":
                doc_date = requested - timedelta(days=rng.randint(5, 45))
            elif name == "infection screen":
                doc_date = requested - timedelta(days=rng.randint(2, 24))
            else:
                doc_date = requested - timedelta(days=rng.randint(1, 90))
            status_map[name] = {"status": state, "date": d(doc_date), "source": pick(rng, facilities)}
        transfers.append(
            {
                "transfer_id": tid,
                "patient_id": transfer_patient_ids[idx % len(transfer_patient_ids)],
                "requested_start_date": d(requested),
                "referring_facility": pick(rng, facilities),
                "dialysis_modality": pick(rng, modalities),
                "documents": status_map,
                "requested_chair_availability": pick(
                    rng, ["chair held", "chair available, not held", "waitlist", "capacity review"]
                ),
                "chart_prep_status": pick(rng, ["not started", "in progress", "ready pending documents", "complete"]),
                "notes": pick(
                    rng,
                    [
                        "transport needs confirmation",
                        "patient prefers mornings",
                        "infection result fax expected",
                        "no special notes",
                    ],
                ),
            }
        )
    return transfers


def build_referrals(rng: random.Random) -> list[dict]:
    referral_ids = TARGET_IDS["referral_train"] + TARGET_IDS["referral_test"] + [f"REF-{n}" for n in range(3201, 3213)]
    practices = [
        "Metro Ortho Group",
        "North Hills Family",
        "Union Sports Medicine",
        "Lakeside Primary",
        "Summit Spine",
    ]
    diagnoses = [
        ("M17.11", "unilateral primary osteoarthritis, right knee", "right", "orthopedics"),
        ("M25.562", "pain in left knee", "left", "orthopedics"),
        ("M54.50", "low back pain, unspecified", "spine", "orthopedics"),
        ("E11.9", "type 2 diabetes without complications", "n/a", "endocrinology"),
        ("S83.241A", "right medial meniscus tear", "right", "orthopedics"),
    ]
    referrals = []
    for idx, rid in enumerate(referral_ids):
        code, narrative, laterality, family = pick(rng, diagnoses)
        name = make_name(rng, idx + 90)
        if idx in (4, 13):
            name = "Maya Chen"
        referrals.append(
            {
                "referral_id": rid,
                "patient_name": name,
                "dob": d(date(rng.randint(1948, 2005), rng.randint(1, 12), rng.randint(1, 28))),
                "insurance": pick(rng, PAYERS),
                "referring_physician": pick(
                    rng, ["Dr. Ellis Park", "Dr. Mina Cohen", "Dr. Rafael Soto", "Dr. Vivian Lee", "Dr. Omar Haddad"]
                ),
                "practice": pick(rng, practices),
                "fax": f"555-{rng.randint(200, 899)}-{rng.randint(1000, 9999)}",
                "phone": f"555-{rng.randint(200, 899)}-{rng.randint(1000, 9999)}",
                "icd10_code": code,
                "diagnosis_narrative": narrative,
                "laterality": laterality,
                "urgency": pick(rng, ["routine", "urgent", "stat review"]),
                "received_date": d(date(2026, 6, 20) + timedelta(days=rng.randint(0, 17))),
                "records_received": rng.random() > 0.16,
                "imaging_received": rng.random() > 0.22,
                "authorization_status": pick(rng, ["not required", "approved", "pending", "missing"]),
                "duplicate_hints": pick(
                    rng, ["none", "similar name same DOB", "same condition within 30 days", "same physician only"]
                ),
                "linked_referral_ids": [],
                "service_family": family,
            }
        )
    referrals[4]["linked_referral_ids"] = ["REF-3190"]
    referrals[15]["linked_referral_ids"] = ["REF-3142"]
    return referrals


def build_charts(rng: random.Random, patients: list[dict]) -> list[dict]:
    charts = []
    for p in patients:
        current_vitals = rng.random() > 0.15
        charts.append(
            {
                "patient_id": p["patient_id"],
                "chart_created": rng.random() > 0.05,
                "demographics_complete": all(p["demographics"].values()),
                "history_complete": rng.random() > 0.13,
                "problems_complete": rng.random() > 0.10,
                "active_problem_codes": rng.sample(
                    ["E11.9", "I10", "N18.31", "J45.909", "M17.11", "E78.5"], rng.randint(0, 3)
                ),
                "vitals": {
                    "bp": f"{rng.randint(108, 168)}/{rng.randint(64, 98)}",
                    "pulse": rng.randint(58, 104),
                    "recorded_date": d(date(2026, 7, 7) - timedelta(days=rng.randint(0, 45))),
                    "current": current_vitals,
                },
                "care_plan": pick(rng, ["documented", "missing", "draft"]),
                "clinical_instructions": pick(rng, ["sent", "pending nurse edit", "not needed", "missing"]),
                "orientation_message": pick(rng, ["sent", "queued", "not sent"]),
                "patient_portal_status": pick(rng, ["active", "invite sent", "not invited", "declined"]),
            }
        )
    return charts


def build_programs(rng: random.Random, patients: list[dict]) -> list[dict]:
    program_patients = [
        p
        for p in patients
        if p["patient_id"].startswith("CCP") or p["service_line"] in ("Endocrinology", "Cardiology", "Renal Care")
    ]
    programs = []
    for p in program_patients[:48]:
        diagnoses = p["clinical"]["conditions"]
        if p["patient_id"].startswith("CCP") and not any(
            x in diagnoses for x in ["Type 2 diabetes", "Hypertension", "Chronic kidney disease"]
        ):
            diagnoses = ["Type 2 diabetes", "Hypertension"]
        programs.append(
            {
                "patient_id": p["patient_id"],
                "active_diagnoses": diagnoses,
                "recent_hba1c": round(rng.uniform(5.7, 10.8), 1) if "Type 2 diabetes" in diagnoses else "",
                "bp": f"{rng.randint(112, 178)}/{rng.randint(68, 102)}",
                "renal_flag": "yes"
                if ("Chronic kidney disease" in diagnoses or p["service_line"] == "Renal Care" or rng.random() < 0.20)
                else "no",
                "consent_status": pick(rng, ["signed", "verbal pending signature", "declined", "not obtained"]),
                "program_form_status": pick(rng, ["complete", "incomplete", "not started"]),
                "medication_adherence": pick(rng, ["good", "variable", "poor", "unknown"]),
                "telehealth_preference": pick(rng, ["video", "phone", "in-person", "no preference"]),
                "last_visit": d(date(2026, 7, 7) - timedelta(days=rng.randint(5, 180))),
                "proposed_program": pick(
                    rng, ["Diabetes Pathway", "Hypertension Pathway", "Renal Risk Monitoring", "Cardiometabolic Combo"]
                ),
                "coordinator": pick(rng, ["I. Barrett", "M. Okafor", "S. Lin", "R. Alvarez"]),
            }
        )
    return programs


def build_queue(
    rng: random.Random, transfers: list[dict], referrals: list[dict], programs: list[dict], patients: list[dict]
) -> list[dict]:
    target = TARGET_IDS["queue_test"]
    linked = [
        ("transfer", transfers[2]["transfer_id"], "Renal Care"),
        ("referral", referrals[5]["referral_id"], "Orthopedics"),
        ("program", programs[1]["patient_id"], "Chronic Care"),
        ("benefits", patients[5]["patient_id"], "Registration"),
        ("chart", patients[12]["patient_id"], "Chart Prep"),
        ("transfer", transfers[7]["transfer_id"], "Renal Care"),
    ]
    queue = []
    for qid, (rtype, rid, family) in zip(target, linked):
        queue.append(
            {
                "queue_id": qid,
                "linked_record_type": rtype,
                "linked_id": rid,
                "service_family": family,
                "created_date": d(date(2026, 7, 7) - timedelta(days=rng.randint(0, 9))),
                "urgency": pick(rng, ["routine", "same day", "urgent"]),
                "visible_summary": pick(
                    rng,
                    [
                        "Review packet before scheduling decision",
                        "Caller reports missing step is now complete",
                        "Coordinator needs next action by end of day",
                        "Follow policy before closing item",
                    ],
                ),
                "current_owner": pick(rng, ["Intake Pool", "Benefit Desk", "Nurse Review", "Referral Desk"]),
                "status": pick(rng, ["open", "in progress", "waiting external"]),
            }
        )
    extra_links = [("referral", r["referral_id"], "Orthopedics") for r in referrals[8:14]]
    extra_links += [("transfer", t["transfer_id"], "Renal Care") for t in transfers[9:14]]
    extra_links += [("program", p["patient_id"], "Chronic Care") for p in programs[4:10]]
    for idx, (rtype, rid, family) in enumerate(extra_links, 1):
        queue.append(
            {
                "queue_id": f"Q-{5300 + idx}",
                "linked_record_type": rtype,
                "linked_id": rid,
                "service_family": family,
                "created_date": d(date(2026, 7, 7) - timedelta(days=rng.randint(0, 15))),
                "urgency": pick(rng, ["routine", "same day", "urgent"]),
                "visible_summary": "Open linked record and apply current SOP before updating.",
                "current_owner": pick(rng, ["Intake Pool", "Benefit Desk", "Nurse Review", "Referral Desk"]),
                "status": pick(rng, ["open", "in progress", "waiting external"]),
            }
        )
    return queue


def build_reference_docs() -> tuple[list[dict], list[dict], list[dict]]:
    pharmacies = [
        {
            "pharmacy_id": f"PH-{idx + 1:03d}",
            "name": name,
            "network": "in network" if idx != 6 else "mail order only",
            "specialty": idx in (2, 3, 6),
            "phone": f"555-700-{1000 + idx}",
        }
        for idx, name in enumerate(PHARMACY_NAMES)
    ]
    documents = [
        {
            "document_id": "DOC-001",
            "title": "Registration Gate Checklist",
            "owner": "Intake Operations",
            "updated": "2026-06-28",
            "summary": "Medical coverage, PBM, pharmacy, demographics, and clinical review checkpoints.",
        },
        {
            "document_id": "DOC-002",
            "title": "Dialysis Transfer Packet Index",
            "owner": "Renal Intake",
            "updated": "2026-06-24",
            "summary": "Freshness standards for labs, infection screen, prescription, authorizations, and transport notes.",
        },
        {
            "document_id": "DOC-003",
            "title": "Orthopedics Referral Triage Aid",
            "owner": "Referral Desk",
            "updated": "2026-07-01",
            "summary": "Musculoskeletal code checks, laterality matching, duplicate review, and authorization follow-up.",
        },
        {
            "document_id": "DOC-004",
            "title": "Chronic Program Enrollment Form",
            "owner": "Care Coordination",
            "updated": "2026-06-18",
            "summary": "Consent, diagnosis, lab/vital, renal flag, and telehealth preference review.",
        },
    ]
    policies = [
        {
            "policy_id": "POL-REG-01",
            "title": "Registration gates",
            "body": "Use the latest portal-verified eligibility snapshot. Medical insurance must be active on the review date and in network. A stale card image never overrides verified portal status. Medication-managed intake also requires active PBM and an in-network preferred pharmacy.",
        },
        {
            "policy_id": "POL-REN-02",
            "title": "Dialysis transfer freshness",
            "body": "Labs are current within 30 days of requested start; infection screening is current within 14 days. Dialysis prescription must be final. Medication list, allergy list, authorization, confidentiality statement, referring contact, and transport note are required.",
        },
        {
            "policy_id": "POL-REF-03",
            "title": "Orthopedics referral scheduling",
            "body": "Scheduling requires an M-code or supported musculoskeletal diagnosis, agreement between narrative and laterality, required clinical records and imaging, and payer authorization when required. Duplicate checks use patient demographics and condition.",
        },
        {
            "policy_id": "POL-CHR-04",
            "title": "Chart readiness",
            "body": "A chart is ready only when demographics, history, applicable active problems, current vitals, onboarding care plan or clinical instructions, and orientation communication are complete.",
        },
        {
            "policy_id": "POL-CCP-05",
            "title": "Chronic program enrollment",
            "body": "Diabetes and hypertension pathways require active diagnosis, recent labs or vitals, consent, and a complete program form. Renal risk changes cadence and may require nurse escalation.",
        },
    ]
    return pharmacies, documents, policies


def build() -> dict:
    rng = random.Random(SEED)
    patients = build_patients(rng)
    benefits = build_benefits(rng, patients)
    transfer_patient_ids = [p["patient_id"] for p in patients if p["patient_id"].startswith("NDT")]
    transfers = build_transfers(rng, transfer_patient_ids)
    referrals = build_referrals(rng)
    charts = build_charts(rng, patients)
    programs = build_programs(rng, patients)
    queue = build_queue(rng, transfers, referrals, programs, patients)
    pharmacies, documents, policies = build_reference_docs()
    return {
        "seed": SEED,
        "generated_at": GENERATED_AT,
        "patients": patients,
        "benefits": benefits,
        "pharmacies": pharmacies,
        "transfers": transfers,
        "referrals": referrals,
        "charts": charts,
        "programs": programs,
        "queue": queue,
        "documents": documents,
        "policies": policies,
    }


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = build()
    DATA_FILE.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "seed": SEED,
        "record_counts": {
            key: len(data[key])
            for key in [
                "patients",
                "benefits",
                "pharmacies",
                "transfers",
                "referrals",
                "charts",
                "programs",
                "queue",
                "documents",
                "policies",
            ]
        },
        "generated_files": ["data/generated_data.json"],
        "app_entry_points": [
            "/",
            "/login",
            "/healthz",
            "/dashboard",
            "/patients",
            "/benefits",
            "/pharmacies",
            "/transfers",
            "/referrals",
            "/charts",
            "/programs",
            "/queue",
            "/documents",
            "/policies",
        ],
        "login_credentials": {
            "email": "intake.admin@northstar.example",
            "password": "Northstar-Intake-2026!",
            "role": "Intake Operations Lead",
        },
        "target_ids": TARGET_IDS,
        "generation_timestamp": GENERATED_AT,
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {DATA_FILE}")
    print(f"Wrote {MANIFEST_FILE}")


if __name__ == "__main__":
    main()
