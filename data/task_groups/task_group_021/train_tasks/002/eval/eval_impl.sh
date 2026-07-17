#!/usr/bin/env bash

prediction_path="${1:-}"
script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

python3 - "$prediction_path" "$script_dir/../output/answer.json" <<'PY'
import json
import math
import sys
from pathlib import Path


POINTS = [
    ("SP001", 1, "Authoritative source and scoped transaction counts"),
    ("SP002", 2, "Canonical fuel results and expected-versus-actual mismatch set"),
    ("SP003", 2, "Recognition and quarantine exception results"),
    ("SP004", 2, "Normalized volume and spend"),
    ("SP005", 1, "Focus-asset reconciled totals"),
    ("SP006", 1, "Merchant exception priority ranking"),
    ("SP007", 3, "Internal reference-policy and retained-source codes"),
    ("SP008", 3, "Internal ledger-disposition codes and reconciliation routing"),
]
TOTAL_WEIGHT = sum(weight for _, weight, _ in POINTS)


def get(value, *path):
    current = value
    for part in path:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def number_equal(actual, expected, digits=2):
    if isinstance(actual, bool) or not isinstance(actual, (int, float)):
        return False
    if not math.isfinite(float(actual)):
        return False
    return round(float(actual), digits) == round(float(expected), digits)


def integer_equal(actual, expected):
    return isinstance(actual, int) and not isinstance(actual, bool) and actual == expected


def string_set(value):
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        return set()
    return set(value)


def set_f1(actual_value, expected_value):
    actual = string_set(actual_value)
    expected = string_set(expected_value)
    true_positive = len(actual & expected)
    precision = true_positive / len(actual) if actual else (1.0 if not expected else 0.0)
    recall = true_positive / len(expected) if expected else (1.0 if not actual else 0.0)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return f1, {
        "expected_count": len(expected),
        "predicted_unique_count": len(actual),
        "true_positive_count": true_positive,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
    }


def index_objects(value, key):
    if not isinstance(value, list):
        return {}
    result = {}
    for item in value:
        if isinstance(item, dict) and isinstance(item.get(key), str):
            result[item[key]] = item
    return result


def mean(flags):
    return sum(1.0 if flag else 0.0 for flag in flags) / len(flags) if flags else 0.0


def emit_zero(error):
    details = []
    for point_id, weight, goal in POINTS:
        details.append({
            "point_id": point_id,
            "goal": goal,
            "raw_weight": weight,
            "max_normalized_weight": round(weight / TOTAL_WEIGHT, 6),
            "earned_fraction": 0.0,
            "earned_normalized_weight": 0.0,
            "subchecks": {"prediction_error": error},
        })
    print(json.dumps({"score": 0.0, "points": details}, sort_keys=True))


try:
    prediction_file = Path(sys.argv[1])
    gold_file = Path(sys.argv[2])
    prediction = json.loads(prediction_file.read_text(encoding="utf-8"))
    gold = json.loads(gold_file.read_text(encoding="utf-8"))
    if not isinstance(prediction, dict):
        raise ValueError("prediction root must be a JSON object")
except Exception as exc:
    emit_zero(f"unreadable prediction: {type(exc).__name__}")
    raise SystemExit(0)


fractions = {}
subchecks = {}

# SP001: source choice and population reconstruction remain independently creditable.
source_checks = {
    "authoritative_snapshot_id": get(prediction, "audit_summary", "authoritative_snapshot_id")
    == get(gold, "audit_summary", "authoritative_snapshot_id"),
    "raw_row_count": integer_equal(
        get(prediction, "audit_summary", "raw_row_count"),
        get(gold, "audit_summary", "raw_row_count"),
    ),
    "logical_transaction_count": integer_equal(
        get(prediction, "audit_summary", "logical_transaction_count"),
        get(gold, "audit_summary", "logical_transaction_count"),
    ),
    "duplicate_raw_count": integer_equal(
        get(prediction, "audit_summary", "duplicate_raw_count"),
        get(gold, "audit_summary", "duplicate_raw_count"),
    ),
    "valid_transaction_count": integer_equal(
        get(prediction, "audit_summary", "valid_transaction_count"),
        get(gold, "audit_summary", "valid_transaction_count"),
    ),
    "normalized_valid_count_consistent": integer_equal(
        get(prediction, "normalized_totals", "valid_transaction_count"),
        get(gold, "normalized_totals", "valid_transaction_count"),
    ),
}
fractions["SP001"] = mean(source_checks.values())
subchecks["SP001"] = source_checks

