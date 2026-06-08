#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PREDICTION_PATH="${1:-${TASK_DIR}/output/answer.json}"

python3 - "$PREDICTION_PATH" <<'PY'
import json
import math
import sys
from pathlib import Path

prediction_path = Path(sys.argv[1])

expected = {
    "save_plan": [
        {
            "rank": 1,
            "account_id": "acct_bayside_bio",
            "risk_score": 55,
            "risk_level": "high",
            "primary_action": "renewal_save",
            "current_arr": 557629.32,
            "latest_nps": 52,
            "clean_ticket_count": 5,
            "overdue_balance": 0.0,
        },
        {
            "rank": 2,
            "account_id": "acct_valence",
            "risk_score": 45,
            "risk_level": "medium",
            "primary_action": "collections_followup",
            "current_arr": 545534.59,
            "latest_nps": 57,
            "clean_ticket_count": 7,
            "overdue_balance": 4858.69,
        },
        {
            "rank": 3,
            "account_id": "acct_peakstone",
            "risk_score": 40,
            "risk_level": "medium",
            "primary_action": "technical_recovery",
            "current_arr": 1308419.10,
            "latest_nps": 20,
            "clean_ticket_count": 15,
            "overdue_balance": 0.0,
        },
        {
            "rank": 4,
            "account_id": "acct_quartz_insure",
            "risk_score": 35,
            "risk_level": "medium",
            "primary_action": "technical_recovery",
            "current_arr": 1061984.61,
            "latest_nps": 47,
            "clean_ticket_count": 15,
            "overdue_balance": 0.0,
        },
        {
            "rank": 5,
            "account_id": "acct_brightharbor",
            "risk_score": 30,
            "risk_level": "medium",
            "primary_action": "nurture_monitor",
            "current_arr": 667197.16,
            "latest_nps": 58,
            "clean_ticket_count": 4,
            "overdue_balance": 0.0,
        },
        {
            "rank": 6,
            "account_id": "acct_apexia",
            "risk_score": 30,
            "risk_level": "medium",
            "primary_action": "nurture_monitor",
            "current_arr": 501966.25,
            "latest_nps": 63,
            "clean_ticket_count": 7,
            "overdue_balance": 0.0,
        },
    ],
    "portfolio_summary": {
        "accounts_reviewed": 10,
        "critical_or_high_count": 1,
        "arr_at_risk": 4642731.03,
        "collections_count": 1,
        "technical_recovery_count": 2,
        "executive_qbr_count": 0,
    },
    "quality_checks": {
        "current_revenue_policy_applied": True,
        "support_data_hygiene_applied": True,
        "sentiment_data_hygiene_applied": True,
    },
    "policy_codes": {
        "risk_model_code": "RS-6",
        "arr_source_code": "REV-4",
        "support_hygiene_code": "SUP-8",
        "action_priority_code": "ACT-5",
    },
}

checks = [
    ("ordered_top_6_account_ids", 3),
    ("risk_scores_and_levels", 3),
    ("primary_actions", 2),
    ("billing_arr_and_arr_at_risk", 2),
    ("clean_ticket_counts_and_latest_nps", 2),
    ("overdue_balances_and_collections_count", 2),
    ("recovery_and_qbr_summary_counts", 1),
    ("quality_checks", 1),
    ("retention_policy_code_core", 3),
    ("complete_policy_code_set", 3),
]

def num_equal(actual, expected_value, places=2):
    if not isinstance(actual, (int, float)) or isinstance(actual, bool):
        return False
    return round(float(actual), places) == round(float(expected_value), places)

def int_equal(actual, expected_value):
    return isinstance(actual, int) and not isinstance(actual, bool) and actual == expected_value

def rows_by_rank(payload):
    rows = payload.get("save_plan")
    if not isinstance(rows, list):
        return []
    return rows

try:
    with prediction_path.open(encoding="utf-8") as handle:
        pred = json.load(handle)
except Exception as exc:
    total = sum(weight for _, weight in checks)
    print(json.dumps({
        "score": 0.0,
        "earned_weight": 0,
        "total_weight": total,
        "error": f"Could not read prediction JSON: {exc}",
    }, sort_keys=True))
    sys.exit(0)

rows = rows_by_rank(pred)
summary = pred.get("portfolio_summary", {})
quality = pred.get("quality_checks", {})
earned = 0
details = {}

def award(name, passed):
    global earned
    weight = dict(checks)[name]
    details[name] = bool(passed)
    if passed:
        earned += weight

award(
    "ordered_top_6_account_ids",
    [row.get("account_id") for row in rows] == [row["account_id"] for row in expected["save_plan"]]
    and [row.get("rank") for row in rows] == [1, 2, 3, 4, 5, 6],
)

award(
    "risk_scores_and_levels",
    len(rows) == 6
    and all(
        row.get("risk_score") == exp["risk_score"]
        and row.get("risk_level") == exp["risk_level"]
        for row, exp in zip(rows, expected["save_plan"])
    ),
)

award(
    "primary_actions",
    len(rows) == 6
    and all(row.get("primary_action") == exp["primary_action"] for row, exp in zip(rows, expected["save_plan"])),
)

award(
    "billing_arr_and_arr_at_risk",
    len(rows) == 6
    and all(num_equal(row.get("current_arr"), exp["current_arr"]) for row, exp in zip(rows, expected["save_plan"]))
    and num_equal(summary.get("arr_at_risk"), expected["portfolio_summary"]["arr_at_risk"]),
)

award(
    "clean_ticket_counts_and_latest_nps",
    len(rows) == 6
    and all(
        row.get("clean_ticket_count") == exp["clean_ticket_count"]
        and row.get("latest_nps") == exp["latest_nps"]
        for row, exp in zip(rows, expected["save_plan"])
    ),
)

award(
    "overdue_balances_and_collections_count",
    len(rows) == 6
    and all(num_equal(row.get("overdue_balance"), exp["overdue_balance"]) for row, exp in zip(rows, expected["save_plan"]))
    and summary.get("collections_count") == expected["portfolio_summary"]["collections_count"],
)

award(
    "recovery_and_qbr_summary_counts",
    summary.get("technical_recovery_count") == expected["portfolio_summary"]["technical_recovery_count"]
    and summary.get("executive_qbr_count") == expected["portfolio_summary"]["executive_qbr_count"],
)

award("quality_checks", quality == expected["quality_checks"])
policy_codes = pred.get("policy_codes", {})
award(
    "retention_policy_code_core",
    policy_codes.get("risk_model_code") == expected["policy_codes"]["risk_model_code"]
    and policy_codes.get("action_priority_code") == expected["policy_codes"]["action_priority_code"]
    and policy_codes.get("arr_source_code") == expected["policy_codes"]["arr_source_code"]
    and policy_codes.get("support_hygiene_code") == expected["policy_codes"]["support_hygiene_code"],
)
award("complete_policy_code_set", policy_codes == expected["policy_codes"])

total = sum(weight for _, weight in checks)
score = earned / total if total else 0.0
print(json.dumps({
    "score": round(score, 6),
    "earned_weight": earned,
    "total_weight": total,
    "details": details,
}, sort_keys=True))
PY
