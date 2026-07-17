#!/usr/bin/env python3
"""Atomic weighted evaluator for test_004."""

from __future__ import annotations

import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Callable


ELIGIBLE_ACCOUNT_IDS = [
    "ACC-0040", "ACC-0073", "ACC-0078", "ACC-0082", "ACC-0124",
    "ACC-0166", "ACC-0170", "ACC-0175", "ACC-0208", "ACC-0217",
    "ACC-0259", "ACC-0263", "ACC-0268", "ACC-0310", "ACC-0314",
    "ACC-0356", "ACC-0365", "ACC-0398", "ACC-0403", "ACC-0407",
    "ACC-0449", "ACC-0458", "ACC-0491", "ACC-0500", "ACC-0542",
    "ACC-0584", "ACC-0588", "ACC-0593", "ACC-0635", "ACC-0639",
]

CRITICAL_ACCOUNT_IDS = [
    "ACC-0040", "ACC-0073", "ACC-0082", "ACC-0166", "ACC-0170",
    "ACC-0175", "ACC-0217", "ACC-0310", "ACC-0365", "ACC-0403",
    "ACC-0407", "ACC-0500", "ACC-0542", "ACC-0635",
]

EXPECTED = {
    "eligible_account_ids": ELIGIBLE_ACCOUNT_IDS,
    "portfolio_fulfillment_failure_rate": Decimal("0.8348"),
    "portfolio_net_refund_exposure_usd": Decimal("29189.11"),
    "portfolio_support_breach_rate": Decimal("0.4726"),
    "bottom_three_accounts": [
        {"account_id": "ACC-0175", "health_score": Decimal("0.6928")},
        {"account_id": "ACC-0073", "health_score": Decimal("0.6903")},
        {"account_id": "ACC-0407", "health_score": Decimal("0.6591")},
    ],
    "critical_account_ids": CRITICAL_ACCOUNT_IDS,
    "dominant_risk_dimension": "FULFILLMENT",
    "portfolio_status": "CRITICAL",
}

POINT_SPECS = [
    ("SP001", "Exact eligible production strategic-account set in stable order", 2),
    ("SP002", "Correct portfolio fulfillment failure rate", 3),
    ("SP003", "Correct portfolio effective net refund exposure USD", 3),
    ("SP004", "Correct portfolio active-clock support breach rate", 3),
    ("SP005", "Exact bottom-three account health ranking and scores", 2),
    ("SP006", "Exact critical-account set in stable order", 3),
    ("SP007", "Correct dominant portfolio risk dimension", 2),
    ("SP008", "Correct portfolio health status", 1),
]
TOTAL_WEIGHT = sum(weight for _point_id, _goal, weight in POINT_SPECS)


def load_candidate(path_text: str) -> tuple[dict[str, Any] | None, str | None]:
    if not path_text:
        return None, "candidate path was not provided"
    try:
        with Path(path_text).open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"candidate could not be read as JSON: {exc.__class__.__name__}"
    if not isinstance(value, dict):
        return None, "candidate JSON must be an object"
    return value, None


def exact_list(candidate: dict[str, Any], field: str, expected: list[str]) -> bool:
    value = candidate.get(field)
    return (
        isinstance(value, list)
        and all(isinstance(item, str) for item in value)
        and value == expected
    )


def number_at_precision(value: Any, expected: Decimal, places: int) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return False
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return False
    if not number.is_finite():
        return False
    quantum = Decimal(1).scaleb(-places)
    return number.quantize(quantum, rounding=ROUND_HALF_UP) == expected


def bottom_three(candidate: dict[str, Any]) -> bool:
    value = candidate.get("bottom_three_accounts")
    if not isinstance(value, list) or len(value) != 3:
        return False
    for actual, expected in zip(value, EXPECTED["bottom_three_accounts"]):
        if not isinstance(actual, dict) or set(actual) != {"account_id", "health_score"}:
            return False
        if actual.get("account_id") != expected["account_id"]:
            return False
        if not number_at_precision(actual.get("health_score"), expected["health_score"], 4):
            return False
    return True


def enum_value(candidate: dict[str, Any], field: str, expected: str) -> bool:
    return isinstance(candidate.get(field), str) and candidate[field] == expected


CHECKS: dict[str, Callable[[dict[str, Any]], bool]] = {
    "SP001": lambda c: exact_list(c, "eligible_account_ids", EXPECTED["eligible_account_ids"]),
    "SP002": lambda c: number_at_precision(c.get("portfolio_fulfillment_failure_rate"), EXPECTED["portfolio_fulfillment_failure_rate"], 4),
    "SP003": lambda c: number_at_precision(c.get("portfolio_net_refund_exposure_usd"), EXPECTED["portfolio_net_refund_exposure_usd"], 2),
    "SP004": lambda c: number_at_precision(c.get("portfolio_support_breach_rate"), EXPECTED["portfolio_support_breach_rate"], 4),
    "SP005": bottom_three,
    "SP006": lambda c: exact_list(c, "critical_account_ids", EXPECTED["critical_account_ids"]),
    "SP007": lambda c: enum_value(c, "dominant_risk_dimension", EXPECTED["dominant_risk_dimension"]),
    "SP008": lambda c: enum_value(c, "portfolio_status", EXPECTED["portfolio_status"]),
}


def evaluate(candidate: dict[str, Any] | None, load_error: str | None) -> dict[str, Any]:
    points = []
    earned_weight = 0
    for point_id, goal, weight in POINT_SPECS:
        passed = candidate is not None and CHECKS[point_id](candidate)
        if passed:
            earned_weight += weight
        assigned_score = weight / TOTAL_WEIGHT
        points.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": assigned_score,
                "passed": bool(passed),
                "earned_score": assigned_score if passed else 0.0,
                "details": (
                    "check passed"
                    if passed
                    else load_error or "candidate value did not match the required normalized outcome"
                ),
            }
        )
    return {
        "score": earned_weight / TOTAL_WEIGHT,
        "total_weight": TOTAL_WEIGHT,
        "points": points,
    }


def main() -> None:
    path_text = sys.argv[1] if len(sys.argv) > 1 else ""
    candidate, load_error = load_candidate(path_text)
    print(json.dumps(evaluate(candidate, load_error), indent=2, sort_keys=False))


if __name__ == "__main__":
    main()
