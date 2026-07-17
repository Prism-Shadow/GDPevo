#!/usr/bin/env python3
"""Exact-match evaluator for task_group_017 train_004."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable


EXPECTED = {
    "task_id": "train_004",
    "matter_id": "M-RDL-304",
    "affected_categories": ["R-01", "R-10", "R-11"],
    "category_status": {
        "R-01": {
            "status": "blocked_zero_production",
            "severity": "high",
            "issue_types": ["coding_error"],
            "produced_count": 0,
            "withheld_privileged_count": 88,
            "privilege_logged_count": 71,
            "required_action_types": ["supplemental_production"],
        },
        "R-10": {
            "status": "privilege_log_incomplete",
            "severity": "high",
            "issue_types": ["privilege_log_gap", "privilege_miscoding"],
            "produced_count": 1440,
            "withheld_privileged_count": 2910,
            "privilege_logged_count": 2102,
            "required_action_types": ["clawback_review", "privilege_log_supplement", "privilege_review"],
        },
        "R-11": {
            "status": "overdesignation_review",
            "severity": "high",
            "issue_types": ["overdesignation_risk"],
            "produced_count": 0,
            "withheld_privileged_count": 612,
            "privilege_logged_count": 0,
            "required_action_types": ["privilege_review"],
        },
    },
    "privilege_metrics": {
        "log_gap_category_id": "R-10",
        "withheld_privileged_count": 2910,
        "privilege_logged_count": 2102,
        "unlogged_privileged_count": 808,
        "counsel_category_id": "R-11",
        "counsel_withheld_count": 612,
        "counsel_produced_count": 0,
        "counsel_all_withheld": True,
        "counsel_overdesignation_risk": True,
        "privileged_coded_nonprivileged_count": 31,
        "clawback_required": True,
    },
    "miscoding_findings": {
        "MF-01": {
            "issue_type": "miscoded_complaint_documents",
            "category_id": "R-01",
            "document_count": 2,
            "document_ids": ["DOC-RDL-COMP-001", "DOC-RDL-COMP-002"],
            "review_coding": "non-responsive",
            "corrected_status": "responsive",
            "production_status": "not produced",
            "action_type": "supplemental_production",
        },
        "MF-02": {
            "issue_type": "privileged_coded_nonprivileged",
            "category_id": "R-10",
            "document_count": 31,
            "document_ids": ["DOC-RDL-PRIV-001", "DOC-RDL-PRIV-031"],
            "review_coding": "responsive",
            "corrected_status": "privileged",
            "production_status": "produced",
            "action_type": "clawback_review",
        },
    },
    "actions": {
        "ACT-01": {
            "action_type": "supplemental_production",
            "category_ids": ["R-01"],
            "priority": "high",
            "required": True,
        },
        "ACT-02": {
            "action_type": "privilege_log_supplement",
            "category_ids": ["R-10"],
            "priority": "high",
            "required": True,
        },
        "ACT-03": {
            "action_type": "clawback_review",
            "category_ids": ["R-10"],
            "priority": "high",
            "required": True,
        },
        "ACT-04": {
            "action_type": "privilege_review",
            "category_ids": ["R-10", "R-11"],
            "priority": "high",
            "required": True,
        },
    },
}


def load_prediction(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
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
    return index_by_id(pred.get("category_status"), "category_id")


def finding_rows(pred: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return index_by_id(pred.get("miscoding_findings"), "finding_id")


def action_rows(pred: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return index_by_id(pred.get("actions"), "action_id")


def match_list(value: Any, expected: list[str]) -> bool:
    return sorted_strings(value) == sorted(expected)


def match_fields(row: dict[str, Any], expected: dict[str, Any]) -> bool:
    for key, expected_value in expected.items():
        actual_value = row.get(key)
        if isinstance(expected_value, list):
            if not match_list(actual_value, expected_value):
                return False
        elif actual_value != expected_value:
            return False
    return True


def check_identity_and_affected(pred: dict[str, Any]) -> bool:
    return (
        pred.get("task_id") == EXPECTED["task_id"]
        and pred.get("matter_id") == EXPECTED["matter_id"]
        and match_list(pred.get("affected_categories"), EXPECTED["affected_categories"])
    )


def check_category_core(pred: dict[str, Any]) -> bool:
    rows = category_rows(pred)
    if sorted(rows) != sorted(EXPECTED["category_status"]):
        return False
    for category_id, expected in EXPECTED["category_status"].items():
        core = {
            "status": expected["status"],
            "severity": expected["severity"],
            "issue_types": expected["issue_types"],
        }
        if not match_fields(rows.get(category_id, {}), core):
            return False
    return True


def check_r01_miscoding(pred: dict[str, Any]) -> bool:
    row = category_rows(pred).get("R-01", {})
    finding = finding_rows(pred).get("MF-01", {})
    return match_fields(
        row,
        {
            "status": "blocked_zero_production",
            "produced_count": 0,
            "required_action_types": ["supplemental_production"],
        },
    ) and match_fields(finding, EXPECTED["miscoding_findings"]["MF-01"])


def check_r10_log_gap(pred: dict[str, Any]) -> bool:
    metrics = pred.get("privilege_metrics")
    if not isinstance(metrics, dict):
        return False
    row = category_rows(pred).get("R-10", {})
    expected_keys = {
        "log_gap_category_id": "R-10",
        "withheld_privileged_count": 2910,
        "privilege_logged_count": 2102,
        "unlogged_privileged_count": 808,
    }
    return match_fields(metrics, expected_keys) and match_fields(
        row,
        {
            "status": "privilege_log_incomplete",
            "withheld_privileged_count": 2910,
            "privilege_logged_count": 2102,
        },
    )


def check_r11_overdesignation(pred: dict[str, Any]) -> bool:
    metrics = pred.get("privilege_metrics")
    if not isinstance(metrics, dict):
        return False
    row = category_rows(pred).get("R-11", {})
    expected_keys = {
        "counsel_category_id": "R-11",
        "counsel_withheld_count": 612,
        "counsel_produced_count": 0,
        "counsel_all_withheld": True,
        "counsel_overdesignation_risk": True,
    }
    return match_fields(metrics, expected_keys) and match_fields(
        row,
        {
            "status": "overdesignation_review",
            "issue_types": ["overdesignation_risk"],
            "produced_count": 0,
            "withheld_privileged_count": 612,
        },
    )


def check_clawback_miscoding(pred: dict[str, Any]) -> bool:
    metrics = pred.get("privilege_metrics")
    if not isinstance(metrics, dict):
        return False
    finding = finding_rows(pred).get("MF-02", {})
    return match_fields(
        metrics,
        {
            "privileged_coded_nonprivileged_count": 31,
            "clawback_required": True,
        },
    ) and match_fields(finding, EXPECTED["miscoding_findings"]["MF-02"])


def check_category_action_types(pred: dict[str, Any]) -> bool:
    rows = category_rows(pred)
    for category_id, expected in EXPECTED["category_status"].items():
        if not match_list(rows.get(category_id, {}).get("required_action_types"), expected["required_action_types"]):
            return False
    return True


def check_actions(pred: dict[str, Any]) -> bool:
    rows = action_rows(pred)
    if sorted(rows) != sorted(EXPECTED["actions"]):
        return False
    for action_id, expected in EXPECTED["actions"].items():
        if not match_fields(rows.get(action_id, {}), expected):
            return False
    return True


POINTS: list[tuple[str, int, Callable[[dict[str, Any]], bool]]] = [
    ("identity_and_affected_categories", 2, check_identity_and_affected),
    ("category_status_core", 2, check_category_core),
    ("r01_zero_production_and_complaint_miscoding", 3, check_r01_miscoding),
    ("r10_unlogged_privilege_gap", 3, check_r10_log_gap),
    ("r11_all_withheld_overdesignation_risk", 3, check_r11_overdesignation),
    ("privileged_coded_nonprivileged_clawback", 2, check_clawback_miscoding),
    ("category_required_action_types", 2, check_category_action_types),
    ("remediation_action_records", 2, check_actions),
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
