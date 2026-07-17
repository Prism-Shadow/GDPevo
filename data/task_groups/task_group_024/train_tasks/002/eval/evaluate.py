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
        return None
    return sorted(str(item) for item in value)


def int_value(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def bucket_counts(value):
    if not isinstance(value, dict):
        return None
    buckets = ["0-7", "8-14", "15-30", "31+"]
    return {bucket: int_value(value.get(bucket)) for bucket in buckets}


def hotspot_rows(value, id_key):
    if not isinstance(value, list):
        return None
    rows = []
    for row in value:
        if not isinstance(row, dict):
            return None
        rows.append(
            {
                id_key: row.get(id_key),
                "overdue_count": int_value(row.get("overdue_count")),
                "max_age_days": int_value(row.get("max_age_days")),
            }
        )
    return rows


def duplicate_rows(value):
    if not isinstance(value, list):
        return None
    rows = []
    for row in value:
        if not isinstance(row, dict):
            return None
        rows.append(
            {
                "cluster_id": row.get("cluster_id"),
                "representative_work_item_id": row.get("representative_work_item_id"),
                "member_ids": sorted_strings(row.get("member_ids")),
            }
        )
    return sorted(rows, key=lambda row: str(row.get("cluster_id")))


def point(point_id, weight, passed, goal):
    return {
        "id": point_id,
        "weight": weight,
        "passed": bool(passed),
        "goal": goal,
    }


def score_prediction(expected, prediction):
    if not isinstance(prediction, dict):
        prediction = {}

    points = []

    points.append(
        point(
            "SP001",
            3,
            prediction.get("product") == expected.get("product")
            and prediction.get("as_of_date") == expected.get("as_of_date")
            and int_value(prediction.get("recent_closed_window_days"))
            == expected.get("recent_closed_window_days")
            and int_value(prediction.get("included_count")) == expected.get("included_count")
            and sorted_strings(prediction.get("included_work_item_ids"))
            == sorted_strings(expected.get("included_work_item_ids")),
            "included effective reliability/security population",
        )
    )

    points.append(
        point(
            "SP002",
            3,
            int_value(prediction.get("overdue_count")) == expected.get("overdue_count")
            and sorted_strings(prediction.get("overdue_work_item_ids"))
            == sorted_strings(expected.get("overdue_work_item_ids")),
            "overdue work item ID set",
        )
    )

    points.append(
        point(
            "SP003",
            2,
            bucket_counts(prediction.get("aging_bucket_counts"))
            == bucket_counts(expected.get("aging_bucket_counts")),
            "aging bucket counts",
        )
    )

    points.append(
        point(
            "SP004",
            2,
            hotspot_rows(prediction.get("owner_hotspots"), "owner_id")
            == hotspot_rows(expected.get("owner_hotspots"), "owner_id")
            and hotspot_rows(prediction.get("team_hotspots"), "team_id")
            == hotspot_rows(expected.get("team_hotspots"), "team_id"),
            "owner and team hotspot rankings",
        )
    )

    points.append(
        point(
            "SP005",
            2,
            duplicate_rows(prediction.get("duplicate_clusters"))
            == duplicate_rows(expected.get("duplicate_clusters")),
            "duplicate cluster representatives and members",
        )
    )

    points.append(
        point(
            "SP006",
            1,
            int_value(prediction.get("escaped_severity_count"))
            == expected.get("escaped_severity_count"),
            "escaped S1/S2 included item count",
        )
    )

    points.append(
        point(
            "SP007",
            1,
            sorted_strings(prediction.get("missing_owner_work_item_ids"))
            == sorted_strings(expected.get("missing_owner_work_item_ids")),
            "missing-owner overdue triage set",
        )
    )

    total_weight = sum(row["weight"] for row in points)
    earned = sum(row["weight"] for row in points if row["passed"])
    return {
        "score": earned / total_weight if total_weight else 0.0,
        "max_score": 1.0,
        "points": points,
    }


def main():
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else EXPECTED_PATH
    expected = load_json(EXPECTED_PATH)
    try:
        prediction = load_json(prediction_path)
    except Exception as exc:
        result = {
            "score": 0.0,
            "max_score": 1.0,
            "points": [
                point("SP000", 1, False, f"prediction JSON could not be loaded: {exc}")
            ],
        }
        print(json.dumps(result, indent=2))
        return

    result = score_prediction(expected, prediction)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
