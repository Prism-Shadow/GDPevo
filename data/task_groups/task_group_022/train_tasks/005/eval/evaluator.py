#!/usr/bin/env python3
"""Atomic weighted evaluator for train_005."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Callable


POINT_SPECS = (
    ("SP001", "Report the correct eligible support-case population.", 2),
    ("SP002", "Report the correct open-at-cutoff and reopened-at-cutoff counts.", 3),
    ("SP003", "Report the correct first-response breach count.", 2),
    ("SP004", "Report the correct active-clock resolution breach count.", 3),
    ("SP005", "Report the correct worst-three account ranking and rollups.", 2),
    ("SP006", "Report the exact sorted severe active case set.", 3),
    ("SP007", "Report the correct median active resolution hours.", 2),
    ("SP008", "Classify support risk under the request policy.", 1),
)
TOTAL_WEIGHT = sum(weight for _, _, weight in POINT_SPECS)
EXPECTED_PATH = Path(__file__).resolve().parent.parent / "output" / "answer.json"


def read_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def exact_integer(value: Any, expected: Any) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and isinstance(expected, int)
        and not isinstance(expected, bool)
        and value == expected
    )


def exact_number(value: Any, expected: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isinstance(expected, (int, float))
        and not isinstance(expected, bool)
        and math.isfinite(float(value))
        and float(value) == float(expected)
    )


def evaluate(
    candidate: dict[str, Any] | None,
    expected: dict[str, Any],
) -> dict[str, Any]:
    checks: dict[str, Callable[[], bool]] = {}
    if candidate is not None:
        state = candidate.get("case_state_summary")
        expected_state = expected["case_state_summary"]
        checks = {
            "SP001": lambda: exact_integer(
                candidate.get("eligible_case_count"),
                expected["eligible_case_count"],
            ),
            "SP002": lambda: isinstance(state, dict)
            and exact_integer(
                state.get("open_at_cutoff_count"),
                expected_state["open_at_cutoff_count"],
            )
            and exact_integer(
                state.get("reopened_at_cutoff_count"),
                expected_state["reopened_at_cutoff_count"],
            ),
            "SP003": lambda: exact_integer(
                candidate.get("first_response_breach_count"),
                expected["first_response_breach_count"],
            ),
            "SP004": lambda: exact_integer(
                candidate.get("active_clock_resolution_breach_count"),
                expected["active_clock_resolution_breach_count"],
            ),
            "SP005": lambda: candidate.get("worst_accounts")
            == expected["worst_accounts"],
            "SP006": lambda: candidate.get("severe_active_case_ids")
            == expected["severe_active_case_ids"],
            "SP007": lambda: exact_number(
                candidate.get("median_active_resolution_hours"),
                expected["median_active_resolution_hours"],
            ),
            "SP008": lambda: candidate.get("support_risk")
            == expected["support_risk"],
        }

    results: list[dict[str, Any]] = []
    earned_weight = 0
    for point_id, goal, weight in POINT_SPECS:
        passed = bool(candidate is not None and checks[point_id]())
        if passed:
            earned_weight += weight
        assigned_score = weight / TOTAL_WEIGHT
        if candidate is None:
            details = "Candidate is not a readable JSON object."
        else:
            outcome = "pass" if passed else "fail"
            details = f"Atomic business-result check: {outcome}."
        results.append(
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
        "points": results,
    }


def main() -> None:
    expected = read_object(EXPECTED_PATH)
    candidate_path = (
        Path(sys.argv[1])
        if len(sys.argv) == 2 and sys.argv[1]
        else Path("__missing_candidate__")
    )
    candidate = read_object(candidate_path)
    if expected is None:
        result = {
            "score": 0.0,
            "total_weight": TOTAL_WEIGHT,
            "points": [],
            "error": "Evaluator standard answer is unavailable.",
        }
    else:
        result = evaluate(candidate, expected)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
