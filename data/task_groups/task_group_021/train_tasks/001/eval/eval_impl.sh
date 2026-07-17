#!/usr/bin/env bash
set -u

if [ "$#" -ne 1 ]; then
  printf '%s\n' '{"score":0.0,"total_score":0.0,"valid_json":false,"error":"Expected prediction JSON path as the first argument.","points":[]}'
  exit 0
fi

python3 - "$1" <<'PY'
import json
import math
import sys

prediction_path = sys.argv[1]

gold_focus = {
    "partner_onboarding_2026w03-cluster-001": {
        "member_row_ids": ["PAR-C00001", "PAR-C00002", "PAR-C00003"],
        "survivor_row_id": "PAR-C00003",
        "canonical_email": "sofia.smith.0@example-fleet.com",
        "canonical_phone_digits": "2100006500",
        "canonical_city": "Austin",
        "city_source_system": "Compliance Master",
    },
    "partner_onboarding_2026w03-cluster-002": {
        "member_row_ids": ["PAR-C00004", "PAR-C00005", "PAR-C00006"],
        "survivor_row_id": "PAR-C00006",
        "canonical_email": "akira.nguyen.1@example-fleet.com",
        "canonical_phone_digits": "2100022901",
        "canonical_city": "Toronto",
        "city_source_system": "Compliance Master",
    },
    "partner_onboarding_2026w03-cluster-003": {
        "member_row_ids": ["PAR-C00007", "PAR-C00008", "PAR-C00009"],
        "survivor_row_id": "PAR-C00009",
        "canonical_email": "wei.rossi.2@example-fleet.com",
        "canonical_phone_digits": "2100006902",
        "canonical_city": "London",
        "city_source_system": "Compliance Master",
    },
    "partner_onboarding_2026w03-cluster-004": {
        "member_row_ids": ["PAR-C00010", "PAR-C00011", "PAR-C00012"],
        "survivor_row_id": "PAR-C00012",
        "canonical_email": "akira.rossi.3@example-fleet.com",
        "canonical_phone_digits": "2100009803",
        "canonical_city": "Berlin",
        "city_source_system": "Compliance Master",
    },
    "partner_onboarding_2026w03-cluster-005": {
        "member_row_ids": ["PAR-C00013", "PAR-C00014", "PAR-C00015"],
        "survivor_row_id": "PAR-C00015",
        "canonical_email": "liam.silva.4@example-fleet.com",
        "canonical_phone_digits": "2100020304",
        "canonical_city": "Madrid",
        "city_source_system": "Compliance Master",
    },
}

gold_quarantine = {
    "PAR-C00091", "PAR-C00092", "PAR-C00093", "PAR-C00094", "PAR-C00095",
    "PAR-C00096", "PAR-C00097", "PAR-C00098", "PAR-C00099", "PAR-C00100",
    "PAR-C00101", "PAR-C00102", "PAR-C00103", "PAR-C00104", "PAR-C00105",
    "PAR-C00106", "PAR-C00107", "PAR-C00108", "PAR-C00109", "PAR-C00110",
    "PAR-C00111", "PAR-C00112", "PAR-C00113", "PAR-C00114", "PAR-C00115",
}

gold_regions = {
    "BE": 125,
    "England": 125,
    "MD": 125,
    "ON": 125,
    "SG": 125,
    "TX": 125,
}

gold_anchor_codes = {
    "PC-ASTERIA-01": {
        "identity_code": "IC-25",
        "outreach_code": "OR-80",
        "field_provenance_code": "FP-20",
    },
    "PC-ASTERIA-02": {
        "identity_code": "IC-90",
        "outreach_code": "OR-80",
        "field_provenance_code": "FP-20",
    },
}

try:
    with open(prediction_path, "r", encoding="utf-8") as handle:
        prediction = json.load(handle)
    if not isinstance(prediction, dict):
        raise ValueError("Top-level JSON value must be an object.")
    valid_json = True
    error = None
except Exception as exc:
    prediction = {}
    valid_json = False
    error = f"Invalid prediction JSON: {exc}"


def as_object(value):
    return value if isinstance(value, dict) else {}


def objects_by_key(value, key):
    if not isinstance(value, list):
        return {}
    result = {}
    for item in value:
        if isinstance(item, dict) and isinstance(item.get(key), str):
            result[item[key]] = item
    return result


def exact_number(value, expected):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)) and value == expected


def check(name, passed, expected=None, actual=None):
    result = {"name": name, "passed": bool(passed)}
    if expected is not None:
        result["expected"] = expected
    if actual is not None:
        result["actual"] = actual
    return result


points = []
total_raw_weight = 17


