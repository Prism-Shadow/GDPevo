#!/usr/bin/env python3
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
EXPECTED_PATH = SCRIPT_DIR.parent / "output" / "answer.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def sorted_strings(value):
    if not isinstance(value, list):
        return value
    return sorted(value)


def normalize_buckets(value):
    if not isinstance(value, dict):
        return value
    keys = ["0-7", "8-14", "15-30", "31+"]
    normalized = {}
    for key in keys:
        try:
            normalized[key] = int(value.get(key, 0))
        except (TypeError, ValueError):
            normalized[key] = value.get(key)
    return normalized


def normalize_hotspots(value, id_key):
    if not isinstance(value, list):
        return value
    normalized = []
    for row in value:
        if not isinstance(row, dict):
            return value
        normalized.append(
            {
                id_key: row.get(id_key),
                "overdue_count": row.get("overdue_count"),
                "max_age_days": row.get("max_age_days"),
            }
        )
    return normalized


def normalize_duplicate_clusters(value):
    if not isinstance(value, list):
        return value
    rows = []
    for row in value:
        if not isinstance(row, dict):
            return value
        rows.append(
            {
                "cluster_id": row.get("cluster_id"),
                "representative_work_item_id": row.get("representative_work_item_id"),
                "member_ids": sorted_strings(row.get("member_ids")),
            }
        )
    return sorted(rows, key=lambda row: row.get("cluster_id") or "")


def point(point_id, weight, goal, expected, actual, normalizer=lambda value: value):
    return {
        "id": point_id,
        "weight": weight,
        "passed": normalizer(actual) == normalizer(expected),
        "goal": goal,
    }


def main():
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else EXPECTED_PATH
    expected = load_json(EXPECTED_PATH)
    try:
        actual = load_json(prediction_path)
    except Exception:
        actual = {}

    points = [
        point(
            "SP001",
            3,
            "Included effective Mobile Platform Reliability/Security population",
            expected.get("included_work_item_ids"),
            actual.get("included_work_item_ids"),
            sorted_strings,
        ),
        point(
            "SP002",
            3,
            "Overdue work item ID set",
            expected.get("overdue_work_item_ids"),
            actual.get("overdue_work_item_ids"),
            sorted_strings,
        ),
        point(
            "SP003",
            2,
            "Aging bucket counts",
            expected.get("aging_bucket_counts"),
            actual.get("aging_bucket_counts"),
            normalize_buckets,
        ),
        point(
            "SP004",
            2,
            "Ranked owner and team overdue hotspots",
            {
                "owner_hotspots": expected.get("owner_hotspots"),
                "team_hotspots": expected.get("team_hotspots"),
            },
            {
                "owner_hotspots": actual.get("owner_hotspots"),
                "team_hotspots": actual.get("team_hotspots"),
            },
            lambda value: {
                "owner_hotspots": normalize_hotspots(value.get("owner_hotspots"), "owner_id")
                if isinstance(value, dict)
                else value,
                "team_hotspots": normalize_hotspots(value.get("team_hotspots"), "team_id")
                if isinstance(value, dict)
                else value,
            },
        ),
        point(
            "SP005",
            2,
            "Duplicate cluster representatives and included members",
            expected.get("duplicate_clusters"),
            actual.get("duplicate_clusters"),
            normalize_duplicate_clusters,
        ),
        point(
            "SP006",
            1,
            "Escaped S1/S2 included item count",
            expected.get("escaped_severity_count"),
            actual.get("escaped_severity_count"),
        ),
        point(
            "SP007",
            2,
            "Overdue missing-owner work item IDs",
            expected.get("missing_owner_work_item_ids"),
            actual.get("missing_owner_work_item_ids"),
            sorted_strings,
        ),
    ]

    earned = sum(item["weight"] for item in points if item["passed"])
    total = sum(item["weight"] for item in points)
    result = {
        "score": earned / total if total else 0.0,
        "max_score": 1.0,
        "points": points,
    }
    print(json.dumps(result, indent=2, sort_keys=False))


if __name__ == "__main__":
    main()