# SP002: the large mismatch set is dominant, with separate category-count checks.
mismatch_f1, mismatch_detail = set_f1(
    get(prediction, "mismatch_transaction_ids"),
    get(gold, "mismatch_transaction_ids"),
)
pred_categories = index_objects(get(prediction, "normalized_totals", "fuel_type_totals"), "fuel_type")
gold_categories = index_objects(get(gold, "normalized_totals", "fuel_type_totals"), "fuel_type")
category_ids_correct = set(pred_categories) == set(gold_categories)
category_count_checks = {
    fuel_type: integer_equal(
        get(pred_categories.get(fuel_type, {}), "transaction_count"),
        get(gold_categories[fuel_type], "transaction_count"),
    )
    for fuel_type in sorted(gold_categories)
}
category_fraction = mean([category_ids_correct, *category_count_checks.values()])
mismatch_count_correct = integer_equal(
    get(prediction, "audit_summary", "mismatch_count"),
    get(gold, "audit_summary", "mismatch_count"),
)
fractions["SP002"] = 0.70 * mismatch_f1 + 0.15 * float(mismatch_count_correct) + 0.15 * category_fraction
subchecks["SP002"] = {
    "mismatch_set": mismatch_detail,
    "mismatch_count_correct": mismatch_count_correct,
    "category_id_set_correct": category_ids_correct,
    "category_transaction_counts": category_count_checks,
}

# SP003: zero-match and ambiguous IDs share a set, while reason counts remain distinct.
recognition_f1, recognition_detail = set_f1(
    get(prediction, "unrecognized_transaction_ids"),
    get(gold, "unrecognized_transaction_ids"),
)
recognition_checks = {
    "unrecognized_count": integer_equal(
        get(prediction, "audit_summary", "unrecognized_count"),
        get(gold, "audit_summary", "unrecognized_count"),
    ),
    "ambiguous_count": integer_equal(
        get(prediction, "audit_summary", "ambiguous_count"),
        get(gold, "audit_summary", "ambiguous_count"),
    ),
    "invalid_quantity_count": integer_equal(
        get(prediction, "audit_summary", "invalid_quantity_count"),
        get(gold, "audit_summary", "invalid_quantity_count"),
    ),
}
fractions["SP003"] = (
    0.60 * recognition_f1
    + 0.15 * float(recognition_checks["unrecognized_count"])
    + 0.15 * float(recognition_checks["ambiguous_count"])
    + 0.10 * float(recognition_checks["invalid_quantity_count"])
)
subchecks["SP003"] = {"recognition_exception_set": recognition_detail, **recognition_checks}

# SP004: liters and spend each retain their own independent exact subchecks.
volume_checks = {
    "total_volume_l": number_equal(
        get(prediction, "normalized_totals", "total_volume_l"),
        get(gold, "normalized_totals", "total_volume_l"),
    )
}
for fuel_type in sorted(gold_categories):
    volume_checks[f"{fuel_type}_volume_l"] = number_equal(
        get(pred_categories.get(fuel_type, {}), "volume_l"),
        get(gold_categories[fuel_type], "volume_l"),
    )
spend_checks = {
    "total_spend_usd": number_equal(
        get(prediction, "normalized_totals", "total_spend_usd"),
        get(gold, "normalized_totals", "total_spend_usd"),
    )
}
for fuel_type in sorted(gold_categories):
    spend_checks[f"{fuel_type}_spend_usd"] = number_equal(
        get(pred_categories.get(fuel_type, {}), "spend_usd"),
        get(gold_categories[fuel_type], "spend_usd"),
    )
fractions["SP004"] = 0.5 * mean(volume_checks.values()) + 0.5 * mean(spend_checks.values())
subchecks["SP004"] = {"volume": volume_checks, "spend": spend_checks}

# SP005 diagnostic fraction: every requested asset and measure must pass for 1.0.
pred_assets = index_objects(get(prediction, "focus_assets"), "asset_id")
gold_assets = index_objects(get(gold, "focus_assets"), "asset_id")
asset_checks = {"asset_id_set_correct": set(pred_assets) == set(gold_assets)}
integer_fields = [
    "logical_transaction_count",
    "valid_transaction_count",
    "mismatch_count",
    "quarantine_count",
    "exception_count",
]
number_fields = ["volume_l", "spend_usd"]
for asset_id in sorted(gold_assets):
    predicted_asset = pred_assets.get(asset_id, {})
    for field in integer_fields:
        asset_checks[f"{asset_id}.{field}"] = integer_equal(
            get(predicted_asset, field), get(gold_assets[asset_id], field)
        )
    for field in number_fields:
        asset_checks[f"{asset_id}.{field}"] = number_equal(
            get(predicted_asset, field), get(gold_assets[asset_id], field)
        )
fractions["SP005"] = mean(asset_checks.values())
subchecks["SP005"] = asset_checks

