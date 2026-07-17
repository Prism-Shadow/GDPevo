#!/usr/bin/env bash

prediction_path="${1:-}"
script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

python3 - "$prediction_path" "$script_dir/../output/answer.json" <<'PY'
import json
import math
import sys
from pathlib import Path


POINTS = [
    ("SP001", 1, "Authoritative source and scoped charge counts"),
    ("SP002", 3, "Reference decisions, recognized classes, and mismatch charges"),
    ("SP003", 2, "Source-retention decisions and duplicate charge groups"),
    ("SP004", 2, "Quarantined charge set and reason profile"),
    ("SP005", 2, "Normalized billed weight and distance"),
    ("SP006", 2, "Normalized freight spend in USD"),
    ("SP007", 2, "Carrier accrual-exposure ranking"),
    ("SP008", 2, "Charge routing decisions and accrual close status"),
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
    indexed = {}
    for item in value:
        if isinstance(item, dict) and isinstance(item.get(key), str):
            indexed[item[key]] = item
    return indexed


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

# SP001: source resolution and ledger population checks are independently creditable.
source_checks = {
    "authoritative_snapshot_id": get(prediction, "audit_summary", "authoritative_snapshot_id")
    == get(gold, "audit_summary", "authoritative_snapshot_id"),
    "raw_row_count": integer_equal(
        get(prediction, "audit_summary", "raw_row_count"),
        get(gold, "audit_summary", "raw_row_count"),
    ),
    "logical_charge_count": integer_equal(
        get(prediction, "audit_summary", "logical_charge_count"),
        get(gold, "audit_summary", "logical_charge_count"),
    ),
    "duplicate_raw_count": integer_equal(
        get(prediction, "audit_summary", "duplicate_raw_count"),
        get(gold, "audit_summary", "duplicate_raw_count"),
    ),
    "valid_charge_count": integer_equal(
        get(prediction, "audit_summary", "valid_charge_count"),
        get(gold, "audit_summary", "valid_charge_count"),
    ),
    "normalized_valid_count_consistent": integer_equal(
        get(prediction, "normalized_totals", "valid_charge_count"),
        get(gold, "normalized_totals", "valid_charge_count"),
    ),
}
fractions["SP001"] = mean(source_checks.values())
subchecks["SP001"] = source_checks

# SP002: reference-row decisions, mismatch identification, and class counts are
# independently creditable within one class-recognition aspect.
mismatch_f1, mismatch_detail = set_f1(
    get(prediction, "class_mismatch_charge_ids"),
    get(gold, "class_mismatch_charge_ids"),
)
pred_classes = index_objects(
    get(prediction, "normalized_totals", "service_class_totals"), "service_class"
)
gold_classes = index_objects(
    get(gold, "normalized_totals", "service_class_totals"), "service_class"
)
class_checks = {"service_class_set": set(pred_classes) == set(gold_classes)}
for service_class in sorted(gold_classes):
    class_checks[f"{service_class}.charge_count"] = integer_equal(
        get(pred_classes.get(service_class, {}), "charge_count"),
        get(gold_classes[service_class], "charge_count"),
    )
mismatch_count_correct = integer_equal(
    get(prediction, "audit_summary", "mismatch_count"),
    get(gold, "audit_summary", "mismatch_count"),
)
pred_reference_rows = index_objects(
    get(prediction, "decision_panels", "reference_rows"), "alias_id"
)
gold_reference_rows = index_objects(
    get(gold, "decision_panels", "reference_rows"), "alias_id"
)
reference_checks = {
    "alias_id_set": set(pred_reference_rows) == set(gold_reference_rows)
}
for alias_id in sorted(gold_reference_rows):
    reference_checks[f"{alias_id}.decision_code"] = (
        get(pred_reference_rows.get(alias_id, {}), "decision_code")
        == get(gold_reference_rows[alias_id], "decision_code")
    )
fractions["SP002"] = (
    0.50 * mismatch_f1
    + 0.10 * float(mismatch_count_correct)
    + 0.15 * mean(class_checks.values())
    + 0.25 * mean(reference_checks.values())
)
subchecks["SP002"] = {
    "mismatch_set": mismatch_detail,
    "mismatch_count_correct": mismatch_count_correct,
    "service_class_counts": class_checks,
    "reference_row_decisions": reference_checks,
}

# SP003: source-retention decisions and duplicate-group evidence are separately
# diagnostic but scored only in this source-resolution aspect.
pred_groups = index_objects(get(prediction, "duplicate_groups"), "charge_id")
gold_groups = index_objects(get(gold, "duplicate_groups"), "charge_id")
group_f1, group_detail = set_f1(list(pred_groups), list(gold_groups))
group_checks = {}
for charge_id in sorted(gold_groups):
    predicted_group = pred_groups.get(charge_id, {})
    expected_group = gold_groups[charge_id]
    group_checks[f"{charge_id}.raw_occurrence_count"] = integer_equal(
        get(predicted_group, "raw_occurrence_count"),
        get(expected_group, "raw_occurrence_count"),
    )
    group_checks[f"{charge_id}.snapshot_ids"] = (
        string_set(get(predicted_group, "snapshot_ids"))
        == string_set(get(expected_group, "snapshot_ids"))
    )
    group_checks[f"{charge_id}.retained_snapshot_id"] = (
        get(predicted_group, "retained_snapshot_id")
        == get(expected_group, "retained_snapshot_id")
    )
pred_source_rows = index_objects(
    get(prediction, "decision_panels", "source_retention"), "charge_id"
)
gold_source_rows = index_objects(
    get(gold, "decision_panels", "source_retention"), "charge_id"
)
source_decision_checks = {
    "charge_id_set": set(pred_source_rows) == set(gold_source_rows)
}
for charge_id in sorted(gold_source_rows):
    source_decision_checks[f"{charge_id}.decision_code"] = (
        get(pred_source_rows.get(charge_id, {}), "decision_code")
        == get(gold_source_rows[charge_id], "decision_code")
    )
fractions["SP003"] = (
    0.30 * group_f1
    + 0.40 * mean(group_checks.values())
    + 0.30 * mean(source_decision_checks.values())
)
subchecks["SP003"] = {
    "duplicate_group_set": group_detail,
    "group_results": group_checks,
    "source_retention_decisions": source_decision_checks,
}

# SP004: quarantine membership and reason counts can earn credit independently.
quarantine_f1, quarantine_detail = set_f1(
    get(prediction, "quarantine_charge_ids"),
    get(gold, "quarantine_charge_ids"),
)
reason_checks = {
    "quarantine_count": integer_equal(
        get(prediction, "audit_summary", "quarantine_count"),
        get(gold, "audit_summary", "quarantine_count"),
    )
}
gold_reasons = get(gold, "audit_summary", "quarantine_reason_counts")
gold_reasons = gold_reasons if isinstance(gold_reasons, dict) else {}
for reason in sorted(gold_reasons):
    reason_checks[reason] = integer_equal(
        get(prediction, "audit_summary", "quarantine_reason_counts", reason),
        gold_reasons[reason],
    )
fractions["SP004"] = 0.60 * quarantine_f1 + 0.40 * mean(reason_checks.values())
subchecks["SP004"] = {
    "quarantine_set": quarantine_detail,
    "reason_counts": reason_checks,
}

# SP005: global and per-class weight/distance are separate exact two-decimal checks.
physical_checks = {
    "total_billed_weight_kg": number_equal(
        get(prediction, "normalized_totals", "total_billed_weight_kg"),
        get(gold, "normalized_totals", "total_billed_weight_kg"),
    ),
    "total_distance_km": number_equal(
        get(prediction, "normalized_totals", "total_distance_km"),
        get(gold, "normalized_totals", "total_distance_km"),
    ),
}
for service_class in sorted(gold_classes):
    physical_checks[f"{service_class}.billed_weight_kg"] = number_equal(
        get(pred_classes.get(service_class, {}), "billed_weight_kg"),
        get(gold_classes[service_class], "billed_weight_kg"),
    )
    physical_checks[f"{service_class}.distance_km"] = number_equal(
        get(pred_classes.get(service_class, {}), "distance_km"),
        get(gold_classes[service_class], "distance_km"),
    )
fractions["SP005"] = mean(physical_checks.values())
subchecks["SP005"] = physical_checks

# SP006: USD conversion is independent of the physical conversion checks.
spend_checks = {
    "total_spend_usd": number_equal(
        get(prediction, "normalized_totals", "total_spend_usd"),
        get(gold, "normalized_totals", "total_spend_usd"),
    )
}
for service_class in sorted(gold_classes):
    spend_checks[f"{service_class}.spend_usd"] = number_equal(
        get(pred_classes.get(service_class, {}), "spend_usd"),
        get(gold_classes[service_class], "spend_usd"),
    )
fractions["SP006"] = mean(spend_checks.values())
subchecks["SP006"] = spend_checks

# SP007 diagnostic fraction: every rank and exposure check must pass for 1.0.
pred_ranking = get(prediction, "carrier_ranking")
gold_ranking = get(gold, "carrier_ranking")
pred_ranking = pred_ranking if isinstance(pred_ranking, list) else []
gold_ranking = gold_ranking if isinstance(gold_ranking, list) else []
pred_rank_ids = [
    item.get("carrier_id") if isinstance(item, dict) else None for item in pred_ranking
]
gold_rank_ids = [item["carrier_id"] for item in gold_ranking]
position_checks = {
    f"rank_{index + 1}": index < len(pred_rank_ids) and pred_rank_ids[index] == carrier_id
    for index, carrier_id in enumerate(gold_rank_ids)
}
position_checks["ranking_length"] = len(pred_rank_ids) == len(gold_rank_ids)
pred_carriers = index_objects(pred_ranking, "carrier_id")
gold_carriers = index_objects(gold_ranking, "carrier_id")
carrier_checks = {}
for carrier_id in gold_rank_ids:
    carrier_checks[f"{carrier_id}.rank"] = integer_equal(
        get(pred_carriers.get(carrier_id, {}), "rank"),
        get(gold_carriers[carrier_id], "rank"),
    )
    for field in ["mismatch_count", "quarantine_count", "exception_count"]:
        carrier_checks[f"{carrier_id}.{field}"] = integer_equal(
            get(pred_carriers.get(carrier_id, {}), field),
            get(gold_carriers[carrier_id], field),
        )
    carrier_checks[f"{carrier_id}.mismatch_spend_usd"] = number_equal(
        get(pred_carriers.get(carrier_id, {}), "mismatch_spend_usd"),
        get(gold_carriers[carrier_id], "mismatch_spend_usd"),
    )
fractions["SP007"] = (
    0.40 * mean(position_checks.values()) + 0.60 * mean(carrier_checks.values())
)
subchecks["SP007"] = {
    "ranking_positions": position_checks,
    "carrier_results": carrier_checks,
}

# SP008: the compact charge routing panel and the two close controls are scored
# once here, without duplicating membership credit from SP002 or SP004.
decision_checks = {
    "status": get(prediction, "close_status", "status")
    == get(gold, "close_status", "status"),
    "routing": get(prediction, "close_status", "routing")
    == get(gold, "close_status", "routing"),
}
pred_ledger_rows = index_objects(
    get(prediction, "decision_panels", "ledger_routing"), "charge_id"
)
gold_ledger_rows = index_objects(
    get(gold, "decision_panels", "ledger_routing"), "charge_id"
)
ledger_decision_checks = {
    "charge_id_set": set(pred_ledger_rows) == set(gold_ledger_rows)
}
for charge_id in sorted(gold_ledger_rows):
    ledger_decision_checks[f"{charge_id}.decision_code"] = (
        get(pred_ledger_rows.get(charge_id, {}), "decision_code")
        == get(gold_ledger_rows[charge_id], "decision_code")
    )
fractions["SP008"] = (
    0.40 * mean(decision_checks.values())
    + 0.60 * mean(ledger_decision_checks.values())
)
subchecks["SP008"] = {
    "close_decision": decision_checks,
    "ledger_routing_decisions": ledger_decision_checks,
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
