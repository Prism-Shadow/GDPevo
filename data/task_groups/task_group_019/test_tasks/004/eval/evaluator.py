#!/usr/bin/env python3
"""Exact-match evaluator for task_group_019 test_004."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


APP_FIELDS = [
    "application_id",
    "current_determination",
    "current_reason_codes",
    "primary_bulletin_ids",
    "prior_rule_determination",
    "prior_rule_reason_codes",
    "rule_impact",
]

CHANGED_FIELDS = [
    "application_id",
    "current_determination",
    "prior_rule_determination",
    "changed_reason_codes",
    "bulletin_ids",
    "rule_types",
]

MANAGEMENT_FIELDS = ["application_id", "escalation_type", "reason_codes"]

EXPECTED_APP_IDS = [
    "CA-2026-0038",
    "CA-2026-0039",
    "CA-2026-0040",
    "CA-2026-0041",
    "CA-2026-0042",
    "CA-2026-0043",
    "CA-2026-0044",
    "CA-2026-0045",
    "CA-2026-0046",
    "CA-2026-0047",
    "CA-2026-0048",
    "CA-2026-0049",
    "CA-2026-0050",
]

POINTS = [
    {
        "id": "SP001",
        "weight": 1,
        "goal": "Target batch, impact date, and complete application list are correct and ordered.",
    },
    {
        "id": "SP002",
        "weight": 2,
        "goal": "Current determination map is exact for all 13 applications.",
    },
    {
        "id": "SP003",
        "weight": 3,
        "goal": "Changed-by-bulletin list exactly identifies the applications whose decisions flip under 2026 bulletins.",
    },
    {
        "id": "SP004",
        "weight": 2,
        "goal": "Bond impact cases separate new-rule shortfalls from the pre-existing cancelled-bond hold.",
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Insurance, field-note, and experience-verification holds are classified with correct rule impact.",
    },
    {
        "id": "SP006",
        "weight": 2,
        "goal": "Penalty, correspondence, financial-statement, and denial cases distinguish pre-existing defects from added rule reasons.",
    },
    {
        "id": "SP007",
        "weight": 3,
        "goal": "Counterfactual counts match the standard answer exactly.",
    },
    {
        "id": "SP008",
        "weight": 2,
        "goal": "Management escalation and unchanged clean approval set are exact.",
    },
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sorted_list(value: Any) -> Any:
    if isinstance(value, list):
        return sorted(value)
    return value


def canonical_app(row: dict[str, Any]) -> dict[str, Any]:
    result = {field: row.get(field) for field in APP_FIELDS}
    for key in ["current_reason_codes", "primary_bulletin_ids", "prior_rule_reason_codes"]:
        result[key] = sorted_list(result.get(key))
    return result


def canonical_changed(row: dict[str, Any]) -> dict[str, Any]:
    result = {field: row.get(field) for field in CHANGED_FIELDS}
    for key in ["changed_reason_codes", "bulletin_ids", "rule_types"]:
        result[key] = sorted_list(result.get(key))
    return result


def canonical_management(row: dict[str, Any]) -> dict[str, Any]:
    result = {field: row.get(field) for field in MANAGEMENT_FIELDS}
    result["reason_codes"] = sorted_list(result.get("reason_codes"))
    return result


def list_of_dicts(doc: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = doc.get(key)
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def app_ids(doc: dict[str, Any]) -> list[str]:
    return [str(row.get("application_id", "")) for row in list_of_dicts(doc, "application_decisions")]


def app_map(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in list_of_dicts(doc, "application_decisions"):
        app_id = row.get("application_id")
        if isinstance(app_id, str):
            result[app_id] = row
    return result


def changed_map(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in list_of_dicts(doc, "changed_by_bulletin"):
        app_id = row.get("application_id")
        if isinstance(app_id, str):
            result[app_id] = row
    return result


def selected_apps_equal(pred: dict[str, Any], ans: dict[str, Any], ids: list[str]) -> bool:
    pred_map = app_map(pred)
    ans_map = app_map(ans)
    for app_id in ids:
        if app_id not in pred_map or app_id not in ans_map:
            return False
        if canonical_app(pred_map[app_id]) != canonical_app(ans_map[app_id]):
            return False
    return True


def current_determinations(doc: dict[str, Any]) -> dict[str, Any]:
    return {app_id: row.get("current_determination") for app_id, row in app_map(doc).items()}


def changed_equal(pred: dict[str, Any], ans: dict[str, Any]) -> bool:
    pred_rows = {app_id: canonical_changed(row) for app_id, row in changed_map(pred).items()}
    ans_rows = {app_id: canonical_changed(row) for app_id, row in changed_map(ans).items()}
    return pred_rows == ans_rows


def management_equal(pred: dict[str, Any], ans: dict[str, Any]) -> bool:
    pred_rows = {
        row.get("application_id"): canonical_management(row)
        for row in list_of_dicts(pred, "management_escalations")
        if isinstance(row.get("application_id"), str)
    }
    ans_rows = {
        row.get("application_id"): canonical_management(row)
        for row in list_of_dicts(ans, "management_escalations")
        if isinstance(row.get("application_id"), str)
    }
    return pred_rows == ans_rows


def clean_approvals(doc: dict[str, Any]) -> list[str]:
    return sorted(
        app_id
        for app_id, row in app_map(doc).items()
        if row.get("current_determination") == "APPROVE"
        and sorted_list(row.get("current_reason_codes")) == ["NO_DEFICIENCY"]
        and row.get("rule_impact") == "NO_DEFICIENCY"
    )


def add_point(results: list[dict[str, Any]], point: dict[str, Any], passed: bool, message: str) -> None:
    weight = int(point["weight"])
    results.append(
        {
            "id": point["id"],
            "goal": point["goal"],
            "weight": weight,
            "passed": passed,
            "earned_weight": weight if passed else 0,
            "message": message,
        }
    )


def evaluate(pred: dict[str, Any], ans: dict[str, Any]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    add_point(
        results,
        POINTS[0],
        pred.get("batch_id") == "HS-2026-Q2B"
        and pred.get("impact_screen_date") == "2026-06-30"
        and app_ids(pred) == EXPECTED_APP_IDS,
        "batch, screen date, and application order match",
    )

    add_point(
        results,
        POINTS[1],
        current_determinations(pred) == current_determinations(ans),
        "current determinations match",
    )

    add_point(
        results,
        POINTS[2],
        changed_equal(pred, ans),
        "changed-by-bulletin rows match",
    )

    add_point(
        results,
        POINTS[3],
        selected_apps_equal(pred, ans, ["CA-2026-0038", "CA-2026-0044", "CA-2026-0048"]),
        "bond impact cases match",
    )

    add_point(
        results,
        POINTS[4],
        selected_apps_equal(pred, ans, ["CA-2026-0039", "CA-2026-0040", "CA-2026-0041", "CA-2026-0045"]),
        "insurance, field-note, and experience cases match",
    )

    add_point(
        results,
        POINTS[5],
        selected_apps_equal(
            pred, ans, ["CA-2026-0042", "CA-2026-0043", "CA-2026-0046", "CA-2026-0047", "CA-2026-0049"]
        ),
        "penalty, correspondence, financial-statement, and denial cases match",
    )

    add_point(
        results,
        POINTS[6],
        pred.get("counterfactual_counts") == ans.get("counterfactual_counts"),
        "counterfactual counts match",
    )

    add_point(
        results,
        POINTS[7],
        management_equal(pred, ans) and clean_approvals(pred) == clean_approvals(ans) == ["CA-2026-0050"],
        "management escalation and clean approval set match",
    )

    total_weight = sum(point["weight"] for point in results)
    earned_weight = sum(point["earned_weight"] for point in results)
    return {
        "score": earned_weight / total_weight if total_weight else 0,
        "earned_weight": earned_weight,
        "total_weight": total_weight,
        "points": results,
    }


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"score": 0, "error": "usage: evaluator.py <prediction.json> <answer.json>", "points": []}))
        return 2
    try:
        pred = load_json(Path(sys.argv[1]))
        ans = load_json(Path(sys.argv[2]))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"score": 0, "error": f"json_load_failed: {exc}", "points": []}, indent=2, sort_keys=True))
        return 1
    if not isinstance(pred, dict) or not isinstance(ans, dict):
        print(
            json.dumps(
                {"score": 0, "error": "prediction and answer must be JSON objects", "points": []},
                indent=2,
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(evaluate(pred, ans), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
