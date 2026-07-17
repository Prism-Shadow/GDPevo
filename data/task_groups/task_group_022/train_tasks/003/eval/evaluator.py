#!/usr/bin/env python3
"""Atomic weighted evaluator for train_003."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


MISSING = object()
TOTAL_WEIGHT = 18

POINTS = (
    {
        "id": "SP001",
        "goal": "Identify the faulty carrier scan row and shipment.",
        "weight": 3,
        "paths": (
            ("correction_target", "scan_row_id"),
            ("correction_target", "shipment_id"),
        ),
    },
    {
        "id": "SP002",
        "goal": "Report the corrected canonical field and exact old and new values.",
        "weight": 3,
        "paths": (
            ("correction_target", "field_name"),
            ("correction_target", "old_value"),
            ("correction_target", "new_value"),
        ),
    },
    {
        "id": "SP003",
        "goal": "Report an exact one-business-row mutation outcome.",
        "weight": 2,
        "paths": (("mutation_result", "affected_business_rows"),),
    },
    {
        "id": "SP004",
        "goal": "Report one compliant audit row with the required correction receipt fields.",
        "weight": 2,
        "paths": (
            ("mutation_result", "audit_rows"),
            ("audit_record", "audit_id"),
            ("audit_record", "correction_key"),
            ("audit_record", "entity_type"),
            ("audit_record", "entity_id"),
            ("audit_record", "source_row_id"),
            ("audit_record", "field_name"),
            ("audit_record", "old_value"),
            ("audit_record", "new_value"),
            ("audit_record", "reason_code"),
            ("audit_record", "corrected_at"),
            ("audit_record", "actor"),
        ),
    },
    {
        "id": "SP005",
        "goal": "Report the pre-correction backlog shipment count.",
        "weight": 2,
        "paths": (("backlog_analysis", "pre_correction_backlog_shipment_count"),),
    },
    {
        "id": "SP006",
        "goal": "Report the post-correction backlog shipment count and its delta.",
        "weight": 3,
        "paths": (
            ("backlog_analysis", "post_correction_backlog_shipment_count"),
            ("backlog_analysis", "backlog_delta"),
        ),
    },
    {
        "id": "SP007",
        "goal": "Report the post-correction delivered shipment count.",
        "weight": 2,
        "paths": (("backlog_analysis", "post_correction_delivered_shipment_count"),),
    },
    {
        "id": "SP008",
        "goal": "Classify the correction status under the request success rule.",
        "weight": 1,
        "paths": (("correction_status",),),
    },
)


def read_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def at_path(value: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = value
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return MISSING
        current = current[part]
    return current


def strict_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    return actual == expected


def evaluate(candidate: dict[str, Any] | None, expected: dict[str, Any]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    earned_weight = 0
    for point in POINTS:
        paths = point["paths"]
        passed = candidate is not None and all(
            strict_equal(at_path(candidate, path), at_path(expected, path))
            for path in paths
        )
        if passed:
            earned_weight += point["weight"]
        assigned_score = point["weight"] / TOTAL_WEIGHT
        checked = ", ".join(".".join(path) for path in paths)
        if candidate is None:
            details = f"Checked fields: {checked}. Candidate is not a readable JSON object."
        else:
            outcome = "pass" if passed else "fail"
            details = f"Checked fields: {checked}. Atomic result: {outcome}."
        results.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "assigned_score": assigned_score,
                "passed": bool(passed),
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
    evaluator_dir = Path(__file__).resolve().parent
    expected_path = evaluator_dir.parent / "output" / "answer.json"
    expected = read_object(expected_path)
    candidate_path = Path(sys.argv[1]) if len(sys.argv) == 2 and sys.argv[1] else Path("__missing_candidate__")
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
