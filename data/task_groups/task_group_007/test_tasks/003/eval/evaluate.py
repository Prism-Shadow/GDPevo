#!/usr/bin/env python3
"""Exact-match evaluator for task_group_007 test_003."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SCORING_POINTS = [
    ("SP001", "Correct analysis window and full-year summary totals.", 2),
    ("SP002", "Correct supplier set, names, quality statuses, incident counts, and incident percentages.", 3),
    ("SP003", "Correct supplier ranking, top-five ranking, and highest-share supplier.", 2),
    ("SP004", "Correct supplier total costs, cost percentages, and highest-cost supplier.", 2),
    ("SP005", "Correct overall and supplier RMA/work-order duration averages.", 3),
    ("SP006", "Correct RMA, work-order, open, severe, and critical-RMA counts by supplier.", 2),
    ("SP007", "Correct controlled management recommendation code by supplier.", 3),
    ("SP008", "Correct controlled management action supplier sets.", 2),
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def rounded(value: Any, places: int) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(float(value), places)
    return value


def normalized_list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        return []
    return sorted(value)


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
                expected_value = rounded(expected_value, numeric_places[field])
                actual_value = rounded(actual_value, numeric_places[field])
            if actual_value != expected_value:
                return False
    return True


def compare_summary(
    expected: dict[str, Any], actual: dict[str, Any], fields: list[str], numeric_places: dict[str, int]
) -> bool:
    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return False
    for field in fields:
        expected_value = expected.get(field)
        actual_value = actual.get(field)
        if field in numeric_places:
            expected_value = rounded(expected_value, numeric_places[field])
            actual_value = rounded(actual_value, numeric_places[field])
        if actual_value != expected_value:
            return False
    return True


def compare_action_sets(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return False
    fields = [
        "procurement_freeze_supplier_ids",
        "supplier_escalation_supplier_ids",
        "warehouse_process_review_supplier_ids",
        "watchlist_supplier_ids",
        "monitor_supplier_ids",
    ]
    return all(normalized_list(actual.get(field)) == normalized_list(expected.get(field)) for field in fields)


def evaluate(actual: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    expected_rows = scorecard_by_supplier(expected)
    actual_rows = scorecard_by_supplier(actual)
    expected_summary = expected.get("summary", {})
    actual_summary = actual.get("summary", {})

    checks = {
        "SP001": (
            actual.get("analysis_window") == expected.get("analysis_window")
            and compare_summary(
                expected_summary,
                actual_summary,
                [
                    "filtered_incident_count",
                    "supplier_count",
                    "total_resolution_cost",
                    "overall_rma_count",
                    "overall_work_order_count",
                    "open_incident_count",
                    "severe_incident_count",
                ],
                {"total_resolution_cost": 2},
            )
        ),
        "SP002": compare_row_fields(
            expected_rows,
            actual_rows,
            ["supplier_id", "supplier_name", "quality_status", "incident_count", "incident_percentage"],
            {"incident_percentage": 1},
        ),
        "SP003": (
            actual.get("supplier_ranking") == expected.get("supplier_ranking")
            and actual.get("top_five_supplier_ranking") == expected.get("top_five_supplier_ranking")
            and actual.get("highest_share_supplier_id") == expected.get("highest_share_supplier_id")
        ),
        "SP004": (
            compare_row_fields(
                expected_rows,
                actual_rows,
                ["total_resolution_cost", "cost_percentage"],
                {"total_resolution_cost": 2, "cost_percentage": 1},
            )
            and actual.get("highest_cost_supplier_id") == expected.get("highest_cost_supplier_id")
        ),
        "SP005": (
            compare_summary(
                expected_summary,
                actual_summary,
                ["overall_rma_avg_duration_days", "overall_work_order_avg_duration_days"],
                {"overall_rma_avg_duration_days": 2, "overall_work_order_avg_duration_days": 2},
            )
            and compare_row_fields(
                expected_rows,
                actual_rows,
                ["avg_duration_days", "avg_rma_duration_days", "avg_work_order_duration_days"],
                {
                    "avg_duration_days": 2,
                    "avg_rma_duration_days": 2,
                    "avg_work_order_duration_days": 2,
                },
            )
        ),
        "SP006": compare_row_fields(
            expected_rows,
            actual_rows,
            ["rma_count", "work_order_count", "open_incident_count", "severe_incident_count", "critical_rma_count"],
        ),
        "SP007": compare_row_fields(expected_rows, actual_rows, ["recommendation_code"]),
        "SP008": compare_action_sets(
            expected.get("management_action_sets", {}),
            actual.get("management_action_sets", {}),
        ),
    }

    total_weight = sum(point[2] for point in SCORING_POINTS)
    earned_weight = sum(weight for point_id, _, weight in SCORING_POINTS if checks[point_id])
    return {
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
                        {"id": point_id, "earned": False, "weight": weight, "goal": goal}
                        for point_id, goal, weight in SCORING_POINTS
                    ],
                },
                indent=2,
            )
        )
        return 0

    print(json.dumps(evaluate(actual, expected), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
