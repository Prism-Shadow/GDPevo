#!/usr/bin/env python3
"""Exact-match evaluator for task_group_017 test_003."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_TOP_LEVEL = {
    "matter_id": "M-LYN-322",
    "custodian_id": "C-MR-118",
    "overall_status": "needs_escalation",
    "notice_recommended": True,
}

EXPECTED_ISSUES: dict[str, dict[str, Any]] = {
    "laptop_wipe": {
        "present": True,
        "issue_type": "device_wipe",
        "severity": "critical",
        "timing_class": "post_hold_spoliation",
        "category_ids": ["L-02"],
        "affected_count": 1,
        "recovered_count": 0,
        "unrecovered_count": 1,
        "primary_action": "forensic_recovery",
        "secondary_actions": ["custodian_declaration", "regulator_notice"],
        "notice_recommended": True,
    },
    "shared_drive_deletion": {
        "present": True,
        "issue_type": "source_deletion",
        "severity": "critical",
        "timing_class": "post_hold_spoliation",
        "category_ids": ["L-03"],
        "affected_count": 52,
        "recovered_count": 41,
        "unrecovered_count": 11,
        "primary_action": "regulator_notice",
        "secondary_actions": ["forensic_recovery"],
        "notice_recommended": True,
    },
    "personal_email_gap": {
        "present": True,
        "issue_type": "uncollected_source",
        "severity": "high",
        "timing_class": "uncollected_source",
        "category_ids": ["L-04"],
        "affected_count": 1,
        "recovered_count": 0,
        "unrecovered_count": 1,
        "primary_action": "supplemental_collection",
        "secondary_actions": ["hold_refresh"],
        "notice_recommended": False,
    },
    "privilege_waiver": {
        "present": True,
        "issue_type": "third_party_forward",
        "severity": "high",
        "timing_class": "privilege_waiver",
        "category_ids": ["L-05"],
        "affected_count": 4,
        "recovered_count": 0,
        "unrecovered_count": 0,
        "primary_action": "waiver_assessment",
        "secondary_actions": ["privilege_log_correction", "privilege_review"],
        "notice_recommended": False,
    },
    "privilege_overdesignation": {
        "present": True,
        "issue_type": "privilege_protocol_defect",
        "severity": "medium",
        "timing_class": "privilege_protocol_defect",
        "category_ids": ["L-06"],
        "affected_count": 18,
        "recovered_count": 0,
        "unrecovered_count": 0,
        "primary_action": "privilege_review",
        "secondary_actions": ["privilege_log_correction", "produce_business_only"],
        "notice_recommended": False,
    },
    "privilege_miscoding": {
        "present": True,
        "issue_type": "review_coding_error",
        "severity": "high",
        "timing_class": "coding_error",
        "category_ids": ["L-06"],
        "affected_count": 39,
        "recovered_count": 0,
        "unrecovered_count": 39,
        "primary_action": "clawback_check",
        "secondary_actions": ["privilege_review"],
        "notice_recommended": False,
    },
    "attachment_failure": {
        "present": True,
        "issue_type": "processing_failure",
        "severity": "medium",
        "timing_class": "processing_exception",
        "category_ids": ["L-06"],
        "affected_count": 31,
        "recovered_count": 0,
        "unrecovered_count": 31,
        "primary_action": "reprocess_qc",
        "secondary_actions": ["forensic_recovery", "supplemental_collection"],
        "notice_recommended": False,
    },
}

EXPECTED_PRIVILEGE_ACTIONS = {
    "waiver_forward": {
        "record_count": 4,
        "category_ids": ["L-05"],
        "action": "waiver_assessment",
        "waiver_risk": True,
        "recipient_role": "outside_consultant",
    },
    "overdesignation_review": {
        "record_count": 18,
        "category_ids": ["L-06"],
        "action": "privilege_review",
        "overdesignation_flag": True,
        "privilege_status": "business_only",
    },
    "miscoding_clawback": {
        "record_count": 39,
        "category_ids": ["L-06"],
        "action": "clawback_check",
        "first_pass_coding": "non_privileged",
        "production_status": "produced",
        "clawback_required": True,
    },
}

EXPECTED_ATTACHMENT_FAILURES = {
    "total_failed": 31,
    "password_protected": 17,
    "corrupt": 14,
    "category_ids": ["L-06"],
    "primary_action": "reprocess_qc",
}

EXPECTED_RANKED_ESCALATIONS = [
    {
        "rank": 1,
        "issue_id": "shared_drive_deletion",
        "escalation_target": "regulator_notice_review",
        "primary_action": "regulator_notice",
    },
    {
        "rank": 2,
        "issue_id": "laptop_wipe",
        "escalation_target": "forensic_vendor",
        "primary_action": "forensic_recovery",
    },
    {
        "rank": 3,
        "issue_id": "personal_email_gap",
        "escalation_target": "client_legal",
        "primary_action": "supplemental_collection",
    },
    {
        "rank": 4,
        "issue_id": "privilege_miscoding",
        "escalation_target": "privilege_team",
        "primary_action": "clawback_check",
    },
    {
        "rank": 5,
        "issue_id": "privilege_waiver",
        "escalation_target": "privilege_team",
        "primary_action": "waiver_assessment",
    },
    {
        "rank": 6,
        "issue_id": "attachment_failure",
        "escalation_target": "review_vendor",
        "primary_action": "reprocess_qc",
    },
    {
        "rank": 7,
        "issue_id": "privilege_overdesignation",
        "escalation_target": "privilege_team",
        "primary_action": "privilege_review",
    },
]

SCORING_POINTS = [
    ("SP001", "Correct target custodian, matter, overall escalation status, and notice recommendation.", 1),
    ("SP002", "Identifies the post-hold laptop wipe with category, counts, severity, and recovery action.", 2),
    (
        "SP003",
        "Identifies shared-folder deletion with 52 deleted, 41 recovered, 11 unrecovered, and top notice action.",
        3,
    ),
    ("SP004", "Identifies uncollected personal Outlook source and supplemental collection action.", 2),
    ("SP005", "Identifies four privileged emails forwarded to outside consultant as waiver risk.", 2),
    ("SP006", "Identifies 18 business-only over-designations and privilege-log correction action.", 1),
    (
        "SP007",
        "Identifies 39 privileged investigation emails first-pass coded non-privileged with clawback action.",
        3,
    ),
    ("SP008", "Identifies 31 failed attachments split into 17 password-protected and 14 corrupt.", 2),
    ("SP009", "Ranks escalations and primary actions in the required order.", 3),
]


def sorted_list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        return []
    return sorted(value)


def normalize_issue(issue: Any) -> dict[str, Any]:
    if not isinstance(issue, dict):
        return {}
    normalized = dict(issue)
    normalized["category_ids"] = sorted_list(issue.get("category_ids"))
    normalized["secondary_actions"] = sorted_list(issue.get("secondary_actions"))
    return normalized


def issue_map(prediction: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = prediction.get("issue_findings", [])
    if not isinstance(rows, list):
        return {}
    mapped = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("issue_id"), str):
            mapped[row["issue_id"]] = normalize_issue(row)
    return mapped


def select_fields(row: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    selected = {}
    for key in expected:
        value = row.get(key)
        if key in {"category_ids", "secondary_actions"}:
            value = sorted_list(value)
        selected[key] = value
    return selected


def match_issue(prediction: dict[str, Any], issue_id: str) -> bool:
    rows = issue_map(prediction)
    actual = rows.get(issue_id, {})
    expected = EXPECTED_ISSUES[issue_id]
    return select_fields(actual, expected) == expected


def normalize_action_block(block: Any) -> dict[str, Any]:
    if not isinstance(block, dict):
        return {}
    normalized = dict(block)
    normalized["category_ids"] = sorted_list(block.get("category_ids"))
    return normalized


def match_privilege_action(prediction: dict[str, Any], key: str) -> bool:
    actions = prediction.get("privilege_actions", {})
    if not isinstance(actions, dict):
        return False
    actual = normalize_action_block(actions.get(key))
    expected = EXPECTED_PRIVILEGE_ACTIONS[key]
    return select_fields(actual, expected) == expected


def match_attachment_failures(prediction: dict[str, Any]) -> bool:
    actual = normalize_action_block(prediction.get("attachment_failures"))
    expected = EXPECTED_ATTACHMENT_FAILURES
    return select_fields(actual, expected) == expected


def normalize_ranked(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized = []
    for row in value:
        if not isinstance(row, dict):
            continue
        normalized.append(
            {
                "rank": row.get("rank"),
                "issue_id": row.get("issue_id"),
                "escalation_target": row.get("escalation_target"),
                "primary_action": row.get("primary_action"),
            }
        )

    def rank_key(row: dict[str, Any]) -> tuple[bool, int, str]:
        rank = row["rank"]
        if isinstance(rank, int):
            return (False, rank, "")
        return (True, 0, str(rank))

    return sorted(normalized, key=rank_key)


def match_ranked_escalations(prediction: dict[str, Any]) -> bool:
    return normalize_ranked(prediction.get("ranked_escalations")) == EXPECTED_RANKED_ESCALATIONS


def evaluate(prediction: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "SP001": all(prediction.get(k) == v for k, v in EXPECTED_TOP_LEVEL.items()),
        "SP002": match_issue(prediction, "laptop_wipe"),
        "SP003": match_issue(prediction, "shared_drive_deletion"),
        "SP004": match_issue(prediction, "personal_email_gap"),
        "SP005": match_issue(prediction, "privilege_waiver") and match_privilege_action(prediction, "waiver_forward"),
        "SP006": match_issue(prediction, "privilege_overdesignation")
        and match_privilege_action(prediction, "overdesignation_review"),
        "SP007": match_issue(prediction, "privilege_miscoding")
        and match_privilege_action(prediction, "miscoding_clawback"),
        "SP008": match_issue(prediction, "attachment_failure") and match_attachment_failures(prediction),
        "SP009": match_ranked_escalations(prediction),
    }
    total_weight = sum(weight for _, _, weight in SCORING_POINTS)
    earned_weight = sum(weight for point_id, _, weight in SCORING_POINTS if checks[point_id])
    details = [
        {
            "id": point_id,
            "goal": goal,
            "weight": weight,
            "matched": bool(checks[point_id]),
            "score_contribution": (weight / total_weight) if checks[point_id] else 0.0,
        }
        for point_id, goal, weight in SCORING_POINTS
    ]
    return {
        "score": earned_weight / total_weight,
        "earned_weight": earned_weight,
        "total_weight": total_weight,
        "details": details,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"score": 0.0, "error": "missing prediction path"}, sort_keys=True))
        return

    path = Path(sys.argv[1])
    try:
        prediction = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"score": 0.0, "error": f"could not read prediction JSON: {exc}"}, sort_keys=True))
        return

    if not isinstance(prediction, dict):
        print(json.dumps({"score": 0.0, "error": "prediction must be a JSON object"}, sort_keys=True))
        return

    print(json.dumps(evaluate(prediction), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
