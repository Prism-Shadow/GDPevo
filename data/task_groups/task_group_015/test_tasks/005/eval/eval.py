#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REF_RE = re.compile(r"REF-APR-[0-9]{3}(?:-DUP)?")

GOLD = {
    "batch": {
        "batch_id": "APR26-ORTHO-B",
        "service_line": "orthopedics",
        "requested_date": "2026-04-15",
        "record_count": 23,
        "unique_patient_count": 20,
    },
    "invalid": {
        "REF-APR-001",
        "REF-APR-008",
        "REF-APR-012",
        "REF-APR-013",
        "REF-APR-015",
        "REF-APR-018",
        "REF-APR-021",
    },
    "mismatch": {
        "REF-APR-001",
        "REF-APR-002",
        "REF-APR-003",
        "REF-APR-004",
        "REF-APR-005",
        "REF-APR-006",
        "REF-APR-007",
        "REF-APR-008",
        "REF-APR-009",
        "REF-APR-010",
        "REF-APR-011",
        "REF-APR-012",
        "REF-APR-013",
        "REF-APR-014",
        "REF-APR-015",
        "REF-APR-016",
        "REF-APR-017",
        "REF-APR-018",
        "REF-APR-020",
        "REF-APR-021",
        "REF-APR-022",
    },
    "duplicate_groups": [
        {
            "patient_id": "P-73008",
            "referral_ids": {"REF-APR-005", "REF-APR-023-DUP"},
        }
    ],
    "anomalies": [
        {
            "anomaly_type": "shared_insurance_different_patients",
            "patient_ids": {"P-40720", "P-73008"},
            "referral_ids": {"REF-APR-005", "REF-APR-016", "REF-APR-019", "REF-APR-023-DUP"},
            "insurance_id": "INS-663020",
            "recommended_disposition": "verify_insurance_membership_do_not_merge",
        },
        {
            "anomaly_type": "same_patient_separate_clinical_referrals",
            "patient_ids": {"P-50831"},
            "referral_ids": {"REF-APR-001", "REF-APR-011"},
            "insurance_id": "INS-901245",
            "recommended_disposition": "separate_clinical_review_not_duplicate",
        },
    ],
    "queues": {
        "authorization_missing": {
            "REF-APR-001",
            "REF-APR-006",
            "REF-APR-011",
            "REF-APR-016",
            "REF-APR-021",
        },
        "authorization_pending": {
            "REF-APR-003",
            "REF-APR-008",
            "REF-APR-013",
            "REF-APR-018",
        },
        "records_request": {
            "REF-APR-002",
            "REF-APR-003",
            "REF-APR-004",
            "REF-APR-005",
            "REF-APR-006",
            "REF-APR-007",
            "REF-APR-011",
            "REF-APR-013",
            "REF-APR-014",
            "REF-APR-015",
            "REF-APR-016",
            "REF-APR-019",
            "REF-APR-020",
            "REF-APR-021",
            "REF-APR-022",
        },
        "imaging_follow_up": {
            "REF-APR-001",
            "REF-APR-002",
            "REF-APR-004",
            "REF-APR-009",
            "REF-APR-013",
            "REF-APR-015",
            "REF-APR-017",
            "REF-APR-019",
            "REF-APR-020",
            "REF-APR-021",
            "REF-APR-022",
        },
    },
    "tiers": {
        "tier_1_immediate": {
            "REF-APR-005": "PRV-ORTHO-011",
            "REF-APR-007": "PRV-ORTHO-011",
            "REF-APR-011": "PRV-ORTHO-010",
            "REF-APR-016": "PRV-ORTHO-011",
            "REF-APR-023-DUP": "PRV-ORTHO-010",
        },
        "tier_2_short_term": {
            "REF-APR-001",
            "REF-APR-002",
            "REF-APR-003",
            "REF-APR-004",
            "REF-APR-006",
            "REF-APR-008",
            "REF-APR-009",
            "REF-APR-010",
            "REF-APR-012",
            "REF-APR-013",
            "REF-APR-014",
            "REF-APR-015",
            "REF-APR-017",
            "REF-APR-018",
            "REF-APR-020",
            "REF-APR-021",
            "REF-APR-022",
        },
        "tier_3_administrative": {"REF-APR-019"},
    },
    "summary_counts": {
        "total_referral_rows": 23,
        "unique_patients": 20,
        "urgent_count": 3,
        "routine_count": 20,
        "invalid_or_out_of_range_count": 7,
        "mismatch_count": 21,
        "duplicate_group_count": 1,
        "insurance_patient_anomaly_count": 2,
        "authorization_missing_count": 5,
        "authorization_pending_count": 4,
        "records_request_count": 15,
        "imaging_follow_up_count": 11,
        "tier_1_count": 5,
        "tier_2_count": 17,
        "tier_3_count": 1,
        "validated_ready_no_follow_up_count": 0,
    },
}

POINTS = [
    ("batch_identity_and_counts", 3),
    ("invalid_chapter_code_set", 3),
    ("laterality_narrative_mismatch_set", 2),
    ("duplicate_group", 2),
    ("authorization_document_queues", 2),
    ("insurance_patient_anomalies", 2),
    ("tier_1_action_assignments", 3),
    ("tier_2_tier_3_split", 2),
    ("summary_counts", 2),
]


def load_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
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


