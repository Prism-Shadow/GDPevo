#!/usr/bin/env python3
import json
import sys
from pathlib import Path


GOLD = {
    "application_id": "L-TR2-001",
    "recommended_posture": "request_follow_up",
    "same_premises_basis_applies": True,
    "covered_risk_codes": [
        "AFTER_HOURS",
        "ASSAULT",
        "MINOR_SALE",
        "SALE_TO_MINOR",
        "SAME_PREMISES",
    ],
    "verification_gap_codes": [
        "CONTROL_SIGNAGE_CONFLICTING",
        "CONTROL_SIGNAGE_CURRENT_MISSING",
        "OPEN_INCIDENT_FOLLOW_UP",
        "POLICE_MEMO_CONFLICTING",
    ],
    "standard_obligation_codes": [
        "FOOD_SERVICE",
        "HOURS",
        "ID_CHECK",
    ],
    "location_specific_control_codes": [
        "CCTV",
        "HOURS",
        "SECURITY",
    ],
    "first_90_day_plan": [
        {"check_code": "after_hours_visit", "timing": "days_31_60"},
        {"check_code": "control_signage_recheck", "timing": "first_30_days"},
        {"check_code": "id_check_observation", "timing": "first_30_days"},
        {"check_code": "police_memo_follow_up", "timing": "first_30_days"},
        {"check_code": "security_cctv_walkthrough", "timing": "first_30_days"},
    ],
    "escalation_trigger_codes": [
        "AFTER_HOURS_VIOLATION",
        "CONTROL_SIGNAGE_NOT_VERIFIED",
        "MAJOR_INCIDENT_REPORTED",
        "REFERRED_MINOR_SALE_UNRESOLVED",
        "SECURITY_CCTV_CONTROL_FAILURE",
    ],
}


POINTS = [
    {
        "id": "SP001",
        "goal": "Correct recommended issuance posture for the restricted transfer package.",
        "weight": 3,
        "kind": "exact",
        "field": "recommended_posture",
    },
    {
        "id": "SP002",
        "goal": "Correctly applies the same-premises basis to the target location.",
        "weight": 2,
        "kind": "exact",
        "field": "same_premises_basis_applies",
    },
    {
        "id": "SP003",
        "goal": "Identifies the complete covered risk-code set from settlement and incident history.",
        "weight": 2,
        "kind": "string_set",
        "field": "covered_risk_codes",
    },
    {
        "id": "SP004",
        "goal": "Identifies the complete unresolved verification-gap set.",
        "weight": 3,
        "kind": "string_set",
        "field": "verification_gap_codes",
    },
    {
        "id": "SP005",
        "goal": "Separates standard Restaurant license obligations from location controls.",
        "weight": 2,
        "kind": "string_set",
        "field": "standard_obligation_codes",
    },
    {
        "id": "SP006",
        "goal": "Identifies active location-specific settlement controls.",
        "weight": 2,
        "kind": "string_set",
        "field": "location_specific_control_codes",
    },
    {
        "id": "SP007",
        "goal": "Selects the correct first-90-day monitoring checks and timing windows.",
        "weight": 2,
        "kind": "plan_set",
        "field": "first_90_day_plan",
    },
    {
        "id": "SP008",
        "goal": "Identifies the correct escalation trigger codes for staff monitoring.",
        "weight": 1,
        "kind": "string_set",
        "field": "escalation_trigger_codes",
    },
]


def normalize_string_set(value):
    if not isinstance(value, list):
        return None
    normalized = []
    for item in value:
        if not isinstance(item, str):
            return None
        normalized.append(item.strip())
    return sorted(set(normalized))


def normalize_plan_set(value):
    if not isinstance(value, list):
        return None
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            return None
        check_code = item.get("check_code")
        timing = item.get("timing")
        if not isinstance(check_code, str) or not isinstance(timing, str):
            return None
        normalized.append((check_code.strip(), timing.strip()))
    return sorted(set(normalized))


def check_point(answer, point):
    field = point["field"]
    actual = answer.get(field) if isinstance(answer, dict) else None
    expected = GOLD[field]
    kind = point["kind"]
    if kind == "exact":
        passed = actual == expected
        detail = f"actual={actual!r}; expected={expected!r}"
    elif kind == "string_set":
        actual_norm = normalize_string_set(actual)
        expected_norm = normalize_string_set(expected)
        passed = actual_norm == expected_norm
        detail = f"actual={actual_norm!r}; expected={expected_norm!r}"
    elif kind == "plan_set":
        actual_norm = normalize_plan_set(actual)
        expected_norm = normalize_plan_set(expected)
        passed = actual_norm == expected_norm
        detail = f"actual={actual_norm!r}; expected={expected_norm!r}"
    else:
        passed = False
        detail = "unknown point kind"
    return passed, detail


def load_answer(path):
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:
        return None, str(exc)


def main():
    candidate_path = (
        sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1] / "output" / "answer.json")
    )
    answer, load_error = load_answer(candidate_path)
    total_weight = sum(point["weight"] for point in POINTS)
    scored_points = []
    score = 0.0

    for point in POINTS:
        assigned = point["weight"] / total_weight
        if load_error:
            passed = False
            detail = f"candidate answer could not be loaded: {load_error}"
        else:
            passed, detail = check_point(answer, point)
        earned = assigned if passed else 0.0
        score += earned
        scored_points.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "assigned_score": round(assigned, 6),
                "passed": passed,
                "earned_score": round(earned, 6),
                "details": detail,
            }
        )

    print(
        json.dumps(
            {
                "score": round(score, 6),
                "points": scored_points,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
