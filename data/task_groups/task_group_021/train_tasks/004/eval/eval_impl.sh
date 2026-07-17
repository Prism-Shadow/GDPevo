#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  printf '%s\n' '{"score":0.0,"correct":false,"error":"usage: eval.sh <prediction.json>","details":[]}'
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOLD_PATH="$SCRIPT_DIR/../output/answer.json"

python3 - "$1" "$GOLD_PATH" <<'PY'
import json
import sys

prediction_path, gold_path = sys.argv[1], sys.argv[2]
weights = {
    "SP001": 1,
    "SP002": 3,
    "SP003": 3,
    "SP004": 2,
    "SP005": 2,
    "SP006": 2,
    "SP007": 2,
    "SP008": 1,
}
total_weight = sum(weights.values())


def point(point_id, fraction, subchecks):
    fraction = max(0.0, min(1.0, float(fraction)))
    maximum = weights[point_id] / total_weight
    return {
        "point_id": point_id,
        "raw_weight": weights[point_id],
        "max_normalized_weight": round(maximum, 6),
        "earned_fraction": round(fraction, 6),
        "earned_normalized_weight": round(maximum * fraction, 6),
        "subchecks": subchecks,
    }


def index_by(value, key):
    result = {}
    if not isinstance(value, list):
        return result
    for item in value:
        if isinstance(item, dict) and isinstance(item.get(key), str):
            result[item[key]] = item
    return result


def normalized_string_set(value):
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str)}


def equal_list_as_set(actual, expected):
    return normalized_string_set(actual) == normalized_string_set(expected)


def average_checks(checks):
    if not checks:
        return 0.0
    return sum(1.0 for item in checks if item["passed"]) / len(checks)


with open(gold_path, "r", encoding="utf-8") as handle:
    gold = json.load(handle)

try:
    with open(prediction_path, "r", encoding="utf-8") as handle:
        candidate = json.load(handle)
    if not isinstance(candidate, dict):
        raise ValueError("prediction root must be a JSON object")
except Exception as exc:
    details = [
        point(point_id, 0.0, [{"name": "prediction_parse", "passed": False}])
        for point_id in weights
    ]
    print(json.dumps({
        "score": 0.0,
        "correct": False,
        "error": f"invalid prediction: {exc}",
        "details": details,
    }, ensure_ascii=False, sort_keys=True))
    sys.exit(0)

details = []

# SP001: independent merge and readiness summary counts.
summary_fields = [
    "raw_row_count",
    "canonical_person_count",
    "merged_duplicate_cluster_count",
    "quarantine_row_count",
    "contested_identifier_cluster_count",
    "dispatchable_person_count",
]
actual_summary = candidate.get("merge_summary", {})
gold_summary = gold["merge_summary"]
checks = []
for field in summary_fields:
    passed = isinstance(actual_summary, dict) and actual_summary.get(field) == gold_summary[field]
    checks.append({"name": field, "passed": passed})
details.append(point("SP001", average_checks(checks), checks))

# SP002: focus-person membership and stable master selection.
actual_focus = index_by(candidate.get("focus_people"), "focus_person_id")
gold_focus = index_by(gold["focus_people"], "focus_person_id")
checks = []
for focus_id in sorted(gold_focus):
    actual = actual_focus.get(focus_id, {})
    expected = gold_focus[focus_id]
    checks.append({
        "name": f"{focus_id}.member_row_ids",
        "passed": equal_list_as_set(actual.get("member_row_ids"), expected["member_row_ids"]),
    })
    checks.append({
        "name": f"{focus_id}.master_id",
        "passed": actual.get("master_id") == expected["master_id"],
    })
details.append(point("SP002", average_checks(checks), checks))

# SP003: canonical identity, channel, depot, consent, and status fields.
canonical_fields = [
    "canonical_name",
    "canonical_email",
    "canonical_phone_digits",
    "canonical_city",
    "depot_code",
    "canonical_consent_status",
    "canonical_record_status",
]
checks = []
for focus_id in sorted(gold_focus):
    actual = actual_focus.get(focus_id, {})
    expected = gold_focus[focus_id]
    for field in canonical_fields:
        checks.append({
            "name": f"{focus_id}.{field}",
            "passed": actual.get(field) == expected[field],
        })
details.append(point("SP003", average_checks(checks), checks))

# SP004: identifier classifications and the four identity-family controls.
actual_contested = normalized_string_set(candidate.get("contested_cluster_ids"))
gold_contested = normalized_string_set(gold["contested_cluster_ids"])
allowed_cases = {
    "IDENTIFIER-CASE-001",
    "IDENTIFIER-CASE-002",
    "IDENTIFIER-CASE-003",
}
weighted_case_checks = []
for case_id, check_weight in [
    ("IDENTIFIER-CASE-001", 0.50),
    ("IDENTIFIER-CASE-002", 0.125),
    ("IDENTIFIER-CASE-003", 0.125),
]:
    passed = (case_id in actual_contested) == (case_id in gold_contested)
    weighted_case_checks.append((check_weight, {
        "name": f"classification.{case_id}",
        "passed": passed,
    }))
