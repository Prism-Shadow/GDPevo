#!/usr/bin/env python3
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


def main() -> int:
    if len(sys.argv) > 2:
        print("usage: evaluate.py [prediction_json_path]", file=sys.stderr)
        return 2

    task_dir = Path(__file__).resolve().parents[1]
    expected = load_json(task_dir / "output" / "answer.json")
    prediction_path = Path(sys.argv[1]) if len(sys.argv) == 2 else task_dir / "output" / "answer.json"

    try:
        prediction = load_json(prediction_path)
    except Exception as exc:  # noqa: BLE001 - evaluator should return structured failure
        result = {
            "score": 0.0,
            "max_score": 1.0,
            "points": [
                {
                    "id": "SP000",
                    "weight": 1,
                    "passed": False,
                    "goal": f"Prediction JSON could not be loaded: {exc}",
                }
            ],
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    checks = [
        (
            "SP001",
            3,
            "ship decision enum",
            prediction.get("ship_decision") == expected["ship_decision"],
        ),
        (
            "SP002",
            3,
            "gating work item ID set",
            sorted_strings(prediction.get("gating_work_item_ids")) == sorted_strings(expected["gating_work_item_ids"]),
        ),
        (
            "SP003",
            2,
            "milestone completion percentages",
            milestone_map(prediction.get("milestones")) == milestone_map(expected["milestones"]),
        ),
        (
            "SP004",
            2,
            "blocker cause counts",
            cause_counts(prediction.get("blocker_cause_counts")) == cause_counts(expected["blocker_cause_counts"]),
        ),
        (
            "SP005",
            2,
            "critical dependency chain",
            exact_chain(prediction.get("critical_dependency_chain")) == exact_chain(expected["critical_dependency_chain"]),
        ),
        (
            "SP006",
            1,
            "release risk tier",
            prediction.get("risk_tier") == expected["risk_tier"],
        ),
        (
            "SP007",
            1,
            "owner escalation ID set",
            sorted_strings(prediction.get("owner_escalation_ids")) == sorted_strings(expected["owner_escalation_ids"]),
        ),
    ]

    max_weight = sum(weight for _, weight, _, _ in checks)
    earned = sum(weight for _, weight, _, passed in checks if passed)
    result = {
        "score": earned / max_weight,
        "max_score": 1.0,
        "points": [
            {
                "id": point_id,
                "weight": weight,
                "passed": passed,
                "goal": goal,
            }
            for point_id, weight, goal, passed in checks
        ],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
