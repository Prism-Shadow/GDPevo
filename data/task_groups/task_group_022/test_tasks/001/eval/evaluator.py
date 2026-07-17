#!/usr/bin/env python3
"""Atomic weighted evaluator for test_001."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Callable


POINT_SPECS = [
    ("SP001", "Correct eligible production-order count.", 2),
    ("SP002", "Correct effective complete-order count at the cutoff.", 3),
    ("SP003", "Correct overall on-time complete-order rate.", 3),
    ("SP004", "Correct partial-or-unshipped eligible-order count.", 2),
    ("SP005", "Correct complete warehouse reliability ranking and rates.", 2),
    ("SP006", "Correct exact sorted severe-exception order set.", 3),
    ("SP007", "Correct highest-late-rate carrier and rate.", 2),
    ("SP008", "Correct delivery service status.", 1),
]
TOTAL_WEIGHT = sum(spec[2] for spec in POINT_SPECS)
EXPECTED_PATH = Path(__file__).resolve().parent.parent / "output" / "answer.json"


def load_candidate(path_text: str | None) -> tuple[dict[str, Any] | None, str | None]:
    if path_text is None:
        return None, "candidate path was not provided"
    try:
        with Path(path_text).open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None, "candidate is not a readable JSON object"
    if not isinstance(value, dict):
        return None, "candidate is not a readable JSON object"
    return value, None


def is_exact_integer(value: Any, expected: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value == expected


def is_exact_rate(value: Any, expected: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) == expected
    )


def check_equal(candidate: dict[str, Any], expected: dict[str, Any], key: str) -> bool:
    return key in candidate and candidate[key] == expected[key]


def evaluate(candidate: dict[str, Any] | None, read_error: str | None) -> dict[str, Any]:
    with EXPECTED_PATH.open("r", encoding="utf-8") as handle:
        expected = json.load(handle)

    checks: dict[str, Callable[[], bool]] = {}
    if candidate is not None:
        checks = {
            "SP001": lambda: is_exact_integer(
                candidate.get("eligible_production_order_count"),
                expected["eligible_production_order_count"],
            ),
            "SP002": lambda: is_exact_integer(
                candidate.get("effectively_complete_order_count"),
                expected["effectively_complete_order_count"],
            ),
            "SP003": lambda: is_exact_rate(
                candidate.get("on_time_complete_order_rate"),
                expected["on_time_complete_order_rate"],
            ),
            "SP004": lambda: is_exact_integer(
                candidate.get("partial_or_unshipped_order_count"),
                expected["partial_or_unshipped_order_count"],
            ),
            "SP005": lambda: check_equal(
                candidate, expected, "warehouse_reliability_ranking"
            ),
            "SP006": lambda: check_equal(
                candidate, expected, "severe_exception_order_ids"
            ),
            "SP007": lambda: check_equal(
                candidate, expected, "highest_late_rate_carrier"
            ),
            "SP008": lambda: check_equal(candidate, expected, "service_status"),
        }

    points = []
    for point_id, goal, weight in POINT_SPECS:
        passed = bool(candidate is not None and checks[point_id]())
        assigned_score = weight / TOTAL_WEIGHT
        if read_error is not None:
            details = read_error
        elif passed:
            details = f"{point_id} business result matches the standard answer"
        else:
            details = f"{point_id} business result does not match the standard answer"
        points.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": assigned_score,
                "passed": passed,
                "earned_score": assigned_score if passed else 0,
                "details": details,
            }
        )

    return {
        "score": round(sum(point["earned_score"] for point in points), 12),
        "total_weight": TOTAL_WEIGHT,
        "points": points,
    }


def main() -> None:
    path_text = sys.argv[1] if len(sys.argv) == 2 else None
    candidate, read_error = load_candidate(path_text)
    print(json.dumps(evaluate(candidate, read_error), indent=2, sort_keys=False))


if __name__ == "__main__":
    main()
