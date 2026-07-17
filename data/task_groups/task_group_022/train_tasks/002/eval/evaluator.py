#!/usr/bin/env python3
"""Atomic weighted evaluator for train_002."""

from __future__ import annotations

import json
import math
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Callable


STANDARD: dict[str, Any] = {
    "eligible_refunded_order_count": 484,
    "effective_settled_logical_refund_count": 484,
    "effective_linked_reversal_count": 2,
    "net_refund_amount_usd": Decimal("115674.62"),
    "top_two_reason_codes": ["DAMAGED", "NOT_AS_DESCRIBED"],
    "unresolved_leakage_order_ids": [
        "ORD-000344",
        "ORD-000436",
        "ORD-000778",
        "ORD-001237",
        "ORD-001551",
        "ORD-001845",
        "ORD-002365",
        "ORD-002486",
        "ORD-004262",
        "ORD-004502",
        "ORD-004714",
        "ORD-006117",
        "ORD-007093",
        "ORD-007527",
        "ORD-007808",
        "ORD-008014",
        "ORD-008530",
        "ORD-008622",
        "ORD-009050",
        "ORD-009142",
        "ORD-009898",
        "ORD-010367",
        "ORD-010528",
        "ORD-010602",
        "ORD-012121",
        "ORD-012803",
        "ORD-013147",
        "ORD-013581",
        "ORD-013737",
    ],
    "cohort_risk": "HIGH",
}

POINTS = [
    ("SP001", "Correct eligible distinct refunded-order population.", 2),
    ("SP002", "Correct effective settled logical refund count.", 3),
    ("SP003", "Correct effective linked reversal count.", 2),
    ("SP004", "Correct net refund amount in USD to two decimals.", 3),
    ("SP005", "Correct exact top-two normalized reason-code ranking.", 2),
    ("SP006", "Correct exact ascending unresolved leakage order set.", 3),
    ("SP007", "Correct cohort risk classification.", 1),
]
TOTAL_WEIGHT = sum(point[2] for point in POINTS)


def load_candidate(path_text: str) -> tuple[dict[str, Any] | None, str | None]:
    if not path_text:
        return None, "Candidate path was not supplied."
    try:
        with Path(path_text).open("r", encoding="utf-8") as handle:
            candidate = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return None, "Candidate JSON is unreadable."
    if not isinstance(candidate, dict):
        return None, "Candidate JSON must be an object."
    return candidate, None


def exact_integer(candidate: dict[str, Any], field: str) -> tuple[bool, str]:
    value = candidate.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        return False, f"{field} must be an integer."
    passed = value == STANDARD[field]
    return passed, f"{field} exact integer {'matched' if passed else 'did not match'}."


def exact_money(candidate: dict[str, Any], field: str) -> tuple[bool, str]:
    value = candidate.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False, f"{field} must be a JSON number."
    if isinstance(value, float) and not math.isfinite(value):
        return False, f"{field} must be finite."
    try:
        normalized = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return False, f"{field} could not be evaluated at two-decimal precision."
    passed = normalized == STANDARD[field]
    return passed, f"{field} two-decimal value {'matched' if passed else 'did not match'}."


def exact_list(candidate: dict[str, Any], field: str) -> tuple[bool, str]:
    value = candidate.get(field)
    if not isinstance(value, list):
        return False, f"{field} must be an array."
    passed = value == STANDARD[field]
    return passed, f"{field} exact ordered array {'matched' if passed else 'did not match'}."


def exact_enum(candidate: dict[str, Any], field: str) -> tuple[bool, str]:
    value = candidate.get(field)
    if not isinstance(value, str):
        return False, f"{field} must be a string enum."
    passed = value == STANDARD[field]
    return passed, f"{field} enum {'matched' if passed else 'did not match'}."


CHECKS: dict[str, Callable[[dict[str, Any]], tuple[bool, str]]] = {
    "SP001": lambda candidate: exact_integer(candidate, "eligible_refunded_order_count"),
    "SP002": lambda candidate: exact_integer(candidate, "effective_settled_logical_refund_count"),
    "SP003": lambda candidate: exact_integer(candidate, "effective_linked_reversal_count"),
    "SP004": lambda candidate: exact_money(candidate, "net_refund_amount_usd"),
    "SP005": lambda candidate: exact_list(candidate, "top_two_reason_codes"),
    "SP006": lambda candidate: exact_list(candidate, "unresolved_leakage_order_ids"),
    "SP007": lambda candidate: exact_enum(candidate, "cohort_risk"),
}


def evaluate(candidate: dict[str, Any] | None, load_error: str | None) -> dict[str, Any]:
    results = []
    score = 0.0
    for point_id, goal, weight in POINTS:
        assigned_score = weight / TOTAL_WEIGHT
        if candidate is None:
            passed = False
            details = load_error or "Candidate JSON is unavailable."
        else:
            passed, details = CHECKS[point_id](candidate)
        earned_score = assigned_score if passed else 0.0
        score += earned_score
        results.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": assigned_score,
                "passed": passed,
                "earned_score": earned_score,
                "details": details,
            }
        )
    return {
        "score": round(score, 12),
        "total_weight": TOTAL_WEIGHT,
        "points": results,
    }


def main() -> None:
    candidate, load_error = load_candidate(sys.argv[1] if len(sys.argv) > 1 else "")
    print(json.dumps(evaluate(candidate, load_error), indent=2, sort_keys=False))


if __name__ == "__main__":
    main()
