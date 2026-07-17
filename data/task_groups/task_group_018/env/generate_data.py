#!/usr/bin/env python3
"""Generate deterministic clerk operations data for task_group_018."""

from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "clerk_ops.json"
MANIFEST_FILE = DATA_DIR / "manifest.json"

SCHEMA_VERSION = "1.0"
GENERATED_AT = "2026-07-07T00:00:00Z"
SEEDS = {
    "master": 18072026,
    "cases": 18072027,
    "citations": 18072028,
    "fees": 18072029,
    "hearings": 18072030,
    "finance": 18072031,
    "stale_exports": 18072032,
}

COUNTIES = [
    {"county": "Benton", "court": "Benton County Circuit Court", "code": "BEN"},
    {"county": "Lane", "court": "Lane County Justice Court", "code": "LAN"},
    {"county": "Gloucester", "court": "Gloucester County Superior Court", "code": "GLO"},
    {"county": "Marion", "court": "Marion County Circuit Court", "code": "MAR"},
    {"county": "Wasco", "court": "Wasco County District Court", "code": "WAS"},
    {"county": "Columbia", "court": "Columbia County Circuit Court", "code": "COL"},
    {"county": "Jefferson", "court": "Jefferson County Municipal Court", "code": "JEF"},
    {"county": "Middlesex", "court": "Middlesex County Superior Court", "code": "MID"},
]

COUNTY_BY_NAME = {row["county"]: row for row in COUNTIES}

FIRST_NAMES = [
    "Alicia",
    "Andre",
    "Bianca",
    "Calvin",
    "Daniel",
    "Darla",
    "Elena",
    "Evan",
    "Fatima",
    "Felix",
    "Gabriel",
    "Hannah",
    "Imani",
    "Isaac",
    "Janelle",
    "Jonah",
    "Kara",
    "Luis",
    "Marta",
    "Miguel",
    "Nadia",
    "Owen",
    "Priya",
    "Renee",
    "Samuel",
    "Talia",
    "Victor",
    "Yasmin",
]

LAST_NAMES = [
    "Abbott",
    "Bennett",
    "Brooks",
    "Chen",
    "Cruz",
    "Diaz",
    "Ellis",
    "Foster",
    "Garcia",
    "Hayes",
    "Ibarra",
    "Jones",
    "Keller",
    "Lopez",
    "Mason",
    "Nguyen",
    "Patel",
    "Reed",
    "Santos",
    "Turner",
    "Vargas",
    "Walker",
    "Young",
]

JUDGES = [
    "Hon. Amara Kline",
    "Hon. Robert Vale",
    "Hon. Nina Bell",
    "Hon. Patrick Howe",
    "Hon. Selene Cross",
    "Hon. Thomas Rivera",
    "Hon. Miriam Fox",
    "Hon. George Fielding",
]

CLERKS = [
    "Dana Holt",
    "Marcus Lee",
    "Nora Finch",
    "Elise Grant",
    "Walter Pierce",
    "Julia Stone",
    "Omar Blake",
    "Tessa Irving",
]

FIRMS = [
    "County Public Defender Office",
    "Northbank Defense Group",
    "Riverside Legal Clinic",
    "Cedar Street Law",
    "Harbor Rights Project",
    "Independent Appointed Counsel Panel",
    "Mason & Vale LLP",
    "Kepler Law Offices",
]

CRIMINAL_CHARGES = [
    ("CR-121", "Theft in the second degree", "misdemeanor"),
    ("CR-209", "Criminal mischief", "misdemeanor"),
    ("CR-330", "Unlawful possession of a controlled substance", "felony"),
    ("CR-412", "Assault in the fourth degree", "misdemeanor"),
    ("CR-507", "Failure to appear", "misdemeanor"),
    ("CR-610", "Identity theft", "felony"),
]

DUI_CHARGES = [
    ("DUI-101", "Driving under the influence of intoxicants", "misdemeanor"),
    ("DUI-104", "Refusal to submit to chemical test", "violation"),
    ("DUI-210", "Reckless driving related to DUI", "misdemeanor"),
    ("DUI-225", "Open container violation", "violation"),
]

COMPLIANCE_CHARGES = [
    ("CMP-040", "Probation review", "compliance"),
    ("CMP-055", "Failure to complete treatment", "compliance"),
    ("CMP-072", "Missed payment review", "compliance"),
    ("CMP-088", "License reinstatement compliance", "compliance"),
]

TRAFFIC_VIOLATIONS = [
    ("TR-201", "Speeding 11 to 20 mph over limit"),
    ("TR-202", "Speeding 21 to 30 mph over limit"),
    ("TR-215", "Failure to obey traffic control device"),
    ("TR-231", "Driving while suspended"),
    ("TR-244", "No proof of insurance"),
    ("TR-260", "Unsafe lane change"),
]

STATUSES_BY_MATTER = {
    "criminal": ["open", "closed", "probation_active", "deferred", "warrant"],
    "traffic": ["open", "closed", "deferred", "satisfied"],
    "dui": ["open", "closed", "probation_active", "compliance_review"],
    "compliance": ["open", "satisfied", "compliance_review", "warrant"],
}

PLEAS = ["not_guilty", "guilty", "no_contest", "deferred_entry", "not_entered"]
VERDICTS = ["guilty", "dismissed", "deferred", "not_adjudicated", "not_guilty"]
DISPOSITIONS = ["convicted", "dismissed", "deferred", "amended", "pending"]
DEFENSE_TYPES = ["public_defender", "appointed_private", "retained", "unknown"]


def iso(value: date) -> str:
    return value.isoformat()


