#!/usr/bin/env bash
set -uo pipefail

prediction_path="${1:-}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
gold_path="${script_dir}/../output/answer.json"

python3 - "$prediction_path" "$gold_path" <<'PY'
import json
import math
import os
import sys


PREDICTION_PATH = sys.argv[1]
GOLD_PATH = sys.argv[2]
WEIGHTS = {
    "SP001": 2,
    "SP002": 2,
    "SP003": 3,
    "SP004": 2,
    "SP005": 3,
    "SP006": 2,
    "SP007": 2,
    "SP008": 1,
}
TOTAL_WEIGHT = sum(WEIGHTS.values())


def load_prediction(path):
    if not path:
        return {}, "prediction path argument is required"
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
    except Exception as exc:
        return {}, f"could not parse prediction JSON: {type(exc).__name__}"
    if not isinstance(value, dict):
        return {}, "prediction root must be a JSON object"
    return value, None


def nested(obj, *keys):
    current = obj
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def exact(predicted, expected):
    return predicted == expected


def exact_number(predicted, expected, places):
    if isinstance(predicted, bool) or not isinstance(predicted, (int, float)):
        return False
    if not math.isfinite(float(predicted)):
        return False
    return round(float(predicted), places) == round(float(expected), places)


def augmented_jaccard(predicted, expected):
    expected_set = set(expected)
    if not isinstance(predicted, list):
        return 0.0, {
            "expected_count": len(expected_set),
            "predicted_count": 0,
            "intersection_count": 0,
            "extra_or_duplicate_count": 0,
        }
    valid = [value for value in predicted if isinstance(value, str)]
    predicted_set = set(valid)
    duplicate_excess = len(valid) - len(predicted_set)
    malformed = len(predicted) - len(valid)
    intersection = len(predicted_set & expected_set)
    denominator = len(predicted_set | expected_set) + duplicate_excess + malformed
    fraction = 1.0 if denominator == 0 else intersection / denominator
    return fraction, {
        "expected_count": len(expected_set),
        "predicted_count": len(predicted),
        "intersection_count": intersection,
        "extra_or_duplicate_count": len(predicted_set - expected_set) + duplicate_excess + malformed,
    }


def panel_field_fraction(prediction, gold, field, event_ids):
    predicted_panel = prediction.get("event_decision_panel")
    predicted_panel = predicted_panel if isinstance(predicted_panel, list) else []
    predicted_by_event = {}
    duplicate_ids = []
    malformed_count = 0
    for item in predicted_panel:
        if not isinstance(item, dict) or not isinstance(item.get("event_id"), str):
            malformed_count += 1
            continue
        event_id = item["event_id"]
        if event_id in predicted_by_event:
            duplicate_ids.append(event_id)
            continue
        predicted_by_event[event_id] = item
    gold_by_event = {item["event_id"]: item for item in gold["event_decision_panel"]}
    checks = {
        event_id: exact(
            nested(predicted_by_event.get(event_id, {}), field),
            nested(gold_by_event[event_id], field),
        )
        for event_id in event_ids
    }
    return sum(checks.values()) / len(checks), {
        "field": field,
        "event_checks": checks,
        "duplicate_event_ids": duplicate_ids,
        "malformed_item_count": malformed_count,
    }


def add_point(results, point_id, goal, earned_fraction, subchecks):
    earned_fraction = min(1.0, max(0.0, float(earned_fraction)))
    raw_weight = WEIGHTS[point_id]
    maximum = raw_weight / TOTAL_WEIGHT
    earned = maximum * earned_fraction
    results.append({
        "point_id": point_id,
        "goal": goal,
        "raw_weight": raw_weight,
        "max_normalized_weight": maximum,
        "earned_fraction": earned_fraction,
        "earned_normalized_weight": earned,
        "subchecks": subchecks,
    })


with open(GOLD_PATH, "r", encoding="utf-8") as handle:
    gold = json.load(handle)
prediction, parse_error = load_prediction(PREDICTION_PATH)
rubric = []

# SP001: source and snapshot decision.
source_checks = {
    "authoritative_snapshot_id": exact(
        nested(prediction, "source_decision", "authoritative_snapshot_id"),
        nested(gold, "source_decision", "authoritative_snapshot_id"),
    ),
    "snapshot_status": exact(
        nested(prediction, "source_decision", "snapshot_status"),
        nested(gold, "source_decision", "snapshot_status"),
    ),
    "authoritative_row_count": exact(
        nested(prediction, "source_decision", "authoritative_row_count"),
        nested(gold, "source_decision", "authoritative_row_count"),
    ),
    "scoped_raw_row_count": exact(
        nested(prediction, "source_decision", "scoped_raw_row_count"),
        nested(gold, "source_decision", "scoped_raw_row_count"),
    ),
}
source_fraction = (
    0.32 * source_checks["authoritative_snapshot_id"]
    + 0.12 * source_checks["snapshot_status"]
    + 0.20 * source_checks["authoritative_row_count"]
    + 0.16 * source_checks["scoped_raw_row_count"]
)
unique_source_fraction, unique_source_details = panel_field_fraction(
    prediction,
    gold,
    "maintenance_source_code",
    [
        "ME-Q1-000002",
        "ME-Q1-000007",
        "ME-Q1-000263",
        "ME-Q1-000275",
        "ME-Q1-000823",
        "ME-Q1-001100",
    ],
)
source_fraction += 0.20 * unique_source_fraction
add_point(
    rubric,
    "SP001",
    "Identify the authoritative snapshot, source population, and unique-event source codes.",
    source_fraction,
    {**source_checks, "unique_event_source_codes": unique_source_details},
)

