#!/usr/bin/env python3
"""Atomic weighted evaluator for test_005."""

from __future__ import annotations

import json
import math
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable


EXPECTED = {
    "backlog_task_count": 126,
    "backlog_planned_units": 5840,
    "total_projected_recoverable_units": Decimal("3972.83"),
    "facility_recovery_ranking": [
        ("WH-CENTRAL-01", Decimal("0.7056")),
        ("WH-WEST-01", Decimal("0.6556")),
    ],
    "employee_candidates_by_facility": [
        (
            "WH-CENTRAL-01",
            [
                ("EMP-0090", Decimal("58.07")),
                ("EMP-0077", Decimal("56.91")),
            ],
        ),
        (
            "WH-WEST-01",
            [
                ("EMP-0051", Decimal("59.72")),
                ("EMP-0040", Decimal("51.62")),
            ],
        ),
    ],
    "carrier_cutoff_exposed_order_ids": [
        "ORD-000266", "ORD-000281", "ORD-000471", "ORD-000636",
        "ORD-001131", "ORD-001956", "ORD-002131", "ORD-002446",
        "ORD-003476", "ORD-004286", "ORD-004626", "ORD-005121",
        "ORD-005436", "ORD-006136", "ORD-006286", "ORD-006436",
        "ORD-006631", "ORD-007136", "ORD-007286", "ORD-007631",
        "ORD-008811", "ORD-010456", "ORD-010636", "ORD-011636",
        "ORD-012281", "ORD-012786", "ORD-012981", "ORD-013131",
        "ORD-013446", "ORD-013636", "ORD-013786", "ORD-013966",
        "ORD-013981",
    ],
    "severe_linked_support_escalation_count": 1,
    "recommended_action": "REALLOCATE_AND_EXPEDITE",
    "recovery_status": "CRITICAL",
}

POINT_SPECS = [
    ("SP001", "Correct effective backlog task and planned-unit totals.", 3),
    ("SP002", "Correct total projected recoverable units.", 3),
    ("SP003", "Correct facility recovery ranking and projected coverage.", 2),
    ("SP004", "Correct top employee candidates for both facilities.", 2),
    ("SP005", "Correct exact carrier-cutoff exposed order set.", 3),
    ("SP006", "Correct severe linked support escalation count.", 2),
    ("SP007", "Correct recommended recovery action.", 2),
    ("SP008", "Correct recovery status.", 1),
]
TOTAL_WEIGHT = sum(weight for _, _, weight in POINT_SPECS)
MISSING = object()


def strict_json_load(path_text: str) -> dict[str, Any] | None:
    if not path_text:
        return None
    try:
        raw = Path(path_text).read_text(encoding="utf-8")

        def reject_constant(value: str) -> None:
            raise ValueError(f"invalid JSON constant: {value}")

        value = json.loads(raw, parse_constant=reject_constant)
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
    if type(value) not in (int, float):
        return False
    if type(value) is float and not math.isfinite(value):
        return False
    try:
        return Decimal(str(value)) == expected
    except (InvalidOperation, ValueError):
        return False


def check_backlog(candidate: dict[str, Any]) -> tuple[bool, str]:
    actual = candidate.get("backlog_summary", MISSING)
    valid = isinstance(actual, dict) and set(actual) == {"task_count", "planned_units"}
    passed = valid and is_integer(actual.get("task_count"), EXPECTED["backlog_task_count"]) and is_integer(
        actual.get("planned_units"), EXPECTED["backlog_planned_units"]
    )
    if passed:
        return True, "backlog_summary matched both effective task and planned-unit totals."
    return False, (
        "backlog_summary expected task_count=126 and planned_units=5840; "
        f"received {shown(actual)}."
    )


def check_recoverable(candidate: dict[str, Any]) -> tuple[bool, str]:
    field = "total_projected_recoverable_units"
    actual = candidate.get(field, MISSING)
    expected = EXPECTED[field]
    passed = is_decimal(actual, expected)
    if passed:
        return True, f"{field} matched expected numeric value {expected}."
    return False, f"{field} expected numeric value {expected}; received {shown(actual)}."


