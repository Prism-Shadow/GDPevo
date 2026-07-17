#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


EXPECTED = {
    "task_id": "test_002",
    "case_id": "CASE-HEAD-822",
    "patient_id": "PAT-2822",
    "primary_assessment": "pediatric_head_injury_with_concussion_features",
    "risk_tier": "high",
    "disposition": "ed_evaluation_ct_consideration",
    "imaging_recommendation": "ct_or_ed_per_protocol",
    "red_flags": [
        "head_impact",
        "brief_loss_of_consciousness",
        "repeated_vomiting",
        "worsening_headache",
    ],
    "absent_red_flags": [
        "abnormal_gcs",
        "seizure",
        "focal_weakness",
        "basilar_skull_signs",
    ],
    "restrictions": [
        "no_driving_until_cleared",
        "no_high_risk_sports_until_cleared",
        "return_to_learn_accommodations",
    ],
    "follow_up": {
        "timeframe_hours": 0,
        "route": "emergency_department",
    },
    "evidence_ids": [
        "CASE-HEAD-822",
        "VISIT-HEAD-822",
        "OBS-HEAD-822-LOC",
        "OBS-HEAD-822-GCS",
        "OBS-HEAD-822-VOMIT",
        "OBS-HEAD-822-NEURO",
        "EXAM-HEAD-822",
    ],
    "safety_checks": {
        "no_false_seizure": True,
        "no_false_focal_weakness": True,
    },
}

RUBRIC = [
    {
        "id": "SP001",
        "weight": 1,
        "goal": "Correct concussion/head-injury classification and key symptom extraction.",
    },
    {
        "id": "SP002",
        "weight": 1,
        "goal": "Correct high-risk tier from repeated vomiting and worsening headache.",
    },
    {
        "id": "SP003",
        "weight": 1,
        "goal": "Correct ED and CT disposition rather than home observation.",
    },
    {
        "id": "SP004",
        "weight": 3,
        "goal": "Correct red-flag set and omission of absent seizure/focal weakness.",
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Correct no-return-to-play, driving, and school restrictions.",
    },
    {
        "id": "SP006",
        "weight": 1,
        "goal": "Correct follow-up and escalation timing.",
    },
    {
        "id": "SP007",
        "weight": 3,
        "goal": "Correct evidence ids and contradiction checks.",
    },
]


def candidate_path() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    env_path = os.environ.get("ANSWER_JSON")
    if env_path:
        return Path(env_path)
    return Path("answer.json")


def load_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def get_value(data, dotted_path, default=None):
    current = data
    for key in dotted_path.split("."):
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def norm_scalar(value):
    if isinstance(value, str):
        return value.strip()
    return value


def norm_set(value):
    if not isinstance(value, list):
        return None
    return {norm_scalar(item) for item in value}


def expect_equal(data, path):
    actual = norm_scalar(get_value(data, path))
    expected = get_value(EXPECTED, path)
    return actual == expected, {"path": path, "expected": expected, "actual": actual}


def expect_bool(data, path):
    actual = get_value(data, path)
    expected = get_value(EXPECTED, path)
    return actual is expected, {"path": path, "expected": expected, "actual": actual}


def expect_set(data, path):
    actual = norm_set(get_value(data, path))
    expected = set(get_value(EXPECTED, path))
    return actual == expected, {
        "path": path,
        "expected": sorted(expected),
        "actual": None if actual is None else sorted(actual),
    }


def expect_contains(data, path, expected_items):
    actual = norm_set(get_value(data, path))
    expected = {norm_scalar(item) for item in expected_items}
    passed = actual is not None and expected.issubset(actual)
    return passed, {
        "path": path,
        "expected_contains": sorted(expected),
        "actual": None if actual is None else sorted(actual),
    }


def combine(*checks):
    passed = all(item[0] for item in checks)
    details = [item[1] for item in checks]
    return passed, details


def check_point(point_id, data):
    if point_id == "SP001":
        return combine(
            expect_equal(data, "primary_assessment"),
            expect_contains(
                data,
                "red_flags",
                [
                    "brief_loss_of_consciousness",
                    "repeated_vomiting",
                    "worsening_headache",
                ],
            ),
        )
    if point_id == "SP002":
        return expect_equal(data, "risk_tier")
    if point_id == "SP003":
        return combine(
            expect_equal(data, "disposition"),
            expect_equal(data, "imaging_recommendation"),
        )
    if point_id == "SP004":
        return combine(
            expect_set(data, "red_flags"),
            expect_set(data, "absent_red_flags"),
        )
    if point_id == "SP005":
        return expect_set(data, "restrictions")
    if point_id == "SP006":
        return combine(
            expect_equal(data, "follow_up.timeframe_hours"),
            expect_equal(data, "follow_up.route"),
        )
    if point_id == "SP007":
        return combine(
            expect_equal(data, "case_id"),
            expect_equal(data, "patient_id"),
            expect_set(data, "evidence_ids"),
            expect_bool(data, "safety_checks.no_false_seizure"),
            expect_bool(data, "safety_checks.no_false_focal_weakness"),
        )
    raise ValueError(f"Unknown rubric point {point_id}")


def zero_result(error_message):
    total_weight = sum(point["weight"] for point in RUBRIC)
    details = []
    for point in RUBRIC:
        assigned = point["weight"] / total_weight
        details.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "assigned_score": assigned,
                "passed": False,
                "earned_score": 0.0,
                "details": [{"error": error_message}],
            }
        )
    return {"score": 0.0, "details": details}


def evaluate(data):
    total_weight = sum(point["weight"] for point in RUBRIC)
    details = []
    score = 0.0

    if not isinstance(data, dict):
        return zero_result("Candidate answer must be a JSON object.")

    for point in RUBRIC:
        assigned = point["weight"] / total_weight
        passed, point_details = check_point(point["id"], data)
        earned = assigned if passed else 0.0
        score += earned
        details.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "assigned_score": assigned,
                "passed": passed,
                "earned_score": earned,
                "details": point_details,
            }
        )

    return {"score": round(score, 10), "details": details}


def main():
    path = candidate_path()
    data, error = load_json(path)
    if error is not None:
        result = zero_result(f"Could not read candidate JSON at {path}: {error}")
    else:
        result = evaluate(data)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
