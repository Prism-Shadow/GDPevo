#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED = {
    "patient": {
        "patient_id": "P-44702",
        "enterprise_mrn": "E10044702",
        "display_name": "Thomas Bennett",
        "dob": "1949-02-27",
    },
    "recipient": {
        "provider_id": "PRV-ORTHO-010",
        "name": "Dr. Priya Nair",
        "facility": "Cedar Orthopedic Institute",
        "service_line": "orthopedics",
    },
    "active_condition_keys": [
        "diabetes_type_2",
        "hypertension",
        "memory_loss",
        "right_hip_oa",
        "right_knee_oa",
    ],
    "active_medication_keys": [
        "acetaminophen",
        "baseline_med",
        "insulin_glargine",
    ],
    "active_allergy_keys": [
        "baseline_allergy",
        "latex",
    ],
    "handoff_encounters": [
        {
            "encounter_id": "ENC-44702-0",
            "date": "2026-03-01",
            "type": "care_transition",
            "signed_status": "signed",
        },
        {
            "encounter_id": "ENC-44702-1",
            "date": "2026-02-14",
            "type": "office_visit",
            "signed_status": "signed",
        },
        {
            "encounter_id": "ENC-44702-2",
            "date": "2026-01-29",
            "type": "office_visit",
            "signed_status": "signed",
        },
        {
            "encounter_id": "ENC-44702-3",
            "date": "2026-01-02",
            "type": "office_visit",
            "signed_status": "signed",
        },
    ],
    "source_selection": {
        "selection_basis": "orthopedic_surgical_handoff_window",
        "selected_encounter_ids": [
            "ENC-44702-0",
            "ENC-44702-1",
            "ENC-44702-2",
            "ENC-44702-3",
        ],
        "excluded_encounter_ids": {
            "ENC-0460F33D",
            "ENC-0FE06CF3",
            "ENC-44702-4",
            "ENC-FA393BB8",
        },
    },
    "latest_immunization": {
        "immunization_id": "IMM-1372CDAF",
        "date": "2026-03-11",
        "vaccine": "influenza high-dose",
    },
    "disclosure": {
        "disclosure_id": "DISC-44702-ORTHO",
        "date": "2026-03-02",
        "status": "permitted",
        "purpose": "surgical handoff",
        "recipient_provider_id": "PRV-ORTHO-010",
    },
    "risk_flags": [
        "cognitive_memory_loss",
        "fall_risk_note_required",
        "hypertension",
        "insulin_dependent_diabetes",
        "latex_allergy",
        "perioperative_glucose_plan_needed",
    ],
    "risk_flag_evidence": {
        "cognitive_memory_loss": {
            "condition_keys": {"memory_loss"},
            "medication_keys": set(),
            "encounter_ids": {"ENC-0460F33D"},
        },
        "fall_risk_note_required": {
            "condition_keys": {"right_hip_oa", "right_knee_oa"},
            "medication_keys": {"acetaminophen"},
            "encounter_ids": {"ENC-44702-0"},
        },
        "hypertension": {
            "condition_keys": {"hypertension"},
            "medication_keys": set(),
            "encounter_ids": {"ENC-0460F33D"},
        },
        "insulin_dependent_diabetes": {
            "condition_keys": {"diabetes_type_2"},
            "medication_keys": {"insulin_glargine"},
            "encounter_ids": {"ENC-44702-0", "ENC-44702-1", "ENC-44702-2", "ENC-44702-3"},
        },
        "latex_allergy": {
            "condition_keys": set(),
            "medication_keys": set(),
            "encounter_ids": set(),
        },
        "perioperative_glucose_plan_needed": {
            "condition_keys": {"diabetes_type_2"},
            "medication_keys": {"insulin_glargine"},
            "encounter_ids": {"ENC-44702-0"},
        },
    },
    "packet_readiness": {
        "status": "ready_with_risk_flags",
        "ready_to_send": True,
        "blocking_issue_codes": [],
    },
}


POINTS = [
    ("patient_recipient", 2, "Correct patient identity and orthopedic recipient directory details."),
    ("active_conditions", 2, "Correct active condition normalized-key set."),
    ("active_medications", 2, "Correct active medication normalized-key set."),
    ("active_allergies", 1, "Correct active allergy normalized-key set."),
    (
        "handoff_encounters",
        3,
        "Correct four selected handoff encounters with dates, type, status, and newest-to-oldest order.",
    ),
    (
        "source_selection_exclusions",
        3,
        "Correct orthopedic handoff source-selection rule, selected encounter sequence, and excluded distractor encounters.",
    ),
    ("latest_immunization", 1, "Correct latest immunization id, date, and vaccine."),
    ("disclosure", 2, "Correct permitted orthopedic surgical handoff disclosure."),
    ("risk_flags_readiness", 3, "Correct risk flag code set and packet readiness decision."),
    ("risk_flag_evidence_map", 3, "Correct condition, medication, and encounter evidence mapped to each risk flag."),
]


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def as_sorted_strings(value):
    if not isinstance(value, list):
        return None
    return sorted(str(item).strip() for item in value)


