#!/usr/bin/env python3
"""Exact-match evaluator for train_003."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SCORING_POINTS = [
    ("SP001", "Correct analysis window and filtered summary totals.", 2),
    ("SP002", "Correct supplier set, names, counts, and percentages.", 3),
    ("SP003", "Correct supplier total costs and highest-cost supplier.", 2),
    ("SP004", "Correct supplier average duration in days.", 2),
    ("SP005", "Correct RMA and WORK_ORDER split by supplier.", 2),
    ("SP006", "Correct open and severe incident counts by supplier.", 1),
    ("SP007", "Correct controlled recommendation code by supplier.", 3),
    ("SP008", "Correct escalation supplier ordering and highest-share supplier.", 2),
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def round_number(value: Any, places: int) -> Any:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(float(value), places)
    return value


def scorecard_by_supplier(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payload.get("supplier_scorecard")
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("supplier_id"), str):
            result[row["supplier_id"]] = row
    return result


def compare_row_fields(
    expected_rows: dict[str, dict[str, Any]],
    actual_rows: dict[str, dict[str, Any]],
    fields: list[str],
    numeric_places: dict[str, int] | None = None,
) -> bool:
    if set(expected_rows) != set(actual_rows):
        return False
    numeric_places = numeric_places or {}
    for supplier_id, expected in expected_rows.items():
        actual = actual_rows[supplier_id]
        for field in fields:
            expected_value = expected.get(field)
            actual_value = actual.get(field)
            if field in numeric_places:
                expected_value = round_number(expected_value, numeric_places[field])
                actual_value = round_number(actual_value, numeric_places[field])
            if actual_value != expected_value:
                return False
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: evaluate.py <candidate_answer.json>", file=sys.stderr)
        return 2

    script_dir = Path(__file__).resolve().parent
    expected_path = script_dir.parent / "output" / "answer.json"
    candidate_path = Path(sys.argv[1])

    try:
        expected = load_json(expected_path)
        actual = load_json(candidate_path)
    except Exception as exc:
        total_weight = sum(point[2] for point in SCORING_POINTS)
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "total_weight": total_weight,
                    "earned_weight": 0,
                    "error": f"Could not load JSON: {exc}",
                    "points": [
                        {"id": pid, "earned": False, "weight": weight, "goal": goal}
                        for pid, goal, weight in SCORING_POINTS
                    ],
                },
                indent=2,
            )
        )
        return 0

    expected_rows = scorecard_by_supplier(expected)
    actual_rows = scorecard_by_supplier(actual)

    checks = {
        "SP001": (
            actual.get("analysis_window") == expected.get("analysis_window")
            and actual.get("summary") == expected.get("summary")
        ),
        "SP002": compare_row_fields(
            expected_rows,
            actual_rows,
            ["supplier_id", "supplier_name", "incident_count", "incident_percentage"],
            {"incident_percentage": 1},
        ),
        "SP003": (
            compare_row_fields(
                expected_rows,
                actual_rows,
                ["total_resolution_cost"],
                {"total_resolution_cost": 2},
            )
            and actual.get("highest_cost_supplier_id") == expected.get("highest_cost_supplier_id")
        ),
        "SP004": compare_row_fields(
            expected_rows,
            actual_rows,
            ["avg_duration_days"],
            {"avg_duration_days": 2},
        ),
        "SP005": compare_row_fields(
            expected_rows,
            actual_rows,
            ["rma_count", "work_order_count"],
        ),
        "SP006": compare_row_fields(
            expected_rows,
            actual_rows,
            ["open_incident_count", "severe_incident_count"],
        ),
        "SP007": compare_row_fields(
            expected_rows,
            actual_rows,
            ["recommendation_code"],
        ),
        "SP008": (
            actual.get("top_escalation_suppliers") == expected.get("top_escalation_suppliers")
            and actual.get("highest_share_supplier_id") == expected.get("highest_share_supplier_id")
        ),
    }

    total_weight = sum(point[2] for point in SCORING_POINTS)
    earned_weight = sum(weight for point_id, _, weight in SCORING_POINTS if checks[point_id])
    result = {
        "score": round(earned_weight / total_weight, 6),
        "total_weight": total_weight,
        "earned_weight": earned_weight,
        "points": [
            {
                "id": point_id,
                "earned": bool(checks[point_id]),
                "weight": weight,
                "goal": goal,
            }
            for point_id, goal, weight in SCORING_POINTS
        ],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
