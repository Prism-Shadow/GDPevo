#!/usr/bin/env python3
"""Evaluator for train_005 Edge Services SLA aging."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PATH = ROOT / "output" / "answer.json"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sorted_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value)


def normalize_buckets(value: Any) -> dict[str, int]:
    if not isinstance(value, list):
        return {}
    normalized: dict[str, int] = {}
    for row in value:
        if isinstance(row, dict) and "bucket" in row and "count" in row:
            normalized[str(row["bucket"])] = int(row["count"])
    return normalized


def normalize_hotspots(value: Any, id_key: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for row in value:
        if not isinstance(row, dict):
            continue
        try:
            rows.append(
                {
                    id_key: str(row[id_key]),
                    "overdue_count": int(row["overdue_count"]),
                    "max_age_days": int(row["max_age_days"]),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return rows


def normalize_duplicate_clusters(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for row in value:
        if not isinstance(row, dict):
            continue
        try:
            rows.append(
                {
                    "cluster_id": str(row["cluster_id"]),
                    "representative_work_item_id": str(row["representative_work_item_id"]),
                    "member_ids": sorted_strings(row["member_ids"]),
                }
            )
        except KeyError:
            continue
    return sorted(rows, key=lambda row: row["cluster_id"])


def int_value(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def point(point_id: str, weight: int, passed: bool, goal: str) -> dict[str, Any]:
    return {"id": point_id, "weight": weight, "passed": bool(passed), "goal": goal}


def evaluate(prediction: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    points = [
        point(
            "SP001",
            3,
            sorted_strings(prediction.get("included_work_item_ids"))
            == sorted_strings(expected.get("included_work_item_ids")),
            "Included effective reliability/security SLA population",
        ),
        point(
            "SP002",
            3,
            sorted_strings(prediction.get("overdue_work_item_ids"))
            == sorted_strings(expected.get("overdue_work_item_ids")),
            "Overdue work item ID set",
        ),
        point(
            "SP003",
            2,
            normalize_buckets(prediction.get("aging_buckets"))
            == normalize_buckets(expected.get("aging_buckets")),
            "Aging bucket counts",
        ),
        point(
            "SP004",
            2,
            normalize_hotspots(prediction.get("owner_hotspots"), "owner_id")
            == normalize_hotspots(expected.get("owner_hotspots"), "owner_id")
            and normalize_hotspots(prediction.get("team_hotspots"), "team_id")
            == normalize_hotspots(expected.get("team_hotspots"), "team_id"),
            "Owner and team hotspot rankings",
        ),
        point(
            "SP005",
            2,
            normalize_duplicate_clusters(prediction.get("duplicate_cluster_representatives"))
            == normalize_duplicate_clusters(expected.get("duplicate_cluster_representatives")),
            "Duplicate cluster representatives and included members",
        ),
        point(
            "SP006",
            1,
            int_value(prediction.get("escaped_severity_count"))
            == int_value(expected.get("escaped_severity_count")),
            "Escaped S1/S2 included item count",
        ),
        point(
            "SP007",
            1,
            sorted_strings(prediction.get("missing_owner_work_item_ids"))
            == sorted_strings(expected.get("missing_owner_work_item_ids")),
            "Overdue missing-owner triage set",
        ),
    ]
    total = sum(row["weight"] for row in points)
    earned = sum(row["weight"] for row in points if row["passed"])
    return {
        "score": earned / total if total else 0.0,
        "max_score": 1.0,
        "points": points,
    }


def main() -> int:
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else EXPECTED_PATH
    try:
        prediction = load_json(prediction_path)
        expected = load_json(EXPECTED_PATH)
        result = evaluate(prediction, expected)
    except Exception as exc:  # Keep evaluator failures machine-readable.
        result = {
            "score": 0.0,
            "max_score": 1.0,
            "points": [
                {
                    "id": "EVAL_ERROR",
                    "weight": 1,
                    "passed": False,
                    "goal": f"Evaluator could not parse or score prediction: {exc}",
                }
            ],
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
