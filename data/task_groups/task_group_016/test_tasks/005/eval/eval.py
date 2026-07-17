#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


EXPECTED = {
    "task_id": "test_005",
    "case_id": "CASE-LAB-927",
    "patient_id": "PAT-5927",
    "window": {
        "from": "2026-05-01T00:00:00Z",
        "to": "2026-05-04T00:00:00Z",
    },
    "target_codes": ["SARS_FLU_RSV_PCR", "CXR-2V"],
    "viral_panel_found": True,
    "cxr_found": True,
    "matched_observation_ids": [
        "OBS-VIRAL-927-20260502-1035",
        "OBS-CXR-927-20260502-1110",
    ],
    "excluded_observation_ids": [
        "OBS-VIRAL-927-PRELIM-20260502",
        "OBS-CXR-927-20260429",
        "OBS-CBC-927-20260502",
    ],
    "latest_cxr": {
        "observation_id": "OBS-CXR-927-20260502-1110",
        "result": "right_middle_lobe_infiltrate",
        "effective_time": "2026-05-02T11:10:00Z",
    },
    "viral_result": "negative",
    "protocol_gate": "bacterial_pneumonia_supported",
    "remaining_tests": ["PULSE_OX_RECHECK"],
    "disposition": "outpatient_close_followup",
    "antibiotic_strategy": "standard_outpatient_beta_lactam_plus_macrolide",
}


