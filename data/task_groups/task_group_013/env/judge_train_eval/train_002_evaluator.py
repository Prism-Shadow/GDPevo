#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from typing import Any


GOLD_ICD = {
    "REF0001": ("S83.512A", ("icd_chapter_mismatch",), "S00-T88", "M00-M99"),
    "REF0005": ("S83.512A", ("icd_chapter_mismatch",), "S00-T88", "M00-M99"),
    "REF0006": ("S83.512A", ("icd_chapter_mismatch",), "S00-T88", "M00-M99"),
    "REF0007": ("S83.512A", ("icd_chapter_mismatch",), "S00-T88", "M00-M99"),
    "REF0008": ("S83.512A", ("icd_chapter_mismatch",), "S00-T88", "M00-M99"),
    "REF0009": ("S83.512A", ("icd_chapter_mismatch",), "S00-T88", "M00-M99"),
}

GOLD_DUPLICATES = {(("REF0007", "REF0009"), "P046", "REF0007", "consolidate_to_primary")}

GOLD_SHARED_INSURANCE = {
    ("DUP-INS-ORTHO", ("REF0004", "REF0005"), ("P043", "P044"), "verify_distinct_patient_policy_id")
}

GOLD_MISSING_RECORDS = {"REF0003", "REF0006"}
GOLD_MISSING_IMAGING = {"REF0002", "REF0006"}
GOLD_AUTH = {"REF0003": "denied", "REF0006": "pending"}
GOLD_READY = set()

GOLD_PRIORITY = {
    "REF0001": "tier_1_immediate",
    "REF0002": "tier_2_short_term",
    "REF0003": "tier_2_short_term",
    "REF0004": "tier_3_administrative",
    "REF0005": "tier_1_immediate",
    "REF0006": "tier_2_short_term",
    "REF0007": "tier_2_short_term",
    "REF0008": "tier_2_short_term",
    "REF0009": "tier_2_short_term",
}

GOLD_ACTION_CODES = {
    "REF0001": {"request_corrected_icd"},
    "REF0002": {"request_imaging"},
    "REF0003": {"request_records", "resolve_authorization"},
    "REF0004": {"verify_insurance_id"},
    "REF0005": {"request_corrected_icd", "verify_insurance_id"},
    "REF0006": {"request_corrected_icd", "request_imaging", "request_records", "resolve_authorization"},
    "REF0007": {"consolidate_duplicate", "request_corrected_icd"},
    "REF0008": {"request_corrected_icd", "review_existing_appointment"},
    "REF0009": {"consolidate_duplicate", "request_corrected_icd"},
}

GOLD_SUMMARY = {
    "total_referrals": 9,
    "ready_to_schedule_count": 0,
    "follow_up_count": 9,
    "counts_by_urgency": {"urgent": 2, "routine": 7, "admin": 0},
    "counts_by_readiness_status": {"ready": 0, "blocked": 3, "under_review": 5, "admin_followup": 1},
    "counts_by_urgency_and_status": {
        ("routine", "admin_followup"): 1,
        ("routine", "blocked"): 3,
        ("routine", "under_review"): 3,
        ("urgent", "under_review"): 2,
    },
    "issue_counts": {
        "icd_discrepancy_referrals": 6,
        "duplicate_groups": 1,
        "shared_insurance_anomalies": 1,
        "missing_records_referrals": 2,
        "missing_imaging_referrals": 2,
        "auth_blocker_referrals": 2,
    },
}

POINTS = [
    ("SP001", "Correct ICD chapter, narrative, or laterality discrepancy referrals.", 3),
    ("SP002", "Correct duplicate referral grouping and consolidation recommendation.", 2),
    ("SP003", "Correct shared insurance anomaly set excluding same-patient duplicate sharing.", 2),
    ("SP004", "Correct missing-records and missing-imaging blocker sets.", 2),
    ("SP005", "Correct authorization blocker set and statuses.", 2),
    ("SP006", "Correct ready-to-schedule referral set.", 3),
    ("SP007", "Correct priority tier and action-code assignment for follow-up referrals.", 3),
    ("SP008", "Correct summary counts by urgency, readiness status, and issue type.", 1),
]


