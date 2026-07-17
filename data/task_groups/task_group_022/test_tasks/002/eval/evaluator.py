#!/usr/bin/env python3
"""Atomic weighted evaluator for test_002."""

from __future__ import annotations

import json
import math
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Callable


STANDARD: dict[str, Any] = {
    "eligible_refunded_order_count": 447,
    "effective_settled_logical_refund_count": 447,
    "effective_reversed_amount_usd": Decimal("1678.67"),
    "net_provider_exposure_usd": Decimal("108542.75"),
    "provider_exposure_ranking": [
        {"provider": "BRAINTREE", "net_exposure_usd": Decimal("37708.88")},
        {"provider": "ADYEN", "net_exposure_usd": Decimal("36425.84")},
        {"provider": "STRIPE", "net_exposure_usd": Decimal("34408.02")},
    ],
    "unresolved_leakage_order_ids": [
        "ORD-001142",
        "ORD-002888",
        "ORD-003638",
        "ORD-004692",
        "ORD-004807",
        "ORD-005208",
        "ORD-005465",
        "ORD-005820",
        "ORD-006234",
        "ORD-006754",
        "ORD-007555",
        "ORD-007597",
        "ORD-008141",
        "ORD-010010",
        "ORD-010598",
        "ORD-011441",
        "ORD-012214",
    ],
    "dominant_normalized_reason_code": "LATE_DELIVERY",
    "exposure_status": "HIGH",
}

POINTS = [
    ("SP001", "Correct eligible distinct refunded-order population.", 2),
    ("SP002", "Correct effective settled logical refund count.", 3),
    ("SP003", "Correct effective reversed amount in USD to two decimals.", 2),
    ("SP004", "Correct net provider exposure in USD to two decimals.", 3),
    ("SP005", "Correct complete provider exposure ranking and provider amounts.", 2),
    ("SP006", "Correct exact ascending unresolved leakage order set.", 3),
    ("SP007", "Correct dominant normalized reason code.", 1),
    ("SP008", "Correct exposure status classification.", 1),
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


def normalize_money(value: Any) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None


def exact_money(candidate: dict[str, Any], field: str) -> tuple[bool, str]:
    normalized = normalize_money(candidate.get(field))
    if normalized is None:
        return False, f"{field} must be a finite JSON number."
    passed = normalized == STANDARD[field]
    return passed, f"{field} two-decimal value {'matched' if passed else 'did not match'}."


def exact_provider_ranking(candidate: dict[str, Any]) -> tuple[bool, str]:
    value = candidate.get("provider_exposure_ranking")
    expected = STANDARD["provider_exposure_ranking"]
    if not isinstance(value, list):
        return False, "provider_exposure_ranking must be an array."
    if len(value) != len(expected):
        return False, "provider_exposure_ranking did not contain the complete ranked provider list."
    for actual, target in zip(value, expected):
        if not isinstance(actual, dict) or set(actual) != {"provider", "net_exposure_usd"}:
            return False, "Each provider ranking item must contain exactly provider and net_exposure_usd."
        if actual.get("provider") != target["provider"]:
            return False, "provider_exposure_ranking provider order did not match."
        if normalize_money(actual.get("net_exposure_usd")) != target["net_exposure_usd"]:
            return False, "provider_exposure_ranking included an incorrect provider amount."
    return True, "provider_exposure_ranking complete ordered provider exposures matched."


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
    "SP003": lambda candidate: exact_money(candidate, "effective_reversed_amount_usd"),
    "SP004": lambda candidate: exact_money(candidate, "net_provider_exposure_usd"),
    "SP005": exact_provider_ranking,
    "SP006": lambda candidate: exact_list(candidate, "unresolved_leakage_order_ids"),
    "SP007": lambda candidate: exact_enum(candidate, "dominant_normalized_reason_code"),
    "SP008": lambda candidate: exact_enum(candidate, "exposure_status"),
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
