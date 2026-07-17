#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


EXPECTED = {
    "task_id": "test_003",
    "case_id": "CASE-K-919",
    "patient_id": "PAT-3919",
    "current_time": "2026-04-18T14:35:00Z",
    "latest_potassium": {
        "observation_id": "OBS-K-919-20260418-1320",
        "value_mmol_l": 2.8,
        "effective_time": "2026-04-18T13:20:00Z",
    },
    "replacement_required": True,
    "potassium_plan": "urgent_escalation",
    "oral_dose_mEq": None,
    "medication_order": {
        "ndc": "40032-917-01",
        "medication": "potassium chloride",
        "route": "per_urgent_protocol",
        "frequency": "per_urgent_protocol",
        "status": "defer_to_urgent_clinician",
    },
    "follow_up_lab": {
        "loinc": "2823-3",
        "scheduled_time": "2026-04-18T18:00:00Z",
    },
    "urgent_actions": [
        "urgent_clinician_notification",
        "ekg_now",
        "telemetry_or_ed_evaluation",
    ],
    "contraindications": {
        "dialysis_dependent": False,
        "arrhythmia_symptoms": True,
        "egfr": 58,
    },
    "evidence_ids": [
        "OBS-K-919-20260418-1320",
        "OBS-EGFR-919-20260417",
        "CASE-K-919",
    ],
}


RUBRIC = [
    {
        "id": "SP001",
        "weight": 3,
        "goal": "Correct latest final potassium observation.",
    },
    {
        "id": "SP002",
        "weight": 3,
        "goal": "Correct urgent escalation classification because K is below 3.0 and symptoms are present.",
    },
    {
        "id": "SP003",
        "weight": 2,
        "goal": "Correct not to use routine oral-only protocol dose as final plan.",
    },
    {
        "id": "SP004",
        "weight": 2,
        "goal": "Correct urgent monitoring and electrocardiogram action set.",
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Correct follow-up potassium timing under urgent branch.",
    },
    {
        "id": "SP006",
        "weight": 2,
        "goal": "Correct contraindication, eGFR, and rhythm evidence.",
    },
    {
        "id": "SP007",
        "weight": 1,
        "goal": "Correct medication and lab codes where applicable.",
    },
]


def candidate_path() -> Path:
    if len(sys.argv) > 1 and sys.argv[1]:
        return Path(sys.argv[1])
    if os.environ.get("ANSWER_JSON"):
        return Path(os.environ["ANSWER_JSON"])
    default = Path("answer.json")
    if default.exists():
        return default
    return Path(__file__).resolve().parents[1] / "output" / "answer.json"


def load_candidate(path: Path):
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Top-level JSON value must be an object.")
    return data