def load_answer(path: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # noqa: BLE001
        return None, f"could not parse JSON: {exc}"
    if not isinstance(data, dict):
        return None, "top-level JSON value must be an object"
    return data, None


def as_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    out: set[str] = set()
    for item in value:
        if isinstance(item, str):
            out.add(item)
        elif isinstance(item, dict) and isinstance(item.get("referral_id"), str):
            out.add(item["referral_id"])
    return out


def clean_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return tuple()
    return tuple(sorted(str(v) for v in value))


def icd_map(answer: dict[str, Any]) -> dict[str, tuple[str, tuple[str, ...], str | None, str | None]]:
    result = {}
    for item in answer.get("icd_discrepancies", []):
        if not isinstance(item, dict) or not isinstance(item.get("referral_id"), str):
            continue
        result[item["referral_id"]] = (
            str(item.get("icd10_code")),
            clean_list(item.get("issue_types")),
            item.get("observed_chapter"),
            item.get("expected_chapter"),
        )
    return result


def duplicate_set(answer: dict[str, Any]) -> set[tuple[tuple[str, ...], str, str, str]]:
    groups = set()
    for item in answer.get("duplicate_groups", []):
        if not isinstance(item, dict):
            continue
        groups.add(
            (
                clean_list(item.get("referral_ids")),
                str(item.get("patient_id")),
                str(item.get("primary_referral_id")),
                str(item.get("recommendation")),
            )
        )
    return groups


def shared_insurance_set(answer: dict[str, Any]) -> set[tuple[str, tuple[str, ...], tuple[str, ...], str]]:
    groups = set()
    for item in answer.get("shared_insurance_anomalies", []):
        if not isinstance(item, dict):
            continue
        groups.add(
            (
                str(item.get("insurance_id")),
                clean_list(item.get("referral_ids")),
                clean_list(item.get("patient_ids")),
                str(item.get("disposition")),
            )
        )
    return groups


def auth_map(answer: dict[str, Any]) -> dict[str, str]:
    result = {}
    blockers = (
        answer.get("blocker_sets", {}).get("auth_blockers") if isinstance(answer.get("blocker_sets"), dict) else None
    )
    if not isinstance(blockers, list):
        return result
    for item in blockers:
        if isinstance(item, dict) and isinstance(item.get("referral_id"), str):
            result[item["referral_id"]] = str(item.get("auth_status"))
    return result


def priority_map(answer: dict[str, Any]) -> dict[str, str]:
    result = {}
    for section in ("action_plan", "referral_reviews"):
        items = answer.get(section, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if (
                isinstance(item, dict)
                and isinstance(item.get("referral_id"), str)
                and item.get("priority_tier") is not None
            ):
                result[item["referral_id"]] = str(item.get("priority_tier"))
    return result


def action_code_map(answer: dict[str, Any]) -> dict[str, set[str]]:
    result = {}
    for item in answer.get("action_plan", []):
        if isinstance(item, dict) and isinstance(item.get("referral_id"), str):
            codes = item.get("action_codes", [])
            result[item["referral_id"]] = {str(v) for v in codes} if isinstance(codes, list) else set()
    return result


def status_map(answer: dict[str, Any]) -> dict[str, str]:
    result = {}
    for item in answer.get("referral_reviews", []):
        if isinstance(item, dict) and isinstance(item.get("referral_id"), str):
            result[item["referral_id"]] = str(item.get("readiness_status"))
    return result


def urgency_status_counts(summary: dict[str, Any]) -> dict[tuple[str, str], int]:
    result: dict[tuple[str, str], int] = {}
    raw = summary.get("counts_by_urgency_and_status")
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                result[(str(item.get("urgency")), str(item.get("readiness_status")))] = int(item.get("count", -1))
    elif isinstance(raw, dict):
        for urgency, statuses in raw.items():
            if isinstance(statuses, dict):
                for status, count in statuses.items():
                    result[(str(urgency), str(status))] = int(count)
    return result


def check_summary(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    summary = answer.get("summary", {})
    if not isinstance(summary, dict):
        return False, {"reason": "summary is missing or not an object"}
    simple_ok = all(summary.get(k) == v for k, v in GOLD_SUMMARY.items() if isinstance(v, int))
    urgency_ok = summary.get("counts_by_urgency") == GOLD_SUMMARY["counts_by_urgency"]
    status_ok = summary.get("counts_by_readiness_status") == GOLD_SUMMARY["counts_by_readiness_status"]
    urgency_status_ok = urgency_status_counts(summary) == GOLD_SUMMARY["counts_by_urgency_and_status"]
    issue_ok = summary.get("issue_counts") == GOLD_SUMMARY["issue_counts"]
    return simple_ok and urgency_ok and status_ok and urgency_status_ok and issue_ok, {
        "simple_counts_ok": simple_ok,
        "urgency_counts_ok": urgency_ok,
        "readiness_counts_ok": status_ok,
        "urgency_status_counts_ok": urgency_status_ok,
        "issue_counts_ok": issue_ok,
    }


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "answer.json"
    answer, error = load_answer(path)
    total_weight = sum(weight for _, _, weight in POINTS)
    results = []

    if answer is None:
        for point_id, goal, weight in POINTS:
            assigned = weight / total_weight
            results.append(
                {
                    "id": point_id,
                    "goal": goal,
                    "weight": weight,
                    "assigned_score": assigned,
                    "passed": False,
                    "earned_score": 0.0,
                    "details": {"error": error},
                }
            )
        print(json.dumps({"score": 0.0, "correct": False, "points": results}, indent=2, sort_keys=True))
        return

    checks: list[tuple[bool, dict[str, Any]]] = []
    checks.append((icd_map(answer) == GOLD_ICD, {"expected_referrals": sorted(GOLD_ICD), "actual": icd_map(answer)}))
    checks.append(
        (
            duplicate_set(answer) == GOLD_DUPLICATES,
            {"expected": sorted(map(str, GOLD_DUPLICATES)), "actual": sorted(map(str, duplicate_set(answer)))},
        )
    )
    checks.append(
        (
            shared_insurance_set(answer) == GOLD_SHARED_INSURANCE,
            {
                "expected": sorted(map(str, GOLD_SHARED_INSURANCE)),
                "actual": sorted(map(str, shared_insurance_set(answer))),
            },
        )
    )

    blockers = answer.get("blocker_sets", {}) if isinstance(answer.get("blocker_sets"), dict) else {}
    missing_records = (
        set(blockers.get("missing_records", [])) if isinstance(blockers.get("missing_records"), list) else set()
    )
    missing_imaging = (
        set(blockers.get("missing_imaging", [])) if isinstance(blockers.get("missing_imaging"), list) else set()
    )
    checks.append(
        (
            missing_records == GOLD_MISSING_RECORDS and missing_imaging == GOLD_MISSING_IMAGING,
            {
                "missing_records": sorted(missing_records),
                "missing_imaging": sorted(missing_imaging),
            },
        )
    )

    checks.append((auth_map(answer) == GOLD_AUTH, {"expected": GOLD_AUTH, "actual": auth_map(answer)}))
    checks.append(
        (
            as_set(answer.get("ready_to_schedule")) == GOLD_READY,
            {"expected": sorted(GOLD_READY), "actual": sorted(as_set(answer.get("ready_to_schedule")))},
        )
    )

    priorities_ok = priority_map(answer) == GOLD_PRIORITY
    actions_ok = action_code_map(answer) == GOLD_ACTION_CODES
    statuses_ok = status_map(answer) == {
        "REF0001": "under_review",
        "REF0002": "blocked",
        "REF0003": "blocked",
        "REF0004": "admin_followup",
        "REF0005": "under_review",
        "REF0006": "blocked",
        "REF0007": "under_review",
        "REF0008": "under_review",
        "REF0009": "under_review",
    }
    checks.append(
        (
            priorities_ok and actions_ok and statuses_ok,
            {
                "priorities_ok": priorities_ok,
                "actions_ok": actions_ok,
                "statuses_ok": statuses_ok,
            },
        )
    )

    checks.append(check_summary(answer))

    score = 0.0
    for (point_id, goal, weight), (passed, details) in zip(POINTS, checks):
        assigned = weight / total_weight
        earned = assigned if passed else 0.0
        score += earned
        results.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": assigned,
                "passed": passed,
                "earned_score": earned,
                "details": details,
            }
        )

    score = round(score, 10)
    print(json.dumps({"score": score, "correct": score == 1.0, "points": results}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