no_unknown = actual_contested.issubset(allowed_cases)
weighted_case_checks.append((0.25, {"name": "no_unknown_case_ids", "passed": no_unknown}))
identifier_fraction = sum(weight for weight, check in weighted_case_checks if check["passed"])
actual_controls = index_by(candidate.get("policy_control_cases"), "control_case_id")
gold_controls = index_by(gold["policy_control_cases"], "control_case_id")
identity_checks = []
for case_id in ["CONTROL-001", "CONTROL-002", "CONTROL-003", "CONTROL-004"]:
    actual = actual_controls.get(case_id, {})
    expected = gold_controls[case_id]
    identity_checks.append({
        "name": f"{case_id}.control_code",
        "passed": actual.get("control_code") == expected["control_code"],
    })
identity_fraction = average_checks(identity_checks)
checks = [check for _, check in weighted_case_checks] + identity_checks
details.append(point("SP004", (identifier_fraction + identity_fraction) / 2.0, checks))

# SP005: dispatchable master population, with independent precision and recall.
actual_ready = normalized_string_set(candidate.get("dispatchable_master_ids"))
gold_ready = normalized_string_set(gold["dispatchable_master_ids"])
intersection = len(actual_ready & gold_ready)
precision = intersection / len(actual_ready) if actual_ready else 0.0
recall = intersection / len(gold_ready) if gold_ready else 1.0
set_fraction = (precision + recall) / 2.0
checks = [
    {
        "name": "dispatchable_set_precision",
        "passed": precision == 1.0,
        "value": round(precision, 6),
    },
    {
        "name": "dispatchable_set_recall",
        "passed": recall == 1.0,
        "value": round(recall, 6),
    },
]
details.append(point("SP005", set_fraction, checks))

# SP006: depot-level readiness is a separate aggregate question.
actual_depots = index_by(candidate.get("readiness_by_depot"), "depot_code")
gold_depots = index_by(gold["readiness_by_depot"], "depot_code")
depot_fields = [
    "total_person_count",
    "dispatchable_person_count",
    "blocked_consent_count",
    "blocked_no_contact_count",
    "blocked_inactive_count",
]
checks = []
for depot_code in sorted(gold_depots):
    actual = actual_depots.get(depot_code, {})
    expected = gold_depots[depot_code]
    for field in depot_fields:
        checks.append({
            "name": f"{depot_code}.{field}",
            "passed": actual.get(field) == expected[field],
        })
details.append(point("SP006", average_checks(checks), checks))

# SP007: field-level source outcomes and provenance/outreach controls.
source_fields = [
    "name_source_system",
    "contact_source_system",
    "depot_source_system",
    "consent_source_system",
    "resolution_outcome",
]
checks = []
for focus_id in sorted(gold_focus):
    actual = actual_focus.get(focus_id, {})
    expected = gold_focus[focus_id]
    for field in source_fields:
        checks.append({
            "name": f"{focus_id}.{field}",
            "passed": actual.get(field) == expected[field],
        })
source_fraction = average_checks(checks)
control_checks = []
for case_id in [
    "CONTROL-005",
    "CONTROL-006",
    "CONTROL-007",
    "CONTROL-008",
    "CONTROL-009",
    "CONTROL-010",
    "CONTROL-011",
]:
    actual = actual_controls.get(case_id, {})
    expected = gold_controls[case_id]
    for field in ["control_family", "evidence_row_ids", "control_code"]:
        if field == "evidence_row_ids":
            passed = equal_list_as_set(actual.get(field), expected[field])
        else:
            passed = actual.get(field) == expected[field]
        control_checks.append({"name": f"{case_id}.{field}", "passed": passed})
control_fraction = average_checks(control_checks)
details.append(point("SP007", (source_fraction + control_fraction) / 2.0, checks + control_checks))

# SP008: release status and operational action are independent controlled choices.
actual_decision = candidate.get("release_decision", {})
gold_decision = gold["release_decision"]
checks = []
for field in ["status", "action"]:
    checks.append({
        "name": field,
        "passed": isinstance(actual_decision, dict) and actual_decision.get(field) == gold_decision[field],
    })
details.append(point("SP008", average_checks(checks), checks))

score = round(sum(item["earned_normalized_weight"] for item in details), 6)
result = {
    "score": score,
    "correct": score >= 0.999999,
    "details": details,
}
print(json.dumps(result, ensure_ascii=False, sort_keys=True))
PY
