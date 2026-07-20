#!/usr/bin/env python3
"""Deterministic evaluator for train_004."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable


EXPECTED_CRITERIA = {
    "PET-IND": "met",
    "PET-FACTOR": "not_met",
}
EXPECTED_MISSING_FACTORS = [
    "prior_equivocal_spect",
    "bmi_limitation",
    "attenuation_artifact",
]
EXPECTED_BASIS_AUDIT = {
    "source_precedence": "new_patient_specific_p2p_information",
    "precedence_record_order": ["p2p-tr-004-e1", "doc-tr-004-card", "pet-factor"],
    "controlling_record_ids": ["doc-tr-004-card", "p2p-tr-004-e1"],
    "exception_record_ids": [
        "pet-factor",
        "prior_equivocal_spect",
        "bmi_limitation",
        "attenuation_artifact",
    ],
}


def load_answer(path: str) -> tuple[Any | None, str | None]:
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            answer = json.load(handle)
    except Exception as exc:  # pragma: no cover - defensive CLI path handling
        return None, f"Unable to read valid JSON: {exc}"
    if not isinstance(answer, dict):
        return None, "Answer must be a JSON object."
    return answer, None


def exact(value: Any, expected: Any) -> bool:
    return value == expected


def string_value(answer: dict[str, Any], key: str) -> str | None:
    value = answer.get(key)
    return value if isinstance(value, str) else None


def lower_string(value: Any) -> str | None:
    return value.strip().lower() if isinstance(value, str) else None


def lower_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    result = []
    for item in value:
        text = lower_string(item)
        if text is None:
            return None
        result.append(text)
    return result


def check_identity_and_cpt(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    expected = {
        "case_id": "P2P-TR-004",
        "p2p_id": "P2P-TR-004-E1",
        "requested_cpt": "78431",
    }
    actual = {key: answer.get(key) for key in expected}
    return actual == expected, {"expected": expected, "actual": actual}


def check_outcome_and_status(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    expected = {
        "p2p_outcome": "uphold_intended_adverse_decision",
        "final_status": "denied",
    }
    actual = {key: answer.get(key) for key in expected}
    return actual == expected, {"expected": expected, "actual": actual}


def check_criteria_results(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    actual = answer.get("criteria_results")
    passed = isinstance(actual, dict) and actual == EXPECTED_CRITERIA
    return passed, {"expected": EXPECTED_CRITERIA, "actual": actual}


def check_unresolved_missing_and_review_change(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    expected = {
        "unresolved_criteria": ["PET-FACTOR"],
        "new_information_changed_review": False,
        "missing_pet_factors": EXPECTED_MISSING_FACTORS,
    }
    actual = {
        "unresolved_criteria": answer.get("unresolved_criteria"),
        "new_information_changed_review": answer.get("new_information_changed_review"),
        "missing_pet_factors": answer.get("missing_pet_factors"),
    }
    passed = actual == expected
    return passed, {"expected": expected, "actual": actual}


def check_letter_and_alternative(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    expected = {
        "letter_type": "denial",
        "recommended_alternative": "SPECT MPI",
    }
    actual = {key: answer.get(key) for key in expected}
    return actual == expected, {"expected": expected, "actual": actual}


def check_appeal_deadline(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    actual = string_value(answer, "internal_appeal_deadline")
    expected = "2026-11-09"
    return exact(actual, expected), {"expected": expected, "actual": actual}


def check_basis_audit(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    audit = answer.get("basis_audit") if isinstance(answer, dict) else None
    actual = {
        "source_precedence": lower_string(audit.get("source_precedence")) if isinstance(audit, dict) else None,
        "precedence_record_order": lower_list(audit.get("precedence_record_order"))
        if isinstance(audit, dict)
        else None,
        "controlling_record_ids": lower_list(audit.get("controlling_record_ids")) if isinstance(audit, dict) else None,
        "exception_record_ids": lower_list(audit.get("exception_record_ids")) if isinstance(audit, dict) else None,
    }
    return actual == EXPECTED_BASIS_AUDIT, {"expected": EXPECTED_BASIS_AUDIT, "actual": actual}


PointCheck = Callable[[dict[str, Any]], tuple[bool, dict[str, Any]]]


RUBRIC: list[dict[str, Any]] = [
    {
        "id": "identity_and_requested_cpt",
        "weight": 1,
        "goal": "Correct case identity, P2P identity, and requested CPT.",
        "check": check_identity_and_cpt,
    },
    {
        "id": "p2p_outcome_and_final_status",
        "weight": 3,
        "goal": "Correct P2P outcome and denied final status.",
        "check": check_outcome_and_status,
    },
    {
        "id": "criteria_result_map",
        "weight": 2,
        "goal": "Correct criteria map with covered indication met and PET factor not met.",
        "check": check_criteria_results,
    },
    {
        "id": "unresolved_missing_factors_and_review_change",
        "weight": 2,
        "goal": "Correct unresolved criterion, missing PET-specific factors, and no-review-change flag.",
        "check": check_unresolved_missing_and_review_change,
    },
    {
        "id": "letter_and_alternative_modality",
        "weight": 1,
        "goal": "Correct denial letter type and recommended alternative modality.",
        "check": check_letter_and_alternative,
    },
    {
        "id": "internal_appeal_deadline",
        "weight": 1,
        "goal": "Correct 180-day internal appeal deadline.",
        "check": check_appeal_deadline,
    },
    {
        "id": "business_basis_audit",
        "weight": 1,
        "goal": "Correct business basis-audit source, controlling records, and exception records.",
        "check": check_basis_audit,
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
    answer_path = (
        sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1] / "output" / "answer.json")
    )
    answer, load_error = load_answer(answer_path)
    result = evaluate(answer, load_error)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
