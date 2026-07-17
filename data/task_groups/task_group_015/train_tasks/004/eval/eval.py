#!/usr/bin/env python3
"""Deterministic evaluator for task_group_015 train_004."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


TOTAL_WEIGHT = 14


def load_candidate(path: Path) -> tuple[Any | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:  # noqa: BLE001 - evaluator should report parse errors as JSON.
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


def norm_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip() for item in value}


def norm_code_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip().upper() for item in value}


def validation_map(value: Any) -> dict[str, dict[str, Any]]:
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

    duplicate = get_path(answer, "duplicate_review", {})
    service_request = get_path(answer, "service_request", {})
    sbar = get_path(answer, "sbar_coverage", {})

    expected_patients = {"P-55218", "P-55281"}
    got_patients = {
        norm_scalar(duplicate.get("primary_patient_id")) if isinstance(duplicate, dict) else None,
        norm_scalar(duplicate.get("possible_duplicate_patient_id")) if isinstance(duplicate, dict) else None,
    }
    duplicate_decision_pass = (
        isinstance(duplicate, dict)
        and duplicate.get("candidate_id") == "DUP-TR-004"
        and duplicate.get("candidate_status") == "needs_review"
        and duplicate.get("decision") == "review_hold"
        and got_patients == expected_patients
        and duplicate.get("merge_target_patient_id") is None
        and duplicate.get("merge_source_patient_id") is None
    )
    points.append(
        point(
            "duplicate_decision",
            2,
            duplicate_decision_pass,
            {
                "expected": {
                    "candidate_id": "DUP-TR-004",
                    "candidate_status": "needs_review",
                    "decision": "review_hold",
                    "patient_ids": sorted(expected_patients),
                    "merge_target_patient_id": None,
                    "merge_source_patient_id": None,
                },
                "got": duplicate if isinstance(duplicate, dict) else type(duplicate).__name__,
            },
        )
    )

    expected_conflicts = {"different_given_name", "different_phone", "opposite_laterality_problem"}
    expected_matches = {"same_dob", "same_insurance", "similar_address"}
    got_conflicts = norm_set(duplicate.get("conflict_signals")) if isinstance(duplicate, dict) else set()
    got_matches = norm_set(duplicate.get("match_signals")) if isinstance(duplicate, dict) else set()
    conflict_pass = got_conflicts == expected_conflicts and got_matches == expected_matches
    points.append(
        point(
            "duplicate_conflict_and_match_signals",
            2,
            conflict_pass,
            {
                "expected_conflict_signals": sorted(expected_conflicts),
                "got_conflict_signals": sorted(got_conflicts),
                "expected_match_signals": sorted(expected_matches),
                "got_match_signals": sorted(got_matches),
            },
        )
    )

    service_code_pass = (
        isinstance(service_request, dict)
        and service_request.get("service_request_id") == "SR-TR-004"
        and service_request.get("patient_id") == "P-55218"
        and str(service_request.get("service_code", "")).strip().upper() == "ORTHO-CONSULT"
        and service_request.get("service_code_valid") is True
    )
    points.append(
        point(
            "service_request_id_and_service_code",
            2,
            service_code_pass,
            {
                "expected": {
                    "service_request_id": "SR-TR-004",
                    "patient_id": "P-55218",
                    "service_code": "ORTHO-CONSULT",
                    "service_code_valid": True,
                },
                "got": {
                    "service_request_id": service_request.get("service_request_id")
                    if isinstance(service_request, dict)
                    else None,
                    "patient_id": service_request.get("patient_id") if isinstance(service_request, dict) else None,
                    "service_code": service_request.get("service_code") if isinstance(service_request, dict) else None,
                    "service_code_valid": service_request.get("service_code_valid")
                    if isinstance(service_request, dict)
                    else None,
                },
            },
        )
    )

    state_pass = (
        isinstance(service_request, dict)
        and service_request.get("status") == "active"
        and service_request.get("intent") == "order"
        and service_request.get("priority") == "routine"
        and service_request.get("authored_on") == "2026-03-04"
        and service_request.get("occurrence_date") == "2026-03-20"
    )
    points.append(
        point(
            "status_intent_priority_and_dates",
            2,
            state_pass,
            {
                "expected": {
                    "status": "active",
                    "intent": "order",
                    "priority": "routine",
                    "authored_on": "2026-03-04",
                    "occurrence_date": "2026-03-20",
                },
                "got": {
                    "status": service_request.get("status") if isinstance(service_request, dict) else None,
                    "intent": service_request.get("intent") if isinstance(service_request, dict) else None,
                    "priority": service_request.get("priority") if isinstance(service_request, dict) else None,
                    "authored_on": service_request.get("authored_on") if isinstance(service_request, dict) else None,
                    "occurrence_date": service_request.get("occurrence_date")
                    if isinstance(service_request, dict)
                    else None,
                },
            },
        )
    )

    expected_reason_codes = {"M17.11", "S83.241A"}
    got_reason_codes = (
        norm_code_set(service_request.get("reason_codes")) if isinstance(service_request, dict) else set()
    )
    validations = (
        validation_map(service_request.get("reason_code_validation")) if isinstance(service_request, dict) else {}
    )
    reason_validation_pass = (
        got_reason_codes == expected_reason_codes
        and set(validations) == expected_reason_codes
        and validations.get("M17.11", {}).get("valid") is True
        and validations.get("M17.11", {}).get("chapter") == "Musculoskeletal"
        and validations.get("M17.11", {}).get("matches_patient_evidence") is True
        and validations.get("S83.241A", {}).get("valid") is True
        and validations.get("S83.241A", {}).get("chapter") == "Injury"
        and validations.get("S83.241A", {}).get("matches_patient_evidence") is True
    )
    points.append(
        point(
            "reason_codes_and_validation",
            2,
            reason_validation_pass,
            {
                "expected_reason_codes": sorted(expected_reason_codes),
                "got_reason_codes": sorted(got_reason_codes),
                "expected_validation": {
                    "M17.11": {"valid": True, "chapter": "Musculoskeletal", "matches_patient_evidence": True},
                    "S83.241A": {"valid": True, "chapter": "Injury", "matches_patient_evidence": True},
                },
                "got_validation": validations,
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

    provider_pass = (
        isinstance(service_request, dict)
        and service_request.get("requester_provider_id") == "PRV-PCP-002"
        and service_request.get("performer_provider_id") == "PRV-ORTHO-011"
        and service_request.get("performer_service_line") == "orthopedics"
    )
    points.append(
        point(
            "provider_assignment",
            2,
            provider_pass,
            {
                "expected": {
                    "requester_provider_id": "PRV-PCP-002",
                    "performer_provider_id": "PRV-ORTHO-011",
                    "performer_service_line": "orthopedics",
                },
                "got": {
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

    earned_weight = sum(p["weight"] for p in points if p["passed"])
    score = round(earned_weight / TOTAL_WEIGHT, 6)
    return {
        "score": score,
        "points": points,
        "total_weight": TOTAL_WEIGHT,
    }


def main() -> None:
    candidate_path = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "../output/answer.json"
    )
    answer, error = load_candidate(candidate_path)
    if error is not None:
        failed = [
            point("duplicate_decision", 2, False, {"candidate_path": str(candidate_path), "error": error}),
            point(
                "duplicate_conflict_and_match_signals",
                2,
                False,
                {"candidate_path": str(candidate_path), "error": error},
            ),
            point(
                "service_request_id_and_service_code",
                2,
                False,
                {"candidate_path": str(candidate_path), "error": error},
            ),
            point(
                "status_intent_priority_and_dates", 2, False, {"candidate_path": str(candidate_path), "error": error}
            ),
            point("reason_codes_and_validation", 2, False, {"candidate_path": str(candidate_path), "error": error}),
            point("sbar_section_completeness", 2, False, {"candidate_path": str(candidate_path), "error": error}),
            point("provider_assignment", 2, False, {"candidate_path": str(candidate_path), "error": error}),
        ]
        print(json.dumps({"score": 0.0, "points": failed, "total_weight": TOTAL_WEIGHT}, indent=2, sort_keys=True))
        return
    print(json.dumps(evaluate(answer), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
