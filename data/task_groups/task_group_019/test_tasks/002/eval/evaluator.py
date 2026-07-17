#!/usr/bin/env python3
"""Evaluator for task_group_019 test_002."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


POINTS = [
    {
        "id": "SP001",
        "weight": 1,
        "goal": "Release metadata, queue size, and post-boundary exclusion count are exact.",
    },
    {
        "id": "SP002",
        "weight": 3,
        "goal": "Core board-review membership includes the six high-risk exact-match cases.",
    },
    {
        "id": "SP003",
        "weight": 2,
        "goal": "Top-three queue set captures the three strongest board-review cases.",
    },
    {
        "id": "SP004",
        "weight": 2,
        "goal": "Close-match fine-review cases are identified with correct confidence and label.",
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Shared-address manual-review case is identified with correct confidence and label.",
    },
    {
        "id": "SP006",
        "weight": 2,
        "goal": "Pre-boundary counts and most-recent dates are exact for core board-review cases.",
    },
    {
        "id": "SP007",
        "weight": 2,
        "goal": "Queue label-count summary is exact.",
    },
    {
        "id": "SP008",
        "weight": 2,
        "goal": "Full queue membership contains the expected 12 current license IDs.",
    },
]


CORE_BOARD = {
    "LIC-RV-2026-0061",
    "LIC-RV-2026-0056",
    "LIC-RV-2026-0055",
    "LIC-RV-2026-0089",
    "LIC-RV-2026-0096",
    "LIC-RV-2026-0063",
}
TOP_THREE = {"LIC-RV-2026-0061", "LIC-RV-2026-0056", "LIC-RV-2026-0055"}
CLOSE_FINE = {"LIC-RV-2026-0098", "LIC-RV-2026-0081"}
SHARED_CASE = "LIC-RV-2026-0053"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def as_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def queue(doc: dict[str, Any]) -> list[dict[str, Any]]:
    value = doc.get("queue")
    return value if isinstance(value, list) else []


def by_id(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in queue(doc):
        if isinstance(item, dict) and isinstance(item.get("license_id"), str):
            result[item["license_id"]] = item
    return result


def by_rank(doc: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for item in queue(doc):
        if not isinstance(item, dict):
            continue
        rank = to_int(item.get("rank"))
        if rank is not None and rank not in result:
            result[rank] = item
    return result


def ids(doc: dict[str, Any]) -> list[str]:
    return [
        item["license_id"] for item in queue(doc) if isinstance(item, dict) and isinstance(item.get("license_id"), str)
    ]


def top_ids(doc: dict[str, Any], n: int) -> set[str]:
    ranked = by_rank(doc)
    return {as_str(ranked.get(rank, {}).get("license_id")) for rank in range(1, n + 1)}


def summary(doc: dict[str, Any]) -> dict[str, Any]:
    value = doc.get("top_risk_summary")
    return value if isinstance(value, dict) else {}


def label_counts(doc: dict[str, Any]) -> dict[str, int | None]:
    summ = summary(doc)
    return {
        "board_review_count": to_int(summ.get("board_review_count")),
        "manual_fine_check_count": to_int(summ.get("manual_fine_check_count")),
        "manual_ALERT_check_count": to_int(summ.get("manual_ALERT_check_count")),
        "additional_record_check_count": to_int(summ.get("additional_record_check_count")),
    }


def metadata(doc: dict[str, Any]) -> dict[str, Any]:
    summ = summary(doc)
    return {
        "release_batch": as_str(summ.get("release_batch")),
        "release_boundary": as_str(summ.get("release_boundary")),
        "queue_size": to_int(summ.get("queue_size")),
        "excluded_post_boundary_count": to_int(doc.get("excluded_post_boundary_count")),
        "latest_pre_boundary_date": as_str(summ.get("latest_pre_boundary_date")),
    }


def row_core(doc: dict[str, Any], license_id: str) -> dict[str, Any]:
    row = by_id(doc).get(license_id, {})
    return {
        "facility_name": as_str(row.get("facility_name")),
        "match_confidence": as_str(row.get("match_confidence")),
        "violation_count_used": to_int(row.get("violation_count_used")),
        "most_recent_date_used": as_str(row.get("most_recent_date_used")),
        "next_step_label": as_str(row.get("next_step_label")),
    }


def check_point(point_id: str, pred: dict[str, Any], ans: dict[str, Any]) -> tuple[bool, str]:
    pred_ids = set(ids(pred))
    ans_ids = set(ids(ans))
    pred_by_id = by_id(pred)

    if point_id == "SP001":
        passed = metadata(pred) == metadata(ans)
        return passed, "metadata matches" if passed else "metadata differs"

    if point_id == "SP002":
        passed = CORE_BOARD.issubset(pred_ids) and all(
            as_str(pred_by_id[item].get("next_step_label")) == "board review"
            for item in CORE_BOARD
            if item in pred_by_id
        )
        return passed, "core board-review membership matches" if passed else "core board-review membership differs"

    if point_id == "SP003":
        passed = top_ids(pred, 3) == TOP_THREE
        return passed, "top-three set matches" if passed else "top-three set differs"

    if point_id == "SP004":
        passed = CLOSE_FINE.issubset(pred_ids) and all(
            row_core(pred, item)["match_confidence"] == row_core(ans, item)["match_confidence"]
            and row_core(pred, item)["next_step_label"] == row_core(ans, item)["next_step_label"]
            for item in CLOSE_FINE
        )
        return passed, "close fine-review cases match" if passed else "close fine-review cases differ"

    if point_id == "SP005":
        passed = SHARED_CASE in pred_ids and row_core(pred, SHARED_CASE) == row_core(ans, SHARED_CASE)
        return passed, "shared-address case matches" if passed else "shared-address case differs"

    if point_id == "SP006":
        passed = CORE_BOARD.issubset(pred_ids) and all(
            row_core(pred, item)["violation_count_used"] == row_core(ans, item)["violation_count_used"]
            and row_core(pred, item)["most_recent_date_used"] == row_core(ans, item)["most_recent_date_used"]
            for item in CORE_BOARD
        )
        return passed, "core counts and dates match" if passed else "core counts or dates differ"

    if point_id == "SP007":
        passed = label_counts(pred) == label_counts(ans)
        return passed, "label counts match" if passed else "label counts differ"

    if point_id == "SP008":
        passed = len(ids(pred)) == 12 and len(pred_ids) == 12 and pred_ids == ans_ids
        return passed, "full membership matches" if passed else "full membership differs"

    return False, "unknown scoring point"


def evaluate(pred: dict[str, Any], ans: dict[str, Any]) -> dict[str, Any]:
    total_weight = sum(int(point["weight"]) for point in POINTS)
    earned = 0
    results = []
    for point in POINTS:
        passed, message = check_point(str(point["id"]), pred, ans)
        weight = int(point["weight"])
        if passed:
            earned += weight
        results.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": weight,
                "passed": passed,
                "earned_weight": weight if passed else 0,
                "message": message,
            }
        )
    return {
        "score": round(earned / total_weight, 6),
        "earned_weight": earned,
        "total_weight": total_weight,
        "points": results,
    }


def main() -> int:
    if len(sys.argv) != 3:
        print(
            json.dumps(
                {"score": 0, "error": "usage: evaluator.py <prediction.json> <answer.json>", "points": []}, indent=2
            )
        )
        return 2
    try:
        pred = load_json(Path(sys.argv[1]))
        ans = load_json(Path(sys.argv[2]))
    except Exception as exc:
        print(json.dumps({"score": 0, "error": f"json_load_failed: {exc}", "points": []}, indent=2))
        return 1
    if not isinstance(pred, dict) or not isinstance(ans, dict):
        print(json.dumps({"score": 0, "error": "prediction and answer must be JSON objects", "points": []}, indent=2))
        return 1
    print(json.dumps(evaluate(pred, ans), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
