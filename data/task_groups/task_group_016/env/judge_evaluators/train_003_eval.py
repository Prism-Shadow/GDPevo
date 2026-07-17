#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


EXPECTED = {
    "task_id": "train_003",
    "case_id": "CASE-K-303",
    "patient_id": "PAT-3303",
    "current_time": "2026-02-10T10:15:00Z",
    "latest_potassium": {
        "observation_id": "OBS-K-303-20260210-0620",
        "value_mmol_l": 3.2,
        "effective_time": "2026-02-10T06:20:00Z",
    },
    "replacement_required": True,
    "potassium_plan": "routine_oral_repletion",
    "oral_dose_mEq": 30,
    "medication_order": {
        "ndc": "40032-917-01",
        "medication": "potassium chloride oral",
        "route": "PO",
        "frequency": "once",
        "status": "recommended",
    },
    "follow_up_lab": {
        "loinc": "2823-3",
        "scheduled_time": "2026-02-11T08:00:00Z",
    },
    "urgent_actions": [],
    "contraindications": {
        "dialysis_dependent": False,
        "arrhythmia_symptoms": False,
        "egfr": 64,
    },
    "evidence_ids": ["OBS-K-303-20260210-0620", "OBS-EGFR-303-20260209"],
}


RUBRIC = [
    {
        "id": "SP001",
        "weight": 3,
        "goal": "Correct latest final potassium observation and ignored stale or preliminary observations.",
    },
    {
        "id": "SP002",
        "weight": 2,
        "goal": "Correct replacement-needed boolean under threshold.",
    },
    {
        "id": "SP003",
        "weight": 3,
        "goal": "Correct oral potassium dose calculation.",
    },
    {
        "id": "SP004",
        "weight": 2,
        "goal": "Correct medication code and route/frequency instructions.",
    },
    {
        "id": "SP005",
        "weight": 3,
        "goal": "Correct follow-up LOINC and scheduled timestamp.",
    },
    {
        "id": "SP006",
        "weight": 1,
        "goal": "Correct no-urgent-escalation classification after renal and rhythm screen.",
    },
    {
        "id": "SP007",
        "weight": 1,
        "goal": "Correct patient/case identifiers and evidence list.",
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


def eq_number_1dp(candidate, expected):
    try:
        return round(float(candidate), 1) == round(float(expected), 1)
    except (TypeError, ValueError):
        return False


def eq_empty_list(candidate):
    return isinstance(candidate, list) and candidate == []


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
            [("replacement_required", EXPECTED["replacement_required"], eq_bool)],
        ),
        "SP003": lambda d: check_fields(
            d,
            [("oral_dose_mEq", EXPECTED["oral_dose_mEq"], eq_int)],
        ),
        "SP004": lambda d: check_fields(
            d,
            [
                ("medication_order.ndc", EXPECTED["medication_order"]["ndc"], eq_text),
                ("medication_order.medication", EXPECTED["medication_order"]["medication"], eq_text),
                ("medication_order.route", EXPECTED["medication_order"]["route"], eq_text),
                ("medication_order.frequency", EXPECTED["medication_order"]["frequency"], eq_text),
                ("medication_order.status", EXPECTED["medication_order"]["status"], eq_text),
            ],
        ),
        "SP005": lambda d: check_fields(
            d,
            [
                ("follow_up_lab.loinc", EXPECTED["follow_up_lab"]["loinc"], eq_text),
                ("follow_up_lab.scheduled_time", EXPECTED["follow_up_lab"]["scheduled_time"], eq_text),
            ],
        ),
        "SP006": lambda d: {
            **check_fields(
                d,
                [
                    ("potassium_plan", EXPECTED["potassium_plan"], eq_text),
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
            "urgent_actions": {
                "expected": [],
                "actual": d.get("urgent_actions"),
                "passed": eq_empty_list(d.get("urgent_actions")),
            },
        },
        "SP007": lambda d: {
            **check_fields(
                d,
                [
                    ("task_id", EXPECTED["task_id"], eq_text),
                    ("case_id", EXPECTED["case_id"], eq_text),
                    ("patient_id", EXPECTED["patient_id"], eq_text),
                    ("current_time", EXPECTED["current_time"], eq_text),
                ],
            ),
            "evidence_ids": {
                "expected": EXPECTED["evidence_ids"],
                "actual": d.get("evidence_ids"),
                "passed": eq_string_set(d.get("evidence_ids"), EXPECTED["evidence_ids"]),
            },
        },
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