def as_set(value):
    if not isinstance(value, list):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def as_ordered_strings(value):
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def exact_object(candidate, expected):
    return isinstance(candidate, dict) and candidate == expected


def check_patient_recipient(answer):
    return exact_object(answer.get("patient"), EXPECTED["patient"]) and exact_object(
        answer.get("recipient"), EXPECTED["recipient"]
    )


def check_set(answer, key):
    return as_sorted_strings(answer.get(key)) == EXPECTED[key]


def check_handoff_encounters(answer):
    rows = answer.get("handoff_encounters")
    if not isinstance(rows, list):
        return False
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            return False
        normalized.append(
            {
                "encounter_id": row.get("encounter_id"),
                "date": row.get("date"),
                "type": row.get("type"),
                "signed_status": row.get("signed_status"),
            }
        )
    return normalized == EXPECTED["handoff_encounters"]


def check_source_selection(answer):
    selection = answer.get("source_selection")
    if not isinstance(selection, dict):
        return False
    expected = EXPECTED["source_selection"]
    return (
        selection.get("selection_basis") == expected["selection_basis"]
        and as_ordered_strings(selection.get("selected_encounter_ids")) == expected["selected_encounter_ids"]
        and as_set(selection.get("excluded_encounter_ids")) == expected["excluded_encounter_ids"]
    )


def check_risk_flags_readiness(answer):
    readiness = answer.get("packet_readiness")
    return (
        as_sorted_strings(answer.get("risk_flags")) == EXPECTED["risk_flags"]
        and isinstance(readiness, dict)
        and readiness.get("status") == "ready_with_risk_flags"
        and readiness.get("ready_to_send") is True
        and readiness.get("blocking_issue_codes") == []
    )


def evidence_map(value):
    if not isinstance(value, list):
        return {}
    result = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        risk_flag = str(item.get("risk_flag", "")).strip()
        if risk_flag:
            result[risk_flag] = {
                "condition_keys": as_set(item.get("condition_keys")),
                "medication_keys": as_set(item.get("medication_keys")),
                "encounter_ids": as_set(item.get("encounter_ids")),
            }
    return result


def check_risk_flag_evidence(answer):
    actual = evidence_map(answer.get("risk_flag_evidence"))
    expected = EXPECTED["risk_flag_evidence"]
    return actual == expected


CHECKS = {
    "patient_recipient": check_patient_recipient,
    "active_conditions": lambda a: check_set(a, "active_condition_keys"),
    "active_medications": lambda a: check_set(a, "active_medication_keys"),
    "active_allergies": lambda a: check_set(a, "active_allergy_keys"),
    "handoff_encounters": check_handoff_encounters,
    "source_selection_exclusions": check_source_selection,
    "latest_immunization": lambda a: exact_object(a.get("latest_immunization"), EXPECTED["latest_immunization"]),
    "disclosure": lambda a: exact_object(a.get("disclosure"), EXPECTED["disclosure"]),
    "risk_flags_readiness": check_risk_flags_readiness,
    "risk_flag_evidence_map": check_risk_flag_evidence,
}


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
    answer, error = load_json(path)
    total_weight = sum(weight for _, weight, _ in POINTS)
    details = []

    if error is not None:
        for point_id, weight, goal in POINTS:
            assigned = weight / total_weight
            details.append(
                {
                    "id": point_id,
                    "goal": goal,
                    "weight": weight,
                    "assigned_score": assigned,
                    "passed": False,
                    "earned_score": 0.0,
                    "details": f"Candidate answer is not readable JSON: {error}",
                }
            )
        print(json.dumps({"score": 0.0, "points": details}, indent=2, sort_keys=True))
        return

    score = 0.0
    for point_id, weight, goal in POINTS:
        assigned = weight / total_weight
        passed = bool(CHECKS[point_id](answer if isinstance(answer, dict) else {}))
        earned = assigned if passed else 0.0
        score += earned
        details.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": assigned,
                "passed": passed,
                "earned_score": earned,
                "details": "pass" if passed else "Expected normalized field values did not match.",
            }
        )

    print(json.dumps({"score": round(score, 6), "points": details}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
