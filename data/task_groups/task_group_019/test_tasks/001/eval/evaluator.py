#!/usr/bin/env python3
"""Evaluator for task_group_019 test_001."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


POINTS = [
    {
        "id": "SP001",
        "weight": 1,
        "goal": "Batch metadata and application coverage exactly include the 14 HS-2026-Q2A applications in required order.",
    },
    {
        "id": "SP002",
        "weight": 3,
        "goal": "Eligibility determination map is exact for all 14 applications.",
    },
    {
        "id": "SP003",
        "weight": 2,
        "goal": "Clean approval cases are correctly identified with no deficiency action.",
    },
    {
        "id": "SP004",
        "weight": 3,
        "goal": "Scoped bond and insurance hold results, bulletin IDs, and actions are exact.",
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Correspondence and field-note override holds are exact.",
    },
    {
        "id": "SP006",
        "weight": 3,
        "goal": "Unresolved-penalty, adverse-registration, and disqualifying-conduct results are exact.",
    },
    {
        "id": "SP007",
        "weight": 2,
        "goal": "Deficiency counts match the standard answer exactly.",
    },
    {
        "id": "SP008",
        "weight": 3,
        "goal": "Bulletin-impact summary matches the standard answer exactly.",
    },
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def app_list(doc: dict[str, Any]) -> list[dict[str, Any]]:
    value = doc.get("application_decisions")
    return value if isinstance(value, list) else []


def app_ids(doc: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for item in app_list(doc):
        if isinstance(item, dict):
            ids.append(str(item.get("application_id", "")))
    return ids


def app_map(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in app_list(doc):
        if isinstance(item, dict) and isinstance(item.get("application_id"), str):
            result[item["application_id"]] = item
    return result


def canonical_app(item: dict[str, Any]) -> dict[str, Any]:
    reason_codes = item.get("reason_codes")
    bulletin_ids = item.get("primary_bulletin_ids")
    return {
        "application_id": item.get("application_id"),
        "determination": item.get("determination"),
        "reason_codes": sorted(reason_codes) if isinstance(reason_codes, list) else reason_codes,
        "primary_bulletin_ids": sorted(bulletin_ids) if isinstance(bulletin_ids, list) else bulletin_ids,
        "next_action": item.get("next_action"),
    }


def selected_apps_equal(pred: dict[str, Any], ans: dict[str, Any], ids: list[str]) -> bool:
    pred_map = app_map(pred)
    ans_map = app_map(ans)
    for app_id in ids:
        if app_id not in pred_map or app_id not in ans_map:
            return False
        if canonical_app(pred_map[app_id]) != canonical_app(ans_map[app_id]):
            return False
    return True


def determination_map(doc: dict[str, Any]) -> dict[str, Any]:
    return {app_id: item.get("determination") for app_id, item in app_map(doc).items()}


def check_point(point_id: str, pred: dict[str, Any], ans: dict[str, Any]) -> tuple[bool, str]:
    if point_id == "SP001":
        passed = (
            pred.get("batch_id") == ans.get("batch_id")
            and pred.get("review_cutoff_date") == ans.get("review_cutoff_date")
            and app_ids(pred) == app_ids(ans)
            and len(app_ids(pred)) == len(set(app_ids(pred)))
        )
        return (
            passed,
            "metadata and application order match" if passed else "metadata, application IDs, or order differ",
        )

    if point_id == "SP002":
        passed = determination_map(pred) == determination_map(ans)
        return passed, "all determinations match" if passed else "one or more determinations differ"

    if point_id == "SP003":
        ids = ["CA-2026-0024", "CA-2026-0034", "CA-2026-0036"]
        approve_set = sorted(app_id for app_id, row in app_map(pred).items() if row.get("determination") == "APPROVE")
        passed = selected_apps_equal(pred, ans, ids) and approve_set == ids
        return passed, "clean approvals match" if passed else "clean approval set or fields differ"

    if point_id == "SP004":
        ids = ["CA-2026-0025", "CA-2026-0026", "CA-2026-0029", "CA-2026-0035"]
        passed = selected_apps_equal(pred, ans, ids)
        return passed, "bond and insurance cases match" if passed else "bond or insurance case fields differ"

    if point_id == "SP005":
        ids = ["CA-2026-0027", "CA-2026-0028"]
        passed = selected_apps_equal(pred, ans, ids)
        return (
            passed,
            "correspondence and field-note cases match" if passed else "correspondence or field-note fields differ",
        )

    if point_id == "SP006":
        ids = ["CA-2026-0028", "CA-2026-0030", "CA-2026-0031", "CA-2026-0032", "CA-2026-0037"]
        passed = selected_apps_equal(pred, ans, ids)
        return (
            passed,
            "penalty, adverse, and denial cases match" if passed else "penalty, adverse, or denial fields differ",
        )

    if point_id == "SP007":
        passed = pred.get("deficiency_counts") == ans.get("deficiency_counts")
        return passed, "deficiency counts match" if passed else "deficiency counts differ"

    if point_id == "SP008":
        passed = pred.get("bulletin_impacts") == ans.get("bulletin_impacts")
        return passed, "bulletin impacts match" if passed else "bulletin impacts differ"

    return False, "unknown scoring point"


def evaluate(pred: dict[str, Any], ans: dict[str, Any]) -> dict[str, Any]:
    total_weight = sum(point["weight"] for point in POINTS)
    earned = 0
    results = []
    for point in POINTS:
        passed, message = check_point(point["id"], pred, ans)
        point_weight = point["weight"]
        if passed:
            earned += point_weight
        results.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point_weight,
                "passed": passed,
                "earned_weight": point_weight if passed else 0,
                "message": message,
            }
        )
    return {
        "score": earned / total_weight,
        "earned_weight": earned,
        "total_weight": total_weight,
        "points": results,
    }


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"score": 0, "error": "usage: evaluator.py <prediction.json> <answer.json>", "points": []}))
        return 2
    pred_path = Path(sys.argv[1])
    ans_path = Path(sys.argv[2])
    try:
        pred = load_json(pred_path)
        ans = load_json(ans_path)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"score": 0, "error": f"json_load_failed: {exc}", "points": []}, indent=2, sort_keys=True))
        return 1
    if not isinstance(pred, dict):
        print(
            json.dumps(
                {"score": 0, "error": "prediction must be a JSON object", "points": []}, indent=2, sort_keys=True
            )
        )
        return 1
    result = evaluate(pred, ans)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
