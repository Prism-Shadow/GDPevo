#!/usr/bin/env python3
"""Deterministic evaluator for train_005."""

from __future__ import annotations

import json
import sys
from typing import Any


GOLD = {
    "batch_id": "PULM-JUN-02",
    "readiness_by_referral": [
        {"referral_id": "REF0010", "patient_id": "P048", "readiness_status": "ready", "blocker_codes": []},
        {
            "referral_id": "REF0011",
            "patient_id": "P049",
            "readiness_status": "under_review",
            "blocker_codes": ["clinical_code_discrepancy"],
        },
        {
            "referral_id": "REF0012",
            "patient_id": "P050",
            "readiness_status": "blocked",
            "blocker_codes": ["authorization_blocked", "records_missing"],
        },
        {"referral_id": "REF0013", "patient_id": "P051", "readiness_status": "ready", "blocker_codes": []},
        {
            "referral_id": "REF0014",
            "patient_id": "P052",
            "readiness_status": "under_review",
            "blocker_codes": ["clinical_code_discrepancy"],
        },
        {
            "referral_id": "REF0015",
            "patient_id": "P053",
            "readiness_status": "blocked",
            "blocker_codes": [
                "authorization_blocked",
                "clinical_code_discrepancy",
                "records_missing",
                "scheduled_before_clearance",
            ],
        },
    ],
    "clinical_code_discrepancy_referrals": ["REF0011", "REF0014", "REF0015"],
    "blocker_sets": {
        "authorization": ["REF0012", "REF0015"],
        "records": ["REF0012", "REF0015"],
        "imaging": [],
    },
    "duplicate_handling": {
        "duplicate_groups": [],
        "cleared_duplicate_review_referrals": ["REF0013", "REF0014"],
    },
    "ready_referral_chart_needs": [
        {
            "referral_id": "REF0010",
            "patient_id": "P048",
            "chart_action": "update_chart",
            "artifacts_to_create": ["active_problems", "allergies", "consent", "labs", "vitals"],
        },
        {
            "referral_id": "REF0013",
            "patient_id": "P051",
            "chart_action": "update_chart",
            "artifacts_to_create": [
                "active_problems",
                "allergies",
                "consent",
                "demographics",
                "labs",
                "medications",
                "vitals",
            ],
        },
    ],
    "correspondence_queue": [
        {
            "referral_id": "REF0011",
            "template_type": "clinical_code_clarification",
            "reason_codes": ["wrong_service_family"],
        },
        {
            "referral_id": "REF0012",
            "template_type": "auth_records_request",
            "reason_codes": ["authorization_denied", "records_missing"],
        },
        {
            "referral_id": "REF0014",
            "template_type": "clinical_code_clarification",
            "reason_codes": ["clinical_reason_mismatch"],
        },
        {
            "referral_id": "REF0015",
            "template_type": "appointment_hold_notice",
            "reason_codes": [
                "appointment_already_scheduled",
                "authorization_denied",
                "clinical_reason_mismatch",
                "records_missing",
            ],
        },
    ],
    "priority_order": [
        {"rank": 1, "referral_id": "REF0014", "priority_tier": "tier_1_immediate"},
        {"rank": 2, "referral_id": "REF0015", "priority_tier": "tier_2_short_term"},
        {"rank": 3, "referral_id": "REF0011", "priority_tier": "tier_2_short_term"},
        {"rank": 4, "referral_id": "REF0012", "priority_tier": "tier_2_short_term"},
    ],
}


POINTS = [
    ("SP001", "Correct scheduling readiness status and blocker code set for all target referrals.", 3),
    ("SP002", "Correct clinical/code discrepancy referral set.", 2),
    ("SP003", "Correct authorization, records, and imaging blocker sets.", 2),
    ("SP004", "Correct duplicate handling, including clearing false duplicate-review flags.", 2),
    ("SP005", "Correct chart activation artifact needs for every ready referral.", 2),
    ("SP006", "Correct correspondence template type and reason codes for every non-ready referral.", 2),
    ("SP007", "Correct priority ordering and tier assignment for the non-ready action queue.", 2),
]

SET_FIELDS = {"blocker_codes", "reason_codes", "artifacts_to_create"}
TOTAL_WEIGHT = sum(point[2] for point in POINTS)


def load_answer(path: str) -> tuple[Any | None, str | None]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), None
    except Exception as exc:  # noqa: BLE001 - evaluator should report parse failures.
        return None, f"{type(exc).__name__}: {exc}"


def sorted_strings(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return sorted(value)


def normalize_referral_readiness(value: Any) -> dict[str, dict[str, Any]] | None:
    if not isinstance(value, list):
        return None
    out: dict[str, dict[str, Any]] = {}
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("referral_id"), str):
            return None
        normalized = {
            "patient_id": item.get("patient_id"),
            "readiness_status": item.get("readiness_status"),
            "blocker_codes": sorted_strings(item.get("blocker_codes")),
        }
        if normalized["blocker_codes"] is None:
            return None
        out[item["referral_id"]] = normalized
    return out


def normalize_blocker_sets(value: Any) -> dict[str, list[str]] | None:
    if not isinstance(value, dict):
        return None
    out = {}
    for key in ("authorization", "records", "imaging"):
        normalized = sorted_strings(value.get(key))
        if normalized is None:
            return None
        out[key] = normalized
    return out


