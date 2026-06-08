#!/usr/bin/env bash
set -euo pipefail

TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREDICTION_PATH="${1:-"$TASK_DIR/output/answer.json"}"

python3 - "$PREDICTION_PATH" <<'PY'
import json
import math
import sys
from pathlib import Path

prediction_path = Path(sys.argv[1])

expected = {
    "model_validation": {
        "training_rows": 180,
        "validation_rows": 60,
        "feature_count": 19,
        "accuracy_pct": 93.3,
        "accuracy_band": "90_plus",
        "tenure_coefficient_direction": "negative",
    },
    "risk_ranking": [
        {
            "rank": 1,
            "customer_id": "acct_tandemworks",
            "predicted_churn_probability": 0.102,
            "outreach_action": "collections_followup",
            "reason_code": "overdue_receivable",
        },
        {
            "rank": 2,
            "customer_id": "acct_northstar_finance",
            "predicted_churn_probability": 0.039,
            "outreach_action": "renewal_save",
            "reason_code": "low_tenure_high_churn",
        },
        {
            "rank": 3,
            "customer_id": "acct_northstar_retail",
            "predicted_churn_probability": 0.032,
            "outreach_action": "renewal_save",
            "reason_code": "low_tenure_high_churn",
        },
        {
            "rank": 4,
            "customer_id": "acct_globex_north",
            "predicted_churn_probability": 0.001,
            "outreach_action": "nurture_monitor",
            "reason_code": "clean_billings",
        },
        {
            "rank": 5,
            "customer_id": "acct_valence",
            "predicted_churn_probability": 0.001,
            "outreach_action": "nurture_monitor",
            "reason_code": "clean_billings",
        },
    ],
    "cohort_checks": {
        "past_due_shortlist_count": 1,
        "low_tenure_shortlist_count": 3,
        "average_probability_top5": 0.035,
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
    "tenure_direction": 2,
    "top5_order": 3,
    "probabilities": 3,
    "actions_and_reasons": 2,
    "cohort_checks": 2,
    "model_policy_codes": 3,
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

mv = actual.get("model_validation", {})
expected_mv = expected["model_validation"]
checks["row_and_feature_counts"] = (
    mv.get("training_rows") == expected_mv["training_rows"]
    and mv.get("validation_rows") == expected_mv["validation_rows"]
    and mv.get("feature_count") == expected_mv["feature_count"]
)
checks["validation_accuracy"] = (
    number_equal(mv.get("accuracy_pct"), expected_mv["accuracy_pct"], 1)
    and mv.get("accuracy_band") == expected_mv["accuracy_band"]
)
checks["tenure_direction"] = (
    mv.get("tenure_coefficient_direction") == expected_mv["tenure_coefficient_direction"]
)

ranking = actual.get("risk_ranking", [])
expected_ranking = expected["risk_ranking"]
checks["top5_order"] = (
    isinstance(ranking, list)
    and len(ranking) >= 5
    and [row.get("customer_id") for row in ranking[:5]]
    == [row["customer_id"] for row in expected_ranking]
    and [row.get("rank") for row in ranking[:5]] == [1, 2, 3, 4, 5]
)
checks["probabilities"] = (
    isinstance(ranking, list)
    and len(ranking) >= 5
    and all(
        number_equal(actual_row.get("predicted_churn_probability"), expected_row["predicted_churn_probability"], 3)
        for actual_row, expected_row in zip(ranking[:5], expected_ranking)
    )
)
checks["actions_and_reasons"] = (
    isinstance(ranking, list)
    and len(ranking) >= 5
    and all(
        actual_row.get("outreach_action") == expected_row["outreach_action"]
        and actual_row.get("reason_code") == expected_row["reason_code"]
        for actual_row, expected_row in zip(ranking[:5], expected_ranking)
    )
)

cohort = actual.get("cohort_checks", {})
expected_cohort = expected["cohort_checks"]
checks["cohort_checks"] = (
    cohort.get("past_due_shortlist_count") == expected_cohort["past_due_shortlist_count"]
    and cohort.get("low_tenure_shortlist_count") == expected_cohort["low_tenure_shortlist_count"]
    and number_equal(cohort.get("average_probability_top5"), expected_cohort["average_probability_top5"], 3)
)
checks["model_policy_codes"] = actual.get("model_policy_codes", {}) == expected["model_policy_codes"]

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
