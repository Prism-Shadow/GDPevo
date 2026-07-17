#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


CATEGORY_ORDER = ["NewFeature", "TechDebt", "Reliability", "Security"]
CATEGORY_INDEX = {category: index for index, category in enumerate(CATEGORY_ORDER)}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def coerce_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def sorted_id_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    return sorted(str(item) for item in value)


def normalize_under_invested(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    try:
        return sorted((str(item) for item in value), key=lambda item: CATEGORY_INDEX[item])
    except KeyError:
        return sorted(str(item) for item in value)


def category_rows(answer: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(answer, dict):
        return {}
    rows = answer.get("category_mix")
    if not isinstance(rows, list):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        category = row.get("category")
        if category in CATEGORY_INDEX:
            normalized[str(category)] = row
    return normalized


def normalize_counts(answer: Any) -> dict[str, int | None]:
    rows = category_rows(answer)
    return {
        category: coerce_int(rows.get(category, {}).get("count"))
        for category in CATEGORY_ORDER
    }


def normalize_mix_metrics(answer: Any) -> dict[str, dict[str, float | int | None]]:
    rows = category_rows(answer)
    metrics: dict[str, dict[str, float | int | None]] = {}
    for category in CATEGORY_ORDER:
        row = rows.get(category, {})
        actual = coerce_float(row.get("actual_percentage"))
        target = coerce_float(row.get("target_percentage"))
        metrics[category] = {
            "actual_percentage": None if actual is None else round(actual, 1),
            "target_percentage": None if target is None else round(target, 1),
            "gap_basis_points": coerce_int(row.get("gap_basis_points")),
        }
    return metrics


def normalize_actions(value: Any) -> list[dict[str, str]] | None:
    if not isinstance(value, list):
        return None
    actions: list[dict[str, str]] = []
    for row in value:
        if not isinstance(row, dict):
            return None
        actions.append(
            {
                "category": str(row.get("category")),
                "action": str(row.get("action")),
                "owner_team_id": str(row.get("owner_team_id")),
            }
        )
    return sorted(
        actions,
        key=lambda row: (CATEGORY_INDEX.get(row["category"], 999), row["action"], row["owner_team_id"]),
    )


def normalize_evidence(value: Any) -> dict[str, list[str] | None] | None:
    if not isinstance(value, dict):
        return None
    return {category: sorted_id_list(value.get(category)) for category in CATEGORY_ORDER}


def point(point_id: str, weight: int, passed: bool, goal: str) -> dict[str, Any]:
    return {"id": point_id, "weight": weight, "passed": bool(passed), "goal": goal}


def score(prediction: Any, expected: Any) -> dict[str, Any]:
    if not isinstance(prediction, dict):
        prediction = {}
    expected_ids = sorted_id_list(expected.get("eligible_work_item_ids"))
    prediction_ids = sorted_id_list(prediction.get("eligible_work_item_ids"))

    points = [
        point(
            "SP001",
            3,
            prediction_ids == expected_ids and prediction.get("eligible_total") == expected.get("eligible_total"),
            "Eligible completed Data Platform Q1 work item set and total",
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
            normalize_under_invested(prediction.get("under_invested_categories")) == normalize_under_invested(expected.get("under_invested_categories")),
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
            normalize_actions(prediction.get("follow_up_actions")) == normalize_actions(expected.get("follow_up_actions")),
            "Follow-up action enum and owner-team mapping",
        ),
        point(
            "SP007",
            1,
            normalize_evidence(prediction.get("evidence_sample_ids")) == normalize_evidence(expected.get("evidence_sample_ids")),
            "Evidence sample IDs by category",
        ),
    ]
    max_weight = sum(row["weight"] for row in points)
    earned = sum(row["weight"] for row in points if row["passed"])
    return {
        "score": earned / max_weight if max_weight else 0.0,
        "max_score": 1.0,
        "points": points,
    }


def main() -> None:
    task_dir = Path(__file__).resolve().parents[1]
    expected_path = task_dir / "output" / "answer.json"
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else expected_path
    expected = load_json(expected_path)
    try:
        prediction = load_json(prediction_path)
    except Exception:
        prediction = {}
    print(json.dumps(score(prediction, expected), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
