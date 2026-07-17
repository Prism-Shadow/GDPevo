#!/usr/bin/env python3
"""Evaluate test_001 portfolio-mix predictions."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


CATEGORY_ORDER = ["NewFeature", "TechDebt", "Reliability", "Security"]
CATEGORY_RANK = {category: index for index, category in enumerate(CATEGORY_ORDER)}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sorted_ids(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value)


def category_sort_key(category: str) -> tuple[int, str]:
    return (CATEGORY_RANK.get(category, len(CATEGORY_ORDER)), category)


def sorted_categories(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted((str(item) for item in value), key=category_sort_key)


def mix_by_category(answer: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = answer.get("category_mix")
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("category"), str):
            result[row["category"]] = row
    return result


def counts(answer: dict[str, Any]) -> dict[str, int]:
    rows = mix_by_category(answer)
    result: dict[str, int] = {}
    for category in CATEGORY_ORDER:
        try:
            result[category] = int(rows.get(category, {}).get("count"))
        except (TypeError, ValueError):
            result[category] = -1
    return result


def percentages_and_gaps(answer: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = mix_by_category(answer)
    result: dict[str, dict[str, Any]] = {}
    for category in CATEGORY_ORDER:
        row = rows.get(category, {})
        try:
            actual = round(float(row.get("actual_percentage")), 1)
        except (TypeError, ValueError):
            actual = None
        try:
            target = round(float(row.get("target_percentage")), 1)
        except (TypeError, ValueError):
            target = None
        try:
            gap = int(row.get("gap_basis_points"))
        except (TypeError, ValueError):
            gap = None
        result[category] = {
            "actual_percentage": actual,
            "target_percentage": target,
            "gap_basis_points": gap,
        }
    return result


def normalized_actions(answer: dict[str, Any]) -> list[dict[str, str]]:
    rows = answer.get("follow_up_actions")
    if not isinstance(rows, list):
        return []
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        normalized.append(
            {
                "category": str(row.get("category")),
                "action": str(row.get("action")),
                "owner_team_id": str(row.get("owner_team_id")),
            }
        )
    return sorted(normalized, key=lambda row: category_sort_key(row["category"]))


def normalized_evidence(answer: dict[str, Any]) -> dict[str, list[str]]:
    samples = answer.get("evidence_sample_ids")
    if not isinstance(samples, dict):
        return {}
    return {category: sorted_ids(samples.get(category)) for category in CATEGORY_ORDER}


def build_points(prediction: dict[str, Any], expected: dict[str, Any]) -> list[dict[str, Any]]:
    pred_eligible = sorted_ids(prediction.get("eligible_work_item_ids"))
    exp_eligible = sorted_ids(expected.get("eligible_work_item_ids"))

    points = [
        {
            "id": "SP001",
            "weight": 3,
            "passed": pred_eligible == exp_eligible and prediction.get("eligible_total") == expected.get("eligible_total"),
            "goal": "Eligible closed-work item set and total match the quarter-end scope.",
        },
        {
            "id": "SP002",
            "weight": 3,
            "passed": counts(prediction) == counts(expected),
            "goal": "Category counts match portfolio classification precedence.",
        },
        {
            "id": "SP003",
            "weight": 2,
            "passed": percentages_and_gaps(prediction) == percentages_and_gaps(expected),
            "goal": "Actual percentages, target percentages, and gap basis points match rounding rules.",
        },
        {
            "id": "SP004",
            "weight": 2,
            "passed": sorted_categories(prediction.get("under_invested_categories")) == sorted_categories(expected.get("under_invested_categories")),
            "goal": "Under-invested category set matches the negative-gap threshold.",
        },
        {
            "id": "SP005",
            "weight": 1,
            "passed": prediction.get("largest_negative_gap_category") == expected.get("largest_negative_gap_category"),
            "goal": "Largest negative gap category is correct.",
        },
        {
            "id": "SP006",
            "weight": 2,
            "passed": normalized_actions(prediction) == normalized_actions(expected),
            "goal": "Follow-up action enum and owner-team mapping are correct.",
        },
        {
            "id": "SP007",
            "weight": 1,
            "passed": normalized_evidence(prediction) == normalized_evidence(expected),
            "goal": "Evidence sample IDs per category are correct.",
        },
    ]
    return points


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    expected_path = script_dir.parent / "output" / "answer.json"
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else expected_path

    try:
        expected = load_json(expected_path)
        prediction = load_json(prediction_path)
    except Exception as exc:  # noqa: BLE001
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
    score = earned_weight / total_weight if total_weight else 0.0

    result = {
        "score": round(score, 6),
        "max_score": 1.0,
        "points": points,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
