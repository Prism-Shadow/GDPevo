#!/usr/bin/env python3
import json
import math
import os
import sys
from pathlib import Path


EXPECTED = {
    "task_id": "train_005",
    "case_id": "CASE-LAB-518",
    "patient_id": "PAT-5518",
    "window": {
        "from": "2026-03-01T00:00:00Z",
        "to": "2026-04-01T00:00:00Z",
    },
    "target_code": "K",
    "lab_found": True,
    "matched_observation_ids": [
        "OBS-K-518-20260305-0810",
        "OBS-K-518-20260320-0745",
    ],
    "excluded_observation_ids": [
        "OBS-K-518-20260227-0900",
        "OBS-K-518-PRELIM-20260328",
        "OBS-NA-518-20260315",
    ],
    "latest_final": {
        "observation_id": "OBS-K-518-20260320-0745",
        "value_mmol_l": 3.6,
        "effective_time": "2026-03-20T07:45:00Z",
    },
    "protocol_gate": "satisfies_recent_final_normal",
    "repeat_lab": {
        "recommended": False,
        "scheduled_time": None,
    },
}


RUBRIC = [
    {
        "id": "SP001",
        "goal": "Correct window inclusion and boolean lab-found result.",
        "weight": 3,
    },
    {
        "id": "SP002",
        "goal": "Correct complete matched Observation id set and stable ordering.",
        "weight": 3,
    },
    {
        "id": "SP003",
        "goal": "Correct exclusion of canceled, preliminary, wrong-code, and wrong-window observations.",
        "weight": 2,
    },
    {
        "id": "SP004",
        "goal": "Correct latest final value and timestamp.",
        "weight": 2,
    },
    {
        "id": "SP005",
        "goal": "Correct protocol gate decision from the retrieved lab.",
        "weight": 2,
    },
    {
        "id": "SP006",
        "goal": "Correct repeat-lab recommendation and timing.",
        "weight": 2,
    },
    {
        "id": "SP007",
        "goal": "Correct task, case, patient, and target-code identifiers.",
        "weight": 1,
    },
]


def candidate_path() -> Path:
    if len(sys.argv) > 1 and sys.argv[1]:
        return Path(sys.argv[1])
    if os.environ.get("ANSWER_JSON"):
        return Path(os.environ["ANSWER_JSON"])
    return Path("answer.json")


