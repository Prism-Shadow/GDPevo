#!/usr/bin/env python3
"""Evaluator for task_group_015 test_003."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXPECTED = {
    "patient": {
        "patient_id": "P-50831",
        "enterprise_mrn": "E10050831",
        "display_name": "Helena Ortiz",
        "dob": "1937-01-18",
    },
    "recipient": {
        "provider_id": "PRV-SNF-050",
        "name": "Kelsey Morgan, RN",
        "facility": "Meadowbrook Skilled Nursing",
        "service_line": "skilled_nursing",
    },
    "active_condition_keys": {
        "diabetes_type_2",
        "heart_failure_diastolic",
        "lumbar_radiculopathy",
        "memory_loss",
        "right_knee_oa",
    },
    "active_medication_keys": {
        "baseline_med",
        "donepezil",
        "furosemide",
    },
    "active_allergy_keys": {
        "baseline_allergy",
    },
    "handoff_encounters": [
        {
            "encounter_id": "ENC-50831-0",
            "date": "2026-04-18",
            "type": "care_transition",
            "signed_status": "signed",
        },
        {
            "encounter_id": "ENC-50831-1",
            "date": "2026-04-14",
            "type": "office_visit",
            "signed_status": "signed",
        },
        {
            "encounter_id": "ENC-50831-2",
            "date": "2026-04-08",
            "type": "office_visit",
            "signed_status": "signed",
        },
        {
            "encounter_id": "ENC-50831-3",
            "date": "2026-03-29",
            "type": "office_visit",
            "signed_status": "signed",
        },
        {
            "encounter_id": "ENC-50831-4",
            "date": "2026-03-22",
            "type": "office_visit",
            "signed_status": "signed",
        },
    ],
    "latest_immunization": {
        "immunization_id": "IMM-D62F24F8",
        "date": "2026-02-19",
        "vaccine": "influenza high-dose",
    },
    "disclosure": {
        "disclosure_id": "DISC-50831-SNF",
        "date": "2026-04-18",
        "status": "permitted",
        "purpose": "post-acute care transition",
        "recipient_provider_id": "PRV-SNF-050",
    },
    "risk_flags": {
        "heart_failure",
        "medication_supervision_required",
        "mild_cognitive_impairment",
        "walker_required",
    },
    "risk_flag_evidence": {
        "heart_failure": {
            "condition_keys": {"heart_failure_diastolic"},
            "medication_keys": {"furosemide"},
            "encounter_ids": {
                "ENC-50831-0",
                "ENC-50831-1",
                "ENC-50831-2",
                "ENC-50831-3",
                "ENC-50831-4",
            },
        },
        "medication_supervision_required": {
            "condition_keys": {"memory_loss"},
            "medication_keys": {"donepezil", "furosemide"},
            "encounter_ids": {"ENC-50831-0", "ENC-50831-1"},
        },
        "mild_cognitive_impairment": {
            "condition_keys": {"memory_loss"},
            "medication_keys": {"donepezil"},
            "encounter_ids": {"ENC-50831-0", "ENC-50831-1"},
        },
        "walker_required": {
            "condition_keys": set(),
            "medication_keys": set(),
            "encounter_ids": {"ENC-50831-0", "ENC-50831-1"},
        },
    },
    "source_selection": {
        "selection_basis": "snf_transition_window",
        "selected_encounter_ids": [
            "ENC-50831-0",
            "ENC-50831-1",
            "ENC-50831-2",
            "ENC-50831-3",
            "ENC-50831-4",
        ],
        "excluded_encounter_ids": {
            "ENC-246716B6",
            "ENC-50831-5",
            "ENC-61DFCB01",
            "ENC-D67A9361",
        },
    },
    "packet_readiness": {
        "status": "ready_with_risk_flags",
        "ready_to_send": True,
        "supporting_document_ids": {"DOC-8334B3FE"},
        "blocking_issue_codes": set(),
    },
}


POINTS = [
    {
        "id": "patient_recipient",
        "weight": 2,
        "description": "Correct patient identity and Meadowbrook Skilled Nursing recipient directory details.",
    },
    {
        "id": "active_conditions",
        "weight": 2,
        "description": "Correct normalized active condition key set.",
    },
    {
        "id": "active_medications",
        "weight": 2,
        "description": "Correct normalized active medication key set.",
    },
    {
        "id": "active_allergies",
        "weight": 1,
        "description": "Correct normalized active allergy key set.",
    },
    {
        "id": "handoff_encounters",
        "weight": 3,
        "description": "Correct five selected SNF handoff encounters with dates, type, status, and newest-to-oldest order.",
    },
    {
        "id": "source_selection_exclusions",
        "weight": 3,
        "description": "Correct SNF transition source-selection rule, selected encounter sequence, and excluded distractor encounters.",
    },
    {
        "id": "latest_immunization",
        "weight": 1,
        "description": "Correct latest immunization id, date, and vaccine.",
    },
    {
        "id": "disclosure",
        "weight": 2,
        "description": "Correct permitted Meadowbrook post-acute care transition disclosure.",
    },
    {
        "id": "risk_flags_readiness",
        "weight": 3,
        "description": "Correct SNF risk flags, final chart-summary support, and packet readiness decision.",
    },
    {
        "id": "risk_flag_evidence_map",
        "weight": 3,
        "description": "Correct condition, medication, and encounter evidence mapped to each SNF risk flag.",
    },
]


def as_obj(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def norm_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def norm_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def set_detail(actual_value: Any, expected: set[str]) -> dict[str, Any]:
    actual = norm_set(actual_value)
    return {
        "expected": sorted(expected),
        "actual": sorted(actual),
        "missing": sorted(expected - actual),
        "extra": sorted(actual - expected),
    }


def object_detail(actual: Any, expected: dict[str, Any]) -> dict[str, Any]:
    actual_obj = as_obj(actual)
    checks = {key: norm_scalar(actual_obj.get(key)) == expected_value for key, expected_value in expected.items()}
    return {
        "checks": checks,
        "actual": {key: actual_obj.get(key) for key in expected},
        "expected": expected,
    }


def norm_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def evidence_map(value: Any) -> dict[str, dict[str, set[str]]]:
    if not isinstance(value, list):
        return {}
    result: dict[str, dict[str, set[str]]] = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        risk_flag = str(item.get("risk_flag", "")).strip()
        if not risk_flag:
            continue
        result[risk_flag] = {
            "condition_keys": norm_set(item.get("condition_keys")),
            "medication_keys": norm_set(item.get("medication_keys")),
            "encounter_ids": norm_set(item.get("encounter_ids")),
        }
    return result


def check_patient_recipient(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    patient = object_detail(answer.get("patient"), EXPECTED["patient"])
    recipient = object_detail(answer.get("recipient"), EXPECTED["recipient"])
    passed = all(patient["checks"].values()) and all(recipient["checks"].values())
    return passed, {"patient": patient, "recipient": recipient}


def check_exact_set(answer: dict[str, Any], key: str) -> tuple[bool, dict[str, Any]]:
    detail = set_detail(answer.get(key), EXPECTED[key])
    return not detail["missing"] and not detail["extra"], detail


def check_handoff_encounters(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    rows = answer.get("handoff_encounters")
    if not isinstance(rows, list):
        return False, {"error": "handoff_encounters must be a list"}
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            return False, {"error": "handoff_encounters entries must be objects"}
        normalized.append(
            {
                "encounter_id": norm_scalar(row.get("encounter_id")),
                "date": norm_scalar(row.get("date")),
                "type": norm_scalar(row.get("type")),
                "signed_status": norm_scalar(row.get("signed_status")),
            }
        )
    passed = normalized == EXPECTED["handoff_encounters"]
    return passed, {"expected": EXPECTED["handoff_encounters"], "actual": normalized}


def check_source_selection(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    selection = as_obj(answer.get("source_selection"))
    expected = EXPECTED["source_selection"]
    selected_actual = norm_list(selection.get("selected_encounter_ids"))
    excluded_detail = set_detail(selection.get("excluded_encounter_ids"), expected["excluded_encounter_ids"])
    checks = {
        "selection_basis": norm_scalar(selection.get("selection_basis")) == expected["selection_basis"],
        "selected_encounter_ids": selected_actual == expected["selected_encounter_ids"],
        "excluded_encounter_ids": not excluded_detail["missing"] and not excluded_detail["extra"],
    }
    return all(checks.values()), {
        "checks": checks,
        "expected": {
            "selection_basis": expected["selection_basis"],
            "selected_encounter_ids": expected["selected_encounter_ids"],
            "excluded_encounter_ids": sorted(expected["excluded_encounter_ids"]),
        },
        "actual": {
            "selection_basis": selection.get("selection_basis"),
            "selected_encounter_ids": selected_actual,
            "excluded_encounter_ids": sorted(norm_set(selection.get("excluded_encounter_ids"))),
        },
        "excluded_detail": excluded_detail,
    }


def check_latest_immunization(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    detail = object_detail(answer.get("latest_immunization"), EXPECTED["latest_immunization"])
    return all(detail["checks"].values()), detail


def check_disclosure(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    detail = object_detail(answer.get("disclosure"), EXPECTED["disclosure"])
    return all(detail["checks"].values()), detail


def check_risk_flags_readiness(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    readiness = as_obj(answer.get("packet_readiness"))
    expected_readiness = EXPECTED["packet_readiness"]
    risk_detail = set_detail(answer.get("risk_flags"), EXPECTED["risk_flags"])
    doc_detail = set_detail(readiness.get("supporting_document_ids"), expected_readiness["supporting_document_ids"])
    blocking_detail = set_detail(readiness.get("blocking_issue_codes"), expected_readiness["blocking_issue_codes"])
    checks = {
        "risk_flags": not risk_detail["missing"] and not risk_detail["extra"],
        "status": norm_scalar(readiness.get("status")) == expected_readiness["status"],
        "ready_to_send": readiness.get("ready_to_send") is expected_readiness["ready_to_send"],
        "supporting_document_ids": not doc_detail["missing"] and not doc_detail["extra"],
        "blocking_issue_codes": not blocking_detail["missing"] and not blocking_detail["extra"],
    }
    return all(checks.values()), {
        "checks": checks,
        "risk_flags": risk_detail,
        "supporting_document_ids": doc_detail,
        "blocking_issue_codes": blocking_detail,
    }


def check_risk_flag_evidence(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    actual = evidence_map(answer.get("risk_flag_evidence"))
    expected = EXPECTED["risk_flag_evidence"]
    detail: dict[str, Any] = {
        "missing_flags": sorted(set(expected) - set(actual)),
        "extra_flags": sorted(set(actual) - set(expected)),
        "by_flag": {},
    }
    passed = not detail["missing_flags"] and not detail["extra_flags"]
    for risk_flag, expected_values in expected.items():
        actual_values = actual.get(risk_flag, {})
        flag_checks = {}
        for field, expected_set in expected_values.items():
            actual_set = actual_values.get(field, set()) if isinstance(actual_values, dict) else set()
            ok = actual_set == expected_set
            flag_checks[field] = {
                "passed": ok,
                "expected": sorted(expected_set),
                "actual": sorted(actual_set),
                "missing": sorted(expected_set - actual_set),
                "extra": sorted(actual_set - expected_set),
            }
            passed = passed and ok
        detail["by_flag"][risk_flag] = flag_checks
    return passed, detail


def evaluate(answer: dict[str, Any]) -> dict[str, Any]:
    total_weight = sum(point["weight"] for point in POINTS)
    checks = {
        "patient_recipient": check_patient_recipient,
        "active_conditions": lambda a: check_exact_set(a, "active_condition_keys"),
        "active_medications": lambda a: check_exact_set(a, "active_medication_keys"),
        "active_allergies": lambda a: check_exact_set(a, "active_allergy_keys"),
        "handoff_encounters": check_handoff_encounters,
        "source_selection_exclusions": check_source_selection,
        "latest_immunization": check_latest_immunization,
        "disclosure": check_disclosure,
        "risk_flags_readiness": check_risk_flags_readiness,
        "risk_flag_evidence_map": check_risk_flag_evidence,
    }
    point_results = []
    score = 0.0
    for point in POINTS:
        passed, detail = checks[point["id"]](answer)
        assigned = point["weight"] / total_weight
        earned = assigned if passed else 0.0
        score += earned
        point_results.append(
            {
                "id": point["id"],
                "description": point["description"],
                "weight": point["weight"],
                "assigned_score": assigned,
                "passed": passed,
                "earned_score": earned,
                "details": detail,
            }
        )
    return {
        "score": round(score, 6),
        "points": point_results,
    }


def main() -> int:
    if len(sys.argv) > 2:
        print(json.dumps({"score": 0.0, "error": "usage: eval.py <candidate_answer.json>"}))
        return 2
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
    try:
        with path.open("r", encoding="utf-8") as handle:
            answer = json.load(handle)
    except Exception as exc:  # noqa: BLE001 - evaluator should return JSON for all parse/read failures.
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "points": [],
                    "error": f"failed to read candidate answer: {exc}",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1
    if not isinstance(answer, dict):
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "points": [],
                    "error": "candidate answer must be a JSON object",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(evaluate(answer), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
