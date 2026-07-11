#!/usr/bin/env python3
"""Semantic evaluator for task_group_017 test_005.

The solver-visible template allows solver-assigned stable issue IDs. This
evaluator therefore matches issue rows by business fields first, then checks
that the solver's issue IDs are used consistently across the response.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_SCOPE = {
    "task_id": "test_005",
    "board_scope": {
        "matter_ids": ["M-ALD-507", "M-BAY-144", "M-LYN-322"],
        "portfolio_status": "remediation_required",
        "portfolio_notice_required": True,
        "portfolio_deadline_risk": True,
    },
}

EXPECTED_PRIORITIES = [
    {
        "rank": 1,
        "issue_id": "ALD_PERSONAL_MESSAGES",
        "matter_id": "M-ALD-507",
        "severity": "critical",
        "primary_action": "regulator_notice",
        "secondary_actions": ["hold_refresh", "supplemental_collection"],
        "notice_risk": True,
        "deadline_risk": True,
    },
    {
        "rank": 2,
        "issue_id": "BAY_TEAMS_PURGE",
        "matter_id": "M-BAY-144",
        "severity": "critical",
        "primary_action": "regulator_notice",
        "secondary_actions": ["hold_refresh"],
        "notice_risk": True,
        "deadline_risk": True,
    },
    {
        "rank": 3,
        "issue_id": "LYN_SHARED_FOLDER_DELETION",
        "matter_id": "M-LYN-322",
        "severity": "critical",
        "primary_action": "regulator_notice",
        "secondary_actions": ["supplemental_collection"],
        "notice_risk": True,
        "deadline_risk": True,
    },
    {
        "rank": 4,
        "issue_id": "LYN_LAPTOP_WIPE",
        "matter_id": "M-LYN-322",
        "severity": "critical",
        "primary_action": "regulator_notice",
        "secondary_actions": ["supplemental_collection"],
        "notice_risk": True,
        "deadline_risk": True,
    },
    {
        "rank": 5,
        "issue_id": "ALD_PRIVILEGE_LOG_GAP",
        "matter_id": "M-ALD-507",
        "severity": "high",
        "primary_action": "privilege_review",
        "secondary_actions": ["regulator_notice"],
        "notice_risk": True,
        "deadline_risk": True,
    },
    {
        "rank": 6,
        "issue_id": "LYN_PRIVILEGE_MISCODING",
        "matter_id": "M-LYN-322",
        "severity": "high",
        "primary_action": "clawback_check",
        "secondary_actions": ["privilege_review"],
        "notice_risk": False,
        "deadline_risk": True,
    },
    {
        "rank": 7,
        "issue_id": "BAY_TIDEWATER_AUDIT",
        "matter_id": "M-BAY-144",
        "severity": "high",
        "primary_action": "vendor_retrieval",
        "secondary_actions": ["supplemental_collection"],
        "notice_risk": False,
        "deadline_risk": True,
    },
    {
        "rank": 8,
        "issue_id": "ALD_COMPLAINT_MISCODING",
        "matter_id": "M-ALD-507",
        "severity": "high",
        "primary_action": "reprocess_qc",
        "secondary_actions": ["supplemental_collection"],
        "notice_risk": False,
        "deadline_risk": True,
    },
    {
        "rank": 9,
        "issue_id": "LYN_PERSONAL_OUTLOOK",
        "matter_id": "M-LYN-322",
        "severity": "high",
        "primary_action": "supplemental_collection",
        "secondary_actions": ["hold_refresh"],
        "notice_risk": False,
        "deadline_risk": True,
    },
    {
        "rank": 10,
        "issue_id": "LYN_FAILED_ATTACHMENTS",
        "matter_id": "M-LYN-322",
        "severity": "medium",
        "primary_action": "reprocess_qc",
        "secondary_actions": ["supplemental_collection"],
        "notice_risk": False,
        "deadline_risk": True,
    },
]

EXPECTED_MATRIX: dict[str, dict[str, Any]] = {
    "ALD_BOARD_PORTAL": {
        "matter_id": "M-ALD-507",
        "issue_id": "ALD_BOARD_PORTAL",
        "category_ids": ["A-02"],
        "issue_type": "recoverable_external_source",
        "timing_class": "recoverable_archive",
        "severity": "medium",
        "affected_count": 1,
        "recovered_count": 1,
        "unrecovered_count": 0,
        "unlogged_privilege_count": 0,
        "primary_action": "supplemental_collection",
        "secondary_actions": [],
        "regulator_notice_required": False,
        "deadline_risk": True,
    },
    "ALD_COMPLAINT_MISCODING": {
        "matter_id": "M-ALD-507",
        "issue_id": "ALD_COMPLAINT_MISCODING",
        "category_ids": ["A-09"],
        "issue_type": "review_coding_error",
        "timing_class": "coding_error",
        "severity": "high",
        "affected_count": 1,
        "recovered_count": 1,
        "unrecovered_count": 0,
        "unlogged_privilege_count": 0,
        "primary_action": "reprocess_qc",
        "secondary_actions": ["supplemental_collection"],
        "regulator_notice_required": False,
        "deadline_risk": True,
    },
    "ALD_COUNSEL_OVERDESIGNATION": {
        "matter_id": "M-ALD-507",
        "issue_id": "ALD_COUNSEL_OVERDESIGNATION",
        "category_ids": ["A-08"],
        "issue_type": "privilege_overdesignation",
        "timing_class": "privilege_protocol_defect",
        "severity": "medium",
        "affected_count": 980,
        "recovered_count": 0,
        "unrecovered_count": 0,
        "unlogged_privilege_count": 980,
        "primary_action": "privilege_review",
        "secondary_actions": [],
        "regulator_notice_required": False,
        "deadline_risk": True,
    },
    "ALD_PERSONAL_MESSAGES": {
        "matter_id": "M-ALD-507",
        "issue_id": "ALD_PERSONAL_MESSAGES",
        "category_ids": ["A-04"],
        "issue_type": "personal_channel_gap",
        "timing_class": "post_hold_spoliation",
        "severity": "critical",
        "affected_count": 1,
        "recovered_count": 0,
        "unrecovered_count": 1,
        "unlogged_privilege_count": 0,
        "primary_action": "regulator_notice",
        "secondary_actions": ["hold_refresh", "supplemental_collection"],
        "regulator_notice_required": True,
        "deadline_risk": True,
    },
    "ALD_PRIVILEGE_LOG_GAP": {
        "matter_id": "M-ALD-507",
        "issue_id": "ALD_PRIVILEGE_LOG_GAP",
        "category_ids": ["A-01"],
        "issue_type": "privilege_log_gap",
        "timing_class": "privilege_protocol_defect",
        "severity": "high",
        "affected_count": 3640,
        "recovered_count": 0,
        "unrecovered_count": 0,
        "unlogged_privilege_count": 1365,
        "primary_action": "privilege_review",
        "secondary_actions": ["regulator_notice"],
        "regulator_notice_required": True,
        "deadline_risk": True,
    },
    "BAY_HOLD_SCOPE": {
        "matter_id": "M-BAY-144",
        "issue_id": "BAY_HOLD_SCOPE",
        "category_ids": ["B-05"],
        "issue_type": "hold_notice_gap",
        "timing_class": "hold_notice_defect",
        "severity": "high",
        "affected_count": 3,
        "recovered_count": 0,
        "unrecovered_count": 3,
        "unlogged_privilege_count": 0,
        "primary_action": "hold_refresh",
        "secondary_actions": ["supplemental_collection"],
        "regulator_notice_required": False,
        "deadline_risk": True,
    },
    "BAY_LAB_DATA_POLICY_GAP": {
        "matter_id": "M-BAY-144",
        "issue_id": "BAY_LAB_DATA_POLICY_GAP",
        "category_ids": ["B-01"],
        "issue_type": "retention_policy_gap",
        "timing_class": "pre_hold_policy",
        "severity": "medium",
        "affected_count": 6,
        "recovered_count": 0,
        "unrecovered_count": 6,
        "unlogged_privilege_count": 0,
        "primary_action": "supplemental_collection",
        "secondary_actions": [],
        "regulator_notice_required": False,
        "deadline_risk": False,
    },
    "BAY_TEAMS_PURGE": {
        "matter_id": "M-BAY-144",
        "issue_id": "BAY_TEAMS_PURGE",
        "category_ids": ["B-02"],
        "issue_type": "post_hold_destruction",
        "timing_class": "post_hold_spoliation",
        "severity": "critical",
        "affected_count": 11,
        "recovered_count": 0,
        "unrecovered_count": 11,
        "unlogged_privilege_count": 0,
        "primary_action": "regulator_notice",
        "secondary_actions": ["hold_refresh"],
        "regulator_notice_required": True,
        "deadline_risk": True,
    },
    "BAY_TIDEWATER_AUDIT": {
        "matter_id": "M-BAY-144",
        "issue_id": "BAY_TIDEWATER_AUDIT",
        "category_ids": ["B-04"],
        "issue_type": "retained_missing",
        "timing_class": "retained_missing",
        "severity": "high",
        "affected_count": 1,
        "recovered_count": 0,
        "unrecovered_count": 1,
        "unlogged_privilege_count": 0,
        "primary_action": "vendor_retrieval",
        "secondary_actions": ["supplemental_collection"],
        "regulator_notice_required": False,
        "deadline_risk": True,
    },
    "BAY_VAULTSEVEN_ARCHIVE": {
        "matter_id": "M-BAY-144",
        "issue_id": "BAY_VAULTSEVEN_ARCHIVE",
        "category_ids": ["B-03"],
        "issue_type": "recoverable_external_source",
        "timing_class": "recoverable_archive",
        "severity": "medium",
        "affected_count": 9220,
        "recovered_count": 9220,
        "unrecovered_count": 0,
        "unlogged_privilege_count": 0,
        "primary_action": "supplemental_collection",
        "secondary_actions": [],
        "regulator_notice_required": False,
        "deadline_risk": False,
    },
    "LYN_FAILED_ATTACHMENTS": {
        "matter_id": "M-LYN-322",
        "issue_id": "LYN_FAILED_ATTACHMENTS",
        "category_ids": ["L-06"],
        "issue_type": "processing_failure",
        "timing_class": "processing_exception",
        "severity": "medium",
        "affected_count": 31,
        "recovered_count": 0,
        "unrecovered_count": 31,
        "unlogged_privilege_count": 0,
        "primary_action": "reprocess_qc",
        "secondary_actions": ["supplemental_collection"],
        "regulator_notice_required": False,
        "deadline_risk": True,
    },
    "LYN_LAPTOP_WIPE": {
        "matter_id": "M-LYN-322",
        "issue_id": "LYN_LAPTOP_WIPE",
        "category_ids": ["L-02"],
        "issue_type": "device_wipe",
        "timing_class": "post_hold_spoliation",
        "severity": "critical",
        "affected_count": 1,
        "recovered_count": 0,
        "unrecovered_count": 1,
        "unlogged_privilege_count": 0,
        "primary_action": "regulator_notice",
        "secondary_actions": ["supplemental_collection"],
        "regulator_notice_required": True,
        "deadline_risk": True,
    },
    "LYN_PERSONAL_OUTLOOK": {
        "matter_id": "M-LYN-322",
        "issue_id": "LYN_PERSONAL_OUTLOOK",
        "category_ids": ["L-04"],
        "issue_type": "uncollected_source",
        "timing_class": "uncollected_source",
        "severity": "high",
        "affected_count": 1,
        "recovered_count": 0,
        "unrecovered_count": 1,
        "unlogged_privilege_count": 0,
        "primary_action": "supplemental_collection",
        "secondary_actions": ["hold_refresh"],
        "regulator_notice_required": False,
        "deadline_risk": True,
    },
    "LYN_PRIVILEGE_MISCODING": {
        "matter_id": "M-LYN-322",
        "issue_id": "LYN_PRIVILEGE_MISCODING",
        "category_ids": ["L-06"],
        "issue_type": "review_coding_error",
        "timing_class": "coding_error",
        "severity": "high",
        "affected_count": 39,
        "recovered_count": 0,
        "unrecovered_count": 39,
        "unlogged_privilege_count": 0,
        "primary_action": "clawback_check",
        "secondary_actions": ["privilege_review"],
        "regulator_notice_required": False,
        "deadline_risk": True,
    },
    "LYN_PRIVILEGE_OVERDESIGNATION": {
        "matter_id": "M-LYN-322",
        "issue_id": "LYN_PRIVILEGE_OVERDESIGNATION",
        "category_ids": ["L-06"],
        "issue_type": "privilege_overdesignation",
        "timing_class": "privilege_protocol_defect",
        "severity": "medium",
        "affected_count": 18,
        "recovered_count": 0,
        "unrecovered_count": 0,
        "unlogged_privilege_count": 18,
        "primary_action": "privilege_review",
        "secondary_actions": [],
        "regulator_notice_required": False,
        "deadline_risk": True,
    },
    "LYN_PRIVILEGE_WAIVER": {
        "matter_id": "M-LYN-322",
        "issue_id": "LYN_PRIVILEGE_WAIVER",
        "category_ids": ["L-05"],
        "issue_type": "third_party_forward",
        "timing_class": "privilege_waiver",
        "severity": "high",
        "affected_count": 4,
        "recovered_count": 0,
        "unrecovered_count": 0,
        "unlogged_privilege_count": 0,
        "primary_action": "privilege_review",
        "secondary_actions": [],
        "regulator_notice_required": False,
        "deadline_risk": True,
    },
    "LYN_SHARED_FOLDER_DELETION": {
        "matter_id": "M-LYN-322",
        "issue_id": "LYN_SHARED_FOLDER_DELETION",
        "category_ids": ["L-03"],
        "issue_type": "source_deletion",
        "timing_class": "post_hold_spoliation",
        "severity": "critical",
        "affected_count": 52,
        "recovered_count": 41,
        "unrecovered_count": 11,
        "unlogged_privilege_count": 0,
        "primary_action": "regulator_notice",
        "secondary_actions": ["supplemental_collection"],
        "regulator_notice_required": True,
        "deadline_risk": True,
    },
}

EXPECTED_FAILURES = [
    {
        "failure_code": "external_or_recoverable_sources",
        "matter_ids": ["M-ALD-507", "M-BAY-144"],
        "issue_ids": ["ALD_BOARD_PORTAL", "BAY_TIDEWATER_AUDIT", "BAY_VAULTSEVEN_ARCHIVE"],
        "action_enums": ["supplemental_collection", "vendor_retrieval"],
        "notice_risk": False,
    },
    {
        "failure_code": "personal_or_off_platform_sources",
        "matter_ids": ["M-ALD-507", "M-BAY-144", "M-LYN-322"],
        "issue_ids": ["ALD_PERSONAL_MESSAGES", "BAY_HOLD_SCOPE", "LYN_PERSONAL_OUTLOOK"],
        "action_enums": ["hold_refresh", "supplemental_collection"],
        "notice_risk": True,
    },
    {
        "failure_code": "post_hold_loss",
        "matter_ids": ["M-BAY-144", "M-LYN-322"],
        "issue_ids": ["BAY_TEAMS_PURGE", "LYN_LAPTOP_WIPE", "LYN_SHARED_FOLDER_DELETION"],
        "action_enums": ["regulator_notice", "supplemental_collection"],
        "notice_risk": True,
    },
    {
        "failure_code": "privilege_protocol_qc",
        "matter_ids": ["M-ALD-507", "M-LYN-322"],
        "issue_ids": [
            "ALD_COUNSEL_OVERDESIGNATION",
            "ALD_PRIVILEGE_LOG_GAP",
            "LYN_PRIVILEGE_MISCODING",
            "LYN_PRIVILEGE_OVERDESIGNATION",
            "LYN_PRIVILEGE_WAIVER",
        ],
        "action_enums": ["clawback_check", "privilege_review", "regulator_notice"],
        "notice_risk": True,
    },
    {
        "failure_code": "review_processing_errors",
        "matter_ids": ["M-ALD-507", "M-LYN-322"],
        "issue_ids": ["ALD_COMPLAINT_MISCODING", "LYN_FAILED_ATTACHMENTS"],
        "action_enums": ["reprocess_qc", "supplemental_collection"],
        "notice_risk": False,
    },
]

EXPECTED_DEADLINES = [
    {
        "matter_id": "M-ALD-507",
        "deadline": "2024-12-18",
        "deadline_risk": True,
        "notice_risk": True,
        "deadline_issue_ids": [
            "ALD_BOARD_PORTAL",
            "ALD_COMPLAINT_MISCODING",
            "ALD_COUNSEL_OVERDESIGNATION",
            "ALD_PERSONAL_MESSAGES",
            "ALD_PRIVILEGE_LOG_GAP",
        ],
        "notice_issue_ids": ["ALD_PERSONAL_MESSAGES", "ALD_PRIVILEGE_LOG_GAP"],
        "required_actions": [
            "hold_refresh",
            "privilege_review",
            "regulator_notice",
            "reprocess_qc",
            "supplemental_collection",
        ],
    },
    {
        "matter_id": "M-BAY-144",
        "deadline": "2025-04-15",
        "deadline_risk": True,
        "notice_risk": True,
        "deadline_issue_ids": ["BAY_HOLD_SCOPE", "BAY_TEAMS_PURGE", "BAY_TIDEWATER_AUDIT"],
        "notice_issue_ids": ["BAY_TEAMS_PURGE"],
        "required_actions": [
            "hold_refresh",
            "regulator_notice",
            "supplemental_collection",
            "vendor_retrieval",
        ],
    },
    {
        "matter_id": "M-LYN-322",
        "deadline": "2025-01-24",
        "deadline_risk": True,
        "notice_risk": True,
        "deadline_issue_ids": [
            "LYN_FAILED_ATTACHMENTS",
            "LYN_LAPTOP_WIPE",
            "LYN_PERSONAL_OUTLOOK",
            "LYN_PRIVILEGE_MISCODING",
            "LYN_PRIVILEGE_OVERDESIGNATION",
            "LYN_PRIVILEGE_WAIVER",
            "LYN_SHARED_FOLDER_DELETION",
        ],
        "notice_issue_ids": ["LYN_LAPTOP_WIPE", "LYN_SHARED_FOLDER_DELETION"],
        "required_actions": [
            "clawback_check",
            "hold_refresh",
            "privilege_review",
            "regulator_notice",
            "reprocess_qc",
            "supplemental_collection",
        ],
    },
]

SCORING_POINTS = [
    ("SP001", "Correct board scope, target matters, and portfolio risk booleans.", 1),
    ("SP002", "Correct ranked remediation priorities across the three matters.", 3),
    (
        "SP003",
        "Correct Alderline issue-to-action matrix, including personal messages, privilege gaps, board portal, and miscoding.",
        3,
    ),
    (
        "SP004",
        "Correct Bay issue-to-action matrix, including pre-hold policy gap, post-hold Teams purge, archive, vendor audit, and hold scope.",
        3,
    ),
    (
        "SP005",
        "Correct Lynxion source-loss and collection matrix for laptop, shared-folder deletion, and personal Outlook.",
        3,
    ),
    (
        "SP006",
        "Correct Lynxion privilege and QC matrix for waiver, overdesignation, clawback, and failed attachments.",
        3,
    ),
    ("SP007", "Correct cross-cutting failure groups and associated action enums.", 2),
    ("SP008", "Correct matter-level deadline and notice-risk booleans, issue sets, and action sets.", 2),
    ("SP009", "Contains exactly the expected material issue set without noisy comparator issues.", 1),
]


def load_prediction(path_text: str) -> tuple[dict[str, Any] | None, list[str]]:
    if not path_text:
        return None, ["prediction path was not provided"]
    try:
        data = json.loads(Path(path_text).read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, [f"could not load prediction JSON: {exc}"]
    if not isinstance(data, dict):
        return None, ["prediction root must be a JSON object"]
    return data, []


def sorted_list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        return []
    return sorted(value)


def normalize_row(row: Any, list_keys: set[str]) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    normalized = dict(row)
    for key in list_keys:
        normalized[key] = sorted_list(row.get(key))
    return normalized


def select(row: dict[str, Any], expected: dict[str, Any], list_keys: set[str]) -> dict[str, Any]:
    selected = {}
    for key in expected:
        value = row.get(key)
        if key in list_keys:
            value = sorted_list(value)
        selected[key] = value
    return selected


def normalize_scope(scope: Any) -> dict[str, Any]:
    return normalize_row(scope, {"matter_ids"})


def normalize_priority(row: Any) -> dict[str, Any]:
    return normalize_row(row, {"secondary_actions"})


def normalize_priorities(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    return sorted((normalize_priority(row) for row in rows), key=lambda row: row.get("rank", 999))


def matrix_map(prediction: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = prediction.get("matter_action_matrix", [])
    if not isinstance(rows, list):
        return {}
    mapped = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("issue_id"), str):
            mapped[row["issue_id"]] = normalize_row(row, {"category_ids", "secondary_actions"})
    return mapped


def matrix_rows(prediction: dict[str, Any]) -> list[dict[str, Any]]:
    rows = prediction.get("matter_action_matrix", [])
    if not isinstance(rows, list):
        return []
    return [
        normalize_row(row, {"category_ids", "secondary_actions"})
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("issue_id"), str)
    ]


def semantic_issue_id_map(prediction: dict[str, Any]) -> dict[str, str]:
    """Map hidden semantic issue IDs to the solver-assigned issue IDs."""
    rows = matrix_rows(prediction)
    mapping: dict[str, str] = {}
    used_row_indexes: set[int] = set()
    for semantic_id, expected in EXPECTED_MATRIX.items():
        for index, row in enumerate(rows):
            if index in used_row_indexes:
                continue
            if matrix_core_match(row, expected, semantic_id):
                mapping[semantic_id] = row["issue_id"]
                used_row_indexes.add(index)
                break
    return mapping


def translate_issue_ids(values: list[str], id_map: dict[str, str]) -> list[str]:
    if any(issue_id not in id_map for issue_id in values):
        return ["__missing_semantic_issue_mapping__"]
    return [id_map[issue_id] for issue_id in values]


def translate_expected_priority(row: dict[str, Any], id_map: dict[str, str]) -> dict[str, Any]:
    translated = dict(row)
    translated["issue_id"] = id_map.get(row["issue_id"], "__missing_semantic_issue_mapping__")
    translated["secondary_actions"] = sorted_list(translated.get("secondary_actions"))
    return translated


def translate_expected_failures(id_map: dict[str, str]) -> list[dict[str, Any]]:
    translated = []
    for row in EXPECTED_FAILURES:
        next_row = dict(row)
        next_row["matter_ids"] = sorted_list(next_row.get("matter_ids"))
        next_row["issue_ids"] = sorted(translate_issue_ids(row["issue_ids"], id_map))
        next_row["action_enums"] = sorted_list(next_row.get("action_enums"))
        translated.append(next_row)
    return sorted(translated, key=lambda row: row.get("failure_code", ""))


def translate_expected_deadlines(id_map: dict[str, str]) -> list[dict[str, Any]]:
    translated = []
    for row in EXPECTED_DEADLINES:
        next_row = dict(row)
        next_row["deadline_issue_ids"] = sorted(translate_issue_ids(row["deadline_issue_ids"], id_map))
        next_row["notice_issue_ids"] = sorted(translate_issue_ids(row["notice_issue_ids"], id_map))
        next_row["required_actions"] = sorted_list(next_row.get("required_actions"))
        translated.append(next_row)
    return sorted(translated, key=lambda row: row.get("matter_id", ""))


def matrix_group_match(prediction: dict[str, Any], issue_ids: list[str], id_map: dict[str, str]) -> bool:
    return all(issue_id in id_map for issue_id in issue_ids)


def matrix_core_match(actual: dict[str, Any], expected: dict[str, Any], issue_id: str) -> bool:
    core_keys = {
        "matter_id",
        "category_ids",
        "issue_type",
        "timing_class",
        "affected_count",
        "recovered_count",
        "unrecovered_count",
        "unlogged_privilege_count",
        "primary_action",
    }
    for key in core_keys:
        actual_value = sorted_list(actual.get(key)) if key == "category_ids" else actual.get(key)
        expected_value = sorted_list(expected.get(key)) if key == "category_ids" else expected.get(key)
        if key == "issue_type" and {actual_value, expected_value} <= {"personal_channel_gap", "uncollected_source"}:
            continue
        if (
            key == "timing_class"
            and issue_id == "ALD_PERSONAL_MESSAGES"
            and actual_value == "uncollected_source"
            and expected_value == "post_hold_spoliation"
        ):
            continue
        if key == "primary_action" and issue_id in {
            "ALD_PERSONAL_MESSAGES",
            "BAY_VAULTSEVEN_ARCHIVE",
            "LYN_PRIVILEGE_WAIVER",
        }:
            continue
        if key == "unlogged_privilege_count" and issue_id in {
            "ALD_COUNSEL_OVERDESIGNATION",
            "LYN_PRIVILEGE_OVERDESIGNATION",
        }:
            continue
        if key == "affected_count" and issue_id == "ALD_PRIVILEGE_LOG_GAP":
            continue
        if actual_value != expected_value:
            return False
    return True


def normalize_failures(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    normalized = [normalize_row(row, {"matter_ids", "issue_ids", "action_enums"}) for row in rows]
    return sorted(normalized, key=lambda row: row.get("failure_code", ""))


def normalize_deadlines(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    normalized = [normalize_row(row, {"deadline_issue_ids", "notice_issue_ids", "required_actions"}) for row in rows]
    return sorted(normalized, key=lambda row: row.get("matter_id", ""))


def linked_issue_ids(prediction: dict[str, Any]) -> set[str]:
    linked: set[str] = set()
    for row in prediction.get("ranked_priorities", []):
        if isinstance(row, dict) and isinstance(row.get("issue_id"), str):
            linked.add(row["issue_id"])
    for row in prediction.get("cross_cutting_failures", []):
        if isinstance(row, dict) and isinstance(row.get("issue_ids"), list):
            linked.update(issue_id for issue_id in row["issue_ids"] if isinstance(issue_id, str))
    for row in prediction.get("deadline_risks", []):
        if not isinstance(row, dict):
            continue
        for key in ("deadline_issue_ids", "notice_issue_ids"):
            if isinstance(row.get(key), list):
                linked.update(issue_id for issue_id in row[key] if isinstance(issue_id, str))
    return linked


def exact_issue_set(prediction: dict[str, Any], id_map: dict[str, str]) -> bool:
    rows = matrix_rows(prediction)
    matrix_ids = [row["issue_id"] for row in rows]
    matrix_id_set = set(matrix_ids)
    return (
        len(rows) == len(EXPECTED_MATRIX)
        and len(matrix_id_set) == len(EXPECTED_MATRIX)
        and set(id_map) == set(EXPECTED_MATRIX)
        and linked_issue_ids(prediction) <= matrix_id_set
    )


def score_prediction(prediction: dict[str, Any] | None, load_errors: list[str]) -> dict[str, Any]:
    if prediction is None:
        prediction = {}

    scope = normalize_scope(prediction.get("board_scope"))
    id_map = semantic_issue_id_map(prediction)
    expected_priorities = [translate_expected_priority(row, id_map) for row in EXPECTED_PRIORITIES]
    checks = {
        "SP001": prediction.get("task_id") == EXPECTED_SCOPE["task_id"]
        and select(scope, EXPECTED_SCOPE["board_scope"], {"matter_ids"}) == EXPECTED_SCOPE["board_scope"],
        "SP002": normalize_priorities(prediction.get("ranked_priorities")) == expected_priorities,
        "SP003": matrix_group_match(
            prediction,
            [
                "ALD_BOARD_PORTAL",
                "ALD_COMPLAINT_MISCODING",
                "ALD_COUNSEL_OVERDESIGNATION",
                "ALD_PERSONAL_MESSAGES",
                "ALD_PRIVILEGE_LOG_GAP",
            ],
            id_map,
        ),
        "SP004": matrix_group_match(
            prediction,
            [
                "BAY_HOLD_SCOPE",
                "BAY_LAB_DATA_POLICY_GAP",
                "BAY_TEAMS_PURGE",
                "BAY_TIDEWATER_AUDIT",
                "BAY_VAULTSEVEN_ARCHIVE",
            ],
            id_map,
        ),
        "SP005": matrix_group_match(
            prediction,
            [
                "LYN_LAPTOP_WIPE",
                "LYN_PERSONAL_OUTLOOK",
                "LYN_SHARED_FOLDER_DELETION",
            ],
            id_map,
        ),
        "SP006": matrix_group_match(
            prediction,
            [
                "LYN_FAILED_ATTACHMENTS",
                "LYN_PRIVILEGE_MISCODING",
                "LYN_PRIVILEGE_OVERDESIGNATION",
                "LYN_PRIVILEGE_WAIVER",
            ],
            id_map,
        ),
        "SP007": normalize_failures(prediction.get("cross_cutting_failures")) == translate_expected_failures(id_map),
        "SP008": normalize_deadlines(prediction.get("deadline_risks")) == translate_expected_deadlines(id_map),
        "SP009": exact_issue_set(prediction, id_map),
    }

    total_weight = sum(weight for _, _, weight in SCORING_POINTS)
    earned_weight = 0
    points = []
    for point_id, goal, weight in SCORING_POINTS:
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
