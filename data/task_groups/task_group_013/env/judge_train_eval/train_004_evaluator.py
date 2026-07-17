#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


GOLD: dict[str, Any] = {
    "program_code": "DMHTN-2026A",
    "as_of_date": "2026-07-15",
    "patients": [
        {
            "patient_id": "P026",
            "eligible": True,
            "enrollment_status": "enroll",
            "reason_codes": ["meets_dmhtn_criteria", "recent_hospitalization_high_touch"],
            "follow_up_cadence": "weekly",
            "missing_chart_artifacts": [],
            "outreach_channel": "portal",
            "initial_monitoring_package": {
                "package_type": "high_touch_dm_htn",
                "components": [
                    "bp_cuff",
                    "glucometer",
                    "lab_order_a1c_cmp_lipid",
                    "medication_reconciliation",
                    "care_plan_setup",
                ],
                "first_checkin_days": 7,
            },
        },
        {
            "patient_id": "P027",
            "eligible": True,
            "enrollment_status": "enroll",
            "reason_codes": ["meets_dmhtn_criteria", "low_adherence_high_touch"],
            "follow_up_cadence": "weekly",
            "missing_chart_artifacts": [],
            "outreach_channel": "phone",
            "initial_monitoring_package": {
                "package_type": "high_touch_dm_htn",
                "components": [
                    "bp_cuff",
                    "glucometer",
                    "lab_order_a1c_cmp_lipid",
                    "medication_reconciliation",
                    "care_plan_setup",
                ],
                "first_checkin_days": 7,
            },
        },
        {
            "patient_id": "P028",
            "eligible": True,
            "enrollment_status": "reject",
            "reason_codes": ["consent_declined", "chart_not_active"],
            "follow_up_cadence": "none",
            "missing_chart_artifacts": ["chart_record"],
            "outreach_channel": "phone",
            "initial_monitoring_package": {
                "package_type": "not_applicable",
                "components": [],
                "first_checkin_days": None,
            },
        },
        {
            "patient_id": "P029",
            "eligible": True,
            "enrollment_status": "enroll",
            "reason_codes": ["meets_dmhtn_criteria", "ckd_biweekly_monitoring"],
            "follow_up_cadence": "biweekly",
            "missing_chart_artifacts": [],
            "outreach_channel": "phone",
            "initial_monitoring_package": {
                "package_type": "standard_dm_htn",
                "components": [
                    "bp_cuff",
                    "glucometer",
                    "lab_order_a1c_cmp_lipid",
                    "medication_reconciliation",
                ],
                "first_checkin_days": 14,
            },
        },
        {
            "patient_id": "P030",
            "eligible": True,
            "enrollment_status": "enroll",
            "reason_codes": ["meets_dmhtn_criteria", "recent_ed_high_touch"],
            "follow_up_cadence": "weekly",
            "missing_chart_artifacts": [],
            "outreach_channel": "email",
            "initial_monitoring_package": {
                "package_type": "high_touch_dm_htn",
                "components": [
                    "bp_cuff",
                    "glucometer",
                    "lab_order_a1c_cmp_lipid",
                    "medication_reconciliation",
                    "care_plan_setup",
                ],
                "first_checkin_days": 7,
            },
        },
        {
            "patient_id": "P031",
            "eligible": True,
            "enrollment_status": "reject",
            "reason_codes": ["consent_declined", "chart_not_active"],
            "follow_up_cadence": "none",
            "missing_chart_artifacts": ["chart_record"],
            "outreach_channel": "email",
            "initial_monitoring_package": {
                "package_type": "not_applicable",
                "components": [],
                "first_checkin_days": None,
            },
        },
        {
            "patient_id": "P032",
            "eligible": True,
            "enrollment_status": "enroll",
            "reason_codes": ["meets_dmhtn_criteria"],
            "follow_up_cadence": "monthly",
            "missing_chart_artifacts": [],
            "outreach_channel": "portal",
            "initial_monitoring_package": {
                "package_type": "standard_dm_htn",
                "components": ["bp_cuff", "glucometer", "lab_order_a1c_cmp_lipid"],
                "first_checkin_days": 30,
            },
        },
        {
            "patient_id": "P058",
            "eligible": True,
            "enrollment_status": "hold",
            "reason_codes": [
                "consent_missing",
                "chart_not_active",
                "stale_active_problems",
                "missing_recent_vitals",
                "missing_recent_labs",
                "missing_medication_list",
            ],
            "follow_up_cadence": "deferred",
            "missing_chart_artifacts": [
                "chart_record",
                "active_problems",
                "vitals",
                "labs",
                "medications",
                "consent",
            ],
            "outreach_channel": "email",
            "initial_monitoring_package": {
                "package_type": "deferred",
                "components": ["consent_packet", "chart_update_request"],
                "first_checkin_days": None,
            },
        },
        {
            "patient_id": "P059",
            "eligible": False,
            "enrollment_status": "reject",
            "reason_codes": ["wrong_target_condition", "missing_active_dmhtn_diagnosis"],
            "follow_up_cadence": "none",
            "missing_chart_artifacts": [],
            "outreach_channel": "email",
            "initial_monitoring_package": {
                "package_type": "not_applicable",
                "components": [],
                "first_checkin_days": None,
            },
        },
        {
            "patient_id": "P076",
            "eligible": False,
            "enrollment_status": "reject",
            "reason_codes": [
                "wrong_target_condition",
                "missing_active_dmhtn_diagnosis",
                "consent_declined",
                "chart_not_active",
            ],
            "follow_up_cadence": "none",
            "missing_chart_artifacts": [],
            "outreach_channel": "sms",
            "initial_monitoring_package": {
                "package_type": "not_applicable",
                "components": [],
                "first_checkin_days": None,
            },
        },
    ],
    "summary": {
        "total_candidates": 10,
        "eligible_count": 8,
        "ineligible_count": 2,
        "status_counts": {"enroll": 5, "hold": 1, "reject": 4},
        "follow_up_counts": {"weekly": 3, "biweekly": 1, "monthly": 1, "deferred": 1, "none": 4},
        "outreach_counts": {"phone": 3, "portal": 2, "sms": 1, "email": 4, "none": 0},
        "monitoring_package_counts": {
            "standard_dm_htn": 2,
            "high_touch_dm_htn": 3,
            "deferred": 1,
            "not_applicable": 4,
        },
    },
}


