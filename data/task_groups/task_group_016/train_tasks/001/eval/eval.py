#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


EXPECTED = {
    "task_id": "train_001",
    "case_id": "CASE-RESP-102",
    "patient_id": "PAT-1002",
    "primary_assessment": "community_acquired_pneumonia",
    "risk_level": "moderate",
    "disposition": "outpatient_close_followup",
    "red_flags": ["hypoxemia_92_93", "pleuritic_chest_pain"],
    "recommended_tests": ["CXR-2V", "PULSE_OX_RECHECK", "SARS_FLU_RSV_PCR"],
    "medication_plan": {
        "antibiotic_strategy": "doxycycline_outpatient",
        "medication": "doxycycline",
        "dose": "100 mg",
        "route": "PO",
        "frequency": "BID",
        "duration_days": 5,
        "avoid_allergens": ["penicillin", "sulfonamide"],
    },
    "stabilization_actions": [],
    "follow_up": {"timeframe_hours": 48, "route": "primary_care_recheck"},
    "return_precautions": [
        "chest_pain",
        "confusion",
        "hemoptysis",
        "hypoxia",
        "persistent_fever",
        "worsening_shortness_of_breath",
    ],
    "evidence_ids": ["CASE-RESP-102", "IMG-RESP-102-CXR", "OBS-RESP-102-SPO2"],
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
        "goal": "Correct primary respiratory classification and diagnosis evidence.",
    },
    {
        "id": "SP002",
        "weight": 3,
        "goal": "Correct outpatient-vs-ED disposition under oxygen and vital thresholds.",
    },
    {
        "id": "SP003",
        "weight": 2,
        "goal": "Correct required diagnostic tests from symptoms, CXR, and exposure context.",
    },
    {
        "id": "SP004",
        "weight": 3,
        "goal": "Correct allergy-safe antibiotic selection and avoidance flags.",
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Correct medication dose, route, frequency, and duration.",
    },
    {
        "id": "SP006",
        "weight": 2,
        "goal": "Correct return precautions as a controlled set.",
    },
    {
        "id": "SP007",
        "weight": 1,
        "goal": "Correct follow-up timing and no contradictory normal-lung or CXR assertions.",
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
    normalized = as_set(value)
    return normalized


def check_sp001(data):
    expected_red_flags = set(EXPECTED["red_flags"])
    expected_evidence = set(EXPECTED["evidence_ids"])
    actual_evidence = exact_set(data, "evidence_ids")
    evidence_ok = actual_evidence is not None and expected_evidence.issubset(actual_evidence)
    details = {
        "task_id": get(data, "task_id"),
        "case_id": get(data, "case_id"),
        "patient_id": get(data, "patient_id"),
        "primary_assessment": get(data, "primary_assessment"),
        "risk_level": get(data, "risk_level"),
        "red_flags": sorted_values(exact_set(data, "red_flags")),
        "required_evidence_present": evidence_ok,
    }
    passed = (
        get(data, "task_id") == EXPECTED["task_id"]
        and get(data, "case_id") == EXPECTED["case_id"]
        and get(data, "patient_id") == EXPECTED["patient_id"]
        and get(data, "primary_assessment") == EXPECTED["primary_assessment"]
        and get(data, "risk_level") == EXPECTED["risk_level"]
        and exact_set(data, "red_flags") == expected_red_flags
        and evidence_ok
    )
    return passed, details


def check_sp002(data):
    actions = exact_set(data, "stabilization_actions")
    details = {
        "disposition": get(data, "disposition"),
        "stabilization_actions": sorted_values(actions),
    }
    passed = get(data, "disposition") == EXPECTED["disposition"] and actions == set(EXPECTED["stabilization_actions"])
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
    details = {
        "antibiotic_strategy": get(data, "medication_plan", "antibiotic_strategy"),
        "medication": get(data, "medication_plan", "medication"),
        "avoid_allergens": sorted_values(allergens),
        "no_penicillin_or_sulfa": get(data, "safety_checks", "no_penicillin_or_sulfa"),
    }
    passed = (
        get(data, "medication_plan", "antibiotic_strategy") == EXPECTED["medication_plan"]["antibiotic_strategy"]
        and get(data, "medication_plan", "medication") == EXPECTED["medication_plan"]["medication"]
        and allergens == set(EXPECTED["medication_plan"]["avoid_allergens"])
        and get(data, "safety_checks", "no_penicillin_or_sulfa") is True
    )
    return passed, details


def check_sp005(data):
    fields = ["dose", "route", "frequency", "duration_days"]
    details = {field: get(data, "medication_plan", field) for field in fields}
    passed = all(get(data, "medication_plan", field) == EXPECTED["medication_plan"][field] for field in fields)
    return passed, details


def check_sp006(data):
    precautions = exact_set(data, "return_precautions")
    details = {
        "return_precautions": sorted_values(precautions),
        "expected_return_precautions": sorted(EXPECTED["return_precautions"]),
    }
    passed = precautions == set(EXPECTED["return_precautions"])
    return passed, details


def check_sp007(data):
    details = {
        "follow_up": get(data, "follow_up"),
        "no_normal_cxr_claim": get(data, "safety_checks", "no_normal_cxr_claim"),
        "no_clear_lungs_claim": get(data, "safety_checks", "no_clear_lungs_claim"),
    }
    passed = (
        get(data, "follow_up", "timeframe_hours") == EXPECTED["follow_up"]["timeframe_hours"]
        and get(data, "follow_up", "route") == EXPECTED["follow_up"]["route"]
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
