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
    "risk_accounts": [
        {
            "rank": 1,
            "account_id": "acct_northstar_finance",
            "risk_score": 100,
            "risk_level": "critical",
            "primary_action": "collections_followup",
            "current_arr": 1416439.47,
            "latest_nps": 39,
            "clean_ticket_count": 13,
            "overdue_balance": 8773.03,
        },
        {
            "rank": 2,
            "account_id": "acct_polaris_health",
            "risk_score": 60,
            "risk_level": "high",
            "primary_action": "collections_followup",
            "current_arr": 705648.74,
            "latest_nps": 53,
            "clean_ticket_count": 14,
            "overdue_balance": 8353.43,
        },
        {
            "rank": 3,
            "account_id": "acct_northstar_retail",
            "risk_score": 50,
            "risk_level": "high",
            "primary_action": "technical_recovery",
            "current_arr": 237281.77,
            "latest_nps": 18,
            "clean_ticket_count": 14,
            "overdue_balance": 0.0,
        },
        {
            "rank": 4,
            "account_id": "acct_arcstone",
            "risk_score": 20,
            "risk_level": "low",
            "primary_action": "technical_recovery",
            "current_arr": 536552.47,
            "latest_nps": 65,
            "clean_ticket_count": 12,
            "overdue_balance": 0.0,
        },
        {
            "rank": 5,
            "account_id": "acct_summit_grid",
            "risk_score": 15,
            "risk_level": "low",
            "primary_action": "technical_recovery",
            "current_arr": 141895.58,
            "latest_nps": 46,
            "clean_ticket_count": 4,
            "overdue_balance": 0.0,
        },
    ],
    "portfolio_summary": {
        "accounts_reviewed": 8,
        "critical_or_high_count": 3,
        "arr_at_risk": 2359369.98,
        "collections_count": 2,
        "technical_recovery_count": 3,
    },
    "model_checks": {
        "uses_billing_arr_source": True,
        "tenure_risk_direction": "negative",
    },
    "policy_codes": {
        "risk_model_code": "RS-6",
        "arr_source_code": "REV-4",
        "support_hygiene_code": "SUP-8",
        "action_priority_code": "ACT-5",
    },
}

checks = [
    ("ordered_top5_account_ids", 3),
    ("risk_scores_and_levels", 3),
    ("primary_actions", 2),
    ("current_arr_values", 2),
    ("clean_ticket_counts_and_latest_nps", 2),
    ("overdue_balances_and_collections_count", 2),
    ("portfolio_summary_counts_and_arr_at_risk", 2),
    ("model_checks", 1),
    ("policy_codes", 3),
]

def load_prediction(path):
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        return {"__load_error__": str(exc)}

def risk_rows(payload):
    rows = payload.get("risk_accounts", [])
    return rows if isinstance(rows, list) else []

def close_money(actual, expected_value):
    try:
        return math.isclose(float(actual), float(expected_value), abs_tol=0.005)
    except Exception:
        return False

def ordered_ids_ok(payload):
    return [row.get("account_id") for row in risk_rows(payload)] == [
        row["account_id"] for row in expected["risk_accounts"]
    ]

def rows_match(payload, keys, money_keys=()):
    rows = risk_rows(payload)
    if len(rows) != len(expected["risk_accounts"]):
        return False
    for actual, exp in zip(rows, expected["risk_accounts"]):
        if actual.get("account_id") != exp["account_id"]:
            return False
        for key in keys:
            if key in money_keys:
                if not close_money(actual.get(key), exp[key]):
                    return False
            elif actual.get(key) != exp[key]:
                return False
    return True

def summary_ok(payload):
    summary = payload.get("portfolio_summary", {})
    exp = expected["portfolio_summary"]
    return (
        summary.get("accounts_reviewed") == exp["accounts_reviewed"]
        and summary.get("critical_or_high_count") == exp["critical_or_high_count"]
        and close_money(summary.get("arr_at_risk"), exp["arr_at_risk"])
        and summary.get("technical_recovery_count") == exp["technical_recovery_count"]
    )

def collections_ok(payload):
    summary = payload.get("portfolio_summary", {})
    return rows_match(payload, ["overdue_balance"], money_keys=("overdue_balance",)) and (
        summary.get("collections_count") == expected["portfolio_summary"]["collections_count"]
    )

def model_ok(payload):
    model = payload.get("model_checks", {})
    exp = expected["model_checks"]
    return (
        model.get("uses_billing_arr_source") is exp["uses_billing_arr_source"]
        and model.get("tenure_risk_direction") == exp["tenure_risk_direction"]
    )

def policy_codes_ok(payload):
    return payload.get("policy_codes", {}) == expected["policy_codes"]

prediction = load_prediction(prediction_path)

results = {
    "ordered_top5_account_ids": ordered_ids_ok(prediction),
    "risk_scores_and_levels": rows_match(prediction, ["risk_score", "risk_level"]),
    "primary_actions": rows_match(prediction, ["primary_action"]),
    "current_arr_values": rows_match(prediction, ["current_arr"], money_keys=("current_arr",)),
    "clean_ticket_counts_and_latest_nps": rows_match(prediction, ["clean_ticket_count", "latest_nps"]),
    "overdue_balances_and_collections_count": collections_ok(prediction),
    "portfolio_summary_counts_and_arr_at_risk": summary_ok(prediction),
    "model_checks": model_ok(prediction),
    "policy_codes": policy_codes_ok(prediction),
}

total_weight = sum(weight for _, weight in checks)
earned_weight = sum(weight for name, weight in checks if results[name])
score = earned_weight / total_weight if total_weight else 0.0

print(json.dumps({
    "score": round(score, 6),
    "earned_weight": earned_weight,
    "total_weight": total_weight,
    "checks": results,
}, sort_keys=True))
PY
