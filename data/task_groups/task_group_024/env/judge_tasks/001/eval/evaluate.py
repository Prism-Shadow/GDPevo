#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


CATEGORY_ORDER = ["NewFeature", "TechDebt", "Reliability", "Security"]
CATEGORY_INDEX = {category: index for index, category in enumerate(CATEGORY_ORDER)}
TASK_DIR = Path(__file__).resolve().parents[1]
EXPECTED_PATH = TASK_DIR / "output" / "answer.json"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def sorted_ids(value: Any) -> list[str]:
    return sorted(str(item) for item in as_list(value))


def category_sort_key(category: Any) -> tuple[int, str]:
    text = str(category)
    return (CATEGORY_INDEX.get(text, len(CATEGORY_ORDER)), text)


def normalize_categories(value: Any) -> list[str]:
    return sorted((str(item) for item in as_list(value)), key=category_sort_key)


def bucket_map(answer: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = as_list(answer.get("bucket_rows"))
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and "category" in row:
            result[str(row["category"])] = row
    return result


def to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_percentage(value: Any) -> float | None:
    try:
        return round(float(value), 1)
    except (TypeError, ValueError):
        return None


def normalize_counts(answer: dict[str, Any]) -> dict[str, int | None]:
    rows = bucket_map(answer)
    return {category: to_int(rows.get(category, {}).get("count")) for category in CATEGORY_ORDER}


def normalize_mix_metrics(answer: dict[str, Any]) -> dict[str, dict[str, float | int | None]]:
    rows = bucket_map(answer)
    return {
        category: {
            "actual_percentage": to_percentage(rows.get(category, {}).get("actual_percentage")),
            "target_percentage": to_percentage(rows.get(category, {}).get("target_percentage")),
            "gap_basis_points": to_int(rows.get(category, {}).get("gap_basis_points")),
        }
        for category in CATEGORY_ORDER
    }


def normalize_actions(value: Any) -> list[dict[str, str]]:
    actions = []
    for row in as_list(value):
        if not isinstance(row, dict):
            continue
        actions.append(
            {
                "category": str(row.get("category")),
                "action": str(row.get("action")),
                "owner_team_id": str(row.get("owner_team_id")),
            }
        )
    return sorted(actions, key=lambda row: (category_sort_key(row["category"]), row["action"], row["owner_team_id"]))


def normalize_evidence(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        value = {}
    return {category: sorted_ids(value.get(category)) for category in CATEGORY_ORDER}


def point(point_id: str, weight: int, passed: bool, goal: str) -> dict[str, Any]:
    return {"id": point_id, "weight": weight, "passed": bool(passed), "goal": goal}


def score(prediction: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    points = [
        point(
            "SP001",
            3,
            sorted_ids(prediction.get("eligible_work_item_ids")) == sorted_ids(expected.get("eligible_work_item_ids"))
            and to_int(prediction.get("eligible_total")) == to_int(expected.get("eligible_total")),
            "Eligible completed non-cancelled work item set and total",
        ),
        point(
            "SP002",
            3,
            normalize_counts(prediction) == normalize_counts(expected),
            "Portfolio category counts",
        ),
        point(
            "SP003",
            2,
            normalize_mix_metrics(prediction) == normalize_mix_metrics(expected),
            "Actual percentages, target percentages, and gap basis points",
        ),
        point(
            "SP004",
            2,
            normalize_categories(prediction.get("under_invested_categories"))
            == normalize_categories(expected.get("under_invested_categories")),
            "Under-invested category set",
        ),
        point(
            "SP005",
            1,
            prediction.get("largest_negative_gap_category") == expected.get("largest_negative_gap_category"),
            "Largest negative gap category",
        ),
        point(
            "SP006",
            2,
            normalize_actions(prediction.get("follow_up_actions"))
            == normalize_actions(expected.get("follow_up_actions")),
            "Follow-up action enum and owner team mapping",
        ),
        point(
            "SP007",
            1,
            normalize_evidence(prediction.get("evidence_sample_ids"))
            == normalize_evidence(expected.get("evidence_sample_ids")),
            "Evidence sample IDs by category",
        ),
    ]
    max_weight = sum(row["weight"] for row in points)
    earned = sum(row["weight"] for row in points if row["passed"])
    return {"score": earned / max_weight, "max_score": 1.0, "points": points}


def main() -> int:
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else TASK_DIR / "output" / "answer.json"
    try:
        prediction = load_json(prediction_path)
        expected = load_json(EXPECTED_PATH)
        if not isinstance(prediction, dict) or not isinstance(expected, dict):
            raise ValueError("prediction and expected answer must be JSON objects")
        result = score(prediction, expected)
    except Exception as exc:
        result = {
            "score": 0.0,
            "max_score": 1.0,
            "points": [
                {
                    "id": "ERROR",
                    "weight": 1,
                    "passed": False,
                    "goal": f"Evaluation failed: {exc}",
                }
            ],
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
