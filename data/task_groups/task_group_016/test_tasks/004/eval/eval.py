#!/usr/bin/env python3
import json
import os
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any


EXPECTED = {
    "task_id": "test_004",
    "case_id": "CASE-CM-908",
    "patient_id": "PAT-4908",
    "risk_tier": "high",
    "program": "complex_care_management",
    "priority_problems": [
        "uncontrolled_diabetes",
        "chronic_kidney_disease_stage_4",
        "heart_failure_recent_admission",
        "hypertension",
        "polypharmacy",
        "transportation_barrier",
        "financial_food_barrier",
    ],
    "numeric_anchors": {
        "risk_score": 0.79,
        "hba1c_percent": 9.1,
        "egfr": 28,
        "blood_pressure": "158/92",
        "active_medication_count": 14,
    },
    "referrals": [
        "pharmacist",
        "social_worker",
        "transportation_benefits",
        "primary_care",
    ],
    "outreach_stance": "permission_based_plain_language",
    "care_plan_minima": {
        "min_problem_count": 3,
        "weekly_follow_up": True,
        "requires_member_stated_priority": True,
        "min_disciplines": 2,
    },
    "escalation_conditions": [
        "dyspnea_weight_gain_or_ed_return",
        "phq9_increase_or_item9_positive",
    ],
    "source_provenance": {
        "chart_facts": [
            "risk_score",
            "hba1c_percent",
            "egfr",
            "active_medication_count",
        ],
        "member_disclosure_needed": [
            "transportation_barrier",
            "financial_food_barrier",
            "medication_access_barrier",
        ],
    },
}


RUBRIC = [
    ("SP001", "Correct high-risk complex-care classification.", 3),
    ("SP002", "Correct priority problem set with numeric anchors.", 3),
    (
        "SP003",
        "Correct pharmacist referral from polypharmacy and high-risk medications.",
        2,
    ),
    (
        "SP004",
        "Correct social-work referral from transportation, financial, and food barriers.",
        2,
    ),
    (
        "SP005",
        "Correct refusal-sensitive outreach stance without pressure or jargon.",
        2,
    ),
    ("SP006", "Correct care-plan minima and follow-up cadence.", 2),
    (
        "SP007",
        "Correct escalation condition set covering clinical and behavioral-health domains.",
        2,
    ),
    ("SP008", "Correct source provenance handling.", 1),
]


def candidate_path() -> Path:
    if len(sys.argv) > 1 and sys.argv[1]:
        return Path(sys.argv[1])
    if os.environ.get("ANSWER_JSON"):
        return Path(os.environ["ANSWER_JSON"])
    return Path("answer.json")


def load_candidate(path: Path) -> tuple[Any, str]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), ""
    except Exception as exc:  # noqa: BLE001 - evaluator must report all load failures as JSON.
        return None, f"{type(exc).__name__}: {exc}"


def as_set(value: Any) -> set:
    if not isinstance(value, list):
        return set()
    normalized = set()
    for item in value:
        if isinstance(item, str):
            normalized.add(item.strip())
        else:
            normalized.add(item)
    return normalized


def get_obj(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def number_equal(actual: Any, expected: float, digits: int) -> bool:
    try:
        return round(float(actual), digits) == round(float(expected), digits)
    except (TypeError, ValueError):
        return False


def int_equal(actual: Any, expected: int) -> bool:
    return isinstance(actual, int) and actual == expected


def str_equal(actual: Any, expected: str) -> bool:
    return isinstance(actual, str) and actual.strip() == expected


def bool_equal(actual: Any, expected: bool) -> bool:
    return isinstance(actual, bool) and actual is expected


def set_equal(actual: Any, expected: Iterable[Any]) -> bool:
    return as_set(actual) == set(expected)


def contains_all(actual: Any, required: Iterable[Any]) -> bool:
    return set(required).issubset(as_set(actual))


def evaluate_points(data: dict[str, Any]) -> list[dict[str, Any]]:
    numeric = get_obj(data, "numeric_anchors")
    care_plan = get_obj(data, "care_plan_minima")
    provenance = get_obj(data, "source_provenance")

    checks: dict[str, dict[str, bool]] = {
        "SP001": {
            "risk_tier": data.get("risk_tier") == EXPECTED["risk_tier"],
            "program": data.get("program") == EXPECTED["program"],
        },
        "SP002": {
            "priority_problems": set_equal(data.get("priority_problems"), EXPECTED["priority_problems"]),
            "risk_score": number_equal(numeric.get("risk_score"), 0.79, 2),
            "hba1c_percent": number_equal(numeric.get("hba1c_percent"), 9.1, 1),
            "egfr": int_equal(numeric.get("egfr"), 28),
            "blood_pressure": str_equal(numeric.get("blood_pressure"), "158/92"),
            "active_medication_count": int_equal(numeric.get("active_medication_count"), 14),
        },
        "SP003": {"pharmacist_referral": contains_all(data.get("referrals"), ["pharmacist"])},
        "SP004": {
            "social_worker_referral": contains_all(data.get("referrals"), ["social_worker"]),
            "transportation_benefits_referral": contains_all(data.get("referrals"), ["transportation_benefits"]),
        },
        "SP005": {"outreach_stance": data.get("outreach_stance") == EXPECTED["outreach_stance"]},
        "SP006": {
            "min_problem_count": int_equal(care_plan.get("min_problem_count"), 3),
            "weekly_follow_up": bool_equal(care_plan.get("weekly_follow_up"), True),
            "requires_member_stated_priority": bool_equal(care_plan.get("requires_member_stated_priority"), True),
            "min_disciplines": int_equal(care_plan.get("min_disciplines"), 2),
        },
        "SP007": {
            "escalation_conditions": set_equal(data.get("escalation_conditions"), EXPECTED["escalation_conditions"])
        },
        "SP008": {
            "chart_facts": set_equal(
                provenance.get("chart_facts"),
                EXPECTED["source_provenance"]["chart_facts"],
            ),
            "member_disclosure_needed": set_equal(
                provenance.get("member_disclosure_needed"),
                EXPECTED["source_provenance"]["member_disclosure_needed"],
            ),
        },
    }

    total_weight = sum(weight for _, _, weight in RUBRIC)
    details = []
    for point_id, goal, weight in RUBRIC:
        assigned = weight / total_weight
        point_checks = checks[point_id]
        passed = all(point_checks.values())
        details.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": assigned,
                "passed": passed,
                "earned_score": assigned if passed else 0.0,
                "checks": point_checks,
            }
        )
    return details


def zero_result(path: Path, error: str) -> dict[str, Any]:
    total_weight = sum(weight for _, _, weight in RUBRIC)
    return {
        "score": 0.0,
        "total_raw_weight": total_weight,
        "candidate_path": str(path),
        "error": error,
        "details": [
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": weight / total_weight,
                "passed": False,
                "earned_score": 0.0,
                "checks": {"candidate_json_loaded": False},
            }
            for point_id, goal, weight in RUBRIC
        ],
    }


def main() -> int:
    path = candidate_path()
    candidate, error = load_candidate(path)
    if error:
        print(json.dumps(zero_result(path, error), indent=2, sort_keys=True))
        return 0
    if not isinstance(candidate, dict):
        print(
            json.dumps(
                zero_result(path, "Top-level JSON value must be an object."),
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    details = evaluate_points(candidate)
    score = sum(item["earned_score"] for item in details)
    result = {
        "score": round(score, 10),
        "total_raw_weight": sum(weight for _, _, weight in RUBRIC),
        "candidate_path": str(path),
        "details": details,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
