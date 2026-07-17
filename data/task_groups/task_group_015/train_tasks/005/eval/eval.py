#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REF_RE = re.compile(r"REF-MAR-[0-9]{3}(?:-DUP)?")

GOLD = {
    "batch": {
        "batch_id": "MAR26-ORTHO-A",
        "service_line": "orthopedics",
        "requested_date": "2026-03-15",
        "record_count": 19,
        "unique_patient_count": 18,
    },
    "invalid": {
        "REF-MAR-001",
        "REF-MAR-003",
        "REF-MAR-005",
        "REF-MAR-006",
        "REF-MAR-011",
        "REF-MAR-012",
        "REF-MAR-015",
        "REF-MAR-017",
        "REF-MAR-018",
        "REF-MAR-019-DUP",
    },
    "mismatch": {
        "REF-MAR-001",
        "REF-MAR-002",
        "REF-MAR-003",
        "REF-MAR-005",
        "REF-MAR-006",
        "REF-MAR-007",
        "REF-MAR-009",
        "REF-MAR-011",
        "REF-MAR-012",
        "REF-MAR-013",
        "REF-MAR-014",
        "REF-MAR-015",
        "REF-MAR-016",
        "REF-MAR-017",
        "REF-MAR-018",
    },
    "duplicate_groups": [
        {
            "patient_id": "P-55218",
            "referral_ids": {"REF-MAR-004", "REF-MAR-019-DUP"},
        }
    ],
    "duplicate_tiering_policy": {
        "same_patient_resubmission_scope": "tier_all_duplicate_group_rows_as_duplicate_blockers",
        "tier_1_duplicate_blocker_referral_ids": {"REF-MAR-004", "REF-MAR-019-DUP"},
        "separate_same_patient_referral_ids": set(),
    },
    "insurance_patient_anomalies": [
        {
            "anomaly_id": "ANOM-MAR-INS-881144",
            "anomaly_type": "shared_insurance_different_patients",
            "patient_ids": {"P-55218", "P-55281"},
            "referral_ids": {"REF-MAR-003", "REF-MAR-004", "REF-MAR-019-DUP"},
            "insurance_id": "INS-881144",
            "recommended_disposition": "verify_insurance_membership_do_not_merge",
        }
    ],
    "queues": {
        "authorization_missing": {
            "REF-MAR-001",
            "REF-MAR-005",
            "REF-MAR-009",
            "REF-MAR-013",
            "REF-MAR-017",
        },
        "authorization_pending": set(),
        "records_request": {
            "REF-MAR-001",
            "REF-MAR-002",
            "REF-MAR-008",
            "REF-MAR-011",
            "REF-MAR-012",
            "REF-MAR-013",
            "REF-MAR-017",
            "REF-MAR-018",
        },
        "imaging_follow_up": {
            "REF-MAR-001",
            "REF-MAR-003",
            "REF-MAR-005",
            "REF-MAR-006",
            "REF-MAR-007",
            "REF-MAR-009",
            "REF-MAR-010",
            "REF-MAR-011",
            "REF-MAR-015",
            "REF-MAR-017",
            "REF-MAR-018",
        },
    },
    "tiers": {
        "tier_1_immediate": {"REF-MAR-004", "REF-MAR-009", "REF-MAR-015", "REF-MAR-019-DUP"},
        "tier_2_short_term": {
            "REF-MAR-001",
            "REF-MAR-002",
            "REF-MAR-003",
            "REF-MAR-005",
            "REF-MAR-006",
            "REF-MAR-007",
            "REF-MAR-011",
            "REF-MAR-012",
            "REF-MAR-013",
            "REF-MAR-014",
            "REF-MAR-016",
            "REF-MAR-017",
            "REF-MAR-018",
        },
        "tier_3_administrative": {"REF-MAR-008", "REF-MAR-010"},
    },
    "summary_counts": {
        "total_referral_rows": 19,
        "unique_patients": 18,
        "urgent_count": 4,
        "routine_count": 15,
        "invalid_or_out_of_range_count": 10,
        "mismatch_count": 15,
        "duplicate_group_count": 1,
        "insurance_patient_anomaly_count": 1,
        "authorization_missing_count": 5,
        "authorization_pending_count": 0,
        "records_request_count": 8,
        "imaging_follow_up_count": 11,
        "tier_1_count": 4,
        "tier_2_count": 13,
        "tier_3_count": 2,
        "validated_ready_no_follow_up_count": 0,
    },
}

