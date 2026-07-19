#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED = {
    "application_id": "L-TR5-001",
    "recommended_posture": "request_follow_up",
    "same_premises_basis_applies": True,
    "covered_risk_codes": ["NOISE", "PATIO_BOUNDARY"],
    "verification_gap_codes": [
        "camera_evidence_missing",
        "food_service_evidence_missing",
        "floor_plan_conflicting",
        "late_night_monitoring_needed",
        "tax_hold_unresolved",
    ],
    "standard_obligation_codes": ["ID_CHECK", "HOURS", "FOOD_SERVICE"],
    "location_specific_control_codes": ["NOISE", "PATIO"],
    "first_90_day_plan": [
        {"check_code": "camera_export_test", "timing": "first_30_days"},
        {"check_code": "food_service_service_area_check", "timing": "first_30_days"},
        {"check_code": "late_night_closing_visit", "timing": "days_31_60"},
        {"check_code": "noise_patio_boundary_check", "timing": "days_61_90"},
    ],
    "escalation_trigger_codes": [
        "after_hours_service",
        "missing_camera_coverage",
        "footage_not_produced",
        "food_service_not_available",
        "noise_or_patio_breach",
        "open_tax_hold_uncleared",
    ],
}


POINTS = [
    {
        "id": "SP001",
        "goal": "Correct target application and recommended issuance posture.",
        "weight": 3,
        "check": "posture",
    },
    {
        "id": "SP002",
        "goal": "Correctly determines whether same-premises history remains applicable.",
        "weight": 2,
        "check": "same_premises",
    },
    {
        "id": "SP003",
        "goal": "Correctly identifies risks covered by current active controls.",
        "weight": 2,
        "check": "covered_risks",
    },
    {
        "id": "SP004",
        "goal": "Correctly identifies unresolved verification gaps.",
        "weight": 3,
        "check": "verification_gaps",
    },
    {
        "id": "SP005",
        "goal": "Correctly separates ordinary standard obligations for the license class.",
        "weight": 2,
        "check": "standard_obligations",
    },
    {
        "id": "SP006",
        "goal": "Correctly identifies current location-specific controls.",
        "weight": 2,
        "check": "location_controls",
    },
    {
        "id": "SP007",
        "goal": "Correctly provides the first-90-day monitoring plan in operational sequence.",
        "weight": 2,
        "check": "first_90_day_plan",
    },
    {
        "id": "SP008",
        "goal": "Correctly identifies escalation triggers for field staff.",
        "weight": 2,
        "check": "escalation_triggers",
    },
]


def load_candidate(path):
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def exact_set(candidate, field):
    value = candidate.get(field)
    if not isinstance(value, list):
        return False, f"{field} is not a list"
    if any(not isinstance(item, str) for item in value):
        return False, f"{field} contains non-string values"
    if len(value) != len(set(value)):
        return False, f"{field} contains duplicate codes"
    expected = set(EXPECTED[field])
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        return False, f"missing={missing}; extra={extra}"
    return True, f"matched {sorted(expected)}"


def exact_plan(candidate):
    value = candidate.get("first_90_day_plan")
    if not isinstance(value, list):
        return False, "first_90_day_plan is not a list"
    actual = []
    for item in value:
        if not isinstance(item, dict):
            return False, "first_90_day_plan contains a non-object item"
        actual.append({"check_code": item.get("check_code"), "timing": item.get("timing")})
    if actual != EXPECTED["first_90_day_plan"]:
        return False, f"expected ordered plan {EXPECTED['first_90_day_plan']}; got {actual}"
    return True, "matched ordered first-90-day plan"


def evaluate_point(point, candidate, parse_error):
    if parse_error:
        return False, f"candidate JSON could not be read: {parse_error}"
    if not isinstance(candidate, dict):
        return False, "candidate root is not a JSON object"

    check = point["check"]
    if check == "posture":
        ok = (
            candidate.get("application_id") == EXPECTED["application_id"]
            and candidate.get("recommended_posture") == EXPECTED["recommended_posture"]
        )
        return (
            ok,
            f"application_id={candidate.get('application_id')!r}; recommended_posture={candidate.get('recommended_posture')!r}",
        )
    if check == "same_premises":
        ok = candidate.get("same_premises_basis_applies") is EXPECTED["same_premises_basis_applies"]
        return ok, f"same_premises_basis_applies={candidate.get('same_premises_basis_applies')!r}"
    if check == "covered_risks":
        return exact_set(candidate, "covered_risk_codes")
    if check == "verification_gaps":
        return exact_set(candidate, "verification_gap_codes")
    if check == "standard_obligations":
        return exact_set(candidate, "standard_obligation_codes")
    if check == "location_controls":
        return exact_set(candidate, "location_specific_control_codes")
    if check == "first_90_day_plan":
        return exact_plan(candidate)
    if check == "escalation_triggers":
        return exact_set(candidate, "escalation_trigger_codes")
    return False, f"unknown check {check}"


def main():
    script_dir = Path(__file__).resolve().parent
    default_candidate = script_dir.parent / "output" / "answer.json"
    candidate_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_candidate
    candidate, parse_error = load_candidate(candidate_path)

    total_weight = sum(point["weight"] for point in POINTS)
    results = []
    score = 0.0

    for point in POINTS:
        assigned = point["weight"] / total_weight
        passed, details = evaluate_point(point, candidate, parse_error)
        earned = assigned if passed else 0.0
        score += earned
        results.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "assigned_score": round(assigned, 10),
                "passed": bool(passed),
                "earned_score": round(earned, 10),
                "details": details,
            }
        )

    print(json.dumps({"score": round(score, 10), "points": results}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
