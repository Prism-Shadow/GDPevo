#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED = {
    "review_date": "2025-02-13",
    "case_reviews": [
        {
            "case_id": "AUTH00007",
            "service_category": "Durable Medical Equipment",
            "criteria_source_id": "SRC003",
            "nurse_recommendation": "approve_as_requested",
            "md_escalation_required": False,
            "md_escalation_reason_code": "none",
            "missing_evidence_keys": [],
            "p2p_suitable": False,
            "approved_units": 12,
        },
        {
            "case_id": "AUTH00008",
            "service_category": "Experimental Therapy",
            "criteria_source_id": "SRC003",
            "nurse_recommendation": "escalate_to_md",
            "md_escalation_required": True,
            "md_escalation_reason_code": "benefit_exclusion_or_mandatory_md",
            "missing_evidence_keys": ["not_experimental", "standard_options_failed"],
            "p2p_suitable": False,
            "approved_units": None,
        },
        {
            "case_id": "AUTH00009",
            "service_category": "Home Health",
            "criteria_source_id": "SRC003",
            "nurse_recommendation": "escalate_to_md",
            "md_escalation_required": True,
            "md_escalation_reason_code": "criteria_not_clearly_met",
            "missing_evidence_keys": ["homebound_status", "physician_plan"],
            "p2p_suitable": True,
            "approved_units": None,
        },
        {
            "case_id": "AUTH00010",
            "service_category": "Physical Therapy",
            "criteria_source_id": "SRC003",
            "nurse_recommendation": "escalate_to_md",
            "md_escalation_required": True,
            "md_escalation_reason_code": "adverse_multiline_request",
            "missing_evidence_keys": ["functional_limitation", "plan_of_care"],
            "p2p_suitable": True,
            "approved_units": None,
        },
        {
            "case_id": "AUTH00011",
            "service_category": "Physical Therapy",
            "criteria_source_id": "SRC003",
            "nurse_recommendation": "escalate_to_md",
            "md_escalation_required": True,
            "md_escalation_reason_code": "criteria_not_clearly_met",
            "missing_evidence_keys": [
                "functional_limitation",
                "measurable_progress",
                "plan_of_care",
            ],
            "p2p_suitable": True,
            "approved_units": None,
        },
        {
            "case_id": "AUTH00012",
            "service_category": "Physical Therapy",
            "criteria_source_id": "SRC003",
            "nurse_recommendation": "escalate_to_md",
            "md_escalation_required": True,
            "md_escalation_reason_code": "criteria_not_clearly_met",
            "missing_evidence_keys": [
                "functional_limitation",
                "measurable_progress",
                "plan_of_care",
            ],
            "p2p_suitable": True,
            "approved_units": None,
        },
    ],
    "queue_counts": {
        "md_escalations_by_service_category": {
            "Experimental Therapy": 1,
            "Home Health": 1,
            "Physical Therapy": 3,
        },
        "total_md_escalations": 5,
        "nurse_approval_count": 1,
        "p2p_suitable_count": 4,
    },
}


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def case_map(doc):
    reviews = doc.get("case_reviews", [])
    if not isinstance(reviews, list):
        return {}
    return {str(row.get("case_id")): row for row in reviews if isinstance(row, dict)}


def normalize_missing(value):
    if not isinstance(value, list):
        return value
    return sorted(str(item) for item in value)


def field_map(doc, fields):
    mapped = {}
    for case_id, row in case_map(doc).items():
        mapped[case_id] = {}
        for field in fields:
            value = row.get(field)
            if field == "missing_evidence_keys":
                value = normalize_missing(value)
            mapped[case_id][field] = value
    return mapped


def expected_field_map(fields):
    return field_map(EXPECTED, fields)


def queue_counts(doc):
    counts = doc.get("queue_counts")
    return counts if isinstance(counts, dict) else {}


def add_point(points, point_id, description, weight, passed, expected, actual):
    points.append(
        {
            "id": point_id,
            "description": description,
            "weight": weight,
            "passed": bool(passed),
            "score": weight if passed else 0,
            "expected": expected,
            "actual": actual,
        }
    )


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0, "max_score": 1, "raw_score": 0, "max_raw_score": 14, "points": []}))
        return 2

    try:
        candidate = load_json(sys.argv[1])
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": 1,
                    "raw_score": 0,
                    "max_raw_score": 14,
                    "error": f"invalid JSON: {exc}",
                    "points": [],
                }
            )
        )
        return 1

    points = []
    add_point(
        points,
        "SP001",
        "Review date",
        1,
        candidate.get("review_date") == EXPECTED["review_date"],
        EXPECTED["review_date"],
        candidate.get("review_date"),
    )

    expected_cases = sorted(case_map(EXPECTED))
    actual_cases = sorted(case_map(candidate))
    add_point(
        points,
        "SP002",
        "Nurse recommendation and service category for all target cases",
        3,
        actual_cases == expected_cases
        and field_map(candidate, ["service_category", "nurse_recommendation"])
        == expected_field_map(["service_category", "nurse_recommendation"]),
        expected_field_map(["service_category", "nurse_recommendation"]),
        field_map(candidate, ["service_category", "nurse_recommendation"]),
    )

    add_point(
        points,
        "SP003",
        "MD escalation flag and reason code",
        2,
        actual_cases == expected_cases
        and field_map(candidate, ["md_escalation_required", "md_escalation_reason_code"])
        == expected_field_map(["md_escalation_required", "md_escalation_reason_code"]),
        expected_field_map(["md_escalation_required", "md_escalation_reason_code"]),
        field_map(candidate, ["md_escalation_required", "md_escalation_reason_code"]),
    )

    add_point(
        points,
        "SP004",
        "Criteria source selection",
        2,
        actual_cases == expected_cases
        and field_map(candidate, ["criteria_source_id"]) == expected_field_map(["criteria_source_id"]),
        expected_field_map(["criteria_source_id"]),
        field_map(candidate, ["criteria_source_id"]),
    )

    add_point(
        points,
        "SP005",
        "Missing evidence key set",
        2,
        actual_cases == expected_cases
        and field_map(candidate, ["missing_evidence_keys"]) == expected_field_map(["missing_evidence_keys"]),
        expected_field_map(["missing_evidence_keys"]),
        field_map(candidate, ["missing_evidence_keys"]),
    )

    add_point(
        points,
        "SP006",
        "P2P suitability",
        2,
        actual_cases == expected_cases
        and field_map(candidate, ["p2p_suitable"]) == expected_field_map(["p2p_suitable"]),
        expected_field_map(["p2p_suitable"]),
        field_map(candidate, ["p2p_suitable"]),
    )

    add_point(
        points,
        "SP007",
        "Approved units for nurse-approved cases",
        1,
        actual_cases == expected_cases
        and field_map(candidate, ["approved_units"]) == expected_field_map(["approved_units"]),
        expected_field_map(["approved_units"]),
        field_map(candidate, ["approved_units"]),
    )

    add_point(
        points,
        "SP008",
        "Queue counts",
        1,
        queue_counts(candidate) == EXPECTED["queue_counts"],
        EXPECTED["queue_counts"],
        queue_counts(candidate),
    )

    raw_score = sum(point["score"] for point in points)
    max_raw_score = sum(point["weight"] for point in points)
    result = {
        "score": raw_score / max_raw_score,
        "max_score": 1,
        "raw_score": raw_score,
        "max_raw_score": max_raw_score,
        "points": points,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
