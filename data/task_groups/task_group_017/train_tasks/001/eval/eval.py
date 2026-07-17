#!/usr/bin/env python3
"""Exact-match evaluator for train_001."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


EXPECTED_TOP_LEVEL = {
    "matter_id": "M-CRN-041",
    "production_phase": "first_rolling",
    "disclosure_required": True,
}

EXPECTED_CATEGORY_FINDINGS: dict[str, dict[str, Any]] = {
    "CRN-03": {
        "finding_id": "CF-CRN-03-MISCODED-COMPLAINT",
        "category_status": "needs_supplemental_production",
        "blocked": True,
        "issue_ids": ["PI-CRN-QA-MISCODE"],
        "affected_sources": ["email"],
        "source_event_ids": ["CE-0002", "DOC-CRN-TEST-ACC-001", "PL-0001", "QC-0001"],
        "primary_action": "reprocess_qc",
        "notice_required": False,
    },
    "CRN-04": {
        "finding_id": "CF-CRN-04-PRIVILEGE-LOG-GAP",
        "category_status": "needs_privilege_correction",
        "blocked": True,
        "issue_ids": ["PI-CRN-PRIV-UNLOGGED"],
        "affected_sources": ["email", "legal hold system", "review platform"],
        "source_event_ids": ["PL-0002", "PV-0001"],
        "primary_action": "privilege_log_supplement",
        "notice_required": True,
    },
    "CRN-05": {
        "finding_id": "CF-CRN-05-PERSONAL-CHANNEL-GAP",
        "category_status": "blocked",
        "blocked": True,
        "issue_ids": ["PI-CRN-PERSONAL-DEVICE"],
        "affected_sources": ["Signal", "WhatsApp", "personal phone"],
        "source_event_ids": ["CE-0001"],
        "primary_action": "regulator_notice",
        "notice_required": True,
    },
    "CRN-06": {
        "finding_id": "CF-CRN-06-OVERBROAD-COUNSEL",
        "category_status": "needs_privilege_review",
        "blocked": True,
        "issue_ids": ["PI-CRN-COUNSEL-OVERBROAD"],
        "affected_sources": ["email", "legal files"],
        "source_event_ids": ["PL-0003", "PV-0002"],
        "primary_action": "privilege_review",
        "notice_required": False,
    },
}

EXPECTED_ISSUES: dict[str, dict[str, Any]] = {
    "PI-CRN-PERSONAL-DEVICE": {
        "issue_type": "personal_channel_gap",
        "severity": "critical",
        "timing_class": "post_hold_spoliation",
        "category_ids": ["CRN-05"],
        "custodian_ids": ["C-GW-014"],
        "document_ids": [],
        "source_event_ids": ["CE-0001"],
        "affected_sources": ["Signal", "WhatsApp", "personal phone"],
        "affected_count": 1,
        "produced_count": 0,
        "withheld_count": 0,
        "privilege_logged_count": 0,
        "unlogged_privilege_count": 0,
        "primary_action": "regulator_notice",
        "secondary_actions": ["custodian_declaration", "forensic_recovery", "hold_refresh", "supplemental_collection"],
        "notice_required": True,
    },
    "PI-CRN-QA-MISCODE": {
        "issue_type": "review_coding_error",
        "severity": "high",
        "timing_class": "coding_error",
        "category_ids": ["CRN-03"],
        "custodian_ids": ["C-QA-027"],
        "document_ids": ["DOC-CRN-TEST-ACC-001"],
        "source_event_ids": ["CE-0002", "DOC-CRN-TEST-ACC-001", "PL-0001", "QC-0001"],
        "affected_sources": ["email"],
        "affected_count": 1,
        "produced_count": 0,
        "withheld_count": 0,
        "privilege_logged_count": 0,
        "unlogged_privilege_count": 0,
        "primary_action": "reprocess_qc",
        "secondary_actions": ["supplemental_production"],
        "notice_required": False,
    },
    "PI-CRN-PRIV-UNLOGGED": {
        "issue_type": "privilege_log_gap",
        "severity": "high",
        "timing_class": "privilege_protocol_defect",
        "category_ids": ["CRN-04"],
        "custodian_ids": ["C-GW-014"],
        "document_ids": [],
        "source_event_ids": ["PL-0002", "PV-0001"],
        "affected_sources": ["email", "legal hold system", "review platform"],
        "affected_count": 4232,
        "produced_count": 618,
        "withheld_count": 4232,
        "privilege_logged_count": 1847,
        "unlogged_privilege_count": 2385,
        "primary_action": "privilege_log_supplement",
        "secondary_actions": ["privilege_review", "regulator_notice"],
        "notice_required": True,
    },
    "PI-CRN-COUNSEL-OVERBROAD": {
        "issue_type": "privilege_overdesignation",
        "severity": "medium",
        "timing_class": "privilege_protocol_defect",
        "category_ids": ["CRN-06"],
        "custodian_ids": ["C-GW-014"],
        "document_ids": [],
        "source_event_ids": ["PL-0003", "PV-0002"],
        "affected_sources": ["email", "legal files"],
        "affected_count": 1247,
        "produced_count": 0,
        "withheld_count": 1247,
        "privilege_logged_count": 0,
        "unlogged_privilege_count": 1247,
        "primary_action": "privilege_review",
        "secondary_actions": ["produce_nonprivileged"],
        "notice_required": False,
    },
}

EXPECTED_ACTIONS = [
    {
        "rank": 1,
        "action_id": "NA-REGULATOR-NOTICE",
        "action": "regulator_notice",
        "issue_ids": ["PI-CRN-PERSONAL-DEVICE", "PI-CRN-PRIV-UNLOGGED"],
        "category_ids": ["CRN-04", "CRN-05"],
        "owner_queue": "legal",
        "disclosure_step": True,
    },
    {
        "rank": 2,
        "action_id": "NA-PERSONAL-SOURCES",
        "action": "supplemental_collection",
        "issue_ids": ["PI-CRN-PERSONAL-DEVICE"],
        "category_ids": ["CRN-05"],
        "owner_queue": "client_it",
        "disclosure_step": False,
    },
    {
        "rank": 3,
        "action_id": "NA-QC-REPROCESS",
        "action": "reprocess_qc",
        "issue_ids": ["PI-CRN-QA-MISCODE"],
        "category_ids": ["CRN-03"],
        "owner_queue": "review_vendor",
        "disclosure_step": False,
    },
    {
        "rank": 4,
        "action_id": "NA-PRIVILEGE-LOG",
        "action": "privilege_log_supplement",
        "issue_ids": ["PI-CRN-PRIV-UNLOGGED"],
        "category_ids": ["CRN-04"],
        "owner_queue": "privilege_team",
        "disclosure_step": True,
    },
    {
        "rank": 5,
        "action_id": "NA-COUNSEL-OVERDESIGNATION",
        "action": "privilege_review",
        "issue_ids": ["PI-CRN-COUNSEL-OVERBROAD"],
        "category_ids": ["CRN-06"],
        "owner_queue": "privilege_team",
        "disclosure_step": False,
    },
]

SCORING_POINTS = [
    ("SP001", "Correct matter, phase, disclosure flag, and complete affected category and issue sets.", 1),
    (
        "SP002",
        "Identifies missing personal phone, Signal, and WhatsApp for CRN-05 with post-hold disclosure action.",
        3,
    ),
    (
        "SP003",
        "Identifies the miscoded testing-accuracy complaint email for CRN-03 and QC/supplemental production action.",
        2,
    ),
    ("SP004", "Calculates the CRN-04 privilege log gap as 4,232 withheld, 1,847 logged, and 2,385 unlogged.", 3),
    ("SP005", "Flags CRN-06 counsel communications as overbroad with 1,247 withheld and zero produced.", 2),
    (
        "SP006",
        "Maps the four affected categories to the correct statuses, sources, events, actions, and notice flags.",
        2,
    ),
    ("SP007", "Provides the required ranked remediation and disclosure action plan.", 3),
    ("SP008", "Keeps only the material first-production issue set without adding noisy comparator issues.", 1),
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def norm_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def norm_list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        return []
    return sorted(norm_scalar(item) for item in value)


def bool_equal(actual: Any, expected: bool) -> bool:
    return isinstance(actual, bool) and actual is expected


def int_equal(actual: Any, expected: int) -> bool:
    try:
        return int(actual) == expected
    except (TypeError, ValueError):
        return False


def rows_by_id(candidate: dict[str, Any], list_key: str, id_key: str) -> dict[str, dict[str, Any]]:
    rows = candidate.get(list_key, [])
    if not isinstance(rows, list):
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict):
            row_id = row.get(id_key)
            if isinstance(row_id, str) and row_id.strip():
                mapped[row_id.strip()] = row
    return mapped


def subset_match(row: dict[str, Any], expected: dict[str, Any]) -> bool:
    for key, exp_value in expected.items():
        actual = row.get(key)
        if isinstance(exp_value, list):
            if norm_list(actual) != norm_list(exp_value):
                return False
        elif isinstance(exp_value, bool):
            if not bool_equal(actual, exp_value):
                return False
        elif isinstance(exp_value, int):
            if not int_equal(actual, exp_value):
                return False
        else:
            if norm_scalar(actual) != exp_value:
                return False
    return True


def category_match(candidate: dict[str, Any], category_id: str) -> bool:
    categories = rows_by_id(candidate, "category_findings", "category_id")
    return subset_match(categories.get(category_id, {}), EXPECTED_CATEGORY_FINDINGS[category_id])


def issue_match(candidate: dict[str, Any], issue_id: str) -> bool:
    issues = rows_by_id(candidate, "priority_issues", "issue_id")
    return subset_match(issues.get(issue_id, {}), EXPECTED_ISSUES[issue_id])


def normalized_actions(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    rows = candidate.get("next_actions", [])
    if not isinstance(rows, list):
        return []
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        normalized.append(
            {
                "rank": row.get("rank"),
                "action_id": norm_scalar(row.get("action_id")),
                "action": norm_scalar(row.get("action")),
                "issue_ids": norm_list(row.get("issue_ids")),
                "category_ids": norm_list(row.get("category_ids")),
                "owner_queue": norm_scalar(row.get("owner_queue")),
                "disclosure_step": row.get("disclosure_step"),
            }
        )

    def rank_key(row: dict[str, Any]) -> tuple[bool, int, str]:
        rank = row["rank"]
        if isinstance(rank, int):
            return (False, rank, "")
        text = str(rank)
        return (not text.isdigit(), int(text) if text.isdigit() else 999, text)

    return sorted(normalized, key=rank_key)


def expected_actions() -> list[dict[str, Any]]:
    return [
        {
            "rank": row["rank"],
            "action_id": row["action_id"],
            "action": row["action"],
            "issue_ids": norm_list(row["issue_ids"]),
            "category_ids": norm_list(row["category_ids"]),
            "owner_queue": row["owner_queue"],
            "disclosure_step": row["disclosure_step"],
        }
        for row in EXPECTED_ACTIONS
    ]


def evaluate(candidate: dict[str, Any]) -> dict[str, Any]:
    categories = rows_by_id(candidate, "category_findings", "category_id")
    issues = rows_by_id(candidate, "priority_issues", "issue_id")
    expected_category_ids = sorted(EXPECTED_CATEGORY_FINDINGS)
    expected_issue_ids = sorted(EXPECTED_ISSUES)

    checks = {
        "SP001": (
            all(candidate.get(k) == v for k, v in EXPECTED_TOP_LEVEL.items())
            and sorted(categories) == expected_category_ids
            and sorted(issues) == expected_issue_ids
        ),
        "SP002": issue_match(candidate, "PI-CRN-PERSONAL-DEVICE") and category_match(candidate, "CRN-05"),
        "SP003": issue_match(candidate, "PI-CRN-QA-MISCODE") and category_match(candidate, "CRN-03"),
        "SP004": issue_match(candidate, "PI-CRN-PRIV-UNLOGGED") and category_match(candidate, "CRN-04"),
        "SP005": issue_match(candidate, "PI-CRN-COUNSEL-OVERBROAD") and category_match(candidate, "CRN-06"),
        "SP006": all(category_match(candidate, category_id) for category_id in expected_category_ids),
        "SP007": normalized_actions(candidate) == expected_actions(),
        "SP008": len(categories) == 4
        and len(issues) == 4
        and sorted(categories) == expected_category_ids
        and sorted(issues) == expected_issue_ids,
    }

    total_weight = sum(weight for _, _, weight in SCORING_POINTS)
    earned_weight = sum(weight for point_id, _, weight in SCORING_POINTS if checks[point_id])
    points = [
        {
            "id": point_id,
            "description": description,
            "weight": weight,
            "earned": weight if checks[point_id] else 0,
            "passed": bool(checks[point_id]),
        }
        for point_id, description, weight in SCORING_POINTS
    ]
    return {"score": round(earned_weight / total_weight, 6), "points": points}


def main() -> None:
    prediction_arg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PREDICTION", "")
    if prediction_arg:
        prediction_path = Path(prediction_arg)
    else:
        prediction_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"

    try:
        candidate = load_json(prediction_path)
        if not isinstance(candidate, dict):
            raise ValueError("prediction root must be a JSON object")
        result = evaluate(candidate)
    except Exception:
        result = {
            "score": 0.0,
            "points": [
                {
                    "id": point_id,
                    "description": description,
                    "weight": weight,
                    "earned": 0,
                    "passed": False,
                }
                for point_id, description, weight in SCORING_POINTS
            ],
        }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