def load_candidate(path: Path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def get(data, *keys):
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def as_string_list(value):
    if not isinstance(value, list):
        return None
    return [str(item) for item in value]


def close_number(actual, expected, tol=0.05):
    if isinstance(actual, bool):
        return False
    try:
        return math.isclose(float(actual), float(expected), abs_tol=tol, rel_tol=0.0)
    except (TypeError, ValueError):
        return False


def exact_dict_subset(actual, expected, keys):
    if not isinstance(actual, dict):
        return False
    return all(actual.get(key) == expected.get(key) for key in keys)


def build_detail(point, passed, checks):
    total_weight = sum(item["weight"] for item in RUBRIC)
    assigned = point["weight"] / total_weight
    earned = assigned if passed else 0.0
    return {
        "id": point["id"],
        "goal": point["goal"],
        "weight": point["weight"],
        "assigned_score": assigned,
        "passed": bool(passed),
        "earned_score": earned,
        "checks": checks,
    }


def evaluate(answer):
    details = []

    window = answer.get("window") if isinstance(answer, dict) else None
    sp001_checks = {
        "window": {
            "expected": EXPECTED["window"],
            "actual": window,
            "passed": window == EXPECTED["window"],
        },
        "lab_found": {
            "expected": EXPECTED["lab_found"],
            "actual": answer.get("lab_found") if isinstance(answer, dict) else None,
            "passed": isinstance(answer.get("lab_found"), bool) and answer.get("lab_found") == EXPECTED["lab_found"],
        },
    }
    details.append(
        build_detail(
            RUBRIC[0],
            all(check["passed"] for check in sp001_checks.values()),
            sp001_checks,
        )
    )

    actual_matched = as_string_list(answer.get("matched_observation_ids"))
    sp002_checks = {
        "matched_observation_ids_ordered": {
            "expected": EXPECTED["matched_observation_ids"],
            "actual": actual_matched,
            "passed": actual_matched == EXPECTED["matched_observation_ids"],
        }
    }
    details.append(build_detail(RUBRIC[1], sp002_checks["matched_observation_ids_ordered"]["passed"], sp002_checks))

    actual_excluded = as_string_list(answer.get("excluded_observation_ids"))
    matched_set = set(actual_matched or [])
    excluded_set = set(actual_excluded or [])
    expected_excluded_set = set(EXPECTED["excluded_observation_ids"])
    sp003_checks = {
        "excluded_observation_ids_set": {
            "expected": sorted(expected_excluded_set),
            "actual": sorted(excluded_set),
            "passed": excluded_set == expected_excluded_set,
        },
        "excluded_not_in_matched": {
            "expected": [],
            "actual": sorted(excluded_set.intersection(matched_set)),
            "passed": not excluded_set.intersection(matched_set),
        },
    }
    details.append(
        build_detail(
            RUBRIC[2],
            all(check["passed"] for check in sp003_checks.values()),
            sp003_checks,
        )
    )

    latest = answer.get("latest_final") if isinstance(answer.get("latest_final"), dict) else {}
    sp004_checks = {
        "latest_observation_id": {
            "expected": EXPECTED["latest_final"]["observation_id"],
            "actual": latest.get("observation_id"),
            "passed": latest.get("observation_id") == EXPECTED["latest_final"]["observation_id"],
        },
        "latest_value_mmol_l": {
            "expected": EXPECTED["latest_final"]["value_mmol_l"],
            "actual": latest.get("value_mmol_l"),
            "passed": close_number(latest.get("value_mmol_l"), EXPECTED["latest_final"]["value_mmol_l"]),
        },
        "latest_effective_time": {
            "expected": EXPECTED["latest_final"]["effective_time"],
            "actual": latest.get("effective_time"),
            "passed": latest.get("effective_time") == EXPECTED["latest_final"]["effective_time"],
        },
    }
    details.append(
        build_detail(
            RUBRIC[3],
            all(check["passed"] for check in sp004_checks.values()),
            sp004_checks,
        )
    )

    sp005_checks = {
        "protocol_gate": {
            "expected": EXPECTED["protocol_gate"],
            "actual": answer.get("protocol_gate"),
            "passed": answer.get("protocol_gate") == EXPECTED["protocol_gate"],
        }
    }
    details.append(build_detail(RUBRIC[4], sp005_checks["protocol_gate"]["passed"], sp005_checks))

    repeat_lab = answer.get("repeat_lab") if isinstance(answer.get("repeat_lab"), dict) else {}
    sp006_checks = {
        "repeat_lab_recommended": {
            "expected": EXPECTED["repeat_lab"]["recommended"],
            "actual": repeat_lab.get("recommended"),
            "passed": isinstance(repeat_lab.get("recommended"), bool)
            and repeat_lab.get("recommended") == EXPECTED["repeat_lab"]["recommended"],
        },
        "repeat_lab_scheduled_time": {
            "expected": EXPECTED["repeat_lab"]["scheduled_time"],
            "actual": repeat_lab.get("scheduled_time"),
            "passed": repeat_lab.get("scheduled_time") is None,
        },
    }
    details.append(
        build_detail(
            RUBRIC[5],
            all(check["passed"] for check in sp006_checks.values()),
            sp006_checks,
        )
    )

    sp007_checks = {
        "task_id": {
            "expected": EXPECTED["task_id"],
            "actual": answer.get("task_id"),
            "passed": answer.get("task_id") == EXPECTED["task_id"],
        },
        "case_id": {
            "expected": EXPECTED["case_id"],
            "actual": answer.get("case_id"),
            "passed": answer.get("case_id") == EXPECTED["case_id"],
        },
        "patient_id": {
            "expected": EXPECTED["patient_id"],
            "actual": answer.get("patient_id"),
            "passed": answer.get("patient_id") == EXPECTED["patient_id"],
        },
        "target_code": {
            "expected": EXPECTED["target_code"],
            "actual": answer.get("target_code"),
            "passed": answer.get("target_code") == EXPECTED["target_code"],
        },
    }
    details.append(
        build_detail(
            RUBRIC[6],
            all(check["passed"] for check in sp007_checks.values()),
            sp007_checks,
        )
    )

    return details


def failure_result(path, error):
    total_weight = sum(item["weight"] for item in RUBRIC)
    details = [
        build_detail(
            point,
            False,
            {
                "candidate_load": {
                    "expected": "valid JSON object",
                    "actual": error,
                    "passed": False,
                }
            },
        )
        for point in RUBRIC
    ]
    return {
        "score": 0.0,
        "total_weight": total_weight,
        "candidate_path": str(path),
        "details": details,
    }


def main():
    path = candidate_path()
    answer, error = load_candidate(path)
    if error is not None:
        print(json.dumps(failure_result(path, error), indent=2, sort_keys=True))
        return 0
    if not isinstance(answer, dict):
        print(json.dumps(failure_result(path, "Top-level JSON value must be an object."), indent=2, sort_keys=True))
        return 0

    details = evaluate(answer)
    score = sum(item["earned_score"] for item in details)
    result = {
        "score": score,
        "total_weight": sum(item["weight"] for item in RUBRIC),
        "candidate_path": str(path),
        "details": details,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
