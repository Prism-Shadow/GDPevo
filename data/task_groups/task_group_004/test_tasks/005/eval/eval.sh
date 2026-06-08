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

expected_watchlist = [
    {
        "rank": 1,
        "account_id": "acct_northstar_finance",
        "risk_score": 75,
        "risk_level": "critical",
        "primary_action": "collections_followup",
        "current_arr": 1419678.82,
        "overdue_balance": 8498.32,
        "open_expansion_pipeline": 436702.37,
        "net_revenue_exposure": 991474.77,
        "next_touch_due_date": "2026-10-15",
        "reason_codes": [
            "overdue_receivable",
            "nps_drop",
            "sla_degradation",
            "usage_decline",
            "low_tenure_high_churn",
            "expansion_offset",
        ],
    },
    {
        "rank": 2,
        "account_id": "acct_tandemworks",
        "risk_score": 70,
        "risk_level": "critical",
        "primary_action": "collections_followup",
        "current_arr": 91271.68,
        "overdue_balance": 784.37,
        "open_expansion_pipeline": 0.0,
        "net_revenue_exposure": 92056.05,
        "next_touch_due_date": "2026-10-15",
        "reason_codes": [
            "overdue_receivable",
            "nps_drop",
            "sla_degradation",
            "usage_decline",
            "low_tenure_high_churn",
        ],
    },
    {
        "rank": 3,
        "account_id": "acct_bayside_bio",
        "risk_score": 55,
        "risk_level": "high",
        "primary_action": "renewal_save",
        "current_arr": 557629.32,
        "overdue_balance": 0.0,
        "open_expansion_pipeline": 64001.27,
        "net_revenue_exposure": 493628.05,
        "next_touch_due_date": "2026-10-22",
        "reason_codes": [
            "renewal_window",
            "nps_drop",
            "sla_degradation",
            "expansion_offset",
        ],
    },
    {
        "rank": 4,
        "account_id": "acct_lumen_rail",
        "risk_score": 50,
        "risk_level": "high",
        "primary_action": "collections_followup",
        "current_arr": 1153774.24,
        "overdue_balance": 12775.74,
        "open_expansion_pipeline": 0.0,
        "net_revenue_exposure": 1166549.98,
        "next_touch_due_date": "2026-10-15",
        "reason_codes": [
            "overdue_receivable",
            "sla_degradation",
            "usage_decline",
        ],
    },
    {
        "rank": 5,
        "account_id": "acct_valence",
        "risk_score": 45,
        "risk_level": "medium",
        "primary_action": "collections_followup",
        "current_arr": 545534.59,
        "overdue_balance": 4858.69,
        "open_expansion_pipeline": 217778.47,
        "net_revenue_exposure": 332614.81,
        "next_touch_due_date": "2026-10-15",
        "reason_codes": [
            "renewal_window",
            "overdue_receivable",
            "expansion_offset",
        ],
    },
    {
        "rank": 6,
        "account_id": "acct_globex_north",
        "risk_score": 40,
        "risk_level": "medium",
        "primary_action": "collections_followup",
        "current_arr": 1186396.87,
        "overdue_balance": 20929.75,
        "open_expansion_pipeline": 0.0,
        "net_revenue_exposure": 1207326.62,
        "next_touch_due_date": "2026-10-15",
        "reason_codes": [
            "overdue_receivable",
            "sla_degradation",
        ],
    },
    {
        "rank": 7,
        "account_id": "acct_quartz_insure",
        "risk_score": 35,
        "risk_level": "medium",
        "primary_action": "technical_recovery",
        "current_arr": 1061984.61,
        "overdue_balance": 0.0,
        "open_expansion_pipeline": 133745.01,
        "net_revenue_exposure": 928239.6,
        "next_touch_due_date": "2026-10-18",
        "reason_codes": [
            "sla_degradation",
            "usage_decline",
            "expansion_offset",
        ],
    },
]

expected_summary = {
    "watchlist_arr_at_risk": 6016270.13,
    "watchlist_overdue_total": 47846.87,
    "watchlist_open_expansion": 852227.12,
    "net_revenue_exposure": 5211889.88,
    "collections_followups": 5,
    "renewal_saves": 1,
}