# SP006: rank positions and merchant-level exception composition earn separate credit.
pred_ranking = get(prediction, "audit_summary", "exception_merchant_ranking")
gold_ranking = get(gold, "audit_summary", "exception_merchant_ranking")
pred_ranking = pred_ranking if isinstance(pred_ranking, list) else []
gold_ranking = gold_ranking if isinstance(gold_ranking, list) else []
pred_rank_ids = [item.get("merchant_id") if isinstance(item, dict) else None for item in pred_ranking]
gold_rank_ids = [item["merchant_id"] for item in gold_ranking]
position_checks = {
    f"rank_{index + 1}": index < len(pred_rank_ids) and pred_rank_ids[index] == merchant_id
    for index, merchant_id in enumerate(gold_rank_ids)
}
position_checks["ranking_length"] = len(pred_rank_ids) == len(gold_rank_ids)
order_fraction = mean(position_checks.values())
pred_merchants = index_objects(pred_ranking, "merchant_id")
gold_merchants = index_objects(gold_ranking, "merchant_id")
merchant_checks = {}
for merchant_id in gold_rank_ids:
    for field in ["exception_count", "mismatch_count", "quarantine_count"]:
        merchant_checks[f"{merchant_id}.{field}"] = integer_equal(
            get(pred_merchants.get(merchant_id, {}), field),
            get(gold_merchants[merchant_id], field),
        )
merchant_checks["exception_transaction_count"] = integer_equal(
    get(prediction, "audit_summary", "exception_transaction_count"),
    get(gold, "audit_summary", "exception_transaction_count"),
)
fractions["SP006"] = 0.40 * order_fraction + 0.60 * mean(merchant_checks.values())
subchecks["SP006"] = {
    "ranking_positions": position_checks,
    "merchant_counts": merchant_checks,
}

# SP007: internal reference and source codes are credited once per requested stable ID.
pred_panel = get(prediction, "policy_decision_panel")
gold_panel = get(gold, "policy_decision_panel")
pred_references = index_objects(get(pred_panel, "reference_decisions"), "reference_id")
gold_references = index_objects(get(gold_panel, "reference_decisions"), "reference_id")
pred_reference_rows = get(pred_panel, "reference_decisions")
gold_reference_rows = get(gold_panel, "reference_decisions")
reference_code_checks = {
    "reference_id_set_correct": set(pred_references) == set(gold_references),
    "reference_order_correct": (
        isinstance(pred_reference_rows, list)
        and isinstance(gold_reference_rows, list)
        and [get(item, "reference_id") for item in pred_reference_rows]
        == [get(item, "reference_id") for item in gold_reference_rows]
    ),
}
for reference_id in sorted(gold_references):
    reference_code_checks[f"{reference_id}.reference_policy_code"] = (
        get(pred_references.get(reference_id, {}), "reference_policy_code")
        == get(gold_references[reference_id], "reference_policy_code")
    )

pred_transactions = index_objects(get(pred_panel, "transaction_decisions"), "transaction_id")
gold_transactions = index_objects(get(gold_panel, "transaction_decisions"), "transaction_id")
pred_transaction_rows = get(pred_panel, "transaction_decisions")
gold_transaction_rows = get(gold_panel, "transaction_decisions")
source_code_checks = {
    "transaction_id_set_correct": set(pred_transactions) == set(gold_transactions),
    "transaction_order_correct": (
        isinstance(pred_transaction_rows, list)
        and isinstance(gold_transaction_rows, list)
        and [get(item, "transaction_id") for item in pred_transaction_rows]
        == [get(item, "transaction_id") for item in gold_transaction_rows]
    ),
}
for transaction_id in sorted(gold_transactions):
    source_code_checks[f"{transaction_id}.source_basis_code"] = (
        get(pred_transactions.get(transaction_id, {}), "source_basis_code")
        == get(gold_transactions[transaction_id], "source_basis_code")
    )
fractions["SP007"] = 0.4 * mean(reference_code_checks.values()) + 0.6 * mean(source_code_checks.values())
subchecks["SP007"] = {
    "reference_policy_codes": reference_code_checks,
    "source_basis_codes": source_code_checks,
}

# SP008: each ledger code and each operational choice is independently creditable.
ledger_code_checks = {}
for transaction_id in sorted(gold_transactions):
    ledger_code_checks[f"{transaction_id}.ledger_disposition_code"] = (
        get(pred_transactions.get(transaction_id, {}), "ledger_disposition_code")
        == get(gold_transactions[transaction_id], "ledger_disposition_code")
    )
decision_checks = {
    "status": get(prediction, "reconciliation_status", "status")
    == get(gold, "reconciliation_status", "status"),
    "action": get(prediction, "reconciliation_status", "action")
    == get(gold, "reconciliation_status", "action"),
}
fractions["SP008"] = 0.85 * mean(ledger_code_checks.values()) + 0.15 * mean(decision_checks.values())
subchecks["SP008"] = {
    "ledger_disposition_codes": ledger_code_checks,
    "reconciliation_routing": decision_checks,
}


details = []
score = 0.0
for point_id, weight, goal in POINTS:
    fraction = min(1.0, max(0.0, fractions[point_id]))
    maximum = weight / TOTAL_WEIGHT
    earned = maximum * fraction
    score += earned
    details.append({
        "point_id": point_id,
        "goal": goal,
        "raw_weight": weight,
        "max_normalized_weight": round(maximum, 6),
        "earned_fraction": round(fraction, 6),
        "earned_normalized_weight": round(earned, 6),
        "subchecks": subchecks[point_id],
    })

print(json.dumps({"score": round(score, 10), "points": details}, sort_keys=True))
PY
