#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED = {
    "task_id": "train_005",
    "review_date": "2026-07-07",
    "patient_reviews": [
        {
            "patient_id": "CCP-4107",
            "proposed_program": "Cardiometabolic Combo",
            "enrollment_decision": "hold_missing_consent",
            "missing_items": ["consent_signed", "program_form_complete"],
            "follow_up_cadence": "biweekly_checkin",
            "coordinator": "M. Okafor",
            "consent_outcome": "not_obtained",
            "telehealth_preference": "phone",
        },
        {
            "patient_id": "CCP-4116",
            "proposed_program": "Cardiometabolic Combo",
            "enrollment_decision": "hold_missing_consent",
            "missing_items": ["consent_signed"],
            "follow_up_cadence": "weekly_nurse_call",
            "coordinator": "R. Alvarez",
            "consent_outcome": "declined",
            "telehealth_preference": "in-person",
        },
        {
            "patient_id": "CCP-4133",
            "proposed_program": "Hypertension Pathway",
            "enrollment_decision": "clinical_review",
            "missing_items": ["diagnosis_support", "program_form_complete"],
            "follow_up_cadence": "weekly_nurse_call",
            "coordinator": "R. Alvarez",
            "consent_outcome": "signed",
            "telehealth_preference": "video",
        },
        {
            "patient_id": "CCP-4144",
            "proposed_program": "Renal Risk Monitoring",
            "enrollment_decision": "enroll_with_nurse_escalation",
            "missing_items": [],
            "follow_up_cadence": "weekly_nurse_call",
            "coordinator": "S. Lin",
            "consent_outcome": "signed",
            "telehealth_preference": "video",
        },
    ],
    "coordinator_queue": ["CCP-4107", "CCP-4116", "CCP-4133", "CCP-4144"],
    "escalation_count": 1,
}


POINTS = [
    ("enrollment_decisions", 3),
    ("program_selection", 2),
    ("missing_item_sets", 3),
    ("follow_up_cadences", 2),
    ("coordinator_queue", 2),
    ("escalation_count", 1),
    ("consent_outcomes", 1),
]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def by_patient(answer):
    rows = answer.get("patient_reviews", [])
    if not isinstance(rows, list):
        return {}
    normalized = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        patient_id = row.get("patient_id")
        if isinstance(patient_id, str):
            copy = dict(row)
            if isinstance(copy.get("missing_items"), list):
                copy["missing_items"] = sorted(copy["missing_items"])
            normalized[patient_id] = copy
    return normalized


def field_map(rows, field):
    return {patient_id: row.get(field) for patient_id, row in rows.items()}


def missing_map(rows):
    return {patient_id: sorted(row.get("missing_items", [])) for patient_id, row in rows.items()}


def score(candidate):
    expected_rows = by_patient(EXPECTED)
    candidate_rows = by_patient(candidate)
    details = []
    total = 0
    max_score = sum(weight for _, weight in POINTS)

    checks = {
        "enrollment_decisions": (
            field_map(candidate_rows, "enrollment_decision"),
            field_map(expected_rows, "enrollment_decision"),
        ),
        "program_selection": (
            field_map(candidate_rows, "proposed_program"),
            field_map(expected_rows, "proposed_program"),
        ),
        "missing_item_sets": (missing_map(candidate_rows), missing_map(expected_rows)),
        "follow_up_cadences": (
            field_map(candidate_rows, "follow_up_cadence"),
            field_map(expected_rows, "follow_up_cadence"),
        ),
        "coordinator_queue": (
            sorted(candidate.get("coordinator_queue", []))
            if isinstance(candidate.get("coordinator_queue", []), list)
            else candidate.get("coordinator_queue"),
            EXPECTED["coordinator_queue"],
        ),
        "escalation_count": (
            candidate.get("escalation_count"),
            EXPECTED["escalation_count"],
        ),
        "consent_outcomes": (
            field_map(candidate_rows, "consent_outcome"),
            field_map(expected_rows, "consent_outcome"),
        ),
    }

    for name, weight in POINTS:
        actual, expected = checks[name]
        passed = actual == expected
        awarded = weight if passed else 0
        total += awarded
        details.append(
            {
                "name": name,
                "awarded": awarded,
                "possible": weight,
                "passed": passed,
            }
        )

    return {
        "score": total,
        "max_score": max_score,
        "passed": total == max_score,
        "details": details,
    }


def main():
    if len(sys.argv) > 2:
        print("Usage: evaluator.py [candidate_answer.json]", file=sys.stderr)
        return 2
    task_dir = Path(__file__).resolve().parents[1]
    candidate_path = Path(sys.argv[1]) if len(sys.argv) == 2 else task_dir / "output" / "answer.json"
    try:
        candidate = load_json(candidate_path)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": sum(weight for _, weight in POINTS),
                    "passed": False,
                    "error": str(exc),
                },
                indent=2,
            )
        )
        return 1

    result = score(candidate)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