expected_next_actions = {
    "collections_followup": "2026-10-15",
    "renewal_save": "2026-10-22",
    "technical_recovery": "2026-10-18",
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


def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        return {"__load_error__": str(exc)}


def close_money(actual, expected):
    try:
        return math.isclose(float(actual), float(expected), abs_tol=0.005)
    except Exception:
        return False


def add_check(name, weight, passed):
    checks.append({"name": name, "weight": weight, "passed": bool(passed)})


def rows(payload):
    value = payload.get("watchlist", [])
    return value if isinstance(value, list) else []


def by_id(payload):
    return {row.get("account_id"): row for row in rows(payload) if isinstance(row, dict)}


def ordered_ids_and_ranks(payload):
    actual_rows = rows(payload)
    return (
        [row.get("account_id") for row in actual_rows] == [row["account_id"] for row in expected_watchlist]
        and [row.get("rank") for row in actual_rows] == [row["rank"] for row in expected_watchlist]
    )


def exact_fields(payload, field_names):
    actual_by_id = by_id(payload)
    for expected in expected_watchlist:
        actual = actual_by_id.get(expected["account_id"], {})
        for field in field_names:
            if actual.get(field) != expected[field]:
                return False
    return True


def money_fields(payload, field_names):
    actual_by_id = by_id(payload)
    for expected in expected_watchlist:
        actual = actual_by_id.get(expected["account_id"], {})
        for field in field_names:
            if not close_money(actual.get(field), expected[field]):
                return False
    return True


def reason_sets(payload):
    actual_by_id = by_id(payload)
    return all(
        set(actual_by_id.get(expected["account_id"], {}).get("reason_codes", [])) == set(expected["reason_codes"])
        for expected in expected_watchlist
    )


prediction = load_json(prediction_path)
summary = prediction.get("finance_pipeline_summary", {})

add_check("ordered_watchlist_account_ids", 3, ordered_ids_and_ranks(prediction))
add_check("risk_scores_levels_and_actions", 3, exact_fields(prediction, ["risk_score", "risk_level", "primary_action"]))
add_check("current_arr_and_overdue_balances", 2, money_fields(prediction, ["current_arr", "overdue_balance"]))
add_check("pipeline_and_net_exposure_per_account", 2, money_fields(prediction, ["open_expansion_pipeline", "net_revenue_exposure"]))
add_check("reason_code_sets", 2, reason_sets(prediction))
add_check(
    "next_touch_due_dates_and_action_map",
    2,
    exact_fields(prediction, ["next_touch_due_date"]) and prediction.get("next_actions") == expected_next_actions,
)
add_check(
    "finance_pipeline_summary_totals",
    3,
    close_money(summary.get("watchlist_arr_at_risk"), expected_summary["watchlist_arr_at_risk"])
    and close_money(summary.get("watchlist_overdue_total"), expected_summary["watchlist_overdue_total"])
    and close_money(summary.get("watchlist_open_expansion"), expected_summary["watchlist_open_expansion"])
    and close_money(summary.get("net_revenue_exposure"), expected_summary["net_revenue_exposure"])
    and summary.get("collections_followups") == expected_summary["collections_followups"]
    and summary.get("renewal_saves") == expected_summary["renewal_saves"],
)
policy_codes = prediction.get("policy_codes", {})
add_check(
    "retention_policy_code_core",
    3,
    policy_codes.get("risk_model_code") == expected_policy_codes["risk_model_code"]
    and policy_codes.get("action_priority_code") == expected_policy_codes["action_priority_code"]
    and policy_codes.get("arr_source_code") == expected_policy_codes["arr_source_code"]
    and policy_codes.get("support_hygiene_code") == expected_policy_codes["support_hygiene_code"],
)
add_check(
    "board_policy_codes",
    3,
    policy_codes.get("board_sort_code") == expected_policy_codes["board_sort_code"]
    and policy_codes.get("exposure_formula_code") == expected_policy_codes["exposure_formula_code"]
    and policy_codes.get("calendar_policy_code") == expected_policy_codes["calendar_policy_code"],
)
add_check("complete_policy_code_set", 3, policy_codes == expected_policy_codes)

earned_weight = sum(item["weight"] for item in checks if item["passed"])
total_weight = sum(item["weight"] for item in checks)
score = earned_weight / total_weight if total_weight else 0.0

print(json.dumps({
    "score": round(score, 6),
    "earned_weight": earned_weight,
    "total_weight": total_weight,
    "checks": checks,
}, sort_keys=True))
PY