def add_point(point_id, raw_weight, subchecks, earned_fraction=None):
    if earned_fraction is None:
        earned_fraction = sum(1 for item in subchecks if item.get("passed")) / len(subchecks) if subchecks else 0.0
    earned_fraction = max(0.0, min(1.0, float(earned_fraction)))
    earned_fraction_display = round(earned_fraction, 12)
    maximum = raw_weight / total_raw_weight
    points.append({
        "point_id": point_id,
        "raw_weight": raw_weight,
        "max_normalized_weight": maximum,
        "earned_fraction": earned_fraction_display,
        "earned_normalized_weight": maximum * earned_fraction_display,
        "subchecks": subchecks,
    })


summary = as_object(prediction.get("quality_summary"))
controls = as_object(prediction.get("control_codes"))
focus_controls = objects_by_key(controls.get("focus_decisions"), "cluster_id")
anchor_controls = objects_by_key(controls.get("anchored_cases"), "case_id")
add_point("SP001", 1, [
    check("raw_row_count", exact_number(summary.get("raw_row_count"), 810), 810, summary.get("raw_row_count")),
    check("canonical_entity_count", exact_number(summary.get("canonical_entity_count"), 750), 750, summary.get("canonical_entity_count")),
    check("readiness_eligible_entity_count", exact_number(summary.get("readiness_eligible_entity_count"), 718), 718, summary.get("readiness_eligible_entity_count")),
    check("duplicate_cluster_count", exact_number(summary.get("duplicate_cluster_count"), 30), 30, summary.get("duplicate_cluster_count")),
])

focus = objects_by_key(prediction.get("focus_clusters"), "cluster_id")
membership_checks = []
for cluster_id in sorted(gold_focus):
    candidate = as_object(focus.get(cluster_id))
    members = candidate.get("member_row_ids")
    members_ok = (
        isinstance(members, list)
        and all(isinstance(item, str) for item in members)
        and len(members) == len(set(members))
        and set(members) == set(gold_focus[cluster_id]["member_row_ids"])
    )
    membership_checks.append(check(f"{cluster_id}.member_row_ids", members_ok))
    membership_checks.append(check(
        f"{cluster_id}.survivor_row_id",
        candidate.get("survivor_row_id") == gold_focus[cluster_id]["survivor_row_id"],
        gold_focus[cluster_id]["survivor_row_id"],
        candidate.get("survivor_row_id"),
    ))
    control_candidate = as_object(focus_controls.get(cluster_id))
    membership_checks.append(check(
        f"{cluster_id}.identity_code",
        control_candidate.get("identity_code") == "IC-70",
        "IC-70",
        control_candidate.get("identity_code"),
    ))
for case_id, expected_codes in sorted(gold_anchor_codes.items()):
    control_candidate = as_object(anchor_controls.get(case_id))
    membership_checks.append(check(
        f"{case_id}.identity_code",
        control_candidate.get("identity_code") == expected_codes["identity_code"],
        expected_codes["identity_code"],
        control_candidate.get("identity_code"),
    ))
add_point("SP002", 3, membership_checks)

contact_checks = []
for cluster_id in sorted(gold_focus):
    candidate = as_object(focus.get(cluster_id))
    contact_checks.append(check(
        f"{cluster_id}.canonical_email",
        candidate.get("canonical_email") == gold_focus[cluster_id]["canonical_email"],
        gold_focus[cluster_id]["canonical_email"],
        candidate.get("canonical_email"),
    ))
    contact_checks.append(check(
        f"{cluster_id}.canonical_phone_digits",
        candidate.get("canonical_phone_digits") == gold_focus[cluster_id]["canonical_phone_digits"],
        gold_focus[cluster_id]["canonical_phone_digits"],
        candidate.get("canonical_phone_digits"),
    ))
add_point("SP003", 3, contact_checks)

quarantine_value = prediction.get("quarantine_row_ids")
if isinstance(quarantine_value, list):
    predicted_quarantine = {item for item in quarantine_value if isinstance(item, str)}
else:
    predicted_quarantine = set()
true_positive = len(predicted_quarantine & gold_quarantine)
false_positive = len(predicted_quarantine - gold_quarantine)
false_negative = len(gold_quarantine - predicted_quarantine)
precision = true_positive / len(predicted_quarantine) if predicted_quarantine else 0.0
recall = true_positive / len(gold_quarantine)
set_fraction = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
quarantine_control = as_object(controls.get("quarantine_result"))
quarantine_code_checks = [
    check("quarantine_result.identity_code", quarantine_control.get("identity_code") == "IC-40", "IC-40", quarantine_control.get("identity_code")),
    check("quarantine_result.outreach_code", quarantine_control.get("outreach_code") == "OR-60", "OR-60", quarantine_control.get("outreach_code")),
    check("quarantine_result.field_provenance_code", quarantine_control.get("field_provenance_code") == "FP-75", "FP-75", quarantine_control.get("field_provenance_code")),
]
quarantine_code_fraction = sum(1 for item in quarantine_code_checks if item.get("passed")) / len(quarantine_code_checks)
add_point("SP004", 2, [
    {
        "name": "quarantine_set_precision",
        "passed": precision == 1.0,
        "value": round(precision, 12),
        "true_positive": true_positive,
        "false_positive": false_positive,
    },
    {
        "name": "quarantine_set_recall",
        "passed": recall == 1.0,
        "value": round(recall, 12),
        "true_positive": true_positive,
        "false_negative": false_negative,
    },
    {
        "name": "quarantine_set_exact",
        "passed": predicted_quarantine == gold_quarantine,
    },
] + quarantine_code_checks, (3 * set_fraction + quarantine_code_fraction) / 4)

