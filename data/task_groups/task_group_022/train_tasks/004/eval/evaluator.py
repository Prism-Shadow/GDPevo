#!/usr/bin/env python3
"""Atomic weighted evaluator for train_004."""

from __future__ import annotations

import json
import math
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable


EXPECTED = {
    "eligible_production_task_count": 247,
    "completed_production_units": 9408,
    "top_three_employee_ids": ["EMP-0007", "EMP-0006", "EMP-0008"],
    "top_employee_units_per_hour": Decimal("68.95"),
    "rework_task_count": 5,
    "rework_rate": Decimal("0.0202"),
    "delayed_high_priority_task_ids": [
        "WT-000170", "WT-002540", "WT-003609", "WT-007106", "WT-007509",
        "WT-008940", "WT-009039", "WT-010569", "WT-011409", "WT-012840",
        "WT-012939", "WT-014370", "WT-014469", "WT-015210", "WT-016139",
        "WT-016740", "WT-016839", "WT-017604", "WT-018270", "WT-019373",
        "WT-019800", "WT-020039", "WT-020640", "WT-021569", "WT-022170",
        "WT-023840", "WT-023939", "WT-025370", "WT-025469", "WT-026070",
        "WT-027740", "WT-029270", "WT-029369", "WT-029871", "WT-030800",
        "WT-033071", "WT-033170", "WT-033672", "WT-033737", "WT-033836",
        "WT-033935",
    ],
    "lowest_performing_team_id": "WH-NORTH-01-TEAM-3",
    "facility_status": "PRESSURED",
}

POINT_SPECS = [
    ("SP001", "Correct eligible production-task count.", 2),
    ("SP002", "Correct total effective completed production units.", 3),
    ("SP003", "Correct ordered top-three employee ranking.", 3),
    ("SP004", "Correct top employee units per hour at two decimals.", 2),
    ("SP005", "Correct effective rework task count and four-decimal rate.", 2),
    ("SP006", "Correct exact delayed high-priority task ID set.", 3),
    ("SP007", "Correct lowest-performing team identifier.", 1),
    ("SP008", "Correct facility status classification.", 1),
]
TOTAL_WEIGHT = sum(weight for _, _, weight in POINT_SPECS)
MISSING = object()


def strict_json_load(path_text: str) -> dict[str, Any] | None:
    if not path_text:
        return None
    try:
        text = Path(path_text).read_text(encoding="utf-8")

        def reject_constant(value: str) -> None:
            raise ValueError(f"invalid JSON constant: {value}")

        value = json.loads(text, parse_constant=reject_constant)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def shown(value: Any) -> str:
    if value is MISSING:
        return "<missing>"
    try:
        return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return f"<{type(value).__name__}>"


def is_integer(value: Any, expected: int) -> bool:
    return type(value) is int and value == expected


def is_decimal(value: Any, expected: Decimal) -> bool:
    if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
        return False
    try:
        return Decimal(str(value)) == expected
    except (InvalidOperation, ValueError):
        return False


def check_integer(candidate: dict[str, Any], field: str, expected: int) -> tuple[bool, str]:
    actual = candidate.get(field, MISSING)
    passed = is_integer(actual, expected)
    if passed:
        return True, f"{field} matched expected integer {expected}."
    return False, f"{field} expected integer {expected}; received {shown(actual)}."


def check_decimal(candidate: dict[str, Any], field: str, expected: Decimal) -> tuple[bool, str]:
    actual = candidate.get(field, MISSING)
    passed = is_decimal(actual, expected)
    if passed:
        return True, f"{field} matched expected numeric value {expected}."
    return False, f"{field} expected numeric value {expected}; received {shown(actual)}."


