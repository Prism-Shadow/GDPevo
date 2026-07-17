#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED = {
    "recommendation": "ISSUE_RESTRICTED_WITH_MONITORING",
    "successor_risk_classification": "HIGH",
    "verification_gaps": {
        "PENDING_INCIDENT_DISPOSITIONS": {
            "source_ids": ["AI-2026-0008", "AI-2026-0009"],
            "status": "REQUEST_BEFORE_FINAL",
        },
        "POST_REVIEW_SETTLEMENT_TIMING": {
            "source_ids": ["AS-2026-0007"],
            "status": "REQUEST_BEFORE_FINAL",
        },
        "STANDARD_CONTROL_OVERLAP": {
            "source_ids": ["AR-2026-0013"],
            "status": "SEPARATE_FROM_PREMISES_CONTROLS",
        },
        "SUCCESSOR_CONTROL_SEPARATION": {
            "source_ids": ["PM-2026-018"],
            "status": "REQUEST_BEFORE_FINAL",
        },
    },
    "standard_obligation_codes": [
        "BREW_PRODUCTION",
        "BREW_SAMPLES",
        "BREW_TRAINING",
        "INCIDENT_REPORT",
        "PUBLIC_RECORDS",
    ],
    "premises_specific_controls": {
        "AGE_CHECK": {
            "source_ids": ["AR-2026-0014"],
            "check_code": "DEVICE_AUDIT",
            "first_90_day_check": True,
        },
        "LATE_NIGHT_DISORDER_MONITORING": {
            "source_ids": ["AI-2026-0008", "AI-2026-0145"],
            "check_code": "POLICE_CALL_LOG_REVIEW",
            "first_90_day_check": True,
        },
        "QUARTERLY_INSPECTION_CONDITION": {
            "source_ids": ["AS-2026-0007"],
            "check_code": "SITE_INSPECTION",
            "first_90_day_check": True,
        },
        "SECURITY_PLAN_LAPSE_REVIEW": {
            "source_ids": ["AI-2026-0086"],
            "check_code": "SECURITY_LOG_REVIEW",
            "first_90_day_check": True,
        },
    },
    "record_request_codes": [
        "AGE_VERIFICATION_DEVICE_AUDIT",
        "BREWPUB_STANDARD_OBLIGATION_EVIDENCE",
        "FIRST_90_DAY_INSPECTION_CALENDAR",
        "PENDING_INCIDENT_DISPOSITION_PACKET",
        "SUCCESSOR_OWNERSHIP_AND_SERVICE_AREA_STATEMENT",
    ],
    "escalation_trigger_codes": [
        "AGE_CHECK_AUDIT_MISSING_OR_FAILED",
        "FIRST_90_DAY_CHECK_MISSED",
        "NEW_OR_CONFIRMED_HIGH_SEVERITY_INCIDENT",
        "PENDING_INCIDENT_CONFIRMED_VIOLATION",
        "SUCCESSOR_LINK_CONFIRMED_TO_PRIOR_LICENSEE",
    ],
}


def sorted_strings(value):
    if not isinstance(value, list):
        return None
    return sorted(str(item) for item in value)


def map_by_key(items, key):
    if not isinstance(items, list):
        return None
    result = {}
    for item in items:
        if not isinstance(item, dict) or key not in item:
            return None
        result[str(item[key])] = item
    return result


def gap_map_matches(pred):
    gap_map = map_by_key(pred.get("verification_gaps"), "gap_code")
    if gap_map is None or set(gap_map) != set(EXPECTED["verification_gaps"]):
        return False
    for code, expected in EXPECTED["verification_gaps"].items():
        actual = gap_map[code]
        if sorted_strings(actual.get("source_ids")) != expected["source_ids"]:
            return False
        if actual.get("status") != expected["status"]:
            return False
    return True


def obligation_codes_match(pred):
    items = pred.get("standard_obligations")
    if not isinstance(items, list):
        return False
    codes = sorted(str(item.get("obligation_code")) for item in items if isinstance(item, dict))
    return codes == EXPECTED["standard_obligation_codes"]


def controls_match(pred):
    control_map = map_by_key(pred.get("premises_specific_controls"), "control_code")
    if control_map is None or set(control_map) != set(EXPECTED["premises_specific_controls"]):
        return False
    for code, expected in EXPECTED["premises_specific_controls"].items():
        actual = control_map[code]
        if sorted_strings(actual.get("source_ids")) != expected["source_ids"]:
            return False
        if actual.get("check_code") != expected["check_code"]:
            return False
        if actual.get("first_90_day_check") is not expected["first_90_day_check"]:
            return False
    return True


def item_codes_match(pred, field, key, expected):
    items = pred.get(field)
    if not isinstance(items, list):
        return False
    codes = sorted(str(item.get(key)) for item in items if isinstance(item, dict))
    return codes == expected


POINTS = [
    (
        "recommendation",
        2,
        lambda p: (
            p.get("task_id") == "train_005"
            and p.get("review_month") == "2026-03"
            and p.get("application_id") == "AA-2026-0018"
            and p.get("premises_id") == "PM-2026-018"
            and p.get("recommendation") == EXPECTED["recommendation"]
        ),
    ),
    (
        "successor_risk_classification",
        2,
        lambda p: p.get("successor_risk_classification") == EXPECTED["successor_risk_classification"],
    ),
    ("verification_gaps", 2, gap_map_matches),
    ("standard_obligations", 2, obligation_codes_match),
    ("premises_specific_controls", 3, controls_match),
    (
        "records_requests",
        2,
        lambda p: item_codes_match(
            p,
            "records_requests",
            "request_code",
            EXPECTED["record_request_codes"],
        ),
    ),
    (
        "escalation_triggers",
        2,
        lambda p: item_codes_match(
            p,
            "escalation_triggers",
            "trigger_code",
            EXPECTED["escalation_trigger_codes"],
        ),
    ),
]


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/answer.json")
    total = sum(weight for _, weight, _ in POINTS)
    try:
        pred = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(json.dumps({"score": 0.0, "earned_weight": 0, "total_weight": total, "error": str(exc)}))
        return 0

    earned = 0
    checks = []
    for name, weight, check in POINTS:
        passed = bool(check(pred))
        if passed:
            earned += weight
        checks.append({"id": name, "weight": weight, "passed": passed})

    print(
        json.dumps(
            {
                "score": earned / total,
                "earned_weight": earned,
                "total_weight": total,
                "checks": checks,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
