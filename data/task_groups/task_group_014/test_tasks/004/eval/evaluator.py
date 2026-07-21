#!/usr/bin/env python3
"""Deterministic evaluator for test_004."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable


EXPECTED = {
    "case_id": "P2P-TE-004",
    "p2p_id": "P2P-TE-004-E1",
    "requested_cpt": "78431",
    "p2p_outcome": "overturn_to_approval",
    "final_status": "approved",
    "criteria_results": {
        "PET-IND": "met",
        "PET-FACTOR": "met",
    },
    "resolved_criteria": ["PET-FACTOR"],
    "new_information_changed_review": True,
    "supporting_pet_factors": [
        "prior_equivocal_spect",
        "bmi_limitation",
    ],
    "authorization": {
        "auth_number": "NPA-2406199",
        "approved_units": 1,
        "approved_start": "2026-06-18",
        "approved_end": "2026-06-18",
        "approved_cpt": "78431",
    },
    "letter_type": "approval",
    "recommended_alternative": "none",
    "internal_appeal_deadline": None,
    "basis_audit": {
        "source_precedence": "new_patient_specific_p2p_information",
        "precedence_record_order": [
            "p2p-te-004-e1",
            "doc-te-004-p2p",
            "pet-factor",
            "auth-te-004",
        ],
        "controlling_record_ids": [
            "doc-te-004-p2p",
            "p2p-te-004-e1",
            "auth-te-004",
        ],
        "exception_record_ids": [
            "pet-factor",
        ],
    },
}


def load_answer(path: str) -> tuple[Any | None, str | None]:
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            answer = json.load(handle)
    except Exception as exc:
        return None, f"Unable to read valid JSON: {exc}"
    if not isinstance(answer, dict):
        return None, "Answer must be a JSON object."
    return answer, None


def clean_str(value: Any, upper: bool = False, lower: bool = False) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if upper:
        return text.upper()
    if lower:
        return text.lower()
    return text


def as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit()):
            return int(stripped)
    return None


def normalize_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return None


def normalized_list(value: Any, upper: bool = False, lower: bool = False) -> list[str] | None:
    if not isinstance(value, list):
        return None
    result = []
    for item in value:
        text = clean_str(item, upper=upper, lower=lower)
        if text is None:
            return None
        result.append(text)
    return result


def normalized_key_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    result = []
    for item in value:
        text = clean_str(item, lower=True)
        if text is None:
            return None
        result.append(text)
    return result


def normalized_criteria(value: Any) -> dict[str, str] | None:
    if isinstance(value, dict):
        pairs = value.items()
    elif isinstance(value, list):
        pairs = []
        for item in value:
            if not isinstance(item, dict):
                return None
            key = item.get("criterion_id") or item.get("criterion") or item.get("id")
            pairs.append((key, item.get("result")))
    else:
        return None

    result: dict[str, str] = {}
    for key, item_value in pairs:
        norm_key = clean_str(key, upper=True)
        norm_value = clean_str(item_value, lower=True)
        if norm_key is None or norm_value is None:
            return None
        result[norm_key] = norm_value
    return result


def normalized_authorization(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {
        "auth_number": clean_str(value.get("auth_number"), upper=True),
        "approved_units": as_int(value.get("approved_units")),
        "approved_start": clean_str(value.get("approved_start")),
        "approved_end": clean_str(value.get("approved_end")),
        "approved_cpt": clean_str(value.get("approved_cpt")),
    }


def audit_value(answer: dict[str, Any], key: str) -> Any:
    audit = answer.get("basis_audit")
    if not isinstance(audit, dict):
        return None
    return audit.get(key)


def is_null_value(value: Any) -> bool:
    return value is None


def check_identity_and_cpt(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    expected = {
        "case_id": EXPECTED["case_id"],
        "p2p_id": EXPECTED["p2p_id"],
        "requested_cpt": EXPECTED["requested_cpt"],
    }
    actual = {
        "case_id": clean_str(answer.get("case_id"), upper=True),
        "p2p_id": clean_str(answer.get("p2p_id"), upper=True),
        "requested_cpt": clean_str(answer.get("requested_cpt")),
    }
    return actual == expected, {"expected": expected, "actual": actual}


def check_outcome_and_status(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    expected = {
        "p2p_outcome": EXPECTED["p2p_outcome"],
        "final_status": EXPECTED["final_status"],
    }
    actual = {
        "p2p_outcome": clean_str(answer.get("p2p_outcome"), lower=True),
        "final_status": clean_str(answer.get("final_status"), lower=True),
    }
    return actual == expected, {"expected": expected, "actual": actual}


def check_criteria_results(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    actual = normalized_criteria(answer.get("criteria_results"))
    expected = EXPECTED["criteria_results"]
    return actual == expected, {"expected": expected, "actual": actual}


def check_review_change_and_factors(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    expected = {
        "resolved_criteria": EXPECTED["resolved_criteria"],
        "new_information_changed_review": EXPECTED["new_information_changed_review"],
        "supporting_pet_factors": EXPECTED["supporting_pet_factors"],
    }
    actual = {
        "resolved_criteria": normalized_list(answer.get("resolved_criteria"), upper=True),
        "new_information_changed_review": normalize_bool(answer.get("new_information_changed_review")),
        "supporting_pet_factors": normalized_list(answer.get("supporting_pet_factors"), lower=True),
    }
    return actual == expected, {"expected": expected, "actual": actual}


def check_authorization(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    actual = normalized_authorization(answer.get("authorization"))
    expected = EXPECTED["authorization"]
    return actual == expected, {"expected": expected, "actual": actual}


def check_approval_letter_and_no_denial_path(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    expected = {
        "letter_type": EXPECTED["letter_type"],
        "recommended_alternative": EXPECTED["recommended_alternative"],
        "internal_appeal_deadline": EXPECTED["internal_appeal_deadline"],
    }
    actual = {
        "letter_type": clean_str(answer.get("letter_type"), lower=True),
        "recommended_alternative": clean_str(answer.get("recommended_alternative"), lower=True),
        "internal_appeal_deadline": answer.get("internal_appeal_deadline"),
    }
    passed = (
        actual["letter_type"] == expected["letter_type"]
        and actual["recommended_alternative"] == expected["recommended_alternative"]
        and is_null_value(actual["internal_appeal_deadline"])
    )
    return passed, {"expected": expected, "actual": actual}


def check_basis_source_precedence(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    expected = EXPECTED["basis_audit"]["source_precedence"]
    actual = clean_str(audit_value(answer, "source_precedence"), lower=True)
    return actual == expected, {"expected": expected, "actual": actual}


def check_basis_controlling_records(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    expected = EXPECTED["basis_audit"]["controlling_record_ids"]
    actual = normalized_key_list(audit_value(answer, "controlling_record_ids"))
    return actual == expected, {"expected": expected, "actual": actual}


def check_basis_precedence_record_order(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    expected = EXPECTED["basis_audit"]["precedence_record_order"]
    actual = normalized_key_list(audit_value(answer, "precedence_record_order"))
    return actual == expected, {"expected": expected, "actual": actual}


def check_basis_exception_records(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    expected = EXPECTED["basis_audit"]["exception_record_ids"]
    actual = normalized_key_list(audit_value(answer, "exception_record_ids"))
    return actual == expected, {"expected": expected, "actual": actual}


PointCheck = Callable[[dict[str, Any]], tuple[bool, dict[str, Any]]]


RUBRIC: list[dict[str, Any]] = [
    {
        "id": "identity_and_requested_cpt",
        "weight": 1,
        "goal": "Correct case identity, P2P identity, and requested CPT.",
        "check": check_identity_and_cpt,
    },
    {
        "id": "overturn_outcome_and_approved_status",
        "weight": 3,
        "goal": "Correct overturn P2P outcome and approved final status.",
        "check": check_outcome_and_status,
    },
    {
        "id": "criteria_result_map",
        "weight": 2,
        "goal": "Correct criteria map with PET-FACTOR now met.",
        "check": check_criteria_results,
    },
    {
        "id": "new_information_and_supported_pet_factors",
        "weight": 2,
        "goal": "Correct new-information flag, resolved criterion, and supporting PET-over-SPECT factors.",
        "check": check_review_change_and_factors,
    },
    {
        "id": "authorization_details",
        "weight": 2,
        "goal": "Correct authorization number, approved unit count, approval date range, and approved CPT.",
        "check": check_authorization,
    },
    {
        "id": "approval_letter_and_no_denial_path",
        "weight": 1,
        "goal": "Correct approval letter type with no alternative modality or internal appeal deadline.",
        "check": check_approval_letter_and_no_denial_path,
    },
    {
        "id": "basis_source_precedence",
        "weight": 3,
        "goal": "Correct business source-precedence basis.",
        "check": check_basis_source_precedence,
    },
    {
        "id": "basis_precedence_record_order",
        "weight": 3,
        "goal": "Correct source-precedence record order.",
        "check": check_basis_precedence_record_order,
    },
    {
        "id": "basis_controlling_records",
        "weight": 1,
        "goal": "Correct controlling P2P, document, and authorization record IDs.",
        "check": check_basis_controlling_records,
    },
    {
        "id": "basis_exception_records",
        "weight": 2,
        "goal": "Correct resolved exception or gap IDs.",
        "check": check_basis_exception_records,
    },
]


def evaluate(answer: Any, load_error: str | None = None) -> dict[str, Any]:
    total_weight = sum(point["weight"] for point in RUBRIC)
    points: list[dict[str, Any]] = []

    if load_error is not None or not isinstance(answer, dict):
        for point in RUBRIC:
            assigned = point["weight"] / total_weight
            points.append(
                {
                    "id": point["id"],
                    "goal": point["goal"],
                    "weight": point["weight"],
                    "assigned_score": assigned,
                    "passed": False,
                    "earned_score": 0.0,
                    "details": {"error": load_error or "Answer must be a JSON object."},
                }
            )
        return {"score": 0.0, "points": points, "total_weight": total_weight}

    earned_weight = 0
    for point in RUBRIC:
        check: PointCheck = point["check"]
        passed, details = check(answer)
        weight = point["weight"]
        assigned = weight / total_weight
        earned_weight += weight if passed else 0
        points.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": weight,
                "assigned_score": assigned,
                "passed": passed,
                "earned_score": assigned if passed else 0.0,
                "details": details,
            }
        )

    score = earned_weight / total_weight
    return {"score": score, "points": points, "total_weight": total_weight}


def main() -> int:
    default_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"
    answer_path = sys.argv[1] if len(sys.argv) > 1 else str(default_path)
    answer, load_error = load_answer(answer_path)
    result = evaluate(answer, load_error)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