def get_path(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def norm_text(value):
    if value is None:
        return None
    return str(value).strip()


def eq_text(candidate, expected):
    return norm_text(candidate) == expected


def eq_bool(candidate, expected):
    return isinstance(candidate, bool) and candidate is expected


def eq_int(candidate, expected):
    return isinstance(candidate, int) and not isinstance(candidate, bool) and candidate == expected


def eq_null(candidate, expected):
    return candidate is None and expected is None


def eq_number_1dp(candidate, expected):
    try:
        return round(float(candidate), 1) == round(float(expected), 1)
    except (TypeError, ValueError):
        return False


def eq_string_set(candidate, expected):
    if not isinstance(candidate, list):
        return False
    normalized = [norm_text(item) for item in candidate]
    if any(item is None for item in normalized):
        return False
    return set(normalized) == set(expected) and len(normalized) == len(set(normalized))


def check_fields(data, checks):
    results = {}
    for dotted, expected, comparator in checks:
        actual = get_path(data, dotted)
        results[dotted] = {
            "expected": expected,
            "actual": actual,
            "passed": comparator(actual, expected),
        }
    return results


def evaluate(data):
    total_weight = sum(item["weight"] for item in RUBRIC)

    check_map = {
        "SP001": lambda d: check_fields(
            d,
            [
                ("latest_potassium.observation_id", EXPECTED["latest_potassium"]["observation_id"], eq_text),
                ("latest_potassium.value_mmol_l", EXPECTED["latest_potassium"]["value_mmol_l"], eq_number_1dp),
                ("latest_potassium.effective_time", EXPECTED["latest_potassium"]["effective_time"], eq_text),
            ],
        ),
        "SP002": lambda d: check_fields(
            d,
            [
                ("replacement_required", EXPECTED["replacement_required"], eq_bool),
                ("potassium_plan", EXPECTED["potassium_plan"], eq_text),
            ],
        ),
        "SP003": lambda d: check_fields(
            d,
            [
                ("oral_dose_mEq", EXPECTED["oral_dose_mEq"], eq_null),
                ("medication_order.route", EXPECTED["medication_order"]["route"], eq_text),
                ("medication_order.frequency", EXPECTED["medication_order"]["frequency"], eq_text),
                ("medication_order.status", EXPECTED["medication_order"]["status"], eq_text),
            ],
        ),
        "SP004": lambda d: {
            "urgent_actions": {
                "expected": EXPECTED["urgent_actions"],
                "actual": d.get("urgent_actions"),
                "passed": eq_string_set(d.get("urgent_actions"), EXPECTED["urgent_actions"]),
            },
        },
        "SP005": lambda d: check_fields(
            d,
            [("follow_up_lab.scheduled_time", EXPECTED["follow_up_lab"]["scheduled_time"], eq_text)],
        ),
        "SP006": lambda d: {
            **check_fields(
                d,
                [
                    (
                        "contraindications.dialysis_dependent",
                        EXPECTED["contraindications"]["dialysis_dependent"],
                        eq_bool,
                    ),
                    (
                        "contraindications.arrhythmia_symptoms",
                        EXPECTED["contraindications"]["arrhythmia_symptoms"],
                        eq_bool,
                    ),
                    ("contraindications.egfr", EXPECTED["contraindications"]["egfr"], eq_int),
                ],
            ),
            "evidence_ids": {
                "expected": EXPECTED["evidence_ids"],
                "actual": d.get("evidence_ids"),
                "passed": eq_string_set(d.get("evidence_ids"), EXPECTED["evidence_ids"]),
            },
        },
        "SP007": lambda d: check_fields(
            d,
            [
                ("medication_order.ndc", EXPECTED["medication_order"]["ndc"], eq_text),
                ("medication_order.medication", EXPECTED["medication_order"]["medication"], eq_text),
                ("follow_up_lab.loinc", EXPECTED["follow_up_lab"]["loinc"], eq_text),
            ],
        ),
    }

    details = []
    score = 0.0
    for item in RUBRIC:
        assigned = item["weight"] / total_weight
        checks = check_map[item["id"]](data)
        passed = all(check["passed"] for check in checks.values())
        earned = assigned if passed else 0.0
        score += earned
        details.append(
            {
                "id": item["id"],
                "goal": item["goal"],
                "weight": item["weight"],
                "assigned_score": round(assigned, 10),
                "passed": passed,
                "earned_score": round(earned, 10),
                "checks": checks,
            }
        )

    return {
        "score": round(score, 10),
        "total_weight": total_weight,
        "details": details,
    }


def zero_result(error_message):
    total_weight = sum(item["weight"] for item in RUBRIC)
    return {
        "score": 0.0,
        "total_weight": total_weight,
        "error": error_message,
        "details": [
            {
                "id": item["id"],
                "goal": item["goal"],
                "weight": item["weight"],
                "assigned_score": round(item["weight"] / total_weight, 10),
                "passed": False,
                "earned_score": 0.0,
                "checks": {"parse": {"passed": False, "error": error_message}},
            }
            for item in RUBRIC
        ],
    }


def main():
    path = candidate_path()
    try:
        data = load_candidate(path)
        result = evaluate(data)
        result["candidate_path"] = str(path)
    except Exception as exc:
        result = zero_result(str(exc))
        result["candidate_path"] = str(path)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
