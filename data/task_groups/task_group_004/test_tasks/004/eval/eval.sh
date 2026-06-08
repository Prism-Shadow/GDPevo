#!/usr/bin/env bash
set -euo pipefail

TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREDICTION_PATH="${1:-"$TASK_DIR/output/answer.json"}"

python3 - "$PREDICTION_PATH" <<'PY'
import json
import sys
from pathlib import Path

prediction_path = Path(sys.argv[1])

expected = {
    "model_report": {
        "training_rows": 180,
        "validation_rows": 60,
        "feature_count": 19,
        "accuracy_pct": 93.3,
        "accuracy_band": "90_plus",
        "tenure_coefficient_direction": "negative",
        "deployment_recommendation": "approve_with_monitoring",
    },
    "outreach_shortlist": [
        {
            "rank": 1,
            "customer_id": "acct_bayside_bio",
            "predicted_churn_probability": 0.007,
            "risk_level": "low",
            "outreach_action": "nurture_monitor",
            "reason_code": "clean_billings",
        },
        {
            "rank": 2,
            "customer_id": "acct_helios",
            "predicted_churn_probability": 0.005,
            "risk_level": "low",
            "outreach_action": "nurture_monitor",
            "reason_code": "clean_billings",
        },
        {
            "rank": 3,
            "customer_id": "acct_valence",
            "predicted_churn_probability": 0.001,
            "risk_level": "low",
            "outreach_action": "nurture_monitor",
            "reason_code": "clean_billings",
        },
        {
            "rank": 4,
            "customer_id": "acct_westport",
            "predicted_churn_probability": 0.000,
            "risk_level": "low",
            "outreach_action": "nurture_monitor",
            "reason_code": "nps_drop",
        },
        {
            "rank": 5,
            "customer_id": "acct_apexia",
            "predicted_churn_probability": 0.000,
            "risk_level": "low",
            "outreach_action": "nurture_monitor",
            "reason_code": "clean_billings",
        },
        {
            "rank": 6,
            "customer_id": "acct_southridge",
            "predicted_churn_probability": 0.000,
            "risk_level": "low",
            "outreach_action": "nurture_monitor",
            "reason_code": "clean_billings",
        },
    ],
    "cohort_checks": {
        "enterprise_or_strategic_count": 6,
        "past_due_shortlist_count": 0,
        "average_probability_top6": 0.002,
        "low_tenure_shortlist_count": 0,
    },
    "model_policy_codes": {
        "model_protocol_code": "MOD-7",
        "probability_scale_code": "PRB-4",
        "deployment_rule_code": "DEP-5",
        "outreach_mapping_code": "OUT-2",
    },
}

weights = {
    "row_and_feature_counts": 1,
    "validation_accuracy": 2,
    "tenure_and_deployment": 2,
    "top6_order": 3,
    "probabilities_and_risk_levels": 3,
    "actions_and_reasons": 2,
    "cohort_checks": 2,
    "model_policy_code_core": 3,
    "complete_model_policy_code_set": 3,
}

def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)

def number_equal(actual, expected_value, decimals):
    try:
        return round(float(actual), decimals) == round(float(expected_value), decimals)
    except (TypeError, ValueError):
        return False

try:
    actual = load_json(prediction_path)
except Exception as exc:
    total_weight = sum(weights.values())
    print(json.dumps({
        "score": 0.0,
        "earned_weight": 0,
        "total_weight": total_weight,
        "error": f"could not read prediction JSON: {exc}",
    }, sort_keys=True))
    sys.exit(0)

earned = 0
checks = {}

report = actual.get("model_report", {})
expected_report = expected["model_report"]
checks["row_and_feature_counts"] = (
    report.get("training_rows") == expected_report["training_rows"]
    and report.get("validation_rows") == expected_report["validation_rows"]
    and report.get("feature_count") == expected_report["feature_count"]
)
checks["validation_accuracy"] = (
    number_equal(report.get("accuracy_pct"), expected_report["accuracy_pct"], 1)
    and report.get("accuracy_band") == expected_report["accuracy_band"]
)
checks["tenure_and_deployment"] = (
    report.get("tenure_coefficient_direction") == expected_report["tenure_coefficient_direction"]
    and report.get("deployment_recommendation") == expected_report["deployment_recommendation"]
)

shortlist = actual.get("outreach_shortlist", [])
expected_shortlist = expected["outreach_shortlist"]
checks["top6_order"] = (
    isinstance(shortlist, list)
    and len(shortlist) >= 6
    and [row.get("customer_id") for row in shortlist[:6]]
    == [row["customer_id"] for row in expected_shortlist]
    and [row.get("rank") for row in shortlist[:6]] == [1, 2, 3, 4, 5, 6]
)
checks["probabilities_and_risk_levels"] = (
    isinstance(shortlist, list)
    and len(shortlist) >= 6
    and all(
        number_equal(actual_row.get("predicted_churn_probability"), expected_row["predicted_churn_probability"], 3)
        and actual_row.get("risk_level") == expected_row["risk_level"]
        for actual_row, expected_row in zip(shortlist[:6], expected_shortlist)
    )
)
checks["actions_and_reasons"] = (
    isinstance(shortlist, list)
    and len(shortlist) >= 6
    and all(
        actual_row.get("outreach_action") == expected_row["outreach_action"]
        and actual_row.get("reason_code") == expected_row["reason_code"]
        for actual_row, expected_row in zip(shortlist[:6], expected_shortlist)
    )
)

cohort = actual.get("cohort_checks", {})
expected_cohort = expected["cohort_checks"]
checks["cohort_checks"] = (
    cohort.get("enterprise_or_strategic_count") == expected_cohort["enterprise_or_strategic_count"]
    and cohort.get("past_due_shortlist_count") == expected_cohort["past_due_shortlist_count"]
    and number_equal(cohort.get("average_probability_top6"), expected_cohort["average_probability_top6"], 3)
    and cohort.get("low_tenure_shortlist_count") == expected_cohort["low_tenure_shortlist_count"]
)

codes = actual.get("model_policy_codes", {})
checks["model_policy_code_core"] = (
    codes.get("model_protocol_code") == expected["model_policy_codes"]["model_protocol_code"]
    and codes.get("probability_scale_code") == expected["model_policy_codes"]["probability_scale_code"]
    and codes.get("deployment_rule_code") == expected["model_policy_codes"]["deployment_rule_code"]
    and codes.get("outreach_mapping_code") == expected["model_policy_codes"]["outreach_mapping_code"]
)
checks["complete_model_policy_code_set"] = codes == expected["model_policy_codes"]

for name, passed in checks.items():
    if passed:
        earned += weights[name]

total = sum(weights.values())
print(json.dumps({
    "score": earned / total,
    "earned_weight": earned,
    "total_weight": total,
    "checks": checks,
}, sort_keys=True))
PY