RUBRIC = [
    ("SP001", "Correct eligible and ineligible candidate sets for the full program panel.", 3),
    ("SP002", "Correct enrollment status and normalized reason-code sets for every candidate.", 3),
    ("SP003", "Correct follow-up cadence for each candidate.", 2),
    ("SP004", "Correct missing chart artifact set for each candidate.", 2),
    ("SP005", "Correct outreach channel for each candidate after fallback handling.", 1),
    ("SP006", "Correct initial monitoring package type, component set, and first check-in timing.", 2),
    ("SP007", "Correct cohort summary counts across status, cadence, outreach, and package categories.", 1),
]


def load_answer(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"could not read or parse JSON: {exc}"
    if not isinstance(data, dict):
        return None, "top-level answer must be a JSON object"
    return data, None


def patient_map(answer: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = answer.get("patients")
    if not isinstance(rows, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("patient_id"), str):
            out[row["patient_id"]] = row
    return out


def as_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item) for item in value}


def expected_patients() -> dict[str, dict[str, Any]]:
    return {row["patient_id"]: row for row in GOLD["patients"]}


def check_ids_and_eligibility(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    actual = patient_map(answer)
    gold = expected_patients()
    actual_ids = set(actual)
    gold_ids = set(gold)
    actual_eligible = {pid for pid, row in actual.items() if row.get("eligible") is True}
    gold_eligible = {pid for pid, row in gold.items() if row["eligible"] is True}
    return actual_ids == gold_ids and actual_eligible == gold_eligible, {
        "expected_ids": sorted(gold_ids),
        "actual_ids": sorted(actual_ids),
        "expected_eligible": sorted(gold_eligible),
        "actual_eligible": sorted(actual_eligible),
    }


def check_status_reasons(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    actual = patient_map(answer)
    gold = expected_patients()
    mismatches = []
    for pid, grow in gold.items():
        arow = actual.get(pid, {})
        if arow.get("enrollment_status") != grow["enrollment_status"] or as_set(arow.get("reason_codes")) != set(
            grow["reason_codes"]
        ):
            mismatches.append(
                {
                    "patient_id": pid,
                    "expected_status": grow["enrollment_status"],
                    "actual_status": arow.get("enrollment_status"),
                    "expected_reasons": sorted(grow["reason_codes"]),
                    "actual_reasons": sorted(as_set(arow.get("reason_codes"))),
                }
            )
    return not mismatches and set(actual) == set(gold), {"mismatches": mismatches}


def check_simple_patient_field(answer: dict[str, Any], field: str) -> tuple[bool, dict[str, Any]]:
    actual = patient_map(answer)
    gold = expected_patients()
    mismatches = []
    for pid, grow in gold.items():
        arow = actual.get(pid, {})
        if arow.get(field) != grow[field]:
            mismatches.append({"patient_id": pid, "expected": grow[field], "actual": arow.get(field)})
    return not mismatches and set(actual) == set(gold), {"field": field, "mismatches": mismatches}


def check_set_patient_field(answer: dict[str, Any], field: str) -> tuple[bool, dict[str, Any]]:
    actual = patient_map(answer)
    gold = expected_patients()
    mismatches = []
    for pid, grow in gold.items():
        expected = set(grow[field])
        actual_set = as_set(actual.get(pid, {}).get(field))
        if actual_set != expected:
            mismatches.append({"patient_id": pid, "expected": sorted(expected), "actual": sorted(actual_set)})
    return not mismatches and set(actual) == set(gold), {"field": field, "mismatches": mismatches}


def check_package(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    actual = patient_map(answer)
    gold = expected_patients()
    mismatches = []
    for pid, grow in gold.items():
        expected = grow["initial_monitoring_package"]
        actual_pkg = actual.get(pid, {}).get("initial_monitoring_package")
        if not isinstance(actual_pkg, dict):
            mismatches.append({"patient_id": pid, "expected": expected, "actual": actual_pkg})
            continue
        same = (
            actual_pkg.get("package_type") == expected["package_type"]
            and as_set(actual_pkg.get("components")) == set(expected["components"])
            and actual_pkg.get("first_checkin_days") == expected["first_checkin_days"]
        )
        if not same:
            mismatches.append({"patient_id": pid, "expected": expected, "actual": actual_pkg})
    return not mismatches and set(actual) == set(gold), {"mismatches": mismatches}


def check_summary(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    actual = answer.get("summary")
    expected = GOLD["summary"]
    return actual == expected, {"expected": expected, "actual": actual}


def score(answer: dict[str, Any] | None, parse_error: str | None) -> dict[str, Any]:
    total_weight = sum(weight for _, _, weight in RUBRIC)
    if answer is None:
        points = [
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": weight / total_weight,
                "passed": False,
                "earned_score": 0.0,
                "details": {"error": parse_error},
            }
            for point_id, goal, weight in RUBRIC
        ]
        return {"score": 0.0, "correct": False, "points": points}

    checks = [
        check_ids_and_eligibility(answer),
        check_status_reasons(answer),
        check_simple_patient_field(answer, "follow_up_cadence"),
        check_set_patient_field(answer, "missing_chart_artifacts"),
        check_simple_patient_field(answer, "outreach_channel"),
        check_package(answer),
        check_summary(answer),
    ]
    points = []
    earned = 0.0
    for (point_id, goal, weight), (passed, details) in zip(RUBRIC, checks):
        assigned = weight / total_weight
        point_score = assigned if passed else 0.0
        earned += point_score
        points.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": assigned,
                "passed": passed,
                "earned_score": point_score,
                "details": details,
            }
        )
    all_passed = all(point["passed"] for point in points)
    final_score = 1.0 if all_passed else earned
    return {"score": final_score, "correct": all_passed, "points": points}


def main() -> None:
    answer_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("answer.json")
    answer, error = load_answer(answer_path)
    print(json.dumps(score(answer, error), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
