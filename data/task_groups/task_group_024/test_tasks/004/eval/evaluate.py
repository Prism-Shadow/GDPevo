#!/usr/bin/env python3
"""Evaluate test_004 combined portfolio/SLA predictions."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PATH = ROOT / "output" / "answer.json"
CATEGORY_ORDER = ["NewFeature", "TechDebt", "Reliability", "Security"]
CATEGORY_RANK = {category: index for index, category in enumerate(CATEGORY_ORDER)}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sorted_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value)


def int_value(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def section(answer: dict[str, Any], key: str) -> dict[str, Any]:
    value = answer.get(key)
    return value if isinstance(value, dict) else {}


def category_sort_key(category: str) -> tuple[int, str]:
    return (CATEGORY_RANK.get(category, len(CATEGORY_ORDER)), category)


def sorted_categories(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted((str(item) for item in value), key=category_sort_key)


def category_counts(portfolio: dict[str, Any]) -> dict[str, int | None]:
    rows = portfolio.get("category_mix")
    by_category: dict[str, Any] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("category"), str):
                by_category[row["category"]] = row
    return {
        category: int_value(by_category.get(category, {}).get("count"))
        for category in CATEGORY_ORDER
    }


def normalized_actions(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, str]] = []
    for row in value:
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "category": str(row.get("category")),
                "action": str(row.get("action")),
                "owner_team_id": str(row.get("owner_team_id")),
            }
        )
    return sorted(rows, key=lambda row: category_sort_key(row["category"]))


def normalized_hotspots(value: Any, id_key: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for row in value:
        if not isinstance(row, dict):
            continue
        if row.get(id_key) is None:
            continue
        rows.append(
            {
                id_key: str(row.get(id_key)),
                "overdue_count": int_value(row.get("overdue_count")),
                "max_age_days": int_value(row.get("max_age_days")),
            }
        )
    return rows


def normalized_duplicate_clusters(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for row in value:
        if not isinstance(row, dict):
            continue
        if row.get("cluster_id") is None or row.get("representative_work_item_id") is None:
            continue
        rows.append(
            {
                "cluster_id": str(row.get("cluster_id")),
                "representative_work_item_id": str(row.get("representative_work_item_id")),
                "member_ids": sorted_strings(row.get("member_ids")),
            }
        )
    return sorted(rows, key=lambda row: row["cluster_id"])


def point(point_id: str, weight: int, passed: bool, goal: str) -> dict[str, Any]:
    return {"id": point_id, "weight": weight, "passed": bool(passed), "goal": goal}


def build_points(prediction: dict[str, Any], expected: dict[str, Any]) -> list[dict[str, Any]]:
    pred_portfolio = section(prediction, "portfolio")
    exp_portfolio = section(expected, "portfolio")
    pred_sla = section(prediction, "sla")
    exp_sla = section(expected, "sla")

    return [
        point(
            "SP001",
            1,
            int_value(pred_portfolio.get("eligible_total")) == exp_portfolio.get("eligible_total")
            and sorted_strings(pred_portfolio.get("eligible_work_item_ids"))
            == sorted_strings(exp_portfolio.get("eligible_work_item_ids")),
            "Portfolio eligible completed-work item set and total",
        ),
        point(
            "SP002",
            3,
            category_counts(pred_portfolio) == category_counts(exp_portfolio),
            "Portfolio category counts",
        ),
        point(
            "SP003",
            1,
            sorted_categories(pred_portfolio.get("under_invested_categories"))
            == sorted_categories(exp_portfolio.get("under_invested_categories"))
            and pred_portfolio.get("largest_negative_gap_category")
            == exp_portfolio.get("largest_negative_gap_category")
            and normalized_actions(pred_portfolio.get("follow_up_actions"))
            == normalized_actions(exp_portfolio.get("follow_up_actions")),
            "Portfolio under-invested categories and follow-up allocation action",
        ),
        point(
            "SP004",
            1,
            int_value(pred_sla.get("included_count")) == exp_sla.get("included_count")
            and sorted_strings(pred_sla.get("included_work_item_ids"))
            == sorted_strings(exp_sla.get("included_work_item_ids")),
            "SLA included reliability/security population",
        ),
        point(
            "SP005",
            1,
            int_value(pred_sla.get("overdue_count")) == exp_sla.get("overdue_count")
            and sorted_strings(pred_sla.get("overdue_work_item_ids"))
            == sorted_strings(exp_sla.get("overdue_work_item_ids")),
            "SLA overdue work item set",
        ),
        point(
            "SP006",
            1,
            normalized_hotspots(pred_sla.get("owner_hotspots"), "owner_id")
            == normalized_hotspots(exp_sla.get("owner_hotspots"), "owner_id")
            and normalized_hotspots(pred_sla.get("team_hotspots"), "team_id")
            == normalized_hotspots(exp_sla.get("team_hotspots"), "team_id"),
            "SLA owner and team hotspot ranking",
        ),
        point(
            "SP007",
            3,
            normalized_duplicate_clusters(pred_sla.get("duplicate_clusters"))
            == normalized_duplicate_clusters(exp_sla.get("duplicate_clusters"))
            and sorted_strings(pred_sla.get("missing_owner_work_item_ids"))
            == sorted_strings(exp_sla.get("missing_owner_work_item_ids")),
            "Duplicate cluster and missing-owner triage",
        ),
        point(
            "SP008",
            3,
            prediction.get("combined_action") == expected.get("combined_action"),
            "Combined action enum",
        ),
    ]


def evaluate(prediction: Any, expected: Any) -> dict[str, Any]:
    if not isinstance(prediction, dict) or not isinstance(expected, dict):
        points = [point("TYPE", 1, False, "Prediction and expected answer must be JSON objects.")]
    else:
        points = build_points(prediction, expected)

    total_weight = sum(row["weight"] for row in points)
    earned_weight = sum(row["weight"] for row in points if row["passed"])
    return {
        "score": round(earned_weight / total_weight, 6) if total_weight else 0.0,
        "max_score": 1.0,
        "points": points,
    }


def main() -> int:
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else EXPECTED_PATH
    try:
        prediction = load_json(prediction_path)
        expected = load_json(EXPECTED_PATH)
        result = evaluate(prediction, expected)
    except Exception as exc:  # noqa: BLE001
        result = {
            "score": 0.0,
            "max_score": 1.0,
            "points": [
                point("EVAL_ERROR", 1, False, f"Evaluator could not parse or score prediction: {exc}")
            ],
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
