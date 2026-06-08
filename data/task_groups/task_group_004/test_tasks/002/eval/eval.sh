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
        "error": f"could_not_load_prediction: {exc}",
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


def monthly_rows(payload, fields):
    rows = get(payload, ["qbr_packet", "monthly_metrics"], [])
    if not isinstance(rows, list):
        return []
    return [
        {field: row.get(field) for field in fields}
        for row in rows
        if isinstance(row, dict)
    ]


expected_months = monthly_rows(expected, ["month"])
checks = [
    (
        "monthly_revenue_values",
        2,
        monthly_rows(prediction, ["month", "revenue"])
        == monthly_rows(expected, ["month", "revenue"]),
    ),
    (
        "clean_support_ticket_counts",
        2,
        monthly_rows(prediction, ["month", "support_tickets"])
        == monthly_rows(expected, ["month", "support_tickets"]),
    ),
    (
        "monthly_sla_and_nps_values",
        3,
        monthly_rows(prediction, ["month", "sla_compliance_pct", "nps_score"])
        == monthly_rows(expected, ["month", "sla_compliance_pct", "nps_score"]),
    ),
    (
        "qbr_highlights",
        2,
        get(prediction, ["qbr_packet", "highlights"])
        == get(expected, ["qbr_packet", "highlights"]),
    ),
    (
        "metric_source_mapping",
        2,
        prediction.get("metric_sources") == expected["metric_sources"],
    ),
    (
        "review_route",
        2,
        prediction.get("review_route") == expected["review_route"],
    ),
    (
        "client_meeting_agenda_and_theme",
        2,
        prediction.get("client_meeting") == expected["client_meeting"],
    ),
    (
        "account_quarter_and_month_order",
        1,
        get(prediction, ["qbr_packet", "account_id"]) == "acct_lumen_rail"
        and get(prediction, ["qbr_packet", "quarter"]) == "2026-Q3"
        and monthly_rows(prediction, ["month"]) == expected_months,
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
