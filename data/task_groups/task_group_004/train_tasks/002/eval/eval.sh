#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPECTED_PATH="${SCRIPT_DIR}/../output/answer.json"
PREDICTION_PATH="${1:-$EXPECTED_PATH}"

python3 - "$EXPECTED_PATH" "$PREDICTION_PATH" <<'PY'
import json
import sys

expected_path, prediction_path = sys.argv[1], sys.argv[2]

with open(expected_path, "r", encoding="utf-8") as handle:
    expected = json.load(handle)

try:
    with open(prediction_path, "r", encoding="utf-8") as handle:
        prediction = json.load(handle)
except Exception as exc:
    print(json.dumps({
        "score": 0.0,
        "earned_weight": 0,
        "total_weight": 16,
        "error": f"could_not_load_prediction: {exc}"
    }, sort_keys=True))
    sys.exit(0)

def get(obj, path, default=None):
    cur = obj
    for part in path:
        if isinstance(part, int):
            if not isinstance(cur, list) or part >= len(cur):
                return default
            cur = cur[part]
        else:
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
    return cur

def rows_for(fields):
    return [
        {field: row.get(field) for field in fields}
        for row in prediction.get("qbr_metrics", [])
        if isinstance(row, dict)
    ]

def expected_rows_for(fields):
    return [
        {field: row.get(field) for field in fields}
        for row in expected["qbr_metrics"]
    ]

checks = [
    (
        "monthly_revenue",
        2,
        rows_for(["month", "revenue"]) == expected_rows_for(["month", "revenue"]),
    ),
    (
        "clean_support_ticket_counts",
        2,
        rows_for(["month", "support_tickets"]) == expected_rows_for(["month", "support_tickets"]),
    ),
    (
        "monthly_sla_and_nps",
        3,
        rows_for(["month", "sla_compliance_pct", "nps_score"])
        == expected_rows_for(["month", "sla_compliance_pct", "nps_score"]),
    ),
    (
        "average_and_peak_revenue_highlights",
        2,
        get(prediction, ["highlights", "average_revenue"]) == expected["highlights"]["average_revenue"]
        and get(prediction, ["highlights", "peak_revenue_month"]) == expected["highlights"]["peak_revenue_month"]
        and get(prediction, ["highlights", "peak_revenue"]) == expected["highlights"]["peak_revenue"],
    ),
    (
        "max_sla_peak_nps_and_ticket_trend",
        2,
        get(prediction, ["highlights", "max_sla_month"]) == expected["highlights"]["max_sla_month"]
        and get(prediction, ["highlights", "max_sla_pct"]) == expected["highlights"]["max_sla_pct"]
        and get(prediction, ["highlights", "peak_nps_month"]) == expected["highlights"]["peak_nps_month"]
        and get(prediction, ["highlights", "peak_nps_score"]) == expected["highlights"]["peak_nps_score"]
        and get(prediction, ["highlights", "ticket_trend"]) == expected["highlights"]["ticket_trend"],
    ),
    (
        "metric_source_enums",
        2,
        prediction.get("metric_sources") == expected["metric_sources"],
    ),
    (
        "review_plan",
        2,
        prediction.get("review_plan") == expected["review_plan"],
    ),
    (
        "ordered_agenda_topics",
        1,
        prediction.get("agenda_topics") == expected["agenda_topics"],
    ),
]

total_weight = sum(weight for _, weight, _ in checks)
earned_weight = sum(weight for _, weight, passed in checks if passed)
result = {
    "score": round(earned_weight / total_weight, 6),
    "earned_weight": earned_weight,
    "total_weight": total_weight,
    "checks": [
        {"name": name, "weight": weight, "passed": bool(passed)}
        for name, weight, passed in checks
    ],
}
print(json.dumps(result, indent=2, sort_keys=True))
PY