def norm_set(value: Any) -> set[str]:
    if isinstance(value, list):
        return {str(item).strip() for item in value if str(item).strip()}
    if isinstance(value, str):
        return {value.strip()} if value.strip() else set()
    return set()


def norm_scalar(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


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
    return actual == GOLD["batch"], {"expected": GOLD["batch"], "actual": actual}


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
    actual_norm = [
        {"patient_id": g["patient_id"], "referral_ids": sorted_list(g["referral_ids"])} for g in actual_groups
    ]
    expected_norm = [
        {"patient_id": g["patient_id"], "referral_ids": sorted_list(g["referral_ids"])}
        for g in GOLD["duplicate_groups"]
    ]
    return actual_norm == expected_norm, {"expected": expected_norm, "actual": actual_norm}


def normalize_anomalies(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return result
    for item in value:
        if not isinstance(item, dict):
            continue
        anomaly_type = norm_scalar(item.get("anomaly_type"))
        insurance_id = norm_scalar(item.get("insurance_id"))
        if anomaly_type == "same_patient_separate_clinical_referrals" and not insurance_id:
            insurance_id = "INS-901245"
        result.append(
            {
                "anomaly_type": anomaly_type,
                "patient_ids": sorted_list(norm_set(item.get("patient_ids"))),
                "referral_ids": sorted_list(refs_in(item.get("referral_ids", item))),
                "insurance_id": insurance_id,
                "recommended_disposition": norm_scalar(item.get("recommended_disposition")),
            }
        )
    return sorted(result, key=lambda row: (str(row["anomaly_type"]), row["patient_ids"], row["referral_ids"]))


def check_anomalies(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    actual = normalize_anomalies(answer.get("insurance_patient_anomalies", []))
    expected = sorted(
        [
            {
                "anomaly_type": row["anomaly_type"],
                "patient_ids": sorted_list(row["patient_ids"]),
                "referral_ids": sorted_list(row["referral_ids"]),
                "insurance_id": row["insurance_id"],
                "recommended_disposition": row["recommended_disposition"],
            }
            for row in GOLD["anomalies"]
        ],
        key=lambda row: (str(row["anomaly_type"]), row["patient_ids"], row["referral_ids"]),
    )
    return actual == expected, {"expected": expected, "actual": actual}


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


def tier_owner_map(value: Any) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    if not isinstance(value, list):
        return result
    for item in value:
        if isinstance(item, dict):
            refs = refs_in(item.get("referral_id", item))
            for ref in refs:
                result[ref] = norm_scalar(item.get("owner_provider_id"))
        else:
            for ref in refs_in(item):
                result[ref] = None
    return result


def check_tier_1(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    plan = answer.get("action_plan", {})
    if not isinstance(plan, dict):
        plan = {}
    actual = tier_owner_map(plan.get("tier_1_immediate", []))
    expected = GOLD["tiers"]["tier_1_immediate"]
    passed = actual == expected
    return passed, {"expected": expected, "actual": actual}


def check_tier_2_3(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    plan = answer.get("action_plan", {})
    if not isinstance(plan, dict):
        plan = {}
    actual_tier_2 = refs_in(plan.get("tier_2_short_term", []))
    actual_tier_3 = refs_in(plan.get("tier_3_administrative", []))
    tier_2_ok, tier_2_detail = check_set(actual_tier_2, GOLD["tiers"]["tier_2_short_term"])
    tier_3_ok, tier_3_detail = check_set(actual_tier_3, GOLD["tiers"]["tier_3_administrative"])
    return tier_2_ok and tier_3_ok, {"tier_2_short_term": tier_2_detail, "tier_3_administrative": tier_3_detail}


def check_summary(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    summary = answer.get("summary_counts", {})
    if not isinstance(summary, dict):
        summary = {}
    actual = {key: as_int(summary.get(key)) for key in GOLD["summary_counts"]}
    return actual == GOLD["summary_counts"], {"expected": GOLD["summary_counts"], "actual": actual}


def evaluate(answer: Any) -> dict[str, Any]:
    total_weight = sum(weight for _, weight in POINTS)
    if not isinstance(answer, dict):
        answer = {}

    checks = {
        "batch_identity_and_counts": lambda: check_batch(answer),
        "invalid_chapter_code_set": lambda: check_set(
            refs_in(answer.get("invalid_or_out_of_range_code_referrals", [])),
            GOLD["invalid"],
        ),
        "laterality_narrative_mismatch_set": lambda: check_set(
            refs_in(answer.get("laterality_or_narrative_mismatch_referrals", [])),
            GOLD["mismatch"],
        ),
        "duplicate_group": lambda: check_duplicate(answer),
        "authorization_document_queues": lambda: check_queues(answer),
        "insurance_patient_anomalies": lambda: check_anomalies(answer),
        "tier_1_action_assignments": lambda: check_tier_1(answer),
        "tier_2_tier_3_split": lambda: check_tier_2_3(answer),
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


def unreadable_result(error: str) -> dict[str, Any]:
    total_weight = sum(weight for _, weight in POINTS)
    return {
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


def main() -> int:
    if len(sys.argv) > 2:
        print(json.dumps({"score": 0.0, "error": "usage: eval.py <candidate_answer.json>"}))
        return 2
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
    answer, error = load_json(path)
    result = unreadable_result(error) if error is not None else evaluate(answer)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
