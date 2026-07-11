#!/usr/bin/env python3
import json
import sys
from pathlib import Path


PATIENT_IDS = ["CCP-4158", "CCP-4162", "CCP-4179", "CCP-4185", "CHR-2094"]

POINTS = [
    ("task_metadata", 1),
    ("enrollment_decisions", 3),
    ("missing_item_sets", 1),
    ("cadence_fields", 1),
    ("chart_ready_flags", 2),
    ("chart_next_owners", 2),
    ("chart_missing_sections", 1),
    ("nurse_escalation", 2),
    ("telehealth_eligible_patients", 2),
    ("approved_count", 1),
]

SET_FIELDS = {"missing_items", "chart_missing_sections", "escalation_patients", "telehealth_eligible_patients"}


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize(value):
    if isinstance(value, dict):
        normalized = {}
        for key, child in value.items():
            item = normalize(child)
            if key in SET_FIELDS and isinstance(item, list):
                item = sorted(item)
            normalized[key] = item
        if isinstance(normalized.get("record_reviews"), list):
            normalized["record_reviews"] = sorted(
                normalized["record_reviews"],
                key=lambda row: row.get("patient_id", "") if isinstance(row, dict) else "",
            )
        return normalized
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def row_map(answer):
    rows = answer.get("record_reviews")
    if not isinstance(rows, list):
        return {}
    return {
        row.get("patient_id"): row for row in rows if isinstance(row, dict) and row.get("patient_id") in PATIENT_IDS
    }


def fields(rows, names):
    return {patient_id: {name: rows.get(patient_id, {}).get(name) for name in names} for patient_id in PATIENT_IDS}


def score(expected, actual):
    expected = normalize(expected)
    actual = normalize(actual)
    expected_rows = row_map(expected)
    actual_rows = row_map(actual)

    checks = {
        "task_metadata": (
            actual.get("task_id") == expected.get("task_id")
            and actual.get("review_date") == expected.get("review_date")
        ),
        "enrollment_decisions": (
            fields(actual_rows, ["record_type", "enrollment_decision"])
            == fields(expected_rows, ["record_type", "enrollment_decision"])
        ),
        "missing_item_sets": (fields(actual_rows, ["missing_items"]) == fields(expected_rows, ["missing_items"])),
        "cadence_fields": (
            fields(actual_rows, ["proposed_program", "follow_up_cadence", "coordinator", "consent_outcome"])
            == fields(expected_rows, ["proposed_program", "follow_up_cadence", "coordinator", "consent_outcome"])
        ),
        "chart_ready_flags": (fields(actual_rows, ["chart_ready"]) == fields(expected_rows, ["chart_ready"])),
        "chart_next_owners": (
            fields(actual_rows, ["chart_next_owner"]) == fields(expected_rows, ["chart_next_owner"])
        ),
        "chart_missing_sections": (
            fields(actual_rows, ["chart_missing_sections"]) == fields(expected_rows, ["chart_missing_sections"])
        ),
        "nurse_escalation": (
            {
                "list": actual.get("escalation_patients"),
                "flags": fields(actual_rows, ["nurse_escalation"]),
            }
            == {
                "list": expected.get("escalation_patients"),
                "flags": fields(expected_rows, ["nurse_escalation"]),
            }
        ),
        "telehealth_eligible_patients": (
            actual.get("telehealth_eligible_patients") == expected.get("telehealth_eligible_patients")
        ),
        "approved_count": actual.get("approved_count") == expected.get("approved_count"),
    }

    earned = 0
    details = []
    for name, weight in POINTS:
        passed = checks[name]
        if passed:
            earned += weight
        details.append(
            {
                "name": name,
                "awarded": weight if passed else 0,
                "possible": weight,
                "passed": passed,
            }
        )

    max_score = sum(weight for _, weight in POINTS)
    return {
        "score": earned,
        "max_score": max_score,
        "passed": earned == max_score,
        "details": details,
    }


def main():
    if len(sys.argv) not in {2, 3}:
        print("Usage: evaluator.py ACTUAL_JSON [EXPECTED_JSON]", file=sys.stderr)
        return 2

    task_dir = Path(__file__).resolve().parents[1]
    actual_path = Path(sys.argv[1])
    expected_path = Path(sys.argv[2]) if len(sys.argv) == 3 else task_dir / "output" / "answer.json"

    try:
        actual = load_json(actual_path)
        expected = load_json(expected_path)
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
                sort_keys=True,
            )
        )
        return 1

    result = score(expected, actual)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
