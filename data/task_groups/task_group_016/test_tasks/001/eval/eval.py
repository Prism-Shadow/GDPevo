#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


EXPECTED = {
    "task_id": "test_001",
    "case_id": "CASE-RESP-914",
    "patient_id": "PAT-1914",
    "primary_assessment": "community_acquired_pneumonia",
    "risk_level": "high",
    "disposition": "ed_transfer",
    "red_flags": [
        "hypoxemia_below_90",
        "pleuritic_chest_pain",
        "respiratory_distress",
        "persistent_fever",
        "worsening_shortness_of_breath",
    ],
    "recommended_tests": ["CXR-2V", "PULSE_OX_RECHECK", "SARS_FLU_RSV_PCR"],
    "medication_plan": {
        "antibiotic_strategy": "defer_antibiotic_selection_to_ed",
        "medication": None,
        "dose": None,
        "route": None,
        "frequency": None,
        "duration_days": None,
        "avoid_allergens": ["penicillin"],
    },
    "stabilization_actions": ["supplemental_oxygen", "urgent_ed_transfer"],
    "follow_up": {"timeframe_hours": 0, "route": "emergency_department"},
    "return_precautions": [
        "chest_pain",
        "confusion",
        "hypoxia",
        "persistent_fever",
        "worsening_shortness_of_breath",
    ],
    "evidence_ids": ["CASE-RESP-914", "IMG-RESP-914-CXR", "OBS-RESP-914-SPO2"],
    "safety_checks": {
        "no_penicillin_or_sulfa": True,
        "no_normal_cxr_claim": True,
        "no_clear_lungs_claim": True,
    },
}


RUBRIC = [
    {
        "id": "SP001",
        "weight": 3,
        "goal": "Correct CAP classification using focal findings and imaging.",
    },
    {
        "id": "SP002",
        "weight": 3,
        "goal": "Correct ED escalation from oxygen threshold and respiratory distress.",
    },
    {
        "id": "SP003",
        "weight": 2,
        "goal": "Correct test set, including CXR and viral testing.",
    },
    {
        "id": "SP004",
        "weight": 2,
        "goal": "Correct allergy handling and no unsafe outpatient antibiotic recommendation.",
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Correct stabilization actions before transfer.",
    },
    {
        "id": "SP006",
        "weight": 1,
        "goal": "Correct return or escalation precautions and follow-up ownership.",
    },
    {
        "id": "SP007",
        "weight": 3,
        "goal": "Correct evidence ids and no contradictory normal-CXR assertion.",
    },
]


