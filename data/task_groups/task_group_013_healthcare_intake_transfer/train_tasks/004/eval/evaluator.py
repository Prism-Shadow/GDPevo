#!/usr/bin/env python3
import json
import sys
from copy import deepcopy
from pathlib import Path


EXPECTED = {
    "task_id": "train_004",
    "patients": [
        {
            "patient_id": "CHR-2040",
            "chart_ready": False,
            "missing_sections": ["vitals", "orientation_message"],
            "bmi_class": "not_available",
            "orientation_state": "queued",
            "next_owner": "clinical_intake",
            "problem_list_complete": True,
        },
        {
            "patient_id": "CHR-2058",
            "chart_ready": False,
            "missing_sections": ["problems"],
            "bmi_class": "not_available",
            "orientation_state": "sent",
            "next_owner": "clinical_intake",
            "problem_list_complete": False,
        },
        {
            "patient_id": "CHR-2077",
            "chart_ready": True,
            "missing_sections": [],
            "bmi_class": "not_available",
            "orientation_state": "sent",
            "next_owner": "ready",
            "problem_list_complete": True,
        },
    ],
    "ready_count": 1,
}

SECTION_ORDER = {
    "chart_not_created": 0,
    "demographics": 1,
    "history": 2,
    "problems": 3,
    "vitals": 4,
    "care_plan_or_instructions": 5,
    "orientation_message": 6,
}

PATIENT_IDS = ["CHR-2040", "CHR-2058", "CHR-2077"]


def normalize_answer(answer):
    normalized = deepcopy(answer)
    patients = normalized.get("patients")
    if isinstance(patients, list):
        for patient in patients:
            if isinstance(patient, dict) and isinstance(patient.get("missing_sections"), list):
                patient["missing_sections"] = sorted(
                    patient["missing_sections"],
                    key=lambda item: (SECTION_ORDER.get(item, 999), str(item)),
                )
        normalized["patients"] = sorted(
            patients,
            key=lambda patient: patient.get("patient_id", "") if isinstance(patient, dict) else "",
        )
    return normalized


def patient_map(answer):
    patients = answer.get("patients")
    if not isinstance(patients, list):
        return {}
    return {
        patient.get("patient_id"): patient
        for patient in patients
        if isinstance(patient, dict) and patient.get("patient_id") in PATIENT_IDS
    }


def extract_field_map(answer, field):
    mapped = patient_map(answer)
    return {patient_id: mapped.get(patient_id, {}).get(field) for patient_id in PATIENT_IDS}


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0, "max_score": 7, "error": "usage: evaluator.py ANSWER_FILE"}))
        return 2

    answer_path = Path(sys.argv[1])
    try:
        submitted = json.loads(answer_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"score": 0, "max_score": 7, "error": f"could not read JSON: {exc}"}))
        return 1

    expected = normalize_answer(EXPECTED)
    actual = normalize_answer(submitted)

    checks = [
        (
            "chart_ready_by_patient",
            extract_field_map(actual, "chart_ready") == extract_field_map(expected, "chart_ready"),
        ),
        (
            "missing_sections_by_patient",
            extract_field_map(actual, "missing_sections") == extract_field_map(expected, "missing_sections"),
        ),
        (
            "bmi_class_by_patient",
            extract_field_map(actual, "bmi_class") == extract_field_map(expected, "bmi_class"),
        ),
        (
            "orientation_state_by_patient",
            extract_field_map(actual, "orientation_state") == extract_field_map(expected, "orientation_state"),
        ),
        (
            "next_owner_by_patient",
            extract_field_map(actual, "next_owner") == extract_field_map(expected, "next_owner"),
        ),
        ("ready_count", actual.get("ready_count") == expected["ready_count"]),
        (
            "problem_list_complete_by_patient",
            extract_field_map(actual, "problem_list_complete") == extract_field_map(expected, "problem_list_complete"),
        ),
    ]

    score = sum(1 for _, passed in checks if passed)
    result = {
        "score": score,
        "max_score": len(checks),
        "passed": [name for name, passed in checks if passed],
        "failed": [name for name, passed in checks if not passed],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if score == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