def check_facility_ranking(candidate: dict[str, Any]) -> tuple[bool, str]:
    field = "facility_recovery_ranking"
    actual = candidate.get(field, MISSING)
    expected = EXPECTED[field]
    valid = isinstance(actual, list) and len(actual) == len(expected)
    if valid:
        for item, (warehouse_id, coverage) in zip(actual, expected):
            if not isinstance(item, dict) or set(item) != {"warehouse_id", "projected_coverage"}:
                valid = False
                break
            if type(item.get("warehouse_id")) is not str or item["warehouse_id"] != warehouse_id:
                valid = False
                break
            if not is_decimal(item.get("projected_coverage"), coverage):
                valid = False
                break
    if valid:
        return True, "facility_recovery_ranking matched both ordered facilities and coverage values."
    return False, f"facility_recovery_ranking did not match the exact two-facility ranked result; received {shown(actual)}."


def check_employee_candidates(candidate: dict[str, Any]) -> tuple[bool, str]:
    field = "employee_candidates_by_facility"
    actual = candidate.get(field, MISSING)
    expected = EXPECTED[field]
    valid = isinstance(actual, list) and len(actual) == len(expected)
    if valid:
        for facility, (warehouse_id, expected_candidates) in zip(actual, expected):
            if not isinstance(facility, dict) or set(facility) != {"warehouse_id", "candidates"}:
                valid = False
                break
            if type(facility.get("warehouse_id")) is not str or facility["warehouse_id"] != warehouse_id:
                valid = False
                break
            candidates = facility.get("candidates")
            if not isinstance(candidates, list) or len(candidates) != len(expected_candidates):
                valid = False
                break
            for item, (employee_id, rate) in zip(candidates, expected_candidates):
                if not isinstance(item, dict) or set(item) != {"employee_id", "units_per_hour"}:
                    valid = False
                    break
                if type(item.get("employee_id")) is not str or item["employee_id"] != employee_id:
                    valid = False
                    break
                if not is_decimal(item.get("units_per_hour"), rate):
                    valid = False
                    break
            if not valid:
                break
    if valid:
        return True, "employee_candidates_by_facility matched both exact ranked candidate lists."
    return False, f"employee_candidates_by_facility did not match the exact facility/candidate result; received {shown(actual)}."


def check_exposed_set(candidate: dict[str, Any]) -> tuple[bool, str]:
    field = "carrier_cutoff_exposed_order_ids"
    actual = candidate.get(field, MISSING)
    expected = EXPECTED[field]
    if not isinstance(actual, list) or not all(type(item) is str for item in actual):
        return False, f"{field} expected a string list containing 33 unique order IDs; received {shown(actual)}."
    unique = len(actual) == len(set(actual))
    actual_set = set(actual)
    expected_set = set(expected)
    passed = unique and actual_set == expected_set
    if passed:
        return True, f"{field} matched the exact normalized set of 33 order IDs."
    missing = sorted(expected_set - actual_set)
    unexpected = sorted(actual_set - expected_set)
    return False, (
        f"{field} set mismatch: unique={str(unique).lower()}, "
        f"missing={shown(missing)}, unexpected={shown(unexpected)}."
    )


def check_integer_field(candidate: dict[str, Any], field: str, expected: int) -> tuple[bool, str]:
    actual = candidate.get(field, MISSING)
    passed = is_integer(actual, expected)
    if passed:
        return True, f"{field} matched expected integer {expected}."
    return False, f"{field} expected integer {expected}; received {shown(actual)}."


def check_string_field(candidate: dict[str, Any], field: str, expected: str) -> tuple[bool, str]:
    actual = candidate.get(field, MISSING)
    passed = type(actual) is str and actual == expected
    if passed:
        return True, f"{field} matched expected value {expected}."
    return False, f"{field} expected {shown(expected)}; received {shown(actual)}."


CHECKS: dict[str, Callable[[dict[str, Any]], tuple[bool, str]]] = {
    "SP001": check_backlog,
    "SP002": check_recoverable,
    "SP003": check_facility_ranking,
    "SP004": check_employee_candidates,
    "SP005": check_exposed_set,
    "SP006": lambda candidate: check_integer_field(
        candidate,
        "severe_linked_support_escalation_count",
        EXPECTED["severe_linked_support_escalation_count"],
    ),
    "SP007": lambda candidate: check_string_field(
        candidate, "recommended_action", EXPECTED["recommended_action"]
    ),
    "SP008": lambda candidate: check_string_field(
        candidate, "recovery_status", EXPECTED["recovery_status"]
    ),
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
