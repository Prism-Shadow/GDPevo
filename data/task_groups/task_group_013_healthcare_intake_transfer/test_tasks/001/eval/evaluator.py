#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED_IDS = ["NSP-1042", "NSP-1057", "NSP-1073", "NSP-1088", "NSP-1096"]


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"score": 0, "max_score": 10, "error": f"Could not read JSON: {exc}"}))
        sys.exit(0)


def normalize_list(value):
    if not isinstance(value, list):
        return value
    if all(isinstance(item, dict) and "patient_id" in item for item in value):
        return sorted((normalize(item) for item in value), key=lambda item: item["patient_id"])
    return sorted(value)


def normalize(value):
    if isinstance(value, dict):
        return {key: normalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return normalize_list(value)
    return value


def patients_by_id(answer):
    rows = answer.get("patients")
    if not isinstance(rows, list):
        return {}
    return {row.get("patient_id"): row for row in rows if isinstance(row, dict)}


def score_answer(answer, expected):
    expected_patients = patients_by_id(expected)
    actual_patients = patients_by_id(answer)
    details = []
    score = 0
    max_score = 10

    def add(name, weight, passed):
        nonlocal score
        if passed:
            score += weight
        details.append({"name": name, "weight": weight, "passed": bool(passed)})

    add("task_id", 0, answer.get("task_id") == expected.get("task_id"))
    add(
        "patient_gate_statuses",
        2,
        all(actual_patients.get(pid, {}).get("gates") == expected_patients[pid]["gates"] for pid in EXPECTED_IDS),
    )
    add(
        "blocked_reason_sets",
        2,
        all(
            normalize(actual_patients.get(pid, {}).get("blocked_reasons")) == expected_patients[pid]["blocked_reasons"]
            for pid in EXPECTED_IDS
        ),
    )
    add(
        "overall_decisions",
        2,
        all(
            actual_patients.get(pid, {}).get("overall_decision") == expected_patients[pid]["overall_decision"]
            for pid in EXPECTED_IDS
        ),
    )
    add("ready_list", 1, normalize(answer.get("ready_patient_ids")) == expected["ready_patient_ids"])
    add(
        "manual_review_list",
        1,
        normalize(answer.get("manual_review_patient_ids")) == expected["manual_review_patient_ids"],
    )

    expected_outcomes = expected["pbm_pharmacy_outcomes"]
    actual_outcomes = answer.get("pbm_pharmacy_outcomes")
    top_level_outcomes_ok = normalize(actual_outcomes) == normalize(expected_outcomes)
    per_patient_outcomes_ok = all(
        actual_patients.get(pid, {}).get("pbm_status") == expected_patients[pid]["pbm_status"]
        and actual_patients.get(pid, {}).get("pharmacy_network_status")
        == expected_patients[pid]["pharmacy_network_status"]
        for pid in EXPECTED_IDS
    )
    add("pbm_pharmacy_outcomes", 1, top_level_outcomes_ok and per_patient_outcomes_ok)
    add("summary_counts", 1, answer.get("summary_counts") == expected["summary_counts"])

    return {
        "score": score,
        "max_score": max_score,
        "accuracy": score / max_score,
        "details": details,
    }


def main():
    prediction_path = sys.argv[1] if len(sys.argv) > 1 else "output/answer.json"
    gold_path = (
        sys.argv[2] if len(sys.argv) > 2 else str(Path(__file__).resolve().parents[1] / "output" / "answer.json")
    )
    print(json.dumps(score_answer(load_json(prediction_path), load_json(gold_path)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
