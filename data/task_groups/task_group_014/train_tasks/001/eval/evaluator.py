#!/usr/bin/env python3
"""Evaluate train_001 UM nurse determination answers."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Callable


EXPECTED_CRITERIA = {
    "PT-ACTIVE": "met",
    "PT-DEFICIT": "met",
    "PT-DX": "met",
    "PT-POC": "met",
    "PT-UNITS": "met",
}

EXPECTED_BASIS_AUDIT = {
    "source_precedence": "current_clinical_records_over_stale_export",
    "precedence_record_order": ["doc-tr-001-eval", "doc-tr-001-poc", "doc-tr-001-stale"],
    "controlling_record_ids": ["doc-tr-001-eval", "doc-tr-001-poc"],
    "exception_record_ids": ["doc-tr-001-stale"],
}


def load_answer(path: Path) -> tuple[Any, str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:  # noqa: BLE001 - evaluation should report parse failures as JSON.
        return None, f"{type(exc).__name__}: {exc}"


def norm_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def norm_enum(value: Any) -> str:
    return norm_string(value).lower()


def get_path(answer: Any, path: list[str]) -> Any:
    current = answer
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def number_equals(value: Any, expected: float, tolerance: float = 0.0001) -> bool:
    if isinstance(value, bool):
        return False
    try:
        return math.isclose(float(value), expected, abs_tol=tolerance)
    except (TypeError, ValueError):
        return False


def string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return None
        normalized.append(item.strip())
    return normalized


def exact_string_list(value: Any, expected: list[str]) -> bool:
    return string_list(value) == expected


def lower_string_list(value: Any) -> list[str] | None:
    values = string_list(value)
    if values is None:
        return None
    return [item.lower() for item in values]


def point_case_and_route(answer: Any) -> tuple[bool, dict[str, Any]]:
    passed = (
        isinstance(answer, dict)
        and norm_string(answer.get("case_id")) == "CASE-TR-001"
        and norm_enum(answer.get("route")) == "nurse_approval"
    )
    return passed, {
        "case_id": answer.get("case_id") if isinstance(answer, dict) else None,
        "route": answer.get("route") if isinstance(answer, dict) else None,
    }


def point_recommendation_status(answer: Any) -> tuple[bool, dict[str, Any]]:
    passed = (
        isinstance(answer, dict)
        and norm_enum(answer.get("recommendation")) == "approve"
        and norm_enum(answer.get("final_status")) == "approved"
    )
    return passed, {
        "recommendation": answer.get("recommendation") if isinstance(answer, dict) else None,
        "final_status": answer.get("final_status") if isinstance(answer, dict) else None,
    }


def point_authorization_window(answer: Any) -> tuple[bool, dict[str, Any]]:
    authorization = get_path(answer, ["authorization"])
    passed = (
        isinstance(authorization, dict)
        and norm_string(authorization.get("auth_number")) == "NPA-2405014"
        and number_equals(authorization.get("approved_units"), 24)
        and norm_string(authorization.get("approved_start")) == "2026-05-06"
        and norm_string(authorization.get("approved_end")) == "2026-07-05"
    )
    return passed, {
        "auth_number": authorization.get("auth_number") if isinstance(authorization, dict) else None,
        "approved_units": authorization.get("approved_units") if isinstance(authorization, dict) else None,
        "approved_start": authorization.get("approved_start") if isinstance(authorization, dict) else None,
        "approved_end": authorization.get("approved_end") if isinstance(authorization, dict) else None,
    }


def point_cpt_modifier(answer: Any) -> tuple[bool, dict[str, Any]]:
    authorization = get_path(answer, ["authorization"])
    cpt_value = authorization.get("approved_cpt") if isinstance(authorization, dict) else None
    modifier = authorization.get("modifier") if isinstance(authorization, dict) else None
    passed = exact_string_list(cpt_value, ["97110", "97112", "97530"]) and norm_string(modifier) == "GP"
    return passed, {
        "approved_cpt": cpt_value,
        "modifier": modifier,
    }


def point_criteria_map(answer: Any) -> tuple[bool, dict[str, Any]]:
    criteria = get_path(answer, ["criteria_results"])
    passed = (
        isinstance(criteria, dict)
        and {str(key): norm_enum(value) for key, value in criteria.items()} == EXPECTED_CRITERIA
    )
    return passed, {
        "criteria_results": criteria,
        "expected_keys": list(EXPECTED_CRITERIA.keys()),
    }


def point_evidence_exclusion(answer: Any) -> tuple[bool, dict[str, Any]]:
    if not isinstance(answer, dict):
        return False, {"evidence_documents": None, "excluded_documents": None}
    evidence = answer.get("evidence_documents")
    excluded = answer.get("excluded_documents")
    evidence_list = string_list(evidence)
    passed = (
        exact_string_list(evidence, ["DOC-TR-001-EVAL", "DOC-TR-001-POC"])
        and exact_string_list(excluded, ["DOC-TR-001-STALE"])
        and evidence_list is not None
        and "DOC-TR-001-STALE" not in evidence_list
    )
    return passed, {
        "evidence_documents": evidence,
        "excluded_documents": excluded,
    }


def point_next_action(answer: Any) -> tuple[bool, dict[str, Any]]:
    passed = (
        isinstance(answer, dict)
        and norm_enum(answer.get("determination_letter")) == "approval"
        and norm_enum(answer.get("next_action")) == "issue_approval"
        and norm_enum(answer.get("route")) not in {"medical_director_review", "peer_to_peer"}
    )
    return passed, {
        "determination_letter": answer.get("determination_letter") if isinstance(answer, dict) else None,
        "next_action": answer.get("next_action") if isinstance(answer, dict) else None,
        "route": answer.get("route") if isinstance(answer, dict) else None,
    }


def point_basis_audit(answer: Any) -> tuple[bool, dict[str, Any]]:
    audit = answer.get("basis_audit") if isinstance(answer, dict) else None
    actual = {
        "source_precedence": norm_enum(audit.get("source_precedence")) if isinstance(audit, dict) else None,
        "precedence_record_order": lower_string_list(audit.get("precedence_record_order"))
        if isinstance(audit, dict)
        else None,
        "controlling_record_ids": lower_string_list(audit.get("controlling_record_ids"))
        if isinstance(audit, dict)
        else None,
        "exception_record_ids": lower_string_list(audit.get("exception_record_ids"))
        if isinstance(audit, dict)
        else None,
    }
    return actual == EXPECTED_BASIS_AUDIT, {"expected": EXPECTED_BASIS_AUDIT, "actual": actual}


RUBRIC: list[tuple[str, int, Callable[[Any], tuple[bool, dict[str, Any]]]]] = [
    ("target_case_and_route_identity", 1, point_case_and_route),
    ("approval_recommendation_and_final_status", 2, point_recommendation_status),
    ("authorization_number_units_and_dates", 2, point_authorization_window),
    ("approved_cpt_modifier_line_set", 1, point_cpt_modifier),
    ("all_met_pt_criteria_map", 2, point_criteria_map),
    ("current_evidence_and_stale_exclusion", 2, point_evidence_exclusion),
    ("approval_letter_and_next_action", 1, point_next_action),
    ("business_basis_audit", 1, point_basis_audit),
]


def evaluate(answer: Any, parse_error: str | None = None) -> dict[str, Any]:
    total_weight = sum(weight for _, weight, _ in RUBRIC)
    points: list[dict[str, Any]] = []
    earned_weight = 0
    for name, weight, check in RUBRIC:
        if parse_error is None:
            passed, details = check(answer)
        else:
            passed, details = False, {"parse_error": parse_error}
        if passed:
            earned_weight += weight
        assigned_score = weight / total_weight
        points.append(
            {
                "name": name,
                "weight": weight,
                "assigned_score": round(assigned_score, 6),
                "passed": passed,
                "earned_score": round(assigned_score if passed else 0.0, 6),
                "details": details,
            }
        )
    return {
        "score": round(earned_weight / total_weight, 6),
        "points": points,
        "total_weight": total_weight,
    }


def main() -> int:
    answer_path = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
    )
    answer, parse_error = load_answer(answer_path)
    print(json.dumps(evaluate(answer, parse_error), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