def load_candidate(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def as_set(value):
    if not isinstance(value, list):
        return None
    try:
        return set(value)
    except TypeError:
        return None


def sorted_values(value):
    if value is None:
        return []
    return sorted(value, key=lambda item: str(item))


def get(data, *keys):
    cur = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def exact_set(data, *keys):
    value = get(data, *keys)
    return as_set(value)


def check_sp001(data):
    red_flags = exact_set(data, "red_flags")
    details = {
        "case_id": get(data, "case_id"),
        "patient_id": get(data, "patient_id"),
        "primary_assessment": get(data, "primary_assessment"),
        "risk_level": get(data, "risk_level"),
        "red_flags": sorted_values(red_flags),
    }
    passed = (
        get(data, "case_id") == EXPECTED["case_id"]
        and get(data, "patient_id") == EXPECTED["patient_id"]
        and get(data, "primary_assessment") == EXPECTED["primary_assessment"]
        and get(data, "risk_level") == EXPECTED["risk_level"]
        and red_flags == set(EXPECTED["red_flags"])
    )
    return passed, details


def check_sp002(data):
    details = {"disposition": get(data, "disposition")}
    passed = get(data, "disposition") == EXPECTED["disposition"]
    return passed, details


def check_sp003(data):
    tests = exact_set(data, "recommended_tests")
    details = {
        "recommended_tests": sorted_values(tests),
        "expected_tests": sorted(EXPECTED["recommended_tests"]),
    }
    passed = tests == set(EXPECTED["recommended_tests"])
    return passed, details


def check_sp004(data):
    allergens = exact_set(data, "medication_plan", "avoid_allergens")
    medication_fields = ["medication", "dose", "route", "frequency", "duration_days"]
    details = {
        "antibiotic_strategy": get(data, "medication_plan", "antibiotic_strategy"),
        "avoid_allergens": sorted_values(allergens),
        "no_penicillin_or_sulfa": get(data, "safety_checks", "no_penicillin_or_sulfa"),
    }
    details.update({field: get(data, "medication_plan", field) for field in medication_fields})
    passed = (
        get(data, "medication_plan", "antibiotic_strategy") == EXPECTED["medication_plan"]["antibiotic_strategy"]
        and allergens == set(EXPECTED["medication_plan"]["avoid_allergens"])
        and get(data, "safety_checks", "no_penicillin_or_sulfa") is True
        and all(
            get(data, "medication_plan", field) == EXPECTED["medication_plan"][field] for field in medication_fields
        )
    )
    return passed, details


def check_sp005(data):
    actions = exact_set(data, "stabilization_actions")
    details = {
        "stabilization_actions": sorted_values(actions),
        "expected_stabilization_actions": sorted(EXPECTED["stabilization_actions"]),
    }
    passed = actions == set(EXPECTED["stabilization_actions"])
    return passed, details


def check_sp006(data):
    precautions = exact_set(data, "return_precautions")
    details = {
        "follow_up": get(data, "follow_up"),
        "return_precautions": sorted_values(precautions),
        "expected_return_precautions": sorted(EXPECTED["return_precautions"]),
    }
    passed = (
        get(data, "follow_up", "timeframe_hours") == EXPECTED["follow_up"]["timeframe_hours"]
        and get(data, "follow_up", "route") == EXPECTED["follow_up"]["route"]
        and precautions == set(EXPECTED["return_precautions"])
    )
    return passed, details


def check_sp007(data):
    evidence = exact_set(data, "evidence_ids")
    details = {
        "evidence_ids": sorted_values(evidence),
        "expected_evidence_ids": sorted(EXPECTED["evidence_ids"]),
        "no_normal_cxr_claim": get(data, "safety_checks", "no_normal_cxr_claim"),
        "no_clear_lungs_claim": get(data, "safety_checks", "no_clear_lungs_claim"),
    }
    passed = (
        evidence == set(EXPECTED["evidence_ids"])
        and get(data, "safety_checks", "no_normal_cxr_claim") is True
        and get(data, "safety_checks", "no_clear_lungs_claim") is True
    )
    return passed, details


CHECKS = {
    "SP001": check_sp001,
    "SP002": check_sp002,
    "SP003": check_sp003,
    "SP004": check_sp004,
    "SP005": check_sp005,
    "SP006": check_sp006,
    "SP007": check_sp007,
}


def resolve_candidate_path():
    if len(sys.argv) > 1 and sys.argv[1]:
        return Path(sys.argv[1])
    env_path = os.environ.get("ANSWER_JSON")
    if env_path:
        return Path(env_path)
    return Path("answer.json")


def main():
    candidate_path = resolve_candidate_path()
    candidate, error = load_candidate(candidate_path)
    total_weight = sum(item["weight"] for item in RUBRIC)

    if error is not None:
        details = []
        for item in RUBRIC:
            assigned = item["weight"] / total_weight
            details.append(
                {
                    "id": item["id"],
                    "goal": item["goal"],
                    "weight": item["weight"],
                    "assigned_score": assigned,
                    "passed": False,
                    "earned_score": 0.0,
                    "details": {"error": error},
                }
            )
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "candidate_path": str(candidate_path),
                    "details": details,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    details = []
    score = 0.0
    for item in RUBRIC:
        assigned = item["weight"] / total_weight
        passed, check_details = CHECKS[item["id"]](candidate)
        earned = assigned if passed else 0.0
        score += earned
        details.append(
            {
                "id": item["id"],
                "goal": item["goal"],
                "weight": item["weight"],
                "assigned_score": assigned,
                "passed": passed,
                "earned_score": earned,
                "details": check_details,
            }
        )

    print(
        json.dumps(
            {
                "score": round(score, 10),
                "candidate_path": str(candidate_path),
                "details": details,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