def parse_day(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def add_days(value: str, days: int) -> str:
    return iso(parse_day(value) + timedelta(days=days))


def random_day(rng: random.Random, start: str, end: str) -> str:
    start_day = parse_day(start)
    end_day = parse_day(end)
    span = (end_day - start_day).days
    return iso(start_day + timedelta(days=rng.randint(0, span)))


def money(value: float) -> float:
    return round(value + 1e-9, 2)


def person_name(rng: random.Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def dob(rng: random.Random) -> str:
    return random_day(rng, "1962-01-01", "2005-12-31")


def sid(rng: random.Random) -> str:
    return f"SID{rng.randint(100000, 999999)}"


def case_number(county: str, year: int, sequence: int) -> str:
    code = COUNTY_BY_NAME[county]["code"]
    return f"{str(year)[-2:]}-{code}-{sequence:05d}"


def citation_number(county: str, year: int, sequence: int) -> str:
    code = COUNTY_BY_NAME[county]["code"]
    return f"CIT-{code}-{year}-{sequence:05d}"


def make_charge(
    charge_id: str,
    statute: str,
    description: str,
    severity: str,
    offense_date: str,
    plea: str,
    verdict: str,
    disposition: str,
) -> dict:
    return {
        "charge_id": charge_id,
        "statute": statute,
        "description": description,
        "severity": severity,
        "offense_date": offense_date,
        "plea": plea,
        "verdict": verdict,
        "disposition": disposition,
    }


def build_attorneys() -> list[dict]:
    attorneys = []
    names = [
        "Helena Moore",
        "Simon Park",
        "Theresa Walsh",
        "Owen Clarke",
        "Mina Patel",
        "Gareth Phelps",
        "Laura Kim",
        "Carlos Reed",
        "Beatrice Young",
        "Jonas Meyer",
        "Priya Nair",
        "Violet Ames",
        "Felix Grant",
        "Rachel Stone",
        "Nolan Pierce",
        "Irene Mason",
    ]
    rng = random.Random(SEEDS["master"])
    for index, name in enumerate(names, start=1):
        counties = rng.sample([row["county"] for row in COUNTIES], rng.randint(1, 3))
        attorneys.append(
            {
                "attorney_id": f"ATT-{index:03d}",
                "name": name,
                "bar_number": f"BAR{rng.randint(10000, 99999)}",
                "firm": rng.choice(FIRMS),
                "counties": counties,
                "phone": f"555-{rng.randint(200, 899)}-{rng.randint(1000, 9999)}",
                "email": f"{name.lower().replace(' ', '.')}@example-legal.test",
                "active": rng.random() > 0.08,
                "defense_types": rng.sample(DEFENSE_TYPES[:-1], rng.randint(1, 3)),
                "notes": rng.choice(
                    [
                        "Accepts appointment conflicts by written confirmation only.",
                        "Listed on stale assignment exports under a former firm name.",
                        "Requires clerk callback for same-day hearing coverage.",
                        "No special notes.",
                    ]
                ),
            }
        )
    return attorneys


def attorney_for_county(rng: random.Random, attorneys: list[dict], county: str) -> str:
    candidates = [row for row in attorneys if county in row["counties"] and row["active"]]
    if not candidates:
        candidates = attorneys
    return rng.choice(candidates)["name"]


def sentence_for(matter_type: str, status: str, rng: random.Random) -> dict:
    if status in {"open", "warrant"}:
        return {
            "jail_days": 0,
            "suspended_days": 0,
            "community_service_hours": 0,
            "treatment_ordered": False,
            "notes": "No final sentence recorded.",
        }
    if matter_type == "dui":
        return {
            "jail_days": rng.choice([2, 5, 10, 20]),
            "suspended_days": rng.choice([0, 20, 40, 80]),
            "community_service_hours": rng.choice([24, 40, 80]),
            "treatment_ordered": True,
            "notes": rng.choice(["Victim panel required.", "Ignition interlock review required."]),
        }
    if matter_type == "criminal":
        return {
            "jail_days": rng.choice([0, 5, 10, 30, 60]),
            "suspended_days": rng.choice([0, 30, 60, 90]),
            "community_service_hours": rng.choice([0, 20, 40, 80]),
            "treatment_ordered": rng.random() < 0.25,
            "notes": rng.choice(["Standard conditions apply.", "Restitution review remains open."]),
        }
    if matter_type == "traffic":
        return {
            "jail_days": 0,
            "suspended_days": 0,
            "community_service_hours": rng.choice([0, 8, 16]),
            "treatment_ordered": False,
            "notes": rng.choice(["Traffic school eligible.", "Fine only."]),
        }
    return {
        "jail_days": 0,
        "suspended_days": 0,
        "community_service_hours": rng.choice([0, 10, 20]),
        "treatment_ordered": rng.random() < 0.15,
        "notes": "Compliance conditions reviewed.",
    }


def anchor_cases(attorneys: list[dict]) -> list[dict]:
    anchors = [
        {
            "case_number": "24-BEN-00132",
            "county": "Benton",
            "matter_type": "criminal",
            "defendant_name": "Miguel Santos",
            "defendant_dob": "1988-04-17",
            "sid_number": "SID410782",
            "status": "probation_active",
            "filing_date": "2024-03-19",
            "charges": [
                make_charge(
                    "CHG-001",
                    "CR-121",
                    "Theft in the second degree",
                    "misdemeanor",
                    "2024-03-02",
                    "guilty",
                    "guilty",
                    "convicted",
                ),
                make_charge(
                    "CHG-002",
                    "CR-507",
                    "Failure to appear",
                    "misdemeanor",
                    "2024-04-15",
                    "no_contest",
                    "guilty",
                    "convicted",
                ),
            ],
            "defense_attorney": "Helena Moore",
            "defense_type": "public_defender",
            "disposition_date": "2024-08-22",
            "probation_months": 18,
            "license_suspension_months": 0,
            "restitution_ordered": 640.00,
            "tags": ["restitution_review", "active_payment_plan", "similar_name_distractor"],
        },
        {
            "case_number": "24-BEN-00141",
            "county": "Benton",
            "matter_type": "criminal",
            "defendant_name": "Michael Santos",
            "defendant_dob": "1988-04-19",
            "sid_number": "SID410872",
            "status": "closed",
            "filing_date": "2024-03-22",
            "charges": [
                make_charge(
                    "CHG-001",
                    "CR-209",
                    "Criminal mischief",
                    "misdemeanor",
                    "2024-03-04",
                    "no_contest",
                    "guilty",
                    "convicted",
                )
            ],
            "defense_attorney": "Simon Park",
            "defense_type": "retained",
            "disposition_date": "2024-07-30",
            "probation_months": 12,
            "license_suspension_months": 0,
            "restitution_ordered": 125.00,
            "tags": ["name_conflict", "closed"],
        },
        {
            "case_number": "25-BEN-00058",
            "county": "Benton",
            "matter_type": "criminal",
            "defendant_name": "Nadia Brooks",
            "defendant_dob": "1995-11-08",
            "sid_number": "SID552019",
            "status": "open",
            "filing_date": "2025-02-13",
            "charges": [
                make_charge(
                    "CHG-001",
                    "CR-412",
                    "Assault in the fourth degree",
                    "misdemeanor",
                    "2025-01-29",
                    "not_guilty",
                    "not_adjudicated",
                    "pending",
                )
            ],
            "defense_attorney": "Theresa Walsh",
            "defense_type": "appointed_private",
            "disposition_date": None,
            "probation_months": 0,
            "license_suspension_months": 0,
            "restitution_ordered": 0.00,
            "tags": ["pending_trial", "benton_criminal"],
        },
        {
            "case_number": "23-GLO-00218",
            "county": "Gloucester",
            "matter_type": "dui",
            "defendant_name": "Darla Nguyen",
            "defendant_dob": "1982-09-21",
            "sid_number": "SID667204",
            "status": "probation_active",
            "filing_date": "2023-12-11",
            "charges": [
                make_charge(
                    "CHG-001",
                    "DUI-101",
                    "Driving under the influence of intoxicants",
                    "misdemeanor",
                    "2023-11-27",
                    "guilty",
                    "guilty",
                    "convicted",
                ),
                make_charge(
                    "CHG-002",
                    "DUI-104",
                    "Refusal to submit to chemical test",
                    "violation",
                    "2023-11-27",
                    "no_contest",
                    "guilty",
                    "convicted",
                ),
            ],
            "defense_attorney": "Owen Clarke",
            "defense_type": "retained",
            "disposition_date": "2024-04-09",
            "probation_months": 24,
            "license_suspension_months": 12,
            "restitution_ordered": 0.00,
            "tags": ["dui_program", "license_hold"],
        },
        {
            "case_number": "24-MID-00077",
            "county": "Middlesex",
            "matter_type": "dui",
            "defendant_name": "Victor Hayes",
            "defendant_dob": "1979-01-30",
            "sid_number": "SID709321",
            "status": "compliance_review",
            "filing_date": "2024-01-18",
            "charges": [
                make_charge(
                    "CHG-001",
                    "DUI-101",
                    "Driving under the influence of intoxicants",
                    "misdemeanor",
                    "2024-01-03",
                    "guilty",
                    "guilty",
                    "convicted",
                ),
                make_charge(
                    "CHG-002",
                    "DUI-210",
                    "Reckless driving related to DUI",
                    "misdemeanor",
                    "2024-01-03",
                    "no_contest",
                    "dismissed",
                    "dismissed",
                ),
            ],
            "defense_attorney": "Mina Patel",
            "defense_type": "appointed_private",
            "disposition_date": "2024-06-14",
            "probation_months": 30,
            "license_suspension_months": 18,
            "restitution_ordered": 0.00,
            "tags": ["dui_program", "missed_treatment_notice"],
        },
        {
            "case_number": "24-MAR-00305",
            "county": "Marion",
            "matter_type": "criminal",
            "defendant_name": "Alicia Walker",
            "defendant_dob": "1990-07-12",
            "sid_number": "SID882410",
            "status": "closed",
            "filing_date": "2024-05-06",
            "charges": [
                make_charge(
                    "CHG-001", "CR-610", "Identity theft", "felony", "2024-04-18", "guilty", "guilty", "convicted"
                ),
                make_charge(
                    "CHG-002",
                    "CR-121",
                    "Theft in the second degree",
                    "misdemeanor",
                    "2024-04-18",
                    "guilty",
                    "guilty",
                    "amended",
                ),
            ],
            "defense_attorney": "Gareth Phelps",
            "defense_type": "public_defender",
            "disposition_date": "2024-10-02",
            "probation_months": 36,
            "license_suspension_months": 0,
            "restitution_ordered": 1420.75,
            "tags": ["amended_count", "docket_conflict", "financial_hold"],
        },
        {
            "case_number": "25-COL-00112",
            "county": "Columbia",
            "matter_type": "criminal",
            "defendant_name": "Jonah Reed",
            "defendant_dob": "1998-02-25",
            "sid_number": "SID771903",
            "status": "deferred",
            "filing_date": "2025-01-27",
            "charges": [
                make_charge(
                    "CHG-001",
                    "CR-330",
                    "Unlawful possession of a controlled substance",
                    "felony",
                    "2025-01-09",
                    "deferred_entry",
                    "deferred",
                    "deferred",
                )
            ],
            "defense_attorney": "Laura Kim",
            "defense_type": "appointed_private",
            "disposition_date": "2025-04-04",
            "probation_months": 18,
            "license_suspension_months": 0,
            "restitution_ordered": 0.00,
            "tags": ["diversion_review", "drug_treatment"],
        },
        {
            "case_number": "24-WAS-00290",
            "county": "Wasco",
            "matter_type": "compliance",
            "defendant_name": "Priya Mason",
            "defendant_dob": "1985-12-02",
            "sid_number": "SID930218",
            "status": "compliance_review",
            "filing_date": "2024-11-19",
            "charges": [
                make_charge(
                    "CHG-001",
                    "CMP-072",
                    "Missed payment review",
                    "compliance",
                    "2024-11-12",
                    "not_entered",
                    "not_adjudicated",
                    "pending",
                )
            ],
            "defense_attorney": "Carlos Reed",
            "defense_type": "unknown",
            "disposition_date": None,
            "probation_months": 0,
            "license_suspension_months": 0,
            "restitution_ordered": 215.50,
            "tags": ["payment_review", "multi_county_match"],
        },
        {
            "case_number": "23-WAS-00144",
            "county": "Wasco",
            "matter_type": "compliance",
            "defendant_name": "Samuel Turner",
            "defendant_dob": "1976-05-05",
            "sid_number": "SID222901",
            "status": "satisfied",
            "filing_date": "2023-09-08",
            "charges": [
                make_charge(
                    "CHG-001",
                    "CMP-088",
                    "License reinstatement compliance",
                    "compliance",
                    "2023-08-25",
                    "not_entered",
                    "not_adjudicated",
                    "satisfied",
                )
            ],
            "defense_attorney": "Rachel Stone",
            "defense_type": "retained",
            "disposition_date": "2024-02-01",
            "probation_months": 0,
            "license_suspension_months": 0,
            "restitution_ordered": 0.00,
            "tags": ["license_reinstated", "closed_financial"],
        },
    ]
    for row in anchors:
        row["court"] = COUNTY_BY_NAME[row["county"]]["court"]
        row["sentence"] = sentence_for(row["matter_type"], row["status"], random.Random(row["sid_number"]))
        if row["defense_attorney"] not in {attorney["name"] for attorney in attorneys}:
            row["defense_attorney"] = attorneys[0]["name"]
    return anchors


def generate_cases(attorneys: list[dict]) -> list[dict]:
    rng = random.Random(SEEDS["cases"])
    cases = anchor_cases(attorneys)
    used = {row["case_number"] for row in cases}
    seq_by_county_year: dict[tuple[str, int], int] = {}
    matter_choices = ["criminal", "traffic", "dui", "compliance"]
    matter_weights = [0.36, 0.16, 0.20, 0.28]

    while len(cases) < 112:
        county = rng.choice(COUNTIES)["county"]
        filing_date = random_day(rng, "2023-01-01", "2025-06-15")
        year = parse_day(filing_date).year
        key = (county, year)
        seq_by_county_year[key] = seq_by_county_year.get(key, 1000) + 1
        number = case_number(county, year, seq_by_county_year[key])
        if number in used:
            continue
        used.add(number)

        matter_type = rng.choices(matter_choices, weights=matter_weights, k=1)[0]
        status = rng.choice(STATUSES_BY_MATTER[matter_type])
        disposition_date = None
        if status not in {"open", "warrant"}:
            disposition_date = add_days(filing_date, rng.randint(45, 210))
        charge_pool = {
            "criminal": CRIMINAL_CHARGES,
            "traffic": [(code, desc, "violation") for code, desc in TRAFFIC_VIOLATIONS],
            "dui": DUI_CHARGES,
            "compliance": COMPLIANCE_CHARGES,
        }[matter_type]
        charge_count = rng.choice([1, 1, 1, 2, 2, 3])
        selected_charges = rng.sample(charge_pool, min(charge_count, len(charge_pool)))
        charges = []
        for index, item in enumerate(selected_charges, start=1):
            if matter_type == "traffic":
                statute, description, severity = item
            else:
                statute, description, severity = item
            if status in {"open", "warrant", "compliance_review"} and rng.random() < 0.55:
                plea = "not_entered"
                verdict = "not_adjudicated"
                disposition = "pending"
            else:
                plea = rng.choice(PLEAS)
                verdict = rng.choice(VERDICTS)
                disposition = rng.choice(DISPOSITIONS)
            charges.append(
                make_charge(
                    f"CHG-{index:03d}",
                    statute,
                    description,
                    severity,
                    add_days(filing_date, -rng.randint(1, 45)),
                    plea,
                    verdict,
                    disposition,
                )
            )

        defendant = person_name(rng)
        if rng.random() < 0.08:
            defendant = rng.choice(["Miguel Santos", "Alicia Walker", "Victor Hayes", "Priya Mason"])
        restitution = 0.0
        if matter_type in {"criminal", "compliance"} and status not in {"open", "warrant"}:
            restitution = money(rng.choice([0, 0, 0, rng.uniform(75, 1850)]))

        cases.append(
            {
                "case_number": number,
                "county": county,
                "court": COUNTY_BY_NAME[county]["court"],
                "matter_type": matter_type,
                "defendant_name": defendant,
                "defendant_dob": dob(rng),
                "sid_number": sid(rng),
                "status": status,
                "filing_date": filing_date,
                "charges": charges,
                "defense_attorney": attorney_for_county(rng, attorneys, county),
                "defense_type": rng.choice(DEFENSE_TYPES),
                "disposition_date": disposition_date,
                "sentence": sentence_for(matter_type, status, rng),
                "probation_months": rng.choice([0, 6, 12, 18, 24, 36]) if matter_type != "traffic" else 0,
                "license_suspension_months": rng.choice([0, 0, 3, 6, 12, 18]) if matter_type == "dui" else 0,
                "restitution_ordered": restitution,
                "tags": sorted(
                    set(
                        rng.sample(
                            [
                                "stale_export_conflict",
                                "similar_name",
                                "fee_effective_date_sensitive",
                                "manual_review",
                                "active_payment_plan",
                                "attorney_changed",
                                "financial_hold",
                                "calendar_overlap",
                                "clean_record",
                            ],
                            rng.randint(1, 3),
                        )
                    )
                ),
            }
        )
    return sorted(cases, key=lambda row: row["case_number"])


def anchor_citations() -> list[dict]:
    return [
        {
            "citation_number": "CIT-LAN-2024-00411",
            "county": "Lane",
            "defendant_name": "Evan Turner",
            "violation_code": "TR-202",
            "violation_description": "Speeding 21 to 30 mph over limit",
            "event_date": "2024-09-14",
            "hearing_date": "2024-11-08",
            "speed_mph": 78,
            "posted_speed_mph": 55,
            "plea": "no_contest",
            "disposition": "convicted",
            "payment_plan_requested": True,
            "first_due_date": "2024-12-09",
            "requested_monthly_amount": 45.00,
        },
        {
            "citation_number": "CIT-LAN-2024-00412",
            "county": "Lane",
            "defendant_name": "Evan Tuner",
            "violation_code": "TR-215",
            "violation_description": "Failure to obey traffic control device",
            "event_date": "2024-09-14",
            "hearing_date": "2024-11-08",
            "speed_mph": None,
            "posted_speed_mph": None,
            "plea": "not_entered",
            "disposition": "pending",
            "payment_plan_requested": False,
            "first_due_date": None,
            "requested_monthly_amount": None,
        },
        {
            "citation_number": "CIT-JEF-2025-00127",
            "county": "Jefferson",
            "defendant_name": "Kara Lopez",
            "violation_code": "TR-231",
            "violation_description": "Driving while suspended",
            "event_date": "2025-02-20",
            "hearing_date": "2025-04-03",
            "speed_mph": None,
            "posted_speed_mph": None,
            "plea": "guilty",
            "disposition": "convicted",
            "payment_plan_requested": True,
            "first_due_date": "2025-05-05",
            "requested_monthly_amount": 35.00,
        },
        {
            "citation_number": "CIT-JEF-2025-00138",
            "county": "Jefferson",
            "defendant_name": "Kara Lopaz",
            "violation_code": "TR-244",
            "violation_description": "No proof of insurance",
            "event_date": "2025-03-01",
            "hearing_date": "2025-04-03",
            "speed_mph": None,
            "posted_speed_mph": None,
            "plea": "not_entered",
            "disposition": "dismissed",
            "payment_plan_requested": False,
            "first_due_date": None,
            "requested_monthly_amount": None,
        },
    ]


def generate_citations() -> list[dict]:
    rng = random.Random(SEEDS["citations"])
    citations = anchor_citations()
    used = {row["citation_number"] for row in citations}
    seq_by_county_year: dict[tuple[str, int], int] = {}

    while len(citations) < 68:
        county = rng.choice(COUNTIES)["county"]
        event_date = random_day(rng, "2023-01-01", "2025-06-30")
        year = parse_day(event_date).year
        key = (county, year)
        seq_by_county_year[key] = seq_by_county_year.get(key, 700) + 1
        number = citation_number(county, year, seq_by_county_year[key])
        if number in used:
            continue
        used.add(number)
        code, description = rng.choice(TRAFFIC_VIOLATIONS)
        is_speed = code in {"TR-201", "TR-202"}
        posted = rng.choice([25, 30, 35, 45, 55, 65]) if is_speed else None
        speed = posted + rng.randint(11, 33) if posted else None
        hearing_date = add_days(event_date, rng.randint(25, 80))
        disposition = rng.choice(["pending", "convicted", "dismissed", "deferred", "satisfied"])
        payment_plan_requested = disposition in {"convicted", "deferred"} and rng.random() < 0.45
        first_due_date = (
            add_days(hearing_date, rng.choice([30, 35, 45])) if disposition in {"convicted", "deferred"} else None
        )
        citations.append(
            {
                "citation_number": number,
                "county": county,
                "defendant_name": person_name(rng),
                "violation_code": code,
                "violation_description": description,
                "event_date": event_date,
                "hearing_date": hearing_date,
                "speed_mph": speed,
                "posted_speed_mph": posted,
                "plea": rng.choice(PLEAS),
                "disposition": disposition,
                "payment_plan_requested": payment_plan_requested,
                "first_due_date": first_due_date,
                "requested_monthly_amount": money(rng.choice([25, 30, 35, 40, 45, 50, 60]))
                if payment_plan_requested
                else None,
            }
        )
    return sorted(citations, key=lambda row: row["citation_number"])


def generate_fee_schedules() -> list[dict]:
    rng = random.Random(SEEDS["fees"])
    templates = {
        "criminal": [
            ("CR-FILING", "Criminal filing assessment", "case filed", 95.0, True),
            ("CR-CONV", "Conviction assessment", "conviction entered", 160.0, True),
            ("CR-PROB", "Probation setup fee", "probation ordered", 80.0, False),
            ("CR-REST-ADM", "Restitution administration fee", "restitution ordered", 25.0, False),
        ],
        "traffic": [
            ("TR-BASE", "Traffic base fine", "violation convicted or deferred", 130.0, True),
            ("TR-SPEED", "Speed surcharge", "speed over posted limit", 60.0, False),
            ("TR-SCHOOL", "Traffic safety school fee", "traffic school elected", 45.0, False),
            ("TR-LATE", "Late payment fee", "payment more than 30 days late", 25.0, False),
        ],
        "dui": [
            ("DUI-CONV", "DUI conviction assessment", "dui conviction entered", 375.0, True),
            ("DUI-TREAT", "Alcohol assessment and treatment referral", "treatment ordered", 190.0, True),
            ("DUI-LIC", "License suspension processing fee", "license suspension ordered", 85.0, True),
            ("DUI-PROB", "DUI probation monitoring fee", "probation ordered", 120.0, False),
        ],
        "compliance": [
            ("CMP-REVIEW", "Compliance review filing fee", "review scheduled", 55.0, True),
            ("CMP-REINSTATE", "Reinstatement processing fee", "reinstatement requested", 70.0, False),
            ("CMP-MONITOR", "Compliance monitoring fee", "monitoring ordered", 40.0, False),
            ("CMP-RETURN", "Return-to-court notice fee", "missed payment notice issued", 20.0, False),
        ],
    }
    rows = []
    for county_row in COUNTIES:
        county = county_row["county"]
        county_adjustment = rng.choice([-10, -5, 0, 5, 10, 15])
        for matter_type, fee_rows in templates.items():
            for code, description, applies_when, amount, mandatory in fee_rows:
                current_amount = money(max(5.0, amount + county_adjustment + rng.choice([0, 2.5, 5.0])))
                rows.append(
                    {
                        "county": county,
                        "matter_type": matter_type,
                        "fee_code": code,
                        "description": description,
                        "applies_when": applies_when,
                        "amount": current_amount,
                        "effective_start": "2025-01-01",
                        "effective_end": None,
                        "mandatory": mandatory,
                    }
                )
                if rng.random() < 0.65:
                    rows.append(
                        {
                            "county": county,
                            "matter_type": matter_type,
                            "fee_code": code,
                            "description": f"Obsolete {description.lower()}",
                            "applies_when": applies_when,
                            "amount": money(max(5.0, current_amount - rng.choice([5, 10, 15]))),
                            "effective_start": "2023-01-01",
                            "effective_end": "2024-12-31",
                            "mandatory": mandatory,
                        }
                    )
    return sorted(rows, key=lambda row: (row["county"], row["matter_type"], row["fee_code"], row["effective_start"]))


def generate_payment_policies() -> list[dict]:
    rng = random.Random(SEEDS["fees"] + 11)
    policies = []
    unsupported_pool = ["DUI-104", "CR-610", "TR-231", "CMP-072", "CR-507"]
    for county_row in COUNTIES:
        county = county_row["county"]
        minimum = rng.choice([20, 25, 30, 35, 40])
        maximum = rng.choice([150, 175, 200, 225, 250])
        policies.append(
            {
                "county": county,
                "policy_name": f"{county} installment and compliance payment policy",
                "min_monthly": float(minimum),
                "max_monthly": float(maximum),
                "allows_final_smaller_payment": rng.random() < 0.75,
                "first_due_days_after_order": rng.choice([30, 35, 45]),
                "return_to_court_days_after_missed_payment": rng.choice([20, 25, 30, 35]),
                "unknown_field_placeholder": "TBD from case file",
                "unsupported_charge_codes": sorted(rng.sample(unsupported_pool, rng.randint(1, 3))),
            }
        )
    return sorted(policies, key=lambda row: row["county"])


def current_fees_for(fee_schedules: list[dict], county: str, matter_type: str, effective_on: str) -> list[dict]:
    target = parse_day(effective_on)
    rows = []
    for row in fee_schedules:
        if row["county"] != county or row["matter_type"] != matter_type:
            continue
        start = parse_day(row["effective_start"])
        end = parse_day(row["effective_end"]) if row["effective_end"] else None
        if start <= target and (end is None or target <= end):
            rows.append(row)
    return rows


def generate_financial_obligations(cases: list[dict], fee_schedules: list[dict], policies: list[dict]) -> list[dict]:
    rng = random.Random(SEEDS["finance"])
    policy_by_county = {row["county"]: row for row in policies}
    obligations = []
    for case in cases:
        include = case["status"] not in {"open", "warrant"} or rng.random() < 0.70
        if not include:
            continue
        order_date = case["disposition_date"] or add_days(case["filing_date"], rng.randint(35, 115))
        fee_rows = current_fees_for(fee_schedules, case["county"], case["matter_type"], order_date)
        mandatory = [row for row in fee_rows if row["mandatory"]]
        optional = [row for row in fee_rows if not row["mandatory"]]
        selected = mandatory + rng.sample(optional, min(len(optional), rng.randint(0, 2)))
        if not selected:
            selected = rng.sample(fee_rows, min(len(fee_rows), 2))
        components = [
            {
                "fee_code": row["fee_code"],
                "description": row["description"],
                "amount": row["amount"],
                "source_effective_start": row["effective_start"],
            }
            for row in selected
        ]
        principal = money(sum(item["amount"] for item in components) + float(case["restitution_ordered"]))
        amount_paid = money(rng.uniform(0, principal)) if principal > 0 else 0.0
        if case["status"] in {"satisfied", "closed"} and rng.random() < 0.45:
            amount_paid = principal
        balance = money(max(0.0, principal - amount_paid))
        policy = policy_by_county[case["county"]]
        monthly = None
        if balance > 0:
            monthly = money(
                min(policy["max_monthly"], max(policy["min_monthly"], rng.choice([25, 35, 45, 60, 75, 90, 125])))
            )
        obligations.append(
            {
                "case_number": case["case_number"],
                "county": case["county"],
                "order_date": order_date,
                "principal_amount": principal,
                "fee_components": components,
                "restitution_amount": case["restitution_ordered"],
                "amount_paid": amount_paid,
                "balance_due": balance,
                "payment_plan": balance > 0 and rng.random() < 0.80,
                "monthly_amount": monthly,
                "next_due_date": add_days(order_date, policy["first_due_days_after_order"]) if balance > 0 else None,
                "missed_payments": rng.choice([0, 0, 0, 1, 2]) if balance > 0 else 0,
                "status": "paid" if balance == 0 else rng.choice(["current", "delinquent", "pending_adjustment"]),
                "source": "live financial ledger",
            }
        )
    return sorted(obligations, key=lambda row: row["case_number"])


def generate_docket_entries(cases: list[dict]) -> list[dict]:
    rng = random.Random(SEEDS["cases"] + 44)
    rows = []
    for case in cases:
        entries = []
        entry_date = case["filing_date"]
        entries.append(
            {
                "entry_id": f"{case['case_number']}-D001",
                "entry_date": entry_date,
                "event_type": "filing",
                "text": f"Complaint filed in {case['court']} for {case['matter_type']} matter.",
                "entered_by": rng.choice(CLERKS),
                "source": "live docket",
            }
        )
        entries.append(
            {
                "entry_id": f"{case['case_number']}-D002",
                "entry_date": add_days(entry_date, rng.randint(4, 18)),
                "event_type": "appearance",
                "text": f"Initial appearance; defense listed as {case['defense_type']}.",
                "entered_by": rng.choice(CLERKS),
                "source": "live docket",
            }
        )
        if case["disposition_date"]:
            entries.append(
                {
                    "entry_id": f"{case['case_number']}-D003",
                    "entry_date": case["disposition_date"],
                    "event_type": "disposition",
                    "text": f"Disposition entered for {len(case['charges'])} charge records.",
                    "entered_by": rng.choice(CLERKS),
                    "source": "live docket",
                }
            )
        if case["status"] in {"probation_active", "compliance_review", "warrant"}:
            entries.append(
                {
                    "entry_id": f"{case['case_number']}-D004",
                    "entry_date": add_days(case["disposition_date"] or case["filing_date"], rng.randint(20, 140)),
                    "event_type": "review",
                    "text": rng.choice(
                        [
                            "Payment review set; clerk note says amount should be verified against live ledger.",
                            "Compliance review scheduled after provider notice.",
                            "Attorney assignment changed in minute sheet but not on stale export.",
                            "Return-to-court notice prepared; service status pending.",
                        ]
                    ),
                    "entered_by": rng.choice(CLERKS),
                    "source": "live docket",
                }
            )
        if case["case_number"] in {"24-MAR-00305", "25-COL-00112", "24-BEN-00132"}:
            entries.append(
                {
                    "entry_id": f"{case['case_number']}-D099",
                    "entry_date": add_days(case["disposition_date"] or case["filing_date"], 3),
                    "event_type": "correction",
                    "text": "Corrected docket entry supersedes a prior clerk note that used an obsolete charge description.",
                    "entered_by": "Dana Holt",
                    "source": "live docket correction",
                    "supersedes_entry_id": f"{case['case_number']}-D003",
                }
            )
        rows.append(
            {"case_number": case["case_number"], "entries": sorted(entries, key=lambda item: item["entry_date"])}
        )
    return sorted(rows, key=lambda row: row["case_number"])


def generate_hearings(cases: list[dict], citations: list[dict]) -> list[dict]:
    rng = random.Random(SEEDS["hearings"])
    hearings = []
    matters_by_county: dict[str, list[str]] = {row["county"]: [] for row in COUNTIES}
    for case in cases:
        matters_by_county[case["county"]].append(case["case_number"])
    for citation in citations:
        matters_by_county[citation["county"]].append(citation["citation_number"])

    for index in range(1, 57):
        county = rng.choice(COUNTIES)["county"]
        hearing_date = random_day(rng, "2024-01-10", "2025-07-20")
        candidates = matters_by_county[county]
        matter_count = rng.choice([1, 1, 2, 2, 3, 4])
        matters = sorted(rng.sample(candidates, min(len(candidates), matter_count)))
        minute_entries = []
        for matter in matters:
            minute_entries.append(
                {
                    "matter_id": matter,
                    "entry_type": rng.choice(["appearance", "plea", "review", "financial", "continuance"]),
                    "note": rng.choice(
                        [
                            "Minute note contains abbreviated attorney initials; verify against live case record.",
                            "Outcome entered from bench sheet; financial amount may be preliminary.",
                            "Defendant name matches a similar record; check date of birth before filing.",
                            "Hearing continued after docket call.",
                            "Clerk flagged stale export discrepancy.",
                        ]
                    ),
                    "status": rng.choice(["finalized", "draft", "needs_review"]),
                }
            )
        hearings.append(
            {
                "hearing_id": f"HRG-{index:04d}",
                "county": county,
                "hearing_date": hearing_date,
                "judge": rng.choice(JUDGES),
                "clerk": rng.choice(CLERKS),
                "matters": matters,
                "minute_entries": minute_entries,
            }
        )

    fixed_hearings = [
        {
            "hearing_id": "HRG-9001",
            "county": "Marion",
            "hearing_date": "2024-10-02",
            "judge": "Hon. Amara Kline",
            "clerk": "Dana Holt",
            "matters": ["24-MAR-00305"],
            "minute_entries": [
                {
                    "matter_id": "24-MAR-00305",
                    "entry_type": "disposition",
                    "note": "Bench sheet referenced amended count; live docket correction controls final charge description.",
                    "status": "finalized",
                }
            ],
        },
        {
            "hearing_id": "HRG-9002",
            "county": "Columbia",
            "hearing_date": "2025-04-04",
            "judge": "Hon. Robert Vale",
            "clerk": "Marcus Lee",
            "matters": ["25-COL-00112"],
            "minute_entries": [
                {
                    "matter_id": "25-COL-00112",
                    "entry_type": "plea",
                    "note": "Deferred entry accepted; treatment proof due before next review.",
                    "status": "finalized",
                }
            ],
        },
    ]
    hearings.extend(fixed_hearings)
    return sorted(hearings, key=lambda row: (row["hearing_date"], row["county"], row["hearing_id"]))


def stale_case_record(case: dict, rng: random.Random) -> dict:
    stale = {
        "source_type": "case",
        "case_number": case["case_number"],
        "county": case["county"],
        "defendant_name": case["defendant_name"],
        "status": case["status"],
        "defense_attorney": case["defense_attorney"],
        "balance_due_hint": None,
        "known_conflict": rng.choice(
            [
                "status may be older than live docket",
                "attorney may be prior assignment",
                "balance is from a prior ledger batch",
                "charge text may predate amendment",
            ]
        ),
    }
    if rng.random() < 0.45:
        stale["status"] = rng.choice(["open", "closed", "pending", "review"])
    if rng.random() < 0.35:
        stale["defense_attorney"] = rng.choice(["Former Counsel", "Public Defender Pending", case["defense_attorney"]])
    return stale


def stale_citation_record(citation: dict, rng: random.Random) -> dict:
    return {
        "source_type": "citation",
        "citation_number": citation["citation_number"],
        "county": citation["county"],
        "defendant_name": citation["defendant_name"],
        "hearing_date": add_days(citation["hearing_date"], rng.choice([-7, -1, 0, 14])),
        "disposition": rng.choice([citation["disposition"], "pending", "not_imported"]),
        "known_conflict": "citation export may not include later plea or payment-plan action",
    }


def generate_stale_exports(cases: list[dict], citations: list[dict]) -> list[dict]:
    rng = random.Random(SEEDS["stale_exports"])
    exports = []
    export_names = [
        "case_status_roster",
        "financial_ledger_snapshot",
        "citation_hearing_calendar",
        "attorney_assignment_export",
        "probation_review_queue",
    ]
    for index in range(10):
        county = COUNTIES[index % len(COUNTIES)]["county"]
        name = export_names[index % len(export_names)]
        county_cases = [row for row in cases if row["county"] == county]
        county_citations = [row for row in citations if row["county"] == county]
        records = []
        if county_cases:
            for case in rng.sample(county_cases, min(len(county_cases), rng.randint(5, 9))):
                records.append(stale_case_record(case, rng))
        if county_citations and name in {
            "citation_hearing_calendar",
            "financial_ledger_snapshot",
            "case_status_roster",
        }:
            for citation in rng.sample(county_citations, min(len(county_citations), rng.randint(2, 5))):
                records.append(stale_citation_record(citation, rng))
        exports.append(
            {
                "county": county,
                "name": name,
                "export_date": random_day(rng, "2023-11-01", "2025-02-28"),
                "records": records,
            }
        )
    return sorted(exports, key=lambda row: (row["county"], row["name"], row["export_date"]))


def build_dataset() -> dict:
    attorneys = build_attorneys()
    cases = generate_cases(attorneys)
    citations = generate_citations()
    fee_schedules = generate_fee_schedules()
    policies = generate_payment_policies()
    obligations = generate_financial_obligations(cases, fee_schedules, policies)
    docket_entries = generate_docket_entries(cases)
    hearings = generate_hearings(cases, citations)
    stale_exports = generate_stale_exports(cases, citations)
    return {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": GENERATED_AT,
            "seeds": SEEDS,
            "description": "Shared court clerk operations records for training and test tasks.",
        },
        "counties": COUNTIES,
        "attorneys": attorneys,
        "cases": cases,
        "citations": citations,
        "fee_schedules": fee_schedules,
        "payment_policies": policies,
        "financial_obligations": obligations,
        "docket_entries": docket_entries,
        "hearings": hearings,
        "stale_exports": stale_exports,
    }


def endpoint_list() -> list[str]:
    return [
        "GET /health",
        "GET /api/counties",
        "GET /api/cases",
        "GET /api/cases?county=<county>&matter_type=<type>&status=<status>",
        "GET /api/cases/<case_number>",
        "GET /api/citations",
        "GET /api/citations/<citation_number>",
        "GET /api/hearings?date=<YYYY-MM-DD>&county=<county>",
        "GET /api/attorneys",
        "GET /api/fees?county=<county>&matter_type=<type>&effective_on=<YYYY-MM-DD>",
        "GET /api/payment-policies?county=<county>",
        "GET /api/financial-obligations?case_number=<case_number>",
        "GET /api/docket?case_number=<case_number>",
        "GET /api/stale-exports?county=<county>&name=<export_name>",
        "GET /api/search?q=<text>",
        "GET /docs",
    ]


def build_manifest(dataset: dict) -> dict:
    docket_entry_total = sum(len(row["entries"]) for row in dataset["docket_entries"])
    stale_record_total = sum(len(row["records"]) for row in dataset["stale_exports"])
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": GENERATED_AT,
        "seeds": SEEDS,
        "record_counts": {
            "counties": len(dataset["counties"]),
            "attorneys": len(dataset["attorneys"]),
            "cases": len(dataset["cases"]),
            "citations": len(dataset["citations"]),
            "fee_schedule_rows": len(dataset["fee_schedules"]),
            "payment_policies": len(dataset["payment_policies"]),
            "financial_obligations": len(dataset["financial_obligations"]),
            "docket_case_records": len(dataset["docket_entries"]),
            "docket_entries": docket_entry_total,
            "hearings": len(dataset["hearings"]),
            "stale_exports": len(dataset["stale_exports"]),
            "stale_export_records": stale_record_total,
        },
        "files": [
            "env/generate_data.py",
            "env/server.py",
            "env/setup.sh",
            "env/data/clerk_ops.json",
            "env/data/manifest.json",
        ],
        "endpoints": endpoint_list(),
        "selected_named_counties": [row["county"] for row in COUNTIES],
        "known_noise_categories": [
            "similar defendant names and nearby dates of birth",
            "nearby case and citation numbers",
            "obsolete fee rows with explicit effective dates",
            "stale exports with older status, attorney, hearing, and ledger values",
            "draft or needs-review hearing minute entries",
            "docket correction entries that supersede older notes",
            "missing first due dates for pending citations",
            "payment policy placeholder value for unknown case-file fields",
        ],
        "non_solver_visible_note": "This manifest describes generated shared records and endpoints only. It contains no task IDs, answer keys, or scoring rubrics.",
    }


def write_json_if_changed(path: Path, payload: dict) -> None:
    text = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    path.write_text(text, encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dataset = build_dataset()
    manifest = build_manifest(dataset)
    write_json_if_changed(DATA_FILE, dataset)
    write_json_if_changed(MANIFEST_FILE, manifest)
    print(f"Wrote {DATA_FILE.relative_to(BASE_DIR)}")
    print(f"Wrote {MANIFEST_FILE.relative_to(BASE_DIR)}")
    print(json.dumps(manifest["record_counts"], sort_keys=True))


if __name__ == "__main__":
    main()