# SP002: six independently observed integrity-class counts.
issue_keys = [
    "missing_timestamp",
    "invalid_timestamp",
    "invalid_odometer",
    "negative_labor",
    "extreme_labor",
    "odometer_regression",
]
issue_checks = {
    key: exact(nested(prediction, "issue_counts", key), nested(gold, "issue_counts", key))
    for key in issue_keys
}
add_point(
    rubric,
    "SP002",
    "Report the missing, parse, range, and sequence issue counts.",
    sum(issue_checks.values()) / len(issue_checks),
    issue_checks,
)

# SP003: duplicate discovery, membership, and retained-record decisions.
gold_groups = {item["logical_event_id"]: item for item in gold["duplicate_groups"]}
predicted_groups_raw = prediction.get("duplicate_groups")
predicted_groups_raw = predicted_groups_raw if isinstance(predicted_groups_raw, list) else []
predicted_group_entries = [
    item for item in predicted_groups_raw
    if isinstance(item, dict) and isinstance(item.get("logical_event_id"), str)
]
predicted_group_ids = [item["logical_event_id"] for item in predicted_group_entries]
predicted_group_id_set = set(predicted_group_ids)
gold_group_id_set = set(gold_groups)
duplicate_or_malformed_count = (
    len(predicted_group_ids) - len(predicted_group_id_set)
    + len(predicted_groups_raw) - len(predicted_group_entries)
)
group_denominator = max(len(gold_group_id_set), len(predicted_group_ids)) + (len(predicted_groups_raw) - len(predicted_group_entries))
group_id_fraction = 0.0 if group_denominator == 0 else len(predicted_group_id_set & gold_group_id_set) / group_denominator
predicted_group_map = {}
for item in predicted_group_entries:
    event_id = item.get("logical_event_id")
    if isinstance(event_id, str) and event_id not in predicted_group_map:
        predicted_group_map[event_id] = item
membership_matches = 0
retention_matches = 0
for event_id, expected_group in gold_groups.items():
    candidate = predicted_group_map.get(event_id, {})
    if candidate.get("snapshot_ids") == expected_group["snapshot_ids"]:
        membership_matches += 1
    if (
        candidate.get("retained_event_id") == expected_group["retained_event_id"]
        and candidate.get("retained_snapshot_id") == expected_group["retained_snapshot_id"]
    ):
        retention_matches += 1
membership_fraction = membership_matches / len(gold_groups)
retention_fraction = retention_matches / len(gold_groups)
duplicate_fraction = 0.40 * group_id_fraction + 0.30 * membership_fraction + 0.30 * retention_fraction
overlap_source_fraction, overlap_source_details = panel_field_fraction(
    prediction,
    gold,
    "maintenance_source_code",
    ["ME-Q1-000001", "ME-Q1-000018"],
)
add_point(
    rubric,
    "SP003",
    "Identify duplicate logical events, retain the correct records, and code scoped overlaps.",
    0.90 * duplicate_fraction + 0.10 * overlap_source_fraction,
    {
        "group_identifier_fraction": round(group_id_fraction, 12),
        "membership_fraction": round(membership_fraction, 12),
        "retention_fraction": round(retention_fraction, 12),
        "expected_group_count": len(gold_groups),
        "predicted_group_count": len(predicted_groups_raw),
        "duplicate_or_malformed_count": duplicate_or_malformed_count,
        "overlap_source_codes": overlap_source_details,
    },
)

# SP004: non-sequence invalid event population.
invalid_fraction, invalid_details = augmented_jaccard(
    prediction.get("invalid_event_ids"), gold["invalid_event_ids"]
)
invalid_route_fraction, invalid_route_details = panel_field_fraction(
    prediction,
    gold,
    "history_route_code",
    ["ME-Q1-000001", "ME-Q1-000263", "ME-Q1-001100"],
)
add_point(
    rubric,
    "SP004",
    "Identify non-sequence invalid events and code their scoped history routes.",
    0.75 * invalid_fraction + 0.25 * invalid_route_fraction,
    {"invalid_event_set": invalid_details, "invalid_event_route_codes": invalid_route_details},
)

