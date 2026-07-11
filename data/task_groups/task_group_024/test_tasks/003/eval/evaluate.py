#!/usr/bin/env python3
"""Evaluate test_003 release-readiness predictions."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


CAUSES = [
    "ExternalDependency",
    "Environment",
    "SecurityReview",
    "Capacity",
    "DesignDecision",
    "DataMigration",
    "Vendor",
    "OwnershipGap",
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sorted_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value)


def milestone_map(value: Any) -> dict[str, float]:
    if not isinstance(value, list):
        return {}
    rows: dict[str, float] = {}
    for row in value:
        if not isinstance(row, dict):
            continue
        milestone_id = row.get("milestone_id")
        if not isinstance(milestone_id, str):
            continue
        try:
            completion_percentage = round(float(row.get("completion_percentage")), 1)
        except (TypeError, ValueError):
            continue
        rows[milestone_id] = completion_percentage
    return rows


def cause_counts(value: Any) -> dict[str, int]:
    counts = {cause: 0 for cause in CAUSES}
    if isinstance(value, dict):
        for cause in CAUSES:
            try:
                counts[cause] = int(value.get(cause, 0))
            except (TypeError, ValueError):
                counts[cause] = -1
        return counts
    if isinstance(value, list):
        for row in value:
            if not isinstance(row, dict):
                continue
            cause = row.get("cause")
            if cause in counts:
                try:
                    counts[cause] = int(row.get("count", 0))
                except (TypeError, ValueError):
                    counts[cause] = -1
    return counts


def exact_chain(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def build_points(prediction: dict[str, Any], expected: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": "SP001",
            "weight": 3,
            "passed": prediction.get("ship_decision") == expected["ship_decision"],
            "goal": "Ship decision enum matches release gate policy.",
        },
        {
            "id": "SP002",
            "weight": 3,
            "passed": sorted_strings(prediction.get("gating_work_item_ids"))
            == sorted_strings(expected["gating_work_item_ids"]),
            "goal": "Gating work item ID set matches active critical-path blockers.",
        },
        {
            "id": "SP003",
            "weight": 2,
            "passed": milestone_map(prediction.get("milestones")) == milestone_map(expected["milestones"]),
            "goal": "Milestone completion percentages match readiness rules.",
        },
        {
            "id": "SP004",
            "weight": 2,
            "passed": cause_counts(prediction.get("blocker_cause_counts"))
            == cause_counts(expected["blocker_cause_counts"]),
            "goal": "Blocker cause counts match active blockers attached to gating work.",
        },
        {
            "id": "SP005",
            "weight": 2,
            "passed": exact_chain(prediction.get("critical_dependency_chain"))
            == exact_chain(expected["critical_dependency_chain"]),
            "goal": "Critical dependency chain matches the ordered representative chain.",
        },
        {
            "id": "SP006",
            "weight": 1,
            "passed": prediction.get("risk_tier") == expected["risk_tier"],
            "goal": "Release risk tier matches readiness policy.",
        },
        {
            "id": "SP007",
            "weight": 1,
            "passed": sorted_strings(prediction.get("owner_escalation_ids"))
            == sorted_strings(expected["owner_escalation_ids"]),
            "goal": "Owner escalation ID set matches gating item ownership.",
        },
    ]


def main() -> int:
    if len(sys.argv) > 2:
        print("usage: evaluate.py [prediction_json_path]", file=sys.stderr)
        return 2

    task_dir = Path(__file__).resolve().parents[1]
    expected_path = task_dir / "output" / "answer.json"
    prediction_path = Path(sys.argv[1]) if len(sys.argv) == 2 else expected_path

    try:
        expected = load_json(expected_path)
        prediction = load_json(prediction_path)
    except Exception as exc:  # noqa: BLE001 - evaluator should return structured failure
        result = {
            "score": 0.0,
            "max_score": 1.0,
            "points": [
                {
                    "id": "LOAD",
                    "weight": 1,
                    "passed": False,
                    "goal": f"Prediction JSON must load successfully: {exc}",
                }
            ],
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if not isinstance(prediction, dict) or not isinstance(expected, dict):
        points = [
            {
                "id": "TYPE",
                "weight": 1,
                "passed": False,
                "goal": "Prediction and expected answer must be JSON objects.",
            }
        ]
    else:
        points = build_points(prediction, expected)

    total_weight = sum(point["weight"] for point in points)
    earned_weight = sum(point["weight"] for point in points if point["passed"])
    result = {
        "score": round(earned_weight / total_weight, 6) if total_weight else 0.0,
        "max_score": 1.0,
        "points": points,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
