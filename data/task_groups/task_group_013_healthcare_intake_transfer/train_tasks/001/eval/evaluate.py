#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED_IDS = ["NSP-1008", "NSP-1014", "NSP-1022", "NSP-1031"]

EXPECTED = {
    "task_id": "train_001",
    "patients": [
        {
            "patient_id": "NSP-1008",
            "gates": {
                "medical_insurance": "block",
                "pbm": "pass",
                "pharmacy": "pass",
                "demographics": "block",
                "risk": "high",
            },
            "blocked_reasons": [
                "clinical_review_required",
                "demographics_incomplete",
                "insurance_inactive",
            ],
            "overall_decision": "blocked",
            "pharmacy_network_status": "in_network",
        },
        {
            "patient_id": "NSP-1014",
            "gates": {
                "medical_insurance": "block",
                "pbm": "block",
                "pharmacy": "pass",
                "demographics": "pass",
                "risk": "moderate",
            },
            "blocked_reasons": ["insurance_inactive", "pbm_inactive"],
            "overall_decision": "blocked",
            "pharmacy_network_status": "in_network",
        },
        {
            "patient_id": "NSP-1022",
            "gates": {
                "medical_insurance": "pass",
                "pbm": "pass",
                "pharmacy": "pass",
                "demographics": "pass",
                "risk": "moderate",
            },
            "blocked_reasons": [],
            "overall_decision": "ready",
            "pharmacy_network_status": "in_network",
        },
        {
            "patient_id": "NSP-1031",
            "gates": {
                "medical_insurance": "pass",
                "pbm": "block",
                "pharmacy": "pass",
                "demographics": "block",
                "risk": "high",
            },
            "blocked_reasons": [
                "clinical_review_required",
                "demographics_incomplete",
                "pbm_inactive",
            ],
            "overall_decision": "blocked",
            "pharmacy_network_status": "in_network",
        },
    ],
    "ready_count": 1,
    "highest_risk_patient_id": "NSP-1031",
    "manual_review_patient_ids": [],
    "pharmacy_network_statuses": [
        {"patient_id": "NSP-1008", "status": "in_network"},
        {"patient_id": "NSP-1014", "status": "in_network"},
        {"patient_id": "NSP-1022", "status": "in_network"},
        {"patient_id": "NSP-1031", "status": "in_network"},
    ],
}


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"score": 0, "max_score": 15, "error": f"Could not read JSON: {exc}"}))
        sys.exit(0)


def patients_by_id(answer):
    rows = answer.get("patients")
    if not isinstance(rows, list):
        return {}
    return {row.get("patient_id"): row for row in rows if isinstance(row, dict)}


def sorted_list(value):
    return sorted(value) if isinstance(value, list) else value


def score_answer(answer):
    expected_patients = patients_by_id(EXPECTED)
    actual_patients = patients_by_id(answer)
    details = []
    score = 0
    max_score = 13

    def add(name, weight, passed):
        nonlocal score
        if passed:
            score += weight
        details.append({"name": name, "weight": weight, "passed": bool(passed)})

    add(
        "task_id",
        0,
        answer.get("task_id") == EXPECTED["task_id"],
    )

    add(
        "patient_gate_statuses",
        3,
        all(actual_patients.get(pid, {}).get("gates") == expected_patients[pid]["gates"] for pid in EXPECTED_IDS),
    )
    add(
        "blocked_reason_sets",
        3,
        all(
            sorted_list(actual_patients.get(pid, {}).get("blocked_reasons"))
            == expected_patients[pid]["blocked_reasons"]
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
    add("ready_count", 1, answer.get("ready_count") == EXPECTED["ready_count"])
    add(
        "highest_risk_patient",
        1,
        answer.get("highest_risk_patient_id") == EXPECTED["highest_risk_patient_id"],
    )
    add(
        "manual_review_set",
        2,
        sorted_list(answer.get("manual_review_patient_ids")) == EXPECTED["manual_review_patient_ids"],
    )

    expected_status_rows = EXPECTED["pharmacy_network_statuses"]
    actual_status_rows = answer.get("pharmacy_network_statuses")
    top_level_statuses_ok = actual_status_rows == expected_status_rows
    per_patient_statuses_ok = all(
        actual_patients.get(pid, {}).get("pharmacy_network_status")
        == expected_patients[pid]["pharmacy_network_status"]
        for pid in EXPECTED_IDS
    )
    add("pharmacy_network_statuses", 1, top_level_statuses_ok and per_patient_statuses_ok)

    return {
        "score": score,
        "max_score": max_score,
        "accuracy": score / max_score,
        "details": details,
    }


def main():
    answer_path = sys.argv[1] if len(sys.argv) > 1 else "output/answer.json"
    print(json.dumps(score_answer(load_json(answer_path)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