# SP005: regression assets and events are separate natural subchecks.
reg_asset_fraction, reg_asset_details = augmented_jaccard(
    nested(prediction, "corrected_metrics", "regression_asset_ids"),
    nested(gold, "corrected_metrics", "regression_asset_ids"),
)
reg_event_fraction, reg_event_details = augmented_jaccard(
    nested(prediction, "corrected_metrics", "regression_event_ids"),
    nested(gold, "corrected_metrics", "regression_event_ids"),
)
regression_route_fraction, regression_route_details = panel_field_fraction(
    prediction,
    gold,
    "history_route_code",
    ["ME-Q1-000275", "ME-Q1-000823"],
)
add_point(
    rubric,
    "SP005",
    "Identify unit-normalized odometer regressions and code their scoped history routes.",
    0.40 * reg_asset_fraction + 0.40 * reg_event_fraction + 0.20 * regression_route_fraction,
    {
        "asset_set_fraction": round(reg_asset_fraction, 12),
        "asset_set_details": reg_asset_details,
        "event_set_fraction": round(reg_event_fraction, 12),
        "event_set_details": reg_event_details,
        "regression_event_route_codes": regression_route_details,
    },
)

# SP006: corrected population and distance rollup.
metric_checks = {
    "valid_event_count": exact(
        nested(prediction, "corrected_metrics", "valid_event_count"),
        nested(gold, "corrected_metrics", "valid_event_count"),
    ),
    "total_distance_km": exact_number(
        nested(prediction, "corrected_metrics", "total_distance_km"),
        nested(gold, "corrected_metrics", "total_distance_km"),
        2,
    ),
}
add_point(
    rubric,
    "SP006",
    "Calculate the corrected valid-event population and fleet distance.",
    0.40 * metric_checks["valid_event_count"] + 0.60 * metric_checks["total_distance_km"],
    metric_checks,
)

# SP007: selected asset set, ordering, and ranking metrics.
gold_ranking = gold["asset_risk_ranking"]
predicted_ranking = prediction.get("asset_risk_ranking")
predicted_ranking = predicted_ranking if isinstance(predicted_ranking, list) else []
gold_asset_ids = [item["asset_id"] for item in gold_ranking]
predicted_asset_ids = [
    item.get("asset_id")
    if isinstance(item, dict) and isinstance(item.get("asset_id"), str)
    else f"__MALFORMED_RANKING_ITEM_{index}__"
    for index, item in enumerate(predicted_ranking)
]
ranking_set_fraction, ranking_set_details = augmented_jaccard(predicted_asset_ids, gold_asset_ids)
position_matches = 0
for index, expected in enumerate(gold_ranking):
    if index < len(predicted_ranking) and isinstance(predicted_ranking[index], dict):
        candidate = predicted_ranking[index]
        if candidate.get("asset_id") == expected["asset_id"] and candidate.get("rank") == expected["rank"]:
            position_matches += 1
position_fraction = position_matches / len(gold_ranking)
predicted_by_asset = {
    item.get("asset_id"): item
    for item in predicted_ranking
    if isinstance(item, dict) and isinstance(item.get("asset_id"), str)
}
metric_matches = 0
for expected in gold_ranking:
    candidate = predicted_by_asset.get(expected["asset_id"], {})
    if (
        candidate.get("rejected_event_count") == expected["rejected_event_count"]
        and candidate.get("regression_event_count") == expected["regression_event_count"]
    ):
        metric_matches += 1
ranking_metric_fraction = metric_matches / len(gold_ranking)
add_point(
    rubric,
    "SP007",
    "Rank the highest-risk assets using corrected rejected-event metrics.",
    0.30 * ranking_set_fraction + 0.50 * position_fraction + 0.20 * ranking_metric_fraction,
    {
        "asset_set_fraction": round(ranking_set_fraction, 12),
        "asset_set_details": ranking_set_details,
        "position_fraction": round(position_fraction, 12),
        "metric_fraction": round(ranking_metric_fraction, 12),
    },
)

# SP008: controlled certification and routing decisions.
status_checks = {
    "status": exact(
        nested(prediction, "certification_status", "status"),
        nested(gold, "certification_status", "status"),
    ),
    "action": exact(
        nested(prediction, "certification_status", "action"),
        nested(gold, "certification_status", "action"),
    ),
}
reliable_route_fraction, reliable_route_details = panel_field_fraction(
    prediction,
    gold,
    "history_route_code",
    ["ME-Q1-000002", "ME-Q1-000007", "ME-Q1-000018"],
)
add_point(
    rubric,
    "SP008",
    "Return the certification decision and code scoped reliable-history routes.",
    0.35 * status_checks["status"] + 0.35 * status_checks["action"] + 0.30 * reliable_route_fraction,
    {**status_checks, "reliable_event_route_codes": reliable_route_details},
)

score = round(
    sum(item["earned_normalized_weight"] for item in rubric),
    12,
)
score = min(1.0, max(0.0, score))
result = {
    "score": score,
    "correct": abs(score - 1.0) < 1e-12,
    "prediction_path": PREDICTION_PATH,
    "parse_error": parse_error,
    "total_raw_weight": TOTAL_WEIGHT,
    "rubric": rubric,
}
print(json.dumps(result, ensure_ascii=True, sort_keys=True))
PY