def check_ranking(candidate: dict[str, Any]) -> tuple[bool, str]:
    field = "top_three_employee_ids"
    actual = candidate.get(field, MISSING)
    expected = EXPECTED[field]
    valid = isinstance(actual, list) and all(type(item) is str for item in actual)
    passed = valid and actual == expected
    if passed:
        return True, "top_three_employee_ids matched the exact ranked employee sequence."
    return False, f"top_three_employee_ids expected {shown(expected)}; received {shown(actual)}."


def check_rework(candidate: dict[str, Any]) -> tuple[bool, str]:
    count = candidate.get("rework_task_count", MISSING)
    rate = candidate.get("rework_rate", MISSING)
    count_ok = is_integer(count, EXPECTED["rework_task_count"])
    rate_ok = is_decimal(rate, EXPECTED["rework_rate"])
    passed = count_ok and rate_ok
    if passed:
        return True, "rework_task_count and rework_rate both matched."
    return False, (
        "Expected rework_task_count=5 and rework_rate=0.0202; "
        f"received count={shown(count)}, rate={shown(rate)}."
    )


def check_delayed_set(candidate: dict[str, Any]) -> tuple[bool, str]:
    field = "delayed_high_priority_task_ids"
    actual = candidate.get(field, MISSING)
    expected = EXPECTED[field]
    valid = isinstance(actual, list) and all(type(item) is str for item in actual)
    if not valid:
        return False, f"{field} expected a string list containing 41 unique task IDs; received {shown(actual)}."
    unique = len(actual) == len(set(actual))
    actual_set = set(actual)
    expected_set = set(expected)
    passed = unique and actual_set == expected_set
    if passed:
        return True, f"{field} matched the exact normalized set of 41 task IDs."
    missing = sorted(expected_set - actual_set)
    unexpected = sorted(actual_set - expected_set)
    return False, (
        f"{field} set mismatch: unique={str(unique).lower()}, "
        f"missing={shown(missing)}, unexpected={shown(unexpected)}."
    )


def check_string(candidate: dict[str, Any], field: str, expected: str) -> tuple[bool, str]:
    actual = candidate.get(field, MISSING)
    passed = type(actual) is str and actual == expected
    if passed:
        return True, f"{field} matched expected value {expected}."
    return False, f"{field} expected {shown(expected)}; received {shown(actual)}."


CHECKS: dict[str, Callable[[dict[str, Any]], tuple[bool, str]]] = {
    "SP001": lambda candidate: check_integer(
        candidate, "eligible_production_task_count", EXPECTED["eligible_production_task_count"]
    ),
    "SP002": lambda candidate: check_integer(
        candidate, "completed_production_units", EXPECTED["completed_production_units"]
    ),
    "SP003": check_ranking,
    "SP004": lambda candidate: check_decimal(
        candidate, "top_employee_units_per_hour", EXPECTED["top_employee_units_per_hour"]
    ),
    "SP005": check_rework,
    "SP006": check_delayed_set,
    "SP007": lambda candidate: check_string(
        candidate, "lowest_performing_team_id", EXPECTED["lowest_performing_team_id"]
    ),
    "SP008": lambda candidate: check_string(candidate, "facility_status", EXPECTED["facility_status"]),
}


def evaluate(candidate: dict[str, Any] | None) -> dict[str, Any]:
    points: list[dict[str, Any]] = []
    earned_weight = 0
    for point_id, goal, weight in POINT_SPECS:
        assigned_score = weight / TOTAL_WEIGHT
        if candidate is None:
            passed = False
            details = "Candidate must be a readable JSON object."
        else:
            passed, details = CHECKS[point_id](candidate)
        if passed:
            earned_weight += weight
        points.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": assigned_score,
                "passed": passed,
                "earned_score": assigned_score if passed else 0.0,
                "details": details,
            }
        )
    return {
        "score": earned_weight / TOTAL_WEIGHT,
        "total_weight": TOTAL_WEIGHT,
        "points": points,
    }


def main() -> None:
    candidate_path = sys.argv[1] if len(sys.argv) == 2 else ""
    result = evaluate(strict_json_load(candidate_path))
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
