#!/usr/bin/env python3
"""Exact-match evaluator for task_group_017 train_005."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXPECTED = {
    "matter_id": "M-PHN-612",
    "overall_readiness": "not_ready_supplemental_collection_required",
    "custodian": {
        "custodian_id": "C-FC-072",
        "role_status": "former_compliance_custodian",
        "personnel_file_retention": "retained_through_2027",
        "readiness_status": "blocked_source_gap",
    },
    "retention_gaps": {
        "P-01": {
            "category_id": "P-01",
            "source_type": "personnel_file",
            "timing_classification": "within_retention_available",
            "availability_status": "available",
            "missing_count": 0,
            "ready_status": "ready_with_retention_note",
            "primary_action": "no_action",
        },
        "P-02": {
            "category_id": "P-02",
            "source_type": "email_archive",
            "timing_classification": "recoverable_archive",
            "availability_status": "collected",
            "missing_count": 0,
            "ready_status": "ready_after_archive_validation",
            "primary_action": "archive_validation",
        },
        "P-03": {
            "category_id": "P-03",
            "source_type": "teams",
            "timing_classification": "pre_2022_teams_gap",
            "availability_status": "partial_gap",
            "missing_count": 610,
            "ready_status": "blocked_source_gap",
            "primary_action": "teams_gap_assessment",
        },
        "P-04": {
            "category_id": "P-04",
            "source_type": "laptop_pst",
            "timing_classification": "uncollected_source",
            "availability_status": "missing",
            "missing_count": 1,
            "ready_status": "blocked_source_gap",
            "primary_action": "laptop_pst_forensics",
        },
        "P-05": {
            "category_id": "P-05",
            "source_type": "personal_cloud_text",
            "timing_classification": "hold_notice_defect",
            "availability_status": "not_noticed",
            "missing_count": 2,
            "ready_status": "blocked_hold_notice_gap",
            "primary_action": "hold_refresh",
        },
    },
    "collection_plan": [
        {
            "priority_rank": 1,
            "action_code": "hold_refresh",
            "target_category_ids": ["P-05"],
            "target_source_types": ["personal_cloud_text"],
            "required_before_production": True,
        },
        {
            "priority_rank": 2,
            "action_code": "supplemental_collection",
            "target_category_ids": ["P-05"],
            "target_source_types": ["personal_cloud_text"],
            "required_before_production": True,
        },
        {
            "priority_rank": 3,
            "action_code": "laptop_pst_forensics",
            "target_category_ids": ["P-04"],
            "target_source_types": ["laptop_pst"],
            "required_before_production": True,
        },
        {
            "priority_rank": 4,
            "action_code": "teams_gap_assessment",
            "target_category_ids": ["P-03"],
            "target_source_types": ["teams"],
            "required_before_production": True,
        },
        {
            "priority_rank": 5,
            "action_code": "archive_validation",
            "target_category_ids": ["P-02"],
            "target_source_types": ["email_archive"],
            "required_before_production": False,
        },
        {
            "priority_rank": 6,
            "action_code": "vendor_archive_retrieval",
            "target_category_ids": ["P-02"],
            "target_source_types": ["email_archive"],
            "required_before_production": False,
        },
    ],
    "risk_flags": [
        {
            "flag_code": "archive_recoverable_email",
            "severity": "medium",
            "category_ids": ["P-02"],
            "requires_regulator_notice": False,
        },
        {
            "flag_code": "hold_notice_omitted_personal_cloud_text",
            "severity": "high",
            "category_ids": ["P-05"],
            "requires_regulator_notice": False,
        },
        {
            "flag_code": "missing_local_pst",
            "severity": "high",
            "category_ids": ["P-04"],
            "requires_regulator_notice": False,
        },
        {
            "flag_code": "teams_pre_2022_gap",
            "severity": "high",
            "category_ids": ["P-03"],
            "requires_regulator_notice": False,
        },
    ],
}


RUBRIC = [
    (
        "SP001",
        "Correct matter readiness and former compliance custodian retention status.",
        2,
    ),
    (
        "SP002",
        "Correct P-01 personnel-file retention classification through 2027.",
        2,
    ),
    (
        "SP003",
        "Correct P-02 Iron archive classification despite active mailbox purge.",
        2,
    ),
    (
        "SP004",
        "Correct P-03 Teams pre-2022 source-gap classification and missing count.",
        2,
    ),
    (
        "SP005",
        "Correct P-04 missing local PST classification and action.",
        2,
    ),
    (
        "SP006",
        "Correct P-05 personal cloud/text hold-notice defect classification.",
        3,
    ),
    (
        "SP007",
        "Correct prioritized supplemental, hold-refresh, laptop, Teams, archive, and vendor/archive actions.",
        3,
    ),
    (
        "SP008",
        "Correct risk-flag set and regulator-notice booleans.",
        2,
    ),
]


def load_prediction(path_text: str) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    if not path_text:
        return None, ["prediction path was not provided"]
    path = Path(path_text)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, [f"could not load prediction JSON: {exc}"]
    if not isinstance(data, dict):
        errors.append("prediction root must be a JSON object")
        return None, errors
    return data, errors


def find_by_id(items: Any, key: str, expected_id: str) -> dict[str, Any] | None:
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict) and item.get(key) == expected_id:
            return item
    return None


def pick(obj: dict[str, Any] | None, keys: list[str]) -> dict[str, Any] | None:
    if obj is None:
        return None
    return {key: obj.get(key) for key in keys}


def normalize_plan(plan: Any) -> Any:
    if not isinstance(plan, list):
        return plan
    normalized = []
    for item in plan:
        if not isinstance(item, dict):
            normalized.append(item)
            continue
        normalized.append(
            {
                "priority_rank": item.get("priority_rank"),
                "action_code": item.get("action_code"),
                "target_category_ids": sorted(item.get("target_category_ids", [])),
                "target_source_types": sorted(item.get("target_source_types", [])),
                "required_before_production": item.get("required_before_production"),
            }
        )
    return sorted(normalized, key=lambda x: (x.get("priority_rank", 999), x.get("action_code", "")))


def normalize_flags(flags: Any) -> Any:
    if not isinstance(flags, list):
        return flags
    normalized = []
    for item in flags:
        if not isinstance(item, dict):
            normalized.append(item)
            continue
        normalized.append(
            {
                "flag_code": item.get("flag_code"),
                "severity": item.get("severity"),
                "category_ids": sorted(item.get("category_ids", [])),
                "requires_regulator_notice": item.get("requires_regulator_notice"),
            }
        )
    return sorted(normalized, key=lambda x: x.get("flag_code", ""))


def retention_match(prediction: dict[str, Any], category_id: str) -> bool:
    expected = EXPECTED["retention_gaps"][category_id]
    actual = find_by_id(prediction.get("retention_gaps"), "category_id", category_id)
    keys = list(expected.keys())
    return pick(actual, keys) == expected


def score_prediction(prediction: dict[str, Any] | None, load_errors: list[str]) -> dict[str, Any]:
    if prediction is None:
        prediction = {}

    custodian_keys = list(EXPECTED["custodian"].keys())
    custodian = find_by_id(
        prediction.get("custodian_statuses"),
        "custodian_id",
        EXPECTED["custodian"]["custodian_id"],
    )

    checks = {
        "SP001": (
            prediction.get("matter_id") == EXPECTED["matter_id"]
            and prediction.get("overall_readiness") == EXPECTED["overall_readiness"]
            and pick(custodian, custodian_keys) == EXPECTED["custodian"]
        ),
        "SP002": retention_match(prediction, "P-01"),
        "SP003": retention_match(prediction, "P-02"),
        "SP004": retention_match(prediction, "P-03"),
        "SP005": retention_match(prediction, "P-04"),
        "SP006": retention_match(prediction, "P-05"),
        "SP007": normalize_plan(prediction.get("collection_plan")) == EXPECTED["collection_plan"],
        "SP008": normalize_flags(prediction.get("risk_flags")) == EXPECTED["risk_flags"],
    }

    total_weight = sum(weight for _, _, weight in RUBRIC)
    earned_weight = 0
    points = []
    for point_id, goal, weight in RUBRIC:
        matched = bool(checks.get(point_id))
        if matched:
            earned_weight += weight
        points.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "matched": matched,
                "normalized_weight": round(weight / total_weight, 6),
            }
        )

    score = earned_weight / total_weight if total_weight else 0.0
    return {
        "score": round(score, 6),
        "earned_weight": earned_weight,
        "total_weight": total_weight,
        "points": points,
        "errors": load_errors,
    }


def main() -> int:
    prediction_path = sys.argv[1] if len(sys.argv) > 1 else ""
    prediction, errors = load_prediction(prediction_path)
    result = score_prediction(prediction, errors)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
