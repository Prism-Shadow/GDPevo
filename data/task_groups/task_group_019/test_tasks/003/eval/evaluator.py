#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED = {
    "task_id": "test_003",
    "review_month": "2026-05",
    "application_id": "AA-2026-0036",
    "premises_id": "PM-2026-036",
    "recommendation": "ISSUE_RESTRICTED_WITH_MONITORING",
    "risk_assessment": {
        "same_premises_basis": "SAME_ADDRESS_OVERLAP",
        "prior_licensee": "Signal Hospitality LLC",
        "prior_incident_level": "HIGH",
        "incident_count": 6,
        "unresolved_incident_count": 2,
        "high_severity_incident_count": 3,
        "unresolved_incident_ids": ["AI-2026-0071", "AI-2026-0097"],
        "high_severity_incident_ids": ["AI-2026-0012", "AI-2026-0071", "AI-2026-0111"],
        "settlement_posture": "PRIOR_RESTRICTED_OR_DENIAL",
        "control_overlap": "OVERLAPS_PRIOR_FAILED_CONTROLS",
        "successor_risk_classification": "HIGH",
        "overall_risk": "SEVERE",
    },
    "classification_summary": {
        "standard_obligation_count": 5,
        "location_specific_restriction_count": 2,
        "current_controls_overlap_prior_risk": True,
        "standard_obligations_kept_separate": True,
    },
    "standard_obligations": {
        "F_COM_FOOD": {
            "source_obligation_id": "AO-2026-0001",
            "evidence_required": "menu, invoices",
        },
        "F_COM_MINORS": {
            "source_obligation_id": "AO-2026-0003",
            "evidence_required": "photo evidence",
        },
        "F_COM_SERVER": {
            "source_obligation_id": "AO-2026-0002",
            "evidence_required": "training roster",
        },
        "INCIDENT_REPORT": {
            "source_obligation_id": "AO-2026-0014",
            "evidence_required": "incident report log",
        },
        "PUBLIC_RECORDS": {
            "source_obligation_id": "AO-2026-0013",
            "evidence_required": "records binder",
        },
    },
    "location_specific_restrictions": {
        "NO_AFTER_MIDNIGHT_SERVICE": {
            "source_ids": ["AR-2026-0024"],
            "overlap_status": "OVERLAPS_PRIOR_FAILED_CONTROL",
            "evidence_required": "service log",
            "first_90_day_focus": "SERVICE_LOG_REVIEW",
        },
        "SECURITY_LOG": {
            "source_ids": ["AR-2026-0023"],
            "overlap_status": "OVERLAPS_PRIOR_FAILED_CONTROL",
            "evidence_required": "weekly log",
            "first_90_day_focus": "SECURITY_LOG_REVIEW",
        },
    },
    "verification_gaps": {
        "CONTROL_EFFECTIVENESS_EVIDENCE_NOT_VERIFIED": {
            "source_ids": ["AR-2026-0023", "AR-2026-0024"],
            "status": "MONITOR_IN_FIRST_90_DAYS",
        },
        "PENDING_ASSAULT_CALL_DISPOSITION": {
            "source_ids": ["AI-2026-0097"],
            "status": "REQUEST_BEFORE_FINAL",
        },
        "PRIOR_RESTRICTED_SETTLEMENT_PACKET": {
            "source_ids": ["AS-2026-0012"],
            "status": "VERIFY_BEFORE_RELYING",
        },
        "SAME_PREMISES_SUCCESSOR_STATEMENT_MISSING": {
            "source_ids": ["PM-2026-036"],
            "status": "REQUEST_BEFORE_FINAL",
        },
        "SECURITY_PLAN_LAPSE_DISPOSITION_MISSING": {
            "source_ids": ["AI-2026-0071"],
            "status": "REQUEST_BEFORE_FINAL",
        },
    },
    "inspection_priorities": [
        {
            "priority_rank": 1,
            "priority_code": "SECURITY_LOG_REVIEW",
            "target_control_code": "SECURITY_LOG",
            "source_ids": ["AI-2026-0071", "AR-2026-0023"],
            "timing": "FIRST_30_DAYS",
        },
        {
            "priority_rank": 2,
            "priority_code": "POLICE_CALL_LOG_REVIEW",
            "target_control_code": "ASSAULT_CALL_HISTORY",
            "source_ids": ["AI-2026-0012", "AI-2026-0097", "AI-2026-0111"],
            "timing": "FIRST_30_DAYS",
        },
        {
            "priority_rank": 3,
            "priority_code": "AFTER_MIDNIGHT_SERVICE_LOG_REVIEW",
            "target_control_code": "NO_AFTER_MIDNIGHT_SERVICE",
            "source_ids": ["AR-2026-0024"],
            "timing": "FIRST_60_DAYS",
        },
        {
            "priority_rank": 4,
            "priority_code": "F_COM_STANDARD_OBLIGATION_CHECK",
            "target_control_code": "F_COM_STANDARD_OBLIGATIONS",
            "source_ids": [
                "AO-2026-0001",
                "AO-2026-0002",
                "AO-2026-0003",
                "AO-2026-0013",
                "AO-2026-0014",
            ],
            "timing": "FIRST_90_DAYS",
        },
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
        item_key = str(item[key])
        if item_key in result:
            return None
        result[item_key] = item
    return result


def get(pred, *keys):
    cur = pred
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def target_and_recommendation_match(pred):
    return (
        pred.get("task_id") == EXPECTED["task_id"]
        and pred.get("review_month") == EXPECTED["review_month"]
        and pred.get("application_id") == EXPECTED["application_id"]
        and pred.get("premises_id") == EXPECTED["premises_id"]
        and pred.get("recommendation") == EXPECTED["recommendation"]
    )


def risk_classifications_match(pred):
    expected = EXPECTED["risk_assessment"]
    actual = pred.get("risk_assessment")
    if not isinstance(actual, dict):
        return False
    keys = [
        "same_premises_basis",
        "prior_licensee",
        "prior_incident_level",
        "settlement_posture",
        "control_overlap",
        "successor_risk_classification",
        "overall_risk",
    ]
    return all(actual.get(key) == expected[key] for key in keys)


def risk_counts_and_sources_match(pred):
    expected = EXPECTED["risk_assessment"]
    actual = pred.get("risk_assessment")
    if not isinstance(actual, dict):
        return False
    return (
        actual.get("incident_count") == expected["incident_count"]
        and actual.get("unresolved_incident_count") == expected["unresolved_incident_count"]
        and actual.get("high_severity_incident_count") == expected["high_severity_incident_count"]
        and sorted_strings(actual.get("unresolved_incident_ids")) == expected["unresolved_incident_ids"]
        and sorted_strings(actual.get("high_severity_incident_ids")) == expected["high_severity_incident_ids"]
    )


def classification_summary_match(pred):
    actual = get(pred, "controls_classification", "classification_summary")
    return actual == EXPECTED["classification_summary"]


def standard_obligations_match(pred):
    items = get(pred, "controls_classification", "standard_obligations")
    item_map = map_by_key(items, "obligation_code")
    if item_map is None or set(item_map) != set(EXPECTED["standard_obligations"]):
        return False
    for code, expected in EXPECTED["standard_obligations"].items():
        actual = item_map[code]
        if actual.get("source_obligation_id") != expected["source_obligation_id"]:
            return False
        if actual.get("evidence_required") != expected["evidence_required"]:
            return False
    return True


def location_controls_match(pred):
    items = get(pred, "controls_classification", "location_specific_restrictions")
    item_map = map_by_key(items, "control_code")
    if item_map is None or set(item_map) != set(EXPECTED["location_specific_restrictions"]):
        return False
    for code, expected in EXPECTED["location_specific_restrictions"].items():
        actual = item_map[code]
        if sorted_strings(actual.get("source_ids")) != expected["source_ids"]:
            return False
        if actual.get("overlap_status") != expected["overlap_status"]:
            return False
        if actual.get("evidence_required") != expected["evidence_required"]:
            return False
        if actual.get("first_90_day_focus") != expected["first_90_day_focus"]:
            return False
    return True


def verification_gaps_match(pred):
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


def inspection_priorities_match(pred):
    items = pred.get("inspection_priorities")
    if not isinstance(items, list) or len(items) != len(EXPECTED["inspection_priorities"]):
        return False
    try:
        ordered = sorted(items, key=lambda item: item.get("priority_rank"))
    except Exception:
        return False
    for actual, expected in zip(ordered, EXPECTED["inspection_priorities"]):
        if not isinstance(actual, dict):
            return False
        if actual.get("priority_rank") != expected["priority_rank"]:
            return False
        if actual.get("priority_code") != expected["priority_code"]:
            return False
        if actual.get("target_control_code") != expected["target_control_code"]:
            return False
        if sorted_strings(actual.get("source_ids")) != expected["source_ids"]:
            return False
        if actual.get("timing") != expected["timing"]:
            return False
    return True


POINTS = [
    (
        "target_recommendation",
        2,
        "Correct target IDs, review month, and issuance recommendation.",
        target_and_recommendation_match,
    ),
    (
        "risk_classifications",
        2,
        "Correct same-premises, settlement, control-overlap, successor-risk, and overall-risk classifications.",
        risk_classifications_match,
    ),
    (
        "risk_counts_and_sources",
        2,
        "Correct incident counts and source IDs for unresolved and high-severity incidents.",
        risk_counts_and_sources_match,
    ),
    (
        "controls_summary",
        2,
        "Correct standard/location-specific counts and separation/overlap flags.",
        classification_summary_match,
    ),
    (
        "standard_obligations",
        2,
        "Correct F-COM plus all-license standard obligation set with source IDs and evidence.",
        standard_obligations_match,
    ),
    (
        "location_specific_controls",
        3,
        "Correct premises-specific restriction set, overlap status, evidence, and first-90-day focus.",
        location_controls_match,
    ),
    (
        "verification_gaps",
        3,
        "Correct verification-gap set with source IDs and statuses.",
        verification_gaps_match,
    ),
    (
        "inspection_priorities",
        3,
        "Correct ranked first-90-day inspection priorities with source IDs and timing.",
        inspection_priorities_match,
    ),
]


def main():
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/answer.json")
    total = sum(weight for _, weight, _, _ in POINTS)
    try:
        pred = json.loads(prediction_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "earned_weight": 0,
                    "total_weight": total,
                    "error": f"invalid_json: {exc}",
                    "points": [
                        {
                            "id": point_id,
                            "description": description,
                            "weight": weight,
                            "passed": False,
                            "score_contribution": 0.0,
                        }
                        for point_id, weight, description, _ in POINTS
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    earned = 0
    point_results = []
    for point_id, weight, description, check in POINTS:
        passed = bool(check(pred))
        if passed:
            earned += weight
        point_results.append(
            {
                "id": point_id,
                "description": description,
                "weight": weight,
                "passed": passed,
                "score_contribution": (weight / total) if passed else 0.0,
            }
        )

    print(
        json.dumps(
            {
                "score": earned / total,
                "earned_weight": earned,
                "total_weight": total,
                "points": point_results,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
