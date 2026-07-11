#!/usr/bin/env python3
"""Exact-match evaluator for task_group_017 test_001."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


EXPECTED_TOP_LEVEL = {
    "matter_id": "M-ALD-507",
    "production_phase": "first_rolling",
    "disclosure_required": True,
}

EXPECTED_CATEGORY_FINDINGS: dict[str, dict[str, Any]] = {
    "A-01": {
        "finding_id": "CF-ALD-A01-PRIVILEGE-LOG-GAP",
        "category_status": "needs_privilege_correction",
        "blocked": True,
        "issue_ids": ["PI-ALD-PRIV-UNLOGGED"],
        "affected_sources": ["email", "review platform"],
        "source_event_ids": ["PL-0022", "PV-0008"],
        "primary_action": "privilege_log_supplement",
        "notice_required": True,
    },
    "A-02": {
        "finding_id": "CF-ALD-A02-BOARD-PORTAL-GAP",
        "category_status": "needs_source_collection",
        "blocked": True,
        "issue_ids": ["PI-ALD-BOARD-PORTAL"],
        "affected_sources": ["board portal"],
        "source_event_ids": ["CE-0018", "DOC-ALD-BOARD-Q2-2022", "PL-0020", "QC-0008", "RR-0015"],
        "primary_action": "supplemental_collection",
        "notice_required": False,
    },
    "A-04": {
        "finding_id": "CF-ALD-A04-PERSONAL-MESSAGE-GAP",
        "category_status": "blocked",
        "blocked": True,
        "issue_ids": ["PI-ALD-PERSONAL-MESSAGES"],
        "affected_sources": ["Signal", "Telegram", "personal phone"],
        "source_event_ids": ["CE-0016", "PL-0018"],
        "primary_action": "regulator_notice",
        "notice_required": True,
    },
    "A-08": {
        "finding_id": "CF-ALD-A08-PRIOR-COUNSEL-OVERBROAD",
        "category_status": "needs_privilege_review",
        "blocked": True,
        "issue_ids": ["PI-ALD-COUNSEL-OVERBROAD"],
        "affected_sources": ["email", "legal files"],
        "source_event_ids": ["PL-0021", "PV-0009"],
        "primary_action": "privilege_review",
        "notice_required": False,
    },
    "A-09": {
        "finding_id": "CF-ALD-A09-IBARRA-MISCODED-COMPLAINT",
        "category_status": "needs_supplemental_production",
        "blocked": True,
        "issue_ids": ["PI-ALD-IBARRA-MISCODE"],
        "affected_sources": ["email"],
        "source_event_ids": ["CE-0017", "DOC-ALD-IBARRA-001", "PL-0019", "QC-0007"],
        "primary_action": "reprocess_qc",
        "notice_required": False,
    },
}

EXPECTED_ISSUES: dict[str, dict[str, Any]] = {
    "PI-ALD-BOARD-PORTAL": {
        "issue_type": "source_gap",
        "severity": "high",
        "timing_class": "recoverable_source_gap",
        "category_ids": ["A-02"],
        "custodian_ids": ["C-TP-090"],
        "document_ids": ["DOC-ALD-BOARD-Q2-2022"],
        "source_event_ids": ["CE-0018", "DOC-ALD-BOARD-Q2-2022", "PL-0020", "QC-0008", "RR-0015"],
        "affected_sources": ["board portal"],
        "affected_count": 1,
        "produced_count": 142,
        "withheld_count": 11,
        "privilege_logged_count": 11,
        "unlogged_privilege_count": 0,
        "primary_action": "supplemental_collection",
        "secondary_actions": ["supplemental_production"],
        "notice_required": False,
    },
    "PI-ALD-COUNSEL-OVERBROAD": {
        "issue_type": "privilege_overdesignation",
        "severity": "medium",
        "timing_class": "privilege_protocol_defect",
        "category_ids": ["A-08"],
        "custodian_ids": ["C-TP-090"],
        "document_ids": [],
        "source_event_ids": ["PL-0021", "PV-0009"],
        "affected_sources": ["email", "legal files"],
        "affected_count": 980,
        "produced_count": 0,
        "withheld_count": 980,
        "privilege_logged_count": 0,
        "unlogged_privilege_count": 980,
        "primary_action": "privilege_review",
        "secondary_actions": ["produce_nonprivileged"],
        "notice_required": False,
    },
    "PI-ALD-IBARRA-MISCODE": {
        "issue_type": "review_coding_error",
        "severity": "high",
        "timing_class": "coding_error",
        "category_ids": ["A-09"],
        "custodian_ids": ["C-DI-091"],
        "document_ids": ["DOC-ALD-IBARRA-001"],
        "source_event_ids": ["CE-0017", "DOC-ALD-IBARRA-001", "PL-0019", "QC-0007"],
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
    "PI-ALD-PERSONAL-MESSAGES": {
        "issue_type": "personal_channel_gap",
        "severity": "critical",
        "timing_class": "post_hold_spoliation",
        "category_ids": ["A-04"],
        "custodian_ids": ["C-TP-090"],
        "document_ids": [],
        "source_event_ids": ["CE-0016", "PL-0018"],
        "affected_sources": ["Signal", "Telegram", "personal phone"],
        "affected_count": 1,
        "produced_count": 0,
        "withheld_count": 0,
        "privilege_logged_count": 0,
        "unlogged_privilege_count": 0,
        "primary_action": "regulator_notice",
        "secondary_actions": ["custodian_declaration", "forensic_recovery", "hold_refresh", "supplemental_collection"],
        "notice_required": True,
    },
    "PI-ALD-PRIV-UNLOGGED": {
        "issue_type": "privilege_log_gap",
        "severity": "high",
        "timing_class": "privilege_protocol_defect",
        "category_ids": ["A-01"],
        "custodian_ids": ["C-TP-090"],
        "document_ids": [],
        "source_event_ids": ["PL-0022", "PV-0008"],
        "affected_sources": ["email", "review platform"],
        "affected_count": 3640,
        "produced_count": 3295,
        "withheld_count": 3640,
        "privilege_logged_count": 2275,
        "unlogged_privilege_count": 1365,
        "primary_action": "privilege_log_supplement",
        "secondary_actions": ["privilege_review", "regulator_notice"],
        "notice_required": True,
    },
}

EXPECTED_ACTIONS = [
    {
        "rank": 1,
        "action_id": "NA-ALD-REGULATOR-NOTICE",
        "action": "regulator_notice",
        "issue_ids": ["PI-ALD-PERSONAL-MESSAGES", "PI-ALD-PRIV-UNLOGGED"],
        "category_ids": ["A-01", "A-04"],
        "owner_queue": "legal",
        "disclosure_step": True,
    },
    {
        "rank": 2,
        "action_id": "NA-ALD-PERSONAL-SOURCES",
        "action": "supplemental_collection",
        "issue_ids": ["PI-ALD-PERSONAL-MESSAGES"],
        "category_ids": ["A-04"],
        "owner_queue": "client_it",
        "disclosure_step": False,
    },
    {
        "rank": 3,
        "action_id": "NA-ALD-BOARD-PORTAL",
        "action": "supplemental_collection",
        "issue_ids": ["PI-ALD-BOARD-PORTAL"],
        "category_ids": ["A-02"],
        "owner_queue": "e_discovery",
        "disclosure_step": False,
    },
    {
        "rank": 4,
        "action_id": "NA-ALD-QC-REPROCESS",
        "action": "reprocess_qc",
        "issue_ids": ["PI-ALD-IBARRA-MISCODE"],
        "category_ids": ["A-09"],
        "owner_queue": "review_vendor",
        "disclosure_step": False,
    },
    {
        "rank": 5,
        "action_id": "NA-ALD-PRIVILEGE-LOG",
        "action": "privilege_log_supplement",
        "issue_ids": ["PI-ALD-PRIV-UNLOGGED"],
        "category_ids": ["A-01"],
        "owner_queue": "privilege_team",
        "disclosure_step": True,
    },
    {
        "rank": 6,
        "action_id": "NA-ALD-COUNSEL-OVERDESIGNATION",
        "action": "privilege_review",
        "issue_ids": ["PI-ALD-COUNSEL-OVERBROAD"],
        "category_ids": ["A-08"],
        "owner_queue": "privilege_team",
        "disclosure_step": False,
    },
]

SCORING_POINTS = [
    ("SP001", "Correct matter, phase, disclosure flag, and complete affected category and issue sets.", 1),
    ("SP002", "Identifies the C-TP-090 personal phone, Signal, and Telegram gap for A-04 with notice action.", 3),
    ("SP003", "Identifies the D. Ibarra revenue-recognition complaint miscoding for A-09 and QC action.", 2),
    ("SP004", "Calculates the A-01 privilege log gap as 3,640 withheld, 2,275 logged, and 1,365 unlogged.", 3),
    ("SP005", "Flags A-08 prior counsel logistics as overbroad with 980 withheld and zero produced.", 2),
    ("SP006", "Identifies the A-02 Q2 2022 board package gap in the separate board portal.", 2),
    ("SP007", "Maps all affected categories to the correct statuses, sources, events, actions, and notice flags.", 2),
    ("SP008", "Provides the required ranked remediation and disclosure action plan.", 3),
    ("SP009", "Keeps only the material first-production issue set without adding noisy comparator issues.", 1),
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


def list_contains(actual: Any, expected: list[Any]) -> bool:
    if not isinstance(actual, list):
        return False
    actual_norm = set(norm_list(actual))
    return all(norm_scalar(item) in actual_norm for item in expected)


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
        if key in {
            "finding_id",
            "issue_ids",
            "affected_sources",
            "custodian_ids",
            "document_ids",
            "secondary_actions",
        }:
            continue
        actual = row.get(key)
        if isinstance(exp_value, list):
            if key == "source_event_ids":
                if not list_contains(actual, exp_value):
                    return False
            elif norm_list(actual) != norm_list(exp_value):
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
    actual = issues.get(issue_id)
    expected = EXPECTED_ISSUES[issue_id]
    if actual is None:
        for row in candidate.get("priority_issues", []):
            if not isinstance(row, dict):
                continue
            if (
                norm_list(row.get("category_ids")) == norm_list(expected["category_ids"])
                and row.get("issue_type") == expected["issue_type"]
            ):
                actual = row
                break
    return subset_match(actual or {}, expected)


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
            and len(candidate.get("priority_issues", [])) == len(expected_issue_ids)
        ),
        "SP002": issue_match(candidate, "PI-ALD-PERSONAL-MESSAGES") and category_match(candidate, "A-04"),
        "SP003": issue_match(candidate, "PI-ALD-IBARRA-MISCODE") and category_match(candidate, "A-09"),
        "SP004": issue_match(candidate, "PI-ALD-PRIV-UNLOGGED") and category_match(candidate, "A-01"),
        "SP005": issue_match(candidate, "PI-ALD-COUNSEL-OVERBROAD") and category_match(candidate, "A-08"),
        "SP006": issue_match(candidate, "PI-ALD-BOARD-PORTAL") and category_match(candidate, "A-02"),
        "SP007": all(category_match(candidate, category_id) for category_id in expected_category_ids),
        "SP008": normalized_actions(candidate) == expected_actions(),
        "SP009": len(categories) == 5
        and len(issues) == 5
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


def zero_result() -> dict[str, Any]:
    return {
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
        result = zero_result()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
