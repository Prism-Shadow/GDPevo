#!/usr/bin/env python3
"""Evaluator for test_005 mixed UM-finance queue triage."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Callable


EXPECTED_ITEMS = {
    "appeal_deadline": {
        "route": "appeals_deadline",
        "route_priority": 1,
        "next_action": "complete_standard_internal_appeal",
        "deadline": "2026-06-12",
        "reason": "none",
        "recovery_amount": 0.00,
    },
    "md_escalation": {
        "route": "medical_director_escalation",
        "route_priority": 2,
        "next_action": "route_md_review",
        "deadline": "",
        "reason": "PET-FACTOR not_met",
        "recovery_amount": 0.00,
    },
    "claim_correction": {
        "route": "payment_integrity_correction",
        "route_priority": 3,
        "next_action": "resubmit_corrected_claim",
        "deadline": "",
        "reason": "none",
        "recovery_amount": 152.00,
    },
}

EXPECTED_ORDER = ["appeal_deadline", "md_escalation", "claim_correction"]
EXPECTED_COUNTS = {
    "appeals_deadline": 1,
    "medical_director_escalation": 1,
    "payment_integrity_correction": 1,
}

EXPECTED_BASIS_AUDIT = {
    "source_precedence": "appeal_deadline_then_clinical_then_payment_integrity",
    "precedence_record_order": [
        "doc-te-005-appeal",
        "doc-te-005-md",
        "doc-te-005-claim",
    ],
    "controlling_record_ids": [
        "doc-te-005-appeal",
        "doc-te-005-md",
        "doc-te-005-claim",
    ],
    "exception_record_ids": [
        "appeal_deadline",
        "md_escalation",
        "claim_correction",
    ],
}


def norm_text(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def norm_code(value: Any) -> str:
    return str(value or "").strip().upper()


def as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
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


def as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def money_eq(value: Any, expected: float) -> bool:
    number = as_float(value)
    return number is not None and math.isclose(number, expected, abs_tol=0.01)


def queue_items(answer: dict[str, Any]) -> list[dict[str, Any]]:
    items = answer.get("queue_items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def audit_value(answer: dict[str, Any], key: str) -> Any:
    audit = answer.get("basis_audit")
    if not isinstance(audit, dict):
        return None
    return audit.get(key)


def audit_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    return [str(item or "").strip().lower() for item in value]


def item_map(answer: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in queue_items(answer):
        item_id = norm_text(item.get("item_id"))
        if item_id:
            result[item_id] = item
    return result


def exact_item_set(items_by_id: dict[str, dict[str, Any]]) -> bool:
    return set(items_by_id) == set(EXPECTED_ITEMS)


def aggregate_counts(answer: dict[str, Any]) -> dict[str, int | None] | None:
    counts = answer.get("aggregate_counts")
    if not isinstance(counts, dict):
        return None
    normalized: dict[str, int | None] = {}
    for key, value in counts.items():
        normalized[norm_text(key)] = as_int(value)
    return normalized


def check_target_and_date(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    passed = (
        norm_text(answer.get("case_id")) == "queue_te_005"
        and str(answer.get("as_of_date", "")).strip() == "2026-06-11"
    )
    return passed, {
        "case_id": answer.get("case_id"),
        "as_of_date": answer.get("as_of_date"),
    }


def check_appeal_deadline(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    items_by_id = item_map(answer)
    item = items_by_id.get("appeal_deadline", {})
    expected = EXPECTED_ITEMS["appeal_deadline"]
    passed = (
        exact_item_set(items_by_id)
        and norm_text(item.get("route")) == expected["route"]
        and str(item.get("deadline", "")).strip() == expected["deadline"]
        and norm_text(item.get("next_action")) == expected["next_action"]
        and norm_text(answer.get("top_priority_item")) == "appeal_deadline"
    )
    return passed, {
        "item_ids": sorted(items_by_id),
        "appeal_deadline_item": {
            "route": item.get("route"),
            "deadline": item.get("deadline"),
            "next_action": item.get("next_action"),
        },
        "top_priority_item": answer.get("top_priority_item"),
    }


def check_md_escalation(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    items_by_id = item_map(answer)
    item = items_by_id.get("md_escalation", {})
    expected = EXPECTED_ITEMS["md_escalation"]
    passed = (
        exact_item_set(items_by_id)
        and norm_text(item.get("route")) == expected["route"]
        and norm_text(item.get("reason")) == norm_text(expected["reason"])
        and norm_text(item.get("next_action")) == expected["next_action"]
    )
    return passed, {
        "item_ids": sorted(items_by_id),
        "md_escalation_item": {
            "route": item.get("route"),
            "reason": item.get("reason"),
            "next_action": item.get("next_action"),
        },
    }


def check_claim_correction(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    items_by_id = item_map(answer)
    item = items_by_id.get("claim_correction", {})
    expected = EXPECTED_ITEMS["claim_correction"]
    passed = (
        exact_item_set(items_by_id)
        and norm_text(item.get("route")) == expected["route"]
        and norm_text(item.get("next_action")) == expected["next_action"]
        and money_eq(item.get("recovery_amount"), expected["recovery_amount"])
        and money_eq(answer.get("total_recovery_amount"), expected["recovery_amount"])
    )
    return passed, {
        "item_ids": sorted(items_by_id),
        "claim_correction_item": {
            "route": item.get("route"),
            "next_action": item.get("next_action"),
            "recovery_amount": item.get("recovery_amount"),
        },
        "total_recovery_amount": answer.get("total_recovery_amount"),
    }


def check_aggregate_counts(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    counts = aggregate_counts(answer)
    passed = counts == EXPECTED_COUNTS
    return passed, {
        "aggregate_counts": answer.get("aggregate_counts"),
        "expected_counts": EXPECTED_COUNTS,
    }


def check_queue_order(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    items = queue_items(answer)
    ordered_ids = [norm_text(item.get("item_id")) for item in items]
    ordered_priorities = [as_int(item.get("route_priority")) for item in items]
    expected_priorities = [EXPECTED_ITEMS[item_id]["route_priority"] for item_id in EXPECTED_ORDER]
    passed = ordered_ids == EXPECTED_ORDER and ordered_priorities == expected_priorities
    return passed, {
        "ordered_item_ids": ordered_ids,
        "ordered_route_priorities": ordered_priorities,
        "expected_order": EXPECTED_ORDER,
        "expected_route_priorities": expected_priorities,
    }


def check_basis_source_precedence(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    actual = norm_text(audit_value(answer, "source_precedence"))
    expected = EXPECTED_BASIS_AUDIT["source_precedence"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_basis_controlling_records(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    actual = audit_list(audit_value(answer, "controlling_record_ids"))
    expected = EXPECTED_BASIS_AUDIT["controlling_record_ids"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_basis_precedence_record_order(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    actual = audit_list(audit_value(answer, "precedence_record_order"))
    expected = EXPECTED_BASIS_AUDIT["precedence_record_order"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_basis_exception_records(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    actual = audit_list(audit_value(answer, "exception_record_ids"))
    expected = EXPECTED_BASIS_AUDIT["exception_record_ids"]
    return actual == expected, {"actual": actual, "expected": expected}


Check = Callable[[dict[str, Any]], tuple[bool, dict[str, Any]]]

RUBRIC: list[tuple[str, int, Check]] = [
    ("Correct target queue and as-of date.", 1, check_target_and_date),
    (
        "Correct appeal deadline route, deadline, and top priority.",
        3,
        check_appeal_deadline,
    ),
    (
        "Correct MD escalation route and PET-factor reason.",
        2,
        check_md_escalation,
    ),
    (
        "Correct claim correction route and recovery amount.",
        2,
        check_claim_correction,
    ),
    ("Correct aggregate route counts.", 2, check_aggregate_counts),
    ("Correct queue ordering by priority.", 1, check_queue_order),
    (
        "Correct business source-precedence basis.",
        3,
        check_basis_source_precedence,
    ),
    (
        "Correct source-precedence record order.",
        3,
        check_basis_precedence_record_order,
    ),
    (
        "Correct controlling queue source record IDs.",
        1,
        check_basis_controlling_records,
    ),
    (
        "Correct route exception and queue-item IDs.",
        2,
        check_basis_exception_records,
    ),
]


def failed_result(message: str) -> dict[str, Any]:
    total_weight = sum(weight for _, weight, _ in RUBRIC)
    points = []
    for goal, weight, _ in RUBRIC:
        assigned = weight / total_weight
        points.append(
            {
                "goal": goal,
                "weight": weight,
                "assigned_score": round(assigned, 10),
                "passed": False,
                "earned_score": 0.0,
                "details": {"error": message},
            }
        )
    return {"score": 0.0, "points": points, "total_weight": total_weight}


def evaluate(answer: Any) -> dict[str, Any]:
    if not isinstance(answer, dict):
        return failed_result("Answer must be a JSON object.")

    total_weight = sum(weight for _, weight, _ in RUBRIC)
    earned_weight = 0
    points = []
    for goal, weight, check in RUBRIC:
        passed, details = check(answer)
        assigned = weight / total_weight
        if passed:
            earned_weight += weight
        points.append(
            {
                "goal": goal,
                "weight": weight,
                "assigned_score": round(assigned, 10),
                "passed": bool(passed),
                "earned_score": round(assigned if passed else 0.0, 10),
                "details": details,
            }
        )
    return {
        "score": round(earned_weight / total_weight, 10),
        "points": points,
        "total_weight": total_weight,
    }


def main() -> None:
    answer_path = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
    )
    try:
        answer = json.loads(answer_path.read_text(encoding="utf-8"))
    except Exception as exc:
        result = failed_result(f"Could not load submitted JSON: {exc}")
    else:
        result = evaluate(answer)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