POINTS = [
    ("batch_identity_and_counts", 3),
    ("invalid_chapter_code_referrals", 3),
    ("laterality_narrative_mismatches", 2),
    ("duplicate_group", 2),
    ("insurance_patient_anomalies", 2),
    ("auth_doc_queues", 2),
    ("tier_1_assignments", 2),
    ("tier_2_assignments", 2),
    ("tier_3_assignments", 2),
    ("summary_counts", 2),
]


def load_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text()), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def refs_in(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, str):
        found.update(REF_RE.findall(value))
    elif isinstance(value, list):
        for item in value:
            found.update(refs_in(item))
    elif isinstance(value, dict):
        for item in value.values():
            found.update(refs_in(item))
    return found


def as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def sorted_list(values: set[str]) -> list[str]:
    return sorted(values)


def check_set(actual: set[str], expected: set[str]) -> tuple[bool, dict[str, Any]]:
    return actual == expected, {
        "expected": sorted_list(expected),
        "actual": sorted_list(actual),
        "missing": sorted_list(expected - actual),
        "unexpected": sorted_list(actual - expected),
    }


def check_batch(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    batch = answer.get("batch", {})
    if not isinstance(batch, dict):
        batch = {}
    actual = {
        "batch_id": batch.get("batch_id"),
        "service_line": batch.get("service_line"),
        "requested_date": batch.get("requested_date"),
        "record_count": as_int(batch.get("record_count")),
        "unique_patient_count": as_int(batch.get("unique_patient_count")),
    }
    passed = actual == GOLD["batch"]
    return passed, {"expected": GOLD["batch"], "actual": actual}


def check_duplicate(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    groups = answer.get("duplicate_groups", [])
    actual_groups: list[dict[str, Any]] = []
    if isinstance(groups, list):
        for group in groups:
            if isinstance(group, dict):
                actual_groups.append(
                    {
                        "patient_id": group.get("patient_id"),
                        "referral_ids": refs_in(group.get("referral_ids", group)),
                    }
                )
            else:
                actual_groups.append({"patient_id": None, "referral_ids": refs_in(group)})
    actual_norm = [
        {"patient_id": g["patient_id"], "referral_ids": sorted_list(g["referral_ids"])} for g in actual_groups
    ]
    expected_norm = [
        {"patient_id": g["patient_id"], "referral_ids": sorted_list(g["referral_ids"])}
        for g in GOLD["duplicate_groups"]
    ]
    policy = answer.get("duplicate_tiering_policy", {})
    if not isinstance(policy, dict):
        policy = {}
    expected_policy = GOLD["duplicate_tiering_policy"]
    actual_policy = {
        "same_patient_resubmission_scope": policy.get("same_patient_resubmission_scope"),
        "tier_1_duplicate_blocker_referral_ids": sorted_list(
            refs_in(policy.get("tier_1_duplicate_blocker_referral_ids", []))
        ),
        "separate_same_patient_referral_ids": sorted_list(
            refs_in(policy.get("separate_same_patient_referral_ids", []))
        ),
    }
    expected_policy_norm = {
        "same_patient_resubmission_scope": expected_policy["same_patient_resubmission_scope"],
        "tier_1_duplicate_blocker_referral_ids": sorted_list(expected_policy["tier_1_duplicate_blocker_referral_ids"]),
        "separate_same_patient_referral_ids": sorted_list(expected_policy["separate_same_patient_referral_ids"]),
    }
    passed = actual_norm == expected_norm and actual_policy == expected_policy_norm
    return passed, {
        "duplicate_groups": {"expected": expected_norm, "actual": actual_norm},
        "duplicate_tiering_policy": {"expected": expected_policy_norm, "actual": actual_policy},
    }


def check_anomalies(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    rows = answer.get("insurance_patient_anomalies", [])
    actual_rows: list[dict[str, Any]] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            actual_rows.append(
                {
                    "anomaly_id": row.get("anomaly_id"),
                    "anomaly_type": row.get("anomaly_type"),
                    "patient_ids": {str(item) for item in row.get("patient_ids", []) if str(item)},
                    "referral_ids": refs_in(row.get("referral_ids", row)),
                    "insurance_id": row.get("insurance_id"),
                    "recommended_disposition": row.get("recommended_disposition"),
                }
            )
    expected_rows = GOLD["insurance_patient_anomalies"]
    actual_norm = [
        {
            "anomaly_id": row["anomaly_id"],
            "anomaly_type": row["anomaly_type"],
            "patient_ids": sorted_list(row["patient_ids"]),
            "referral_ids": sorted_list(row["referral_ids"]),
            "insurance_id": row["insurance_id"],
            "recommended_disposition": row["recommended_disposition"],
        }
        for row in actual_rows
    ]
    expected_norm = [
        {
            "anomaly_id": row["anomaly_id"],
            "anomaly_type": row["anomaly_type"],
            "patient_ids": sorted_list(row["patient_ids"]),
            "referral_ids": sorted_list(row["referral_ids"]),
            "insurance_id": row["insurance_id"],
            "recommended_disposition": row["recommended_disposition"],
        }
        for row in expected_rows
    ]
    return actual_norm == expected_norm, {"expected": expected_norm, "actual": actual_norm}


def check_queues(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    queues = answer.get("follow_up_queues", {})
    if not isinstance(queues, dict):
        queues = {}
    detail: dict[str, Any] = {}
    passed = True
    for key, expected in GOLD["queues"].items():
        actual = refs_in(queues.get(key, []))
        ok, info = check_set(actual, expected)
        detail[key] = info
        passed = passed and ok
    return passed, detail


def check_tier(answer: dict[str, Any], key: str) -> tuple[bool, dict[str, Any]]:
    plan = answer.get("action_plan", {})
    if not isinstance(plan, dict):
        plan = {}
    actual = refs_in(plan.get(key, []))
    return check_set(actual, GOLD["tiers"][key])


def check_summary(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    summary = answer.get("summary_counts", {})
    if not isinstance(summary, dict):
        summary = {}
    actual = {key: as_int(summary.get(key)) for key in GOLD["summary_counts"]}
    passed = actual == GOLD["summary_counts"]
    return passed, {"expected": GOLD["summary_counts"], "actual": actual}


def evaluate(answer: Any) -> dict[str, Any]:
    total_weight = sum(weight for _, weight in POINTS)
    if not isinstance(answer, dict):
        answer = {}

    checks = {
        "batch_identity_and_counts": lambda: check_batch(answer),
        "invalid_chapter_code_referrals": lambda: check_set(
            refs_in(answer.get("invalid_or_out_of_range_code_referrals", [])),
            GOLD["invalid"],
        ),
        "laterality_narrative_mismatches": lambda: check_set(
            refs_in(answer.get("laterality_or_narrative_mismatch_referrals", [])),
            GOLD["mismatch"],
        ),
        "duplicate_group": lambda: check_duplicate(answer),
        "insurance_patient_anomalies": lambda: check_anomalies(answer),
        "auth_doc_queues": lambda: check_queues(answer),
        "tier_1_assignments": lambda: check_tier(answer, "tier_1_immediate"),
        "tier_2_assignments": lambda: check_tier(answer, "tier_2_short_term"),
        "tier_3_assignments": lambda: check_tier(answer, "tier_3_administrative"),
        "summary_counts": lambda: check_summary(answer),
    }

    point_results = []
    score = 0.0
    for point_id, weight in POINTS:
        assigned = weight / total_weight
        passed, details = checks[point_id]()
        earned = assigned if passed else 0.0
        score += earned
        point_results.append(
            {
                "id": point_id,
                "weight": weight,
                "assigned_score": round(assigned, 6),
                "passed": passed,
                "earned_score": round(earned, 6),
                "details": details,
            }
        )

    return {
        "score": round(score, 6),
        "total_weight": total_weight,
        "points": point_results,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0.0, "error": "usage: eval.py <candidate_answer.json>"}))
        return 2
    answer, error = load_json(Path(sys.argv[1]))
    if error is not None:
        total_weight = sum(weight for _, weight in POINTS)
        result = {
            "score": 0.0,
            "total_weight": total_weight,
            "error": error,
            "points": [
                {
                    "id": point_id,
                    "weight": weight,
                    "assigned_score": round(weight / total_weight, 6),
                    "passed": False,
                    "earned_score": 0.0,
                    "details": {"error": "candidate answer was not readable JSON"},
                }
                for point_id, weight in POINTS
            ],
        }
    else:
        result = evaluate(answer)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
