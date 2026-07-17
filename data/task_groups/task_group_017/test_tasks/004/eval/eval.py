#!/usr/bin/env python3
"""Exact-match evaluator for task_group_017 test_004."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable


EXPECTED = {
    "task_id": "test_004",
    "matter_id": "M-OVL-730",
    "overall_status": "mixed_not_ready",
    "ready_category_ids": ["O-01", "O-02", "O-08", "O-09", "O-10"],
    "blocked_category_ids": ["O-03", "O-04", "O-05", "O-06", "O-07"],
    "category_readiness": {
        "O-01": {
            "readiness_status": "ready",
            "blocker_code": "none",
            "severity": "none",
            "produced_count": 820,
            "withheld_privileged_count": 28,
            "privilege_logged_count": 28,
            "unlogged_privileged_count": 0,
            "affected_count": 0,
            "unrecovered_count": 0,
            "source_event_ids": ["PL-0033"],
            "primary_action": "no_action",
            "notice_required": False,
        },
        "O-02": {
            "readiness_status": "ready",
            "blocker_code": "none",
            "severity": "none",
            "produced_count": 116,
            "withheld_privileged_count": 5,
            "privilege_logged_count": 5,
            "unlogged_privileged_count": 0,
            "affected_count": 0,
            "unrecovered_count": 0,
            "source_event_ids": ["PL-0034"],
            "primary_action": "no_action",
            "notice_required": False,
        },
        "O-03": {
            "readiness_status": "blocked",
            "blocker_code": "uncollected_phone_chat",
            "severity": "high",
            "produced_count": 0,
            "withheld_privileged_count": 0,
            "privilege_logged_count": 0,
            "unlogged_privileged_count": 0,
            "affected_count": 2,
            "unrecovered_count": 2,
            "source_event_ids": ["CE-0027", "PL-0035"],
            "primary_action": "supplemental_collection",
            "notice_required": False,
        },
        "O-04": {
            "readiness_status": "blocked",
            "blocker_code": "missing_archive",
            "severity": "medium",
            "produced_count": 0,
            "withheld_privileged_count": 0,
            "privilege_logged_count": 0,
            "unlogged_privileged_count": 0,
            "affected_count": 1,
            "unrecovered_count": 1,
            "source_event_ids": ["CE-0028", "PL-0036"],
            "primary_action": "archive_retrieval",
            "notice_required": False,
        },
        "O-05": {
            "readiness_status": "blocked",
            "blocker_code": "unlogged_privilege",
            "severity": "high",
            "produced_count": 450,
            "withheld_privileged_count": 520,
            "privilege_logged_count": 310,
            "unlogged_privileged_count": 210,
            "affected_count": 210,
            "unrecovered_count": 0,
            "source_event_ids": ["PL-0037", "PV-0013"],
            "primary_action": "privilege_log_supplement",
            "notice_required": True,
        },
        "O-06": {
            "readiness_status": "blocked",
            "blocker_code": "failed_attachments",
            "severity": "medium",
            "produced_count": 390,
            "withheld_privileged_count": 18,
            "privilege_logged_count": 18,
            "unlogged_privileged_count": 0,
            "affected_count": 16,
            "unrecovered_count": 16,
            "source_event_ids": ["PL-0038", "QC-0012"],
            "primary_action": "reprocess_qc",
            "notice_required": False,
        },
        "O-07": {
            "readiness_status": "blocked",
            "blocker_code": "post_hold_deletion",
            "severity": "critical",
            "produced_count": 278,
            "withheld_privileged_count": 9,
            "privilege_logged_count": 9,
            "unlogged_privileged_count": 0,
            "affected_count": 19,
            "unrecovered_count": 12,
            "source_event_ids": ["CE-0029", "DE-0010", "PL-0039", "QC-0013"],
            "primary_action": "regulator_notice",
            "notice_required": True,
        },
        "O-08": {
            "readiness_status": "ready",
            "blocker_code": "none",
            "severity": "none",
            "produced_count": 690,
            "withheld_privileged_count": 12,
            "privilege_logged_count": 12,
            "unlogged_privileged_count": 0,
            "affected_count": 0,
            "unrecovered_count": 0,
            "source_event_ids": ["PL-0040"],
            "primary_action": "no_action",
            "notice_required": False,
        },
        "O-09": {
            "readiness_status": "ready",
            "blocker_code": "none",
            "severity": "none",
            "produced_count": 344,
            "withheld_privileged_count": 8,
            "privilege_logged_count": 8,
            "unlogged_privileged_count": 0,
            "affected_count": 0,
            "unrecovered_count": 0,
            "source_event_ids": ["PL-0041"],
            "primary_action": "no_action",
            "notice_required": False,
        },
        "O-10": {
            "readiness_status": "ready",
            "blocker_code": "none",
            "severity": "none",
            "produced_count": 73,
            "withheld_privileged_count": 21,
            "privilege_logged_count": 21,
            "unlogged_privileged_count": 0,
            "affected_count": 0,
            "unrecovered_count": 0,
            "source_event_ids": ["PL-0042"],
            "primary_action": "no_action",
            "notice_required": False,
        },
    },
    "blockers": {
        "BLK-O03-PHONE-CHAT": {
            "category_id": "O-03",
            "blocker_code": "uncollected_phone_chat",
            "severity": "high",
            "timing_class": "uncollected_source",
            "affected_count": 2,
            "recovered_count": 0,
            "unrecovered_count": 2,
            "unlogged_privileged_count": 0,
            "source_event_ids": ["CE-0027", "PL-0035"],
            "document_ids": [],
            "primary_action": "supplemental_collection",
            "notice_required": False,
        },
        "BLK-O04-MISSING-ARCHIVE": {
            "category_id": "O-04",
            "blocker_code": "missing_archive",
            "severity": "medium",
            "timing_class": "missing_archive",
            "affected_count": 1,
            "recovered_count": 0,
            "unrecovered_count": 1,
            "unlogged_privileged_count": 0,
            "source_event_ids": ["CE-0028", "PL-0036"],
            "document_ids": [],
            "primary_action": "archive_retrieval",
            "notice_required": False,
        },
        "BLK-O05-UNLOGGED-PRIVILEGE": {
            "category_id": "O-05",
            "blocker_code": "unlogged_privilege",
            "severity": "high",
            "timing_class": "privilege_protocol_defect",
            "affected_count": 210,
            "recovered_count": 0,
            "unrecovered_count": 0,
            "unlogged_privileged_count": 210,
            "source_event_ids": ["PL-0037", "PV-0013"],
            "document_ids": [],
            "primary_action": "privilege_log_supplement",
            "notice_required": True,
        },
        "BLK-O06-FAILED-ATTACHMENTS": {
            "category_id": "O-06",
            "blocker_code": "failed_attachments",
            "severity": "medium",
            "timing_class": "processing_exception",
            "affected_count": 16,
            "recovered_count": 0,
            "unrecovered_count": 16,
            "unlogged_privileged_count": 0,
            "source_event_ids": ["PL-0038", "QC-0012"],
            "document_ids": ["DOC-OVL-ATT-001", "DOC-OVL-ATT-016"],
            "primary_action": "reprocess_qc",
            "notice_required": False,
        },
        "BLK-O07-POST-HOLD-DELETION": {
            "category_id": "O-07",
            "blocker_code": "post_hold_deletion",
            "severity": "critical",
            "timing_class": "post_hold_spoliation",
            "affected_count": 19,
            "recovered_count": 7,
            "unrecovered_count": 12,
            "unlogged_privileged_count": 0,
            "source_event_ids": ["CE-0029", "DE-0010", "PL-0039", "QC-0013"],
            "document_ids": ["DOC-OVL-DEL-001", "DOC-OVL-DEL-019"],
            "primary_action": "regulator_notice",
            "notice_required": True,
        },
    },
    "top_blockers": [
        {
            "rank": 1,
            "blocker_id": "BLK-O07-POST-HOLD-DELETION",
            "category_id": "O-07",
            "blocker_code": "post_hold_deletion",
            "primary_action": "regulator_notice",
            "notice_required": True,
        },
        {
            "rank": 2,
            "blocker_id": "BLK-O03-PHONE-CHAT",
            "category_id": "O-03",
            "blocker_code": "uncollected_phone_chat",
            "primary_action": "supplemental_collection",
            "notice_required": False,
        },
        {
            "rank": 3,
            "blocker_id": "BLK-O05-UNLOGGED-PRIVILEGE",
            "category_id": "O-05",
            "blocker_code": "unlogged_privilege",
            "primary_action": "privilege_log_supplement",
            "notice_required": True,
        },
        {
            "rank": 4,
            "blocker_id": "BLK-O06-FAILED-ATTACHMENTS",
            "category_id": "O-06",
            "blocker_code": "failed_attachments",
            "primary_action": "reprocess_qc",
            "notice_required": False,
        },
        {
            "rank": 5,
            "blocker_id": "BLK-O04-MISSING-ARCHIVE",
            "category_id": "O-04",
            "blocker_code": "missing_archive",
            "primary_action": "archive_retrieval",
            "notice_required": False,
        },
    ],
    "notice_required": {
        "overall_notice_required": True,
        "notice_category_ids": ["O-05", "O-07"],
        "notice_blocker_ids": ["BLK-O05-UNLOGGED-PRIVILEGE", "BLK-O07-POST-HOLD-DELETION"],
        "spoliation_notice_required": True,
        "privilege_protocol_notice_required": True,
        "collection_gap_notice_required": False,
        "archive_notice_required": False,
        "processing_notice_required": False,
    },
    "actions": [
        {
            "rank": 1,
            "action_id": "ACT-OVL-REGULATOR-NOTICE",
            "action": "regulator_notice",
            "category_ids": ["O-07"],
            "blocker_ids": ["BLK-O07-POST-HOLD-DELETION"],
            "owner_queue": "legal",
            "required_before_production": True,
            "notice_required": True,
        },
        {
            "rank": 2,
            "action_id": "ACT-OVL-PHONE-CHAT-COLLECTION",
            "action": "supplemental_collection",
            "category_ids": ["O-03"],
            "blocker_ids": ["BLK-O03-PHONE-CHAT"],
            "owner_queue": "client_it",
            "required_before_production": True,
            "notice_required": False,
        },
        {
            "rank": 3,
            "action_id": "ACT-OVL-PRIVILEGE-LOG",
            "action": "privilege_log_supplement",
            "category_ids": ["O-05"],
            "blocker_ids": ["BLK-O05-UNLOGGED-PRIVILEGE"],
            "owner_queue": "privilege_team",
            "required_before_production": True,
            "notice_required": True,
        },
        {
            "rank": 4,
            "action_id": "ACT-OVL-ATTACHMENT-REPROCESS",
            "action": "reprocess_qc",
            "category_ids": ["O-06"],
            "blocker_ids": ["BLK-O06-FAILED-ATTACHMENTS"],
            "owner_queue": "review_vendor",
            "required_before_production": True,
            "notice_required": False,
        },
        {
            "rank": 5,
            "action_id": "ACT-OVL-ARCHIVE-RETRIEVAL",
            "action": "archive_retrieval",
            "category_ids": ["O-04"],
            "blocker_ids": ["BLK-O04-MISSING-ARCHIVE"],
            "owner_queue": "archive_team",
            "required_before_production": True,
            "notice_required": False,
        },
    ],
}


def load_prediction(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"Could not read prediction JSON: {exc}"
    if not isinstance(data, dict):
        return None, "Prediction must be a JSON object."
    return data, None


def sorted_strings(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    if not all(isinstance(item, str) for item in value):
        return None
    return sorted(value)


def index_by_id(rows: Any, key: str) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get(key), str):
            indexed[row[key]] = row
    return indexed


def category_rows(pred: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return index_by_id(pred.get("category_readiness"), "category_id")


def blocker_rows(pred: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return index_by_id(pred.get("blockers"), "blocker_id")


def match_list(value: Any, expected: list[str]) -> bool:
    return sorted_strings(value) == sorted(expected)


def match_ranked_list(value: Any, expected: list[dict[str, Any]]) -> bool:
    if not isinstance(value, list) or len(value) != len(expected):
        return False
    actual = sorted(value, key=lambda row: row.get("rank") if isinstance(row, dict) else 999)
    return actual == expected


def match_fields(row: dict[str, Any], expected: dict[str, Any]) -> bool:
    for key, expected_value in expected.items():
        actual_value = row.get(key)
        if isinstance(expected_value, list):
            if not match_list(actual_value, expected_value):
                return False
        elif actual_value != expected_value:
            return False
    return True


def check_identity_and_sets(pred: dict[str, Any]) -> bool:
    return (
        pred.get("task_id") == EXPECTED["task_id"]
        and pred.get("matter_id") == EXPECTED["matter_id"]
        and pred.get("overall_status") == EXPECTED["overall_status"]
        and match_list(pred.get("ready_category_ids"), EXPECTED["ready_category_ids"])
        and match_list(pred.get("blocked_category_ids"), EXPECTED["blocked_category_ids"])
    )


def check_all_category_statuses(pred: dict[str, Any]) -> bool:
    rows = category_rows(pred)
    if sorted(rows) != sorted(EXPECTED["category_readiness"]):
        return False
    keys = [
        "readiness_status",
        "blocker_code",
        "severity",
        "primary_action",
        "notice_required",
    ]
    for category_id, expected in EXPECTED["category_readiness"].items():
        if not match_fields(rows.get(category_id, {}), {key: expected[key] for key in keys}):
            return False
    return True


def check_ready_counts(pred: dict[str, Any]) -> bool:
    rows = category_rows(pred)
    for category_id in EXPECTED["ready_category_ids"]:
        expected = EXPECTED["category_readiness"][category_id]
        keys = [
            "produced_count",
            "withheld_privileged_count",
            "privilege_logged_count",
            "unlogged_privileged_count",
            "affected_count",
            "unrecovered_count",
            "source_event_ids",
        ]
        if not match_fields(rows.get(category_id, {}), {key: expected[key] for key in keys}):
            return False
    return True


def check_blocker(pred: dict[str, Any], blocker_id: str) -> bool:
    blocker = blocker_rows(pred).get(blocker_id, {})
    expected_blocker = EXPECTED["blockers"][blocker_id]
    category = category_rows(pred).get(expected_blocker["category_id"], {})
    expected_category = EXPECTED["category_readiness"][expected_blocker["category_id"]]
    category_keys = [
        "produced_count",
        "withheld_privileged_count",
        "privilege_logged_count",
        "unlogged_privileged_count",
        "affected_count",
        "unrecovered_count",
        "source_event_ids",
        "primary_action",
        "notice_required",
    ]
    return match_fields(blocker, expected_blocker) and match_fields(
        category,
        {key: expected_category[key] for key in category_keys},
    )


def check_o03_phone_chat(pred: dict[str, Any]) -> bool:
    return check_blocker(pred, "BLK-O03-PHONE-CHAT")


def check_o04_missing_archive(pred: dict[str, Any]) -> bool:
    return check_blocker(pred, "BLK-O04-MISSING-ARCHIVE")


def check_o05_unlogged_privilege(pred: dict[str, Any]) -> bool:
    return check_blocker(pred, "BLK-O05-UNLOGGED-PRIVILEGE")


def check_o06_failed_attachments(pred: dict[str, Any]) -> bool:
    return check_blocker(pred, "BLK-O06-FAILED-ATTACHMENTS")


def check_o07_post_hold_deletion(pred: dict[str, Any]) -> bool:
    return check_blocker(pred, "BLK-O07-POST-HOLD-DELETION")


def check_top_blocker_ranking(pred: dict[str, Any]) -> bool:
    return match_ranked_list(pred.get("top_blockers"), EXPECTED["top_blockers"])


def normalize_actions(actions: Any) -> Any:
    if not isinstance(actions, list):
        return actions
    normalized = []
    for row in actions:
        if not isinstance(row, dict):
            normalized.append(row)
            continue
        normalized.append(
            {
                "rank": row.get("rank"),
                "action_id": row.get("action_id"),
                "action": row.get("action"),
                "category_ids": sorted(row.get("category_ids", [])),
                "blocker_ids": sorted(row.get("blocker_ids", [])),
                "owner_queue": row.get("owner_queue"),
                "required_before_production": row.get("required_before_production"),
                "notice_required": row.get("notice_required"),
            }
        )
    return sorted(normalized, key=lambda row: (row.get("rank", 999), row.get("action_id", "")))


def check_notice_and_actions(pred: dict[str, Any]) -> bool:
    notice = pred.get("notice_required")
    if not isinstance(notice, dict):
        return False
    expected_notice = EXPECTED["notice_required"]
    if not match_fields(notice, expected_notice):
        return False
    return normalize_actions(pred.get("actions")) == EXPECTED["actions"]


POINTS: list[tuple[str, int, Callable[[dict[str, Any]], bool]]] = [
    ("identity_ready_and_blocked_category_sets", 3, check_identity_and_sets),
    ("category_status_actions_and_notice_flags", 2, check_all_category_statuses),
    ("ready_category_counts_and_current_log_ids", 2, check_ready_counts),
    ("o03_uncollected_phone_chat_blocker", 2, check_o03_phone_chat),
    ("o04_missing_archive_blocker", 2, check_o04_missing_archive),
    ("o05_unlogged_privilege_blocker", 3, check_o05_unlogged_privilege),
    ("o06_failed_attachments_blocker", 2, check_o06_failed_attachments),
    ("o07_post_hold_deletion_blocker", 3, check_o07_post_hold_deletion),
    ("top_blocker_ranking", 3, check_top_blocker_ranking),
    ("notice_summary_and_action_records", 2, check_notice_and_actions),
]


def main() -> None:
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("answer.json")
    pred, load_error = load_prediction(prediction_path)
    total_weight = sum(weight for _, weight, _ in POINTS)
    results = []
    earned = 0

    if pred is None:
        for point_id, weight, _ in POINTS:
            results.append(
                {
                    "id": point_id,
                    "weight": weight,
                    "passed": False,
                    "score": 0.0,
                    "error": load_error,
                }
            )
    else:
        for point_id, weight, check in POINTS:
            try:
                passed = bool(check(pred))
            except Exception as exc:  # noqa: BLE001
                passed = False
                error = str(exc)
            else:
                error = None
            if passed:
                earned += weight
            item = {
                "id": point_id,
                "weight": weight,
                "passed": passed,
                "score": (weight / total_weight) if passed else 0.0,
            }
            if error:
                item["error"] = error
            results.append(item)

    score = earned / total_weight if total_weight else 0.0
    payload = {
        "score": score,
        "earned_weight": earned,
        "total_weight": total_weight,
        "points": results,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