def normalize_duplicate_handling(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    groups = value.get("duplicate_groups")
    cleared = sorted_strings(value.get("cleared_duplicate_review_referrals"))
    if not isinstance(groups, list) or cleared is None:
        return None
    norm_groups = []
    for group in groups:
        if not isinstance(group, dict):
            return None
        ids = sorted_strings(group.get("referral_ids"))
        if ids is None:
            return None
        norm_groups.append(
            {
                "group_id": group.get("group_id"),
                "referral_ids": ids,
                "keep_referral_id": group.get("keep_referral_id"),
            }
        )
    norm_groups.sort(key=lambda g: str(g.get("group_id")))
    return {"duplicate_groups": norm_groups, "cleared_duplicate_review_referrals": cleared}


def normalize_chart_needs(value: Any) -> dict[str, dict[str, Any]] | None:
    if not isinstance(value, list):
        return None
    out: dict[str, dict[str, Any]] = {}
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("referral_id"), str):
            return None
        artifacts = sorted_strings(item.get("artifacts_to_create"))
        if artifacts is None:
            return None
        out[item["referral_id"]] = {
            "patient_id": item.get("patient_id"),
            "chart_action": item.get("chart_action"),
            "artifacts_to_create": artifacts,
        }
    return out


def normalize_correspondence(value: Any) -> dict[str, dict[str, Any]] | None:
    if not isinstance(value, list):
        return None
    out: dict[str, dict[str, Any]] = {}
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("referral_id"), str):
            return None
        reasons = sorted_strings(item.get("reason_codes"))
        if reasons is None:
            return None
        out[item["referral_id"]] = {
            "template_type": item.get("template_type"),
            "reason_codes": reasons,
        }
    return out


def normalize_priority(value: Any) -> list[dict[str, Any]] | None:
    if not isinstance(value, list):
        return None
    out = []
    for item in value:
        if not isinstance(item, dict):
            return None
        out.append(
            {
                "rank": item.get("rank"),
                "referral_id": item.get("referral_id"),
                "priority_tier": item.get("priority_tier"),
            }
        )
    return out


def norm_gold() -> dict[str, Any]:
    return {
        "readiness": normalize_referral_readiness(GOLD["readiness_by_referral"]),
        "discrepancies": sorted(GOLD["clinical_code_discrepancy_referrals"]),
        "blockers": normalize_blocker_sets(GOLD["blocker_sets"]),
        "duplicates": normalize_duplicate_handling(GOLD["duplicate_handling"]),
        "chart": normalize_chart_needs(GOLD["ready_referral_chart_needs"]),
        "correspondence": normalize_correspondence(GOLD["correspondence_queue"]),
        "priority": normalize_priority(GOLD["priority_order"]),
    }


def grade(answer: Any) -> dict[str, Any]:
    gold = norm_gold()
    if not isinstance(answer, dict):
        return emit_points({"fatal": "answer is not a JSON object"}, set())

    passes = set()
    details: dict[str, Any] = {}

    readiness = normalize_referral_readiness(answer.get("readiness_by_referral"))
    details["SP001"] = {"expected": gold["readiness"], "actual": readiness}
    if answer.get("batch_id") == GOLD["batch_id"] and readiness == gold["readiness"]:
        passes.add("SP001")

    discrepancies = sorted_strings(answer.get("clinical_code_discrepancy_referrals"))
    details["SP002"] = {"expected": gold["discrepancies"], "actual": discrepancies}
    if discrepancies == gold["discrepancies"]:
        passes.add("SP002")

    blockers = normalize_blocker_sets(answer.get("blocker_sets"))
    details["SP003"] = {"expected": gold["blockers"], "actual": blockers}
    if blockers == gold["blockers"]:
        passes.add("SP003")

    duplicates = normalize_duplicate_handling(answer.get("duplicate_handling"))
    details["SP004"] = {"expected": gold["duplicates"], "actual": duplicates}
    if duplicates == gold["duplicates"]:
        passes.add("SP004")

    chart = normalize_chart_needs(answer.get("ready_referral_chart_needs"))
    details["SP005"] = {"expected": gold["chart"], "actual": chart}
    if chart == gold["chart"]:
        passes.add("SP005")

    correspondence = normalize_correspondence(answer.get("correspondence_queue"))
    details["SP006"] = {"expected": gold["correspondence"], "actual": correspondence}
    if correspondence == gold["correspondence"]:
        passes.add("SP006")

    priority = normalize_priority(answer.get("priority_order"))
    details["SP007"] = {"expected": gold["priority"], "actual": priority}
    if priority == gold["priority"]:
        passes.add("SP007")

    return emit_points(details, passes)


def emit_points(details: dict[str, Any], passes: set[str]) -> dict[str, Any]:
    point_results = []
    score = 0.0
    for point_id, goal, weight in POINTS:
        assigned = weight / TOTAL_WEIGHT
        passed = point_id in passes
        earned = assigned if passed else 0.0
        score += earned
        point_results.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": assigned,
                "passed": passed,
                "earned_score": earned,
                "details": details.get(point_id, details.get("fatal")),
            }
        )
    score = round(score, 10)
    return {"score": score, "correct": score == 1.0, "points": point_results}


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "answer.json"
    answer, error = load_answer(path)
    if error is not None:
        print(json.dumps(emit_points({"fatal": error}, set()), indent=2, sort_keys=True))
        return 0
    print(json.dumps(grade(answer), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
