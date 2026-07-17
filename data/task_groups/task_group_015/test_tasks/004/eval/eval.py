#!/usr/bin/env python3
"""Deterministic evaluator for task_group_015 test_004."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


TOTAL_WEIGHT = 17


def load_candidate(path: Path) -> tuple[Any | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:  # noqa: BLE001 - evaluator should always return JSON.
        return None, f"{type(exc).__name__}: {exc}"


def get_path(obj: Any, dotted: str, default: Any = None) -> Any:
    current = obj
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def norm_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def norm_lower(value: Any) -> str:
    return str(value).strip().lower()


def norm_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip() for item in value}


def norm_code_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip().upper() for item in value}


def code_validation_map(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code", "")).strip().upper()
        if code:
            result[code] = item
    return result


def point(point_id: str, weight: int, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    assigned = weight / TOTAL_WEIGHT
    return {
        "id": point_id,
        "weight": weight,
        "assigned_score": round(assigned, 6),
        "passed": bool(passed),
        "earned_score": round(assigned if passed else 0.0, 6),
        "details": details,
    }


def evaluate(answer: Any) -> dict[str, Any]:
    points: list[dict[str, Any]] = []

    identity = get_path(answer, "request_identity", {})
    patient = identity.get("patient", {}) if isinstance(identity, dict) else {}
    service_request = get_path(answer, "service_request", {})
    reason_validation = get_path(answer, "reason_code_validation", {})
    evidence = get_path(answer, "clinical_evidence", {})
    encounter = evidence.get("key_encounter", {}) if isinstance(evidence, dict) else {}
    medication = evidence.get("key_medication", {}) if isinstance(evidence, dict) else {}
    sbar = get_path(answer, "sbar_coverage", {})
    filing = get_path(answer, "filing_decision", {})

    identity_pass = (
        isinstance(answer, dict)
        and answer.get("task_id") == "test_004"
        and isinstance(identity, dict)
        and identity.get("service_request_id") == "SR-TE-004"
        and isinstance(patient, dict)
        and patient.get("patient_id") == "P-91804"
        and patient.get("enterprise_mrn") == "E10091804"
        and patient.get("display_name") == "Owen Mercer"
        and patient.get("dob") == "1970-12-06"
    )
    points.append(
        point(
            "request_and_patient_identity",
            2,
            identity_pass,
            {
                "expected": {
                    "task_id": "test_004",
                    "service_request_id": "SR-TE-004",
                    "patient_id": "P-91804",
                    "enterprise_mrn": "E10091804",
                    "display_name": "Owen Mercer",
                    "dob": "1970-12-06",
                },
                "got": {
                    "task_id": answer.get("task_id") if isinstance(answer, dict) else None,
                    "request_identity": identity if isinstance(identity, dict) else type(identity).__name__,
                },
            },
        )
    )

    service_provider_pass = (
        isinstance(service_request, dict)
        and str(service_request.get("service_code", "")).strip().upper() == "NEURO-CONSULT"
        and service_request.get("service_code_valid") is True
        and service_request.get("requester_provider_id") == "PRV-PCP-002"
        and service_request.get("performer_provider_id") == "PRV-NEURO-040"
        and service_request.get("performer_service_line") == "neurology"
    )
    points.append(
        point(
            "service_code_and_provider_assignment",
            2,
            service_provider_pass,
            {
                "expected": {
                    "service_code": "NEURO-CONSULT",
                    "service_code_valid": True,
                    "requester_provider_id": "PRV-PCP-002",
                    "performer_provider_id": "PRV-NEURO-040",
                    "performer_service_line": "neurology",
                },
                "got": {
                    "service_code": service_request.get("service_code") if isinstance(service_request, dict) else None,
                    "service_code_valid": service_request.get("service_code_valid")
                    if isinstance(service_request, dict)
                    else None,
                    "requester_provider_id": service_request.get("requester_provider_id")
                    if isinstance(service_request, dict)
                    else None,
                    "performer_provider_id": service_request.get("performer_provider_id")
                    if isinstance(service_request, dict)
                    else None,
                    "performer_service_line": service_request.get("performer_service_line")
                    if isinstance(service_request, dict)
                    else None,
                },
            },
        )
    )

    status_dates_pass = (
        isinstance(service_request, dict)
        and service_request.get("status") == "active"
        and service_request.get("intent") == "order"
        and service_request.get("priority") == "routine"
        and service_request.get("authored_on") == "2026-04-10"
        and service_request.get("occurrence_date") == "2026-04-28"
        and service_request.get("status_valid") is True
        and service_request.get("intent_valid") is True
        and service_request.get("priority_valid") is True
        and service_request.get("date_sequence_valid") is True
    )
    points.append(
        point(
            "status_intent_priority_and_date_validation",
            2,
            status_dates_pass,
            {
                "expected": {
                    "status": "active",
                    "intent": "order",
                    "priority": "routine",
                    "authored_on": "2026-04-10",
                    "occurrence_date": "2026-04-28",
                    "status_valid": True,
                    "intent_valid": True,
                    "priority_valid": True,
                    "date_sequence_valid": True,
                },
                "got": service_request if isinstance(service_request, dict) else type(service_request).__name__,
            },
        )
    )

    filing_pass = (
        isinstance(filing, dict)
        and filing.get("source_status") == "draft"
        and filing.get("ready_to_file_status") == "active"
        and filing.get("action") == "file_as_active_order"
        and filing.get("ready_to_file") is True
        and norm_set(filing.get("hold_reason_codes")) == set()
    )
    points.append(
        point(
            "filing_disposition",
            3,
            filing_pass,
            {
                "expected": {
                    "source_status": "draft",
                    "ready_to_file_status": "active",
                    "action": "file_as_active_order",
                    "ready_to_file": True,
                    "hold_reason_codes": [],
                },
                "got": filing if isinstance(filing, dict) else type(filing).__name__,
            },
        )
    )

    expected_reason_codes = {"G20.A1", "R41.3"}
    got_reason_codes = (
        norm_code_set(reason_validation.get("reason_codes")) if isinstance(reason_validation, dict) else set()
    )
    validations = code_validation_map(reason_validation.get("codes")) if isinstance(reason_validation, dict) else {}
    reason_codes_pass = (
        got_reason_codes == expected_reason_codes
        and set(validations) == expected_reason_codes
        and validations.get("G20.A1", {}).get("valid") is True
        and validations.get("G20.A1", {}).get("chapter") == "Nervous system"
        and validations.get("G20.A1", {}).get("matches_patient_evidence") is True
        and validations.get("G20.A1", {}).get("condition_id") == "COND-A6D0DA4D"
        and validations.get("R41.3", {}).get("valid") is True
        and validations.get("R41.3", {}).get("chapter") == "Symptoms"
        and validations.get("R41.3", {}).get("matches_patient_evidence") is True
        and validations.get("R41.3", {}).get("condition_id") == "COND-2EEFD6B5"
    )
    points.append(
        point(
            "reason_codes_and_icd_chart_validation",
            2,
            reason_codes_pass,
            {
                "expected_reason_codes": sorted(expected_reason_codes),
                "got_reason_codes": sorted(got_reason_codes),
                "expected_validation": {
                    "G20.A1": {
                        "valid": True,
                        "chapter": "Nervous system",
                        "matches_patient_evidence": True,
                        "condition_id": "COND-A6D0DA4D",
                    },
                    "R41.3": {
                        "valid": True,
                        "chapter": "Symptoms",
                        "matches_patient_evidence": True,
                        "condition_id": "COND-2EEFD6B5",
                    },
                },
                "got_validation": validations,
            },
        )
    )

    encounter_pass = (
        isinstance(encounter, dict)
        and encounter.get("encounter_id") == "ENC-91804-20260409"
        and encounter.get("date") == "2026-04-09"
        and encounter.get("type") == "office_visit"
        and encounter.get("provider_id") == "PRV-PCP-002"
        and encounter.get("signed_status") == "signed"
        and norm_code_set(encounter.get("diagnosis_codes")) == expected_reason_codes
        and {norm_lower(item) for item in encounter.get("medications_mentioned", [])} == {"carbidopa/levodopa"}
        and encounter.get("care_plan_tag") == "neurology_referral_for_parkinson_memory"
    )
    points.append(
        point(
            "key_evidence_encounter",
            2,
            encounter_pass,
            {
                "expected": {
                    "encounter_id": "ENC-91804-20260409",
                    "date": "2026-04-09",
                    "type": "office_visit",
                    "provider_id": "PRV-PCP-002",
                    "signed_status": "signed",
                    "diagnosis_codes": sorted(expected_reason_codes),
                    "medications_mentioned": ["carbidopa/levodopa"],
                    "care_plan_tag": "neurology_referral_for_parkinson_memory",
                },
                "got": encounter if isinstance(encounter, dict) else type(encounter).__name__,
            },
        )
    )

    expected_condition_keys = {"memory_loss", "parkinson_disease"}
    got_condition_keys = (
        norm_set(evidence.get("supporting_active_condition_keys")) if isinstance(evidence, dict) else set()
    )
    medication_condition_pass = (
        isinstance(medication, dict)
        and medication.get("medication_id") == "MED-05C47E07"
        and norm_lower(medication.get("medication")) == "carbidopa/levodopa"
        and medication.get("normalized_key") == "carbidopa_levodopa"
        and medication.get("dose") == "25/100 mg"
        and medication.get("route") == "oral"
        and medication.get("frequency") == "three times daily"
        and medication.get("status") == "active"
        and medication.get("supports_reason") is True
        and got_condition_keys == expected_condition_keys
    )
    points.append(
        point(
            "key_medication_and_current_condition_support",
            2,
            medication_condition_pass,
            {
                "expected_medication": {
                    "medication_id": "MED-05C47E07",
                    "medication": "carbidopa/levodopa",
                    "normalized_key": "carbidopa_levodopa",
                    "dose": "25/100 mg",
                    "route": "oral",
                    "frequency": "three times daily",
                    "status": "active",
                    "supports_reason": True,
                },
                "got_medication": medication if isinstance(medication, dict) else type(medication).__name__,
                "expected_supporting_active_condition_keys": sorted(expected_condition_keys),
                "got_supporting_active_condition_keys": sorted(got_condition_keys),
            },
        )
    )

    expected_sections = {"situation", "background", "assessment", "recommendation"}
    got_sections = norm_set(sbar.get("sections_present")) if isinstance(sbar, dict) else set()
    got_missing = norm_set(sbar.get("missing_sections")) if isinstance(sbar, dict) else set()
    sbar_pass = (
        isinstance(sbar, dict)
        and sbar.get("complete") is True
        and got_sections == expected_sections
        and got_missing == set()
    )
    points.append(
        point(
            "sbar_section_completeness",
            2,
            sbar_pass,
            {
                "expected_complete": True,
                "expected_sections_present": sorted(expected_sections),
                "expected_missing_sections": [],
                "got_complete": sbar.get("complete") if isinstance(sbar, dict) else None,
                "got_sections_present": sorted(got_sections),
                "got_missing_sections": sorted(got_missing),
            },
        )
    )

    earned_weight = sum(p["weight"] for p in points if p["passed"])
    return {
        "score": round(earned_weight / TOTAL_WEIGHT, 6),
        "points": points,
        "total_weight": TOTAL_WEIGHT,
    }


def failed_parse_result(candidate_path: Path, error: str) -> dict[str, Any]:
    point_specs = [
        ("request_and_patient_identity", 2),
        ("service_code_and_provider_assignment", 2),
        ("status_intent_priority_and_date_validation", 2),
        ("filing_disposition", 3),
        ("reason_codes_and_icd_chart_validation", 2),
        ("key_evidence_encounter", 2),
        ("key_medication_and_current_condition_support", 2),
        ("sbar_section_completeness", 2),
    ]
    failed = [
        point(point_id, weight, False, {"candidate_path": str(candidate_path), "error": error})
        for point_id, weight in point_specs
    ]
    return {"score": 0.0, "points": failed, "total_weight": TOTAL_WEIGHT}


def main() -> None:
    candidate_path = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "../output/answer.json"
    )
    answer, error = load_candidate(candidate_path)
    if error is not None:
        print(json.dumps(failed_parse_result(candidate_path, error), indent=2, sort_keys=True))
        return
    print(json.dumps(evaluate(answer), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