RUBRIC = [
    {
        "id": "SP001",
        "goal": "Correct target-window Observation boolean results.",
        "weight": 2,
    },
    {
        "id": "SP002",
        "goal": "Correct matched Observation id sets and stable ordering.",
        "weight": 3,
    },
    {
        "id": "SP003",
        "goal": "Correct exclusion of wrong-window, preliminary, and wrong-code resources.",
        "weight": 2,
    },
    {
        "id": "SP004",
        "goal": "Correct protocol gate classification using CXR and viral result.",
        "weight": 1,
    },
    {
        "id": "SP005",
        "goal": "Correct remaining-test recommendation.",
        "weight": 3,
    },
    {
        "id": "SP006",
        "goal": "Correct disposition and antibiotic posture.",
        "weight": 3,
    },
    {
        "id": "SP007",
        "goal": "Correct patient, case, task, and target-code identifiers.",
        "weight": 2,
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


def as_string_list(value):
    if not isinstance(value, list):
        return None
    return [str(item) for item in value]


def as_string_set(value):
    values = as_string_list(value)
    if values is None:
        return None
    return set(values)


def build_check(expected, actual, passed):
    return {"expected": expected, "actual": actual, "passed": bool(passed)}


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


def get_object(answer, key):
    value = answer.get(key) if isinstance(answer, dict) else None
    return value if isinstance(value, dict) else {}


def evaluate(answer):
    details = []

    window = answer.get("window") if isinstance(answer, dict) else None
    sp001_checks = {
        "window": build_check(EXPECTED["window"], window, window == EXPECTED["window"]),
        "viral_panel_found": build_check(
            EXPECTED["viral_panel_found"],
            answer.get("viral_panel_found"),
            isinstance(answer.get("viral_panel_found"), bool)
            and answer.get("viral_panel_found") == EXPECTED["viral_panel_found"],
        ),
        "cxr_found": build_check(
            EXPECTED["cxr_found"],
            answer.get("cxr_found"),
            isinstance(answer.get("cxr_found"), bool) and answer.get("cxr_found") == EXPECTED["cxr_found"],
        ),
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
        "matched_observation_ids_ordered": build_check(
            EXPECTED["matched_observation_ids"],
            actual_matched,
            actual_matched == EXPECTED["matched_observation_ids"],
        )
    }
    details.append(
        build_detail(
            RUBRIC[1],
            sp002_checks["matched_observation_ids_ordered"]["passed"],
            sp002_checks,
        )
    )

    actual_excluded = as_string_list(answer.get("excluded_observation_ids"))
    matched_set = set(actual_matched or [])
    excluded_set = set(actual_excluded or [])
    expected_excluded_set = set(EXPECTED["excluded_observation_ids"])
    sp003_checks = {
        "excluded_observation_ids_set": build_check(
            sorted(expected_excluded_set),
            sorted(excluded_set),
            excluded_set == expected_excluded_set,
        ),
        "excluded_not_in_matched": build_check(
            [],
            sorted(excluded_set.intersection(matched_set)),
            not excluded_set.intersection(matched_set),
        ),
    }
    details.append(
        build_detail(
            RUBRIC[2],
            all(check["passed"] for check in sp003_checks.values()),
            sp003_checks,
        )
    )

    latest_cxr = get_object(answer, "latest_cxr")
    sp004_checks = {
        "latest_cxr_observation_id": build_check(
            EXPECTED["latest_cxr"]["observation_id"],
            latest_cxr.get("observation_id"),
            latest_cxr.get("observation_id") == EXPECTED["latest_cxr"]["observation_id"],
        ),
        "latest_cxr_result": build_check(
            EXPECTED["latest_cxr"]["result"],
            latest_cxr.get("result"),
            latest_cxr.get("result") == EXPECTED["latest_cxr"]["result"],
        ),
        "latest_cxr_effective_time": build_check(
            EXPECTED["latest_cxr"]["effective_time"],
            latest_cxr.get("effective_time"),
            latest_cxr.get("effective_time") == EXPECTED["latest_cxr"]["effective_time"],
        ),
        "viral_result": build_check(
            EXPECTED["viral_result"],
            answer.get("viral_result"),
            answer.get("viral_result") == EXPECTED["viral_result"],
        ),
        "protocol_gate": build_check(
            EXPECTED["protocol_gate"],
            answer.get("protocol_gate"),
            answer.get("protocol_gate") == EXPECTED["protocol_gate"],
        ),
    }
    details.append(
        build_detail(
            RUBRIC[3],
            all(check["passed"] for check in sp004_checks.values()),
            sp004_checks,
        )
    )

    actual_remaining_tests = as_string_set(answer.get("remaining_tests"))
    expected_remaining_tests = set(EXPECTED["remaining_tests"])
    sp005_checks = {
        "remaining_tests_set": build_check(
            sorted(expected_remaining_tests),
            sorted(actual_remaining_tests) if actual_remaining_tests is not None else None,
            actual_remaining_tests == expected_remaining_tests,
        )
    }
    details.append(
        build_detail(
            RUBRIC[4],
            sp005_checks["remaining_tests_set"]["passed"],
            sp005_checks,
        )
    )

    sp006_checks = {
        "disposition": build_check(
            EXPECTED["disposition"],
            answer.get("disposition"),
            answer.get("disposition") == EXPECTED["disposition"],
        ),
        "antibiotic_strategy": build_check(
            EXPECTED["antibiotic_strategy"],
            answer.get("antibiotic_strategy"),
            answer.get("antibiotic_strategy") == EXPECTED["antibiotic_strategy"],
        ),
    }
    details.append(
        build_detail(
            RUBRIC[5],
            all(check["passed"] for check in sp006_checks.values()),
            sp006_checks,
        )
    )

    actual_target_codes = as_string_set(answer.get("target_codes"))
    expected_target_codes = set(EXPECTED["target_codes"])
    sp007_checks = {
        "task_id": build_check(
            EXPECTED["task_id"], answer.get("task_id"), answer.get("task_id") == EXPECTED["task_id"]
        ),
        "case_id": build_check(
            EXPECTED["case_id"], answer.get("case_id"), answer.get("case_id") == EXPECTED["case_id"]
        ),
        "patient_id": build_check(
            EXPECTED["patient_id"], answer.get("patient_id"), answer.get("patient_id") == EXPECTED["patient_id"]
        ),
        "target_codes_set": build_check(
            sorted(expected_target_codes),
            sorted(actual_target_codes) if actual_target_codes is not None else None,
            actual_target_codes == expected_target_codes,
        ),
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