city_checks = []
for cluster_id in sorted(gold_focus):
    candidate = as_object(focus.get(cluster_id))
    city_checks.append(check(
        f"{cluster_id}.canonical_city",
        candidate.get("canonical_city") == gold_focus[cluster_id]["canonical_city"],
        gold_focus[cluster_id]["canonical_city"],
        candidate.get("canonical_city"),
    ))
    city_checks.append(check(
        f"{cluster_id}.city_source_system",
        candidate.get("city_source_system") == gold_focus[cluster_id]["city_source_system"],
        gold_focus[cluster_id]["city_source_system"],
        candidate.get("city_source_system"),
    ))
    control_candidate = as_object(focus_controls.get(cluster_id))
    city_checks.append(check(
        f"{cluster_id}.field_provenance_code",
        control_candidate.get("field_provenance_code") == "FP-55",
        "FP-55",
        control_candidate.get("field_provenance_code"),
    ))
for case_id, expected_codes in sorted(gold_anchor_codes.items()):
    control_candidate = as_object(anchor_controls.get(case_id))
    city_checks.append(check(
        f"{case_id}.field_provenance_code",
        control_candidate.get("field_provenance_code") == expected_codes["field_provenance_code"],
        expected_codes["field_provenance_code"],
        control_candidate.get("field_provenance_code"),
    ))
add_point("SP005", 3, city_checks)

readiness = as_object(prediction.get("channel_readiness"))
readiness_gold = {"both": 229, "email_only": 0, "phone_only": 0, "not_ready": 489}
readiness_checks = [
    check(name, exact_number(readiness.get(name), expected), expected, readiness.get(name))
    for name, expected in readiness_gold.items()
]
readiness_codes = as_object(controls.get("readiness_partition"))
readiness_code_gold = {"both": "OR-35", "email_only": "OR-35", "phone_only": "OR-35", "not_ready": "OR-80"}
for name, expected in readiness_code_gold.items():
    readiness_checks.append(check(
        f"readiness_partition.{name}",
        readiness_codes.get(name) == expected,
        expected,
        readiness_codes.get(name),
    ))
for case_id, expected_codes in sorted(gold_anchor_codes.items()):
    control_candidate = as_object(anchor_controls.get(case_id))
    readiness_checks.append(check(
        f"{case_id}.outreach_code",
        control_candidate.get("outreach_code") == expected_codes["outreach_code"],
        expected_codes["outreach_code"],
        control_candidate.get("outreach_code"),
    ))
inactive_control = as_object(controls.get("inactive_exclusion"))
readiness_checks.append(check(
    "inactive_exclusion.outreach_code",
    inactive_control.get("outreach_code") == "OR-15",
    "OR-15",
    inactive_control.get("outreach_code"),
))
add_point("SP006", 2, readiness_checks)

regions = objects_by_key(prediction.get("region_rollup"), "region")
add_point("SP007", 1, [
    check(
        f"{region}.canonical_entity_count",
        exact_number(as_object(regions.get(region)).get("canonical_entity_count"), expected),
        expected,
        as_object(regions.get(region)).get("canonical_entity_count"),
    )
    for region, expected in gold_regions.items()
])

decision = as_object(prediction.get("certification_status"))
rate = summary.get("quarantine_rate")
rate_ok = isinstance(rate, (int, float)) and not isinstance(rate, bool) and math.isfinite(float(rate)) and round(float(rate), 4) == 0.0333
add_point("SP008", 2, [
    check("quarantine_rate_4dp", rate_ok, 0.0333, rate),
    check("certification_status.status", decision.get("status") == "PASS_WITH_EXCEPTIONS", "PASS_WITH_EXCEPTIONS", decision.get("status")),
    check("certification_status.next_action", decision.get("next_action") == "REVIEW_EXCEPTIONS", "REVIEW_EXCEPTIONS", decision.get("next_action")),
])

score = round(sum(item["earned_normalized_weight"] for item in points), 12)
score = max(0.0, min(1.0, score))
result = {
    "score": score,
    "total_score": score,
    "valid_json": valid_json,
    "points": points,
}
if error is not None:
    result["error"] = error
print(json.dumps(result, ensure_ascii=False, sort_keys=True))
PY
