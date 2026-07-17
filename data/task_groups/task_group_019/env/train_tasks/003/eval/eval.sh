#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -eq 0 ]]; then
  set -- "$SCRIPT_DIR/../output/answer.json"
elif [[ $# -ne 1 ]]; then
  python3 - <<'PY'
import json
print(json.dumps({
    "score": 0.0,
    "error": "usage: eval.sh <prediction.json>",
    "points": []
}, indent=2))
PY
  exit 0
fi

python3 - "$1" <<'PY'
import json
import sys
from pathlib import Path

prediction_path = Path(sys.argv[1])

EXPECTED_QUEUE = [
    {
        "rank": 1,
        "license_id": "LIC-RV-2026-0004",
        "facility_name": "Drift Grill 004",
        "match_confidence": "exact",
        "violation_count_used": 5,
        "most_recent_date_used": "2025-08-23",
        "next_step_label": "board review",
    },
    {
        "rank": 2,
        "license_id": "LIC-RV-2026-0045",
        "facility_name": "Urban Room 045",
        "match_confidence": "exact",
        "violation_count_used": 3,
        "most_recent_date_used": "2026-02-04",
        "next_step_label": "board review",
    },
    {
        "rank": 3,
        "license_id": "LIC-RV-2026-0010",
        "facility_name": "Depot Grill 010",
        "match_confidence": "exact",
        "violation_count_used": 4,
        "most_recent_date_used": "2026-01-25",
        "next_step_label": "board review",
    },
    {
        "rank": 4,
        "license_id": "LIC-RV-2026-0043",
        "facility_name": "Pier Room 043",
        "match_confidence": "close",
        "violation_count_used": 2,
        "most_recent_date_used": "2026-02-27",
        "next_step_label": "board review",
    },
    {
        "rank": 5,
        "license_id": "LIC-RV-2026-0035",
        "facility_name": "Vista Cafe 035",
        "match_confidence": "exact",
        "violation_count_used": 3,
        "most_recent_date_used": "2026-04-09",
        "next_step_label": "manual fine check",
    },
    {
        "rank": 6,
        "license_id": "LIC-RV-2026-0042",
        "facility_name": "Hearth Room 042",
        "match_confidence": "exact",
        "violation_count_used": 4,
        "most_recent_date_used": "2025-10-28",
        "next_step_label": "board review",
    },
    {
        "rank": 7,
        "license_id": "LIC-RV-2026-0021",
        "facility_name": "Urban Market 021",
        "match_confidence": "close",
        "violation_count_used": 3,
        "most_recent_date_used": "2025-03-16",
        "next_step_label": "manual fine check",
    },
    {
        "rank": 8,
        "license_id": "LIC-RV-2026-0025",
        "facility_name": "Maple Cafe 025",
        "match_confidence": "exact",
        "violation_count_used": 3,
        "most_recent_date_used": "2025-02-10",
        "next_step_label": "manual ALERT check",
    },
    {
        "rank": 9,
        "license_id": "LIC-RV-2026-0032",
        "facility_name": "Crescent Cafe 032",
        "match_confidence": "exact",
        "violation_count_used": 3,
        "most_recent_date_used": "2026-01-16",
        "next_step_label": "manual ALERT check",
    },
    {
        "rank": 10,
        "license_id": "LIC-RV-2026-0019",
        "facility_name": "Pier Market 019",
        "match_confidence": "exact",
        "violation_count_used": 3,
        "most_recent_date_used": "2026-02-18",
        "next_step_label": "board review",
    },
]

EXPECTED_FLAGS = {
    "release_batch": "RV-2026-SPRING",
    "release_boundary": "2026-04-15",
    "queue_size": 10,
    "excluded_post_boundary_count": 10,
    "post_boundary_exclusion_applied": True,
    "shared_address_records_not_spread": True,
}

POINTS = [
    ("queue_membership", 2, "Queue contains exactly the expected 10 license IDs."),
    ("top_three_order", 2, "Ranks 1-3 are in the expected order."),
    ("ranks_four_to_ten_order", 2, "Ranks 4-10 are in the expected order."),
    ("match_confidence_values", 1, "All queue match_confidence values are correct."),
    ("violation_counts", 2, "All violation_count_used values are correct."),
    ("most_recent_dates", 1, "All most_recent_date_used values are correct."),
    ("next_step_labels", 2, "All next_step_label values are correct."),
    ("method_flags", 2, "Release batch, boundary, queue size, and boundary-exclusion flags are correct."),
]


def to_int(value):
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


def as_str(value):
    return value if isinstance(value, str) else None


def load_prediction(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as exc:
        return None, str(exc)


prediction, error = load_prediction(prediction_path)
if error is not None:
    total_weight = sum(weight for _, weight, _ in POINTS)
    print(json.dumps({
        "score": 0.0,
        "error": f"invalid_json: {error}",
        "points": [
            {
                "id": point_id,
                "weight": weight,
                "passed": False,
                "score": 0.0,
                "description": description,
            }
            for point_id, weight, description in POINTS
        ],
    }, indent=2, sort_keys=True))
    sys.exit(0)

queue = prediction.get("queue") if isinstance(prediction, dict) else None
flags = prediction.get("method_flags") if isinstance(prediction, dict) else None
if not isinstance(queue, list):
    queue = []
if not isinstance(flags, dict):
    flags = {}

by_rank = {}
for item in queue:
    if not isinstance(item, dict):
        continue
    rank = to_int(item.get("rank"))
    if rank is not None and rank not in by_rank:
        by_rank[rank] = item

expected_ids = [item["license_id"] for item in EXPECTED_QUEUE]
expected_by_rank = {item["rank"]: item for item in EXPECTED_QUEUE}

def ranked_ids(start, end):
    return [as_str(by_rank.get(rank, {}).get("license_id")) for rank in range(start, end + 1)]

checks = {}
submitted_ids = [as_str(item.get("license_id")) for item in queue if isinstance(item, dict)]
checks["queue_membership"] = len(queue) == 10 and sorted(submitted_ids) == sorted(expected_ids)
checks["top_three_order"] = ranked_ids(1, 3) == expected_ids[:3]
checks["ranks_four_to_ten_order"] = ranked_ids(4, 10) == expected_ids[3:]

checks["match_confidence_values"] = all(
    as_str(by_rank.get(rank, {}).get("match_confidence")) == expected_by_rank[rank]["match_confidence"]
    for rank in range(1, 11)
)
checks["violation_counts"] = all(
    to_int(by_rank.get(rank, {}).get("violation_count_used")) == expected_by_rank[rank]["violation_count_used"]
    for rank in range(1, 11)
)
checks["most_recent_dates"] = all(
    as_str(by_rank.get(rank, {}).get("most_recent_date_used")) == expected_by_rank[rank]["most_recent_date_used"]
    for rank in range(1, 11)
)
checks["next_step_labels"] = all(
    as_str(by_rank.get(rank, {}).get("next_step_label")) == expected_by_rank[rank]["next_step_label"]
    for rank in range(1, 11)
)
checks["method_flags"] = (
    as_str(flags.get("release_batch")) == EXPECTED_FLAGS["release_batch"]
    and as_str(flags.get("release_boundary")) == EXPECTED_FLAGS["release_boundary"]
    and to_int(flags.get("queue_size")) == EXPECTED_FLAGS["queue_size"]
    and to_int(flags.get("excluded_post_boundary_count")) == EXPECTED_FLAGS["excluded_post_boundary_count"]
    and flags.get("post_boundary_exclusion_applied") is True
    and flags.get("shared_address_records_not_spread") is True
)

total_weight = sum(weight for _, weight, _ in POINTS)
earned = sum(weight for point_id, weight, _ in POINTS if checks.get(point_id, False))
result_points = [
    {
        "id": point_id,
        "weight": weight,
        "passed": bool(checks.get(point_id, False)),
        "score": round(weight / total_weight if checks.get(point_id, False) else 0.0, 6),
        "description": description,
    }
    for point_id, weight, description in POINTS
]

print(json.dumps({
    "score": round(earned / total_weight, 6),
    "points": result_points,
}, indent=2, sort_keys=True))
PY
