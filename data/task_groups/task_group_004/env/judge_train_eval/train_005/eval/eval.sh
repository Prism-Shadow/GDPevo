#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PREDICTION_PATH="${1:-${TASK_DIR}/output/answer.json}"

python3 - "$PREDICTION_PATH" <<'PY'
import json
import math
import sys

prediction_path = sys.argv[1]

with open(prediction_path, "r", encoding="utf-8") as f:
    pred = json.load(f)

expected_board = [
    {
        "rank": 1,
        "account_id": "acct_peakstone",
        "risk_level": "critical",
        "primary_action": "technical_recovery",
        "current_arr": 1260762.32,
        "expansion_pipeline": 0.0,
        "overdue_balance": 0.0,
        "next_touch_due_date": "2026-07-18",
        "reason_codes": ["renewal_window", "nps_drop", "sla_degradation", "usage_decline"],
    },
    {
        "rank": 2,
        "account_id": "acct_lumen_rail",
        "risk_level": "high",
        "primary_action": "collections_followup",
        "current_arr": 1147391.72,
        "expansion_pipeline": 0.0,
        "overdue_balance": 9183.05,
        "next_touch_due_date": "2026-07-15",
        "reason_codes": ["overdue_receivable", "nps_drop", "sla_degradation"],
    },
    {
        "rank": 3,
        "account_id": "acct_quartz_insure",
        "risk_level": "high",
        "primary_action": "technical_recovery",
        "current_arr": 1080112.29,
        "expansion_pipeline": 793202.42,
        "overdue_balance": 0.0,
        "next_touch_due_date": "2026-07-18",
        "reason_codes": ["nps_drop", "sla_degradation", "usage_decline", "expansion_offset"],
    },
    {
        "rank": 4,
        "account_id": "acct_metrobyte",
        "risk_level": "medium",
        "primary_action": "renewal_save",
        "current_arr": 871896.76,
        "expansion_pipeline": 0.0,
        "overdue_balance": 0.0,
        "next_touch_due_date": "2026-07-22",
        "reason_codes": ["renewal_window", "sla_degradation"],
    },
    {
        "rank": 5,
        "account_id": "acct_solstice",
        "risk_level": "medium",
        "primary_action": "technical_recovery",
        "current_arr": 849883.74,
        "expansion_pipeline": 0.0,
        "overdue_balance": 0.0,
        "next_touch_due_date": "2026-07-18",
        "reason_codes": ["renewal_window", "sla_degradation"],
    },
    {
        "rank": 6,
        "account_id": "acct_valence",
        "risk_level": "medium",
        "primary_action": "collections_followup",
        "current_arr": 526180.63,
        "expansion_pipeline": 64483.34,
        "overdue_balance": 10044.4,
        "next_touch_due_date": "2026-07-15",
        "reason_codes": ["overdue_receivable", "sla_degradation", "expansion_offset"],
    },
    {
        "rank": 7,
        "account_id": "acct_bayside_bio",
        "risk_level": "low",
        "primary_action": "no_action",
        "current_arr": 564466.38,
        "expansion_pipeline": 118804.9,
        "overdue_balance": 0.0,
        "next_touch_due_date": None,
        "reason_codes": ["sla_degradation", "expansion_offset"],
    },
    {
        "rank": 8,
        "account_id": "acct_apexia",
        "risk_level": "low",
        "primary_action": "no_action",
        "current_arr": 511314.88,
        "expansion_pipeline": 0.0,
        "overdue_balance": 0.0,
        "next_touch_due_date": None,
        "reason_codes": ["nps_drop"],
    },
]

expected_summary = {
    "strategic_accounts": 3,
    "enterprise_accounts": 5,
    "arr_at_risk": 5736227.46,
    "open_expansion_pipeline": 976490.66,
    "net_revenue_exposure": 4759736.8,
}

expected_calendar = {
    "collections_followup": "2026-07-15",
    "technical_recovery": "2026-07-18",
    "renewal_save": "2026-07-22",
    "executive_qbr": "2026-07-29",
    "nurture_monitor": "2026-08-05",
}

expected_policy_codes = {
    "risk_model_code": "RS-6",
    "arr_source_code": "REV-4",
    "support_hygiene_code": "SUP-8",
    "action_priority_code": "ACT-5",
    "board_sort_code": "BORD-4",
    "exposure_formula_code": "EXP-6",
    "calendar_policy_code": "CAL-5",
}

checks = []


def close(a, b):
    return isinstance(a, (int, float)) and math.isclose(float(a), float(b), abs_tol=0.005)


def board_by_id(answer):
    rows = answer.get("action_board", [])
    return {row.get("account_id"): row for row in rows if isinstance(row, dict)}


def reason_set(row):
    return set(row.get("reason_codes", [])) if isinstance(row, dict) else set()


def add_check(name, weight, passed):
    checks.append({"name": name, "weight": weight, "passed": bool(passed)})


pred_board = pred.get("action_board", [])
pred_by_id = board_by_id(pred)

add_check(
    "board_account_order",
    3,
    [row.get("account_id") for row in pred_board] == [row["account_id"] for row in expected_board]
    and [row.get("rank") for row in pred_board] == [row["rank"] for row in expected_board],
)

add_check(
    "risk_levels_and_primary_actions",
    3,
    all(
        pred_by_id.get(exp["account_id"], {}).get("risk_level") == exp["risk_level"]
        and pred_by_id.get(exp["account_id"], {}).get("primary_action") == exp["primary_action"]
        for exp in expected_board
    ),
)

add_check(
    "arr_and_overdue_balances",
    2,
    all(
        close(pred_by_id.get(exp["account_id"], {}).get("current_arr"), exp["current_arr"])
        and close(pred_by_id.get(exp["account_id"], {}).get("overdue_balance"), exp["overdue_balance"])
        for exp in expected_board
    ),
)

add_check(
    "expansion_pipeline",
    2,
    all(
        close(pred_by_id.get(exp["account_id"], {}).get("expansion_pipeline"), exp["expansion_pipeline"])
        for exp in expected_board
    ),
)

add_check(
    "next_touch_due_dates",
    2,
    all(
        pred_by_id.get(exp["account_id"], {}).get("next_touch_due_date") == exp["next_touch_due_date"]
        for exp in expected_board
    )
    and pred.get("followup_calendar") == expected_calendar,
)

add_check(
    "reason_code_sets",
    2,
    all(reason_set(pred_by_id.get(exp["account_id"], {})) == set(exp["reason_codes"]) for exp in expected_board),
)

summary = pred.get("segment_summary", {})
add_check(
    "segment_counts_and_arr_at_risk",
    2,
    summary.get("strategic_accounts") == expected_summary["strategic_accounts"]
    and summary.get("enterprise_accounts") == expected_summary["enterprise_accounts"]
    and close(summary.get("arr_at_risk"), expected_summary["arr_at_risk"]),
)

add_check(
    "open_expansion_and_net_exposure",
    2,
    close(summary.get("open_expansion_pipeline"), expected_summary["open_expansion_pipeline"])
    and close(summary.get("net_revenue_exposure"), expected_summary["net_revenue_exposure"]),
)

add_check("policy_codes", 3, pred.get("policy_codes", {}) == expected_policy_codes)

earned = sum(item["weight"] for item in checks if item["passed"])
total = sum(item["weight"] for item in checks)
score = earned / total if total else 0.0

print(json.dumps({
    "score": round(score, 6),
    "earned_weight": earned,
    "total_weight": total,
    "checks": checks,
}, indent=2, sort_keys=True))
PY
