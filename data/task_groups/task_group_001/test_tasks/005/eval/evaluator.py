#!/usr/bin/env python3
"""Rule-based evaluator for test_005."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


TASK_ROOT = Path(__file__).resolve().parents[1]
STANDARD_ANSWER = TASK_ROOT / "output" / "answer.json"
PLATFORM_ORDER = {"AUV": 0, "ROV": 1, "Underwater Camera": 2}


POINTS = [
    ("SP001", "Correct ranked BlueTech target-account order.", 3),
    ("SP002", "Correct platform coverage and product-fit enums.", 3),
    ("SP003", "Correct CRM action enum per target account.", 2),
    ("SP004", "Correct exclusion of reseller and sensor-only accounts.", 2),
    ("SP005", "Correct pipeline estimate and meeting counts.", 3),
    ("SP006", "Correct existing CRM overlap and update count.", 1),
]


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"Could not parse JSON: {exc}"
    if not isinstance(data, dict):
        return None, "Top-level JSON value must be an object."
    return data, None


def rows_by_company_id(rows: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("company_id"), str):
            result[row["company_id"].strip()] = row
    return result


def sorted_platforms(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    valid = [item for item in value if item in PLATFORM_ORDER]
    return sorted(valid, key=lambda item: PLATFORM_ORDER[item])


def ranked_ids(answer: dict[str, Any]) -> list[str]:
    rows = answer.get("ranked_target_accounts")
    if not isinstance(rows, list):
        return []
    sortable = []
    for row in rows:
        if isinstance(row, dict):
            sortable.append((row.get("rank"), row.get("company_id")))
    try:
        return [company_id for _, company_id in sorted(sortable) if isinstance(company_id, str)]
    except TypeError:
        return []


def summary(answer: dict[str, Any]) -> dict[str, Any]:
    value = answer.get("summary")
    return value if isinstance(value, dict) else {}


def check_ranked_order(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    if pred.get("show_id") != exp.get("show_id"):
        return False
    expected_ids = ranked_ids(exp)
    if ranked_ids(pred) != expected_ids:
        return False
    pred_rows = rows_by_company_id(pred.get("ranked_target_accounts"))
    exp_rows = rows_by_company_id(exp.get("ranked_target_accounts"))
    for company_id in expected_ids:
        pred_row = pred_rows.get(company_id, {})
        exp_row = exp_rows[company_id]
        for field in ("rank", "company_name", "booth", "country", "website", "requested_demo", "interest_score"):
            if pred_row.get(field) != exp_row.get(field):
                return False
    return summary(pred).get("target_account_count") == summary(exp).get("target_account_count")


def check_platforms_and_fit(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    pred_rows = rows_by_company_id(pred.get("ranked_target_accounts"))
    exp_rows = rows_by_company_id(exp.get("ranked_target_accounts"))
    for company_id, exp_row in exp_rows.items():
        pred_row = pred_rows.get(company_id, {})
        if sorted_platforms(pred_row.get("platforms")) != sorted_platforms(exp_row.get("platforms")):
            return False
        if pred_row.get("product_fit") != exp_row.get("product_fit"):
            return False
    pred_summary = summary(pred)
    exp_summary = summary(exp)
    return pred_summary.get("platform_coverage_counts") == exp_summary.get(
        "platform_coverage_counts"
    ) and pred_summary.get("product_fit_counts") == exp_summary.get("product_fit_counts")


def check_crm_actions(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    pred_rows = rows_by_company_id(pred.get("ranked_target_accounts"))
    exp_rows = rows_by_company_id(exp.get("ranked_target_accounts"))
    for company_id, exp_row in exp_rows.items():
        pred_row = pred_rows.get(company_id, {})
        if pred_row.get("crm_action") != exp_row.get("crm_action"):
            return False
        if pred_row.get("crm_account_id") != exp_row.get("crm_account_id"):
            return False
    return summary(pred).get("create_account_count") == summary(exp).get("create_account_count")


def check_exclusions(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    pred_rows = rows_by_company_id(pred.get("excluded_exhibitors"))
    exp_rows = rows_by_company_id(exp.get("excluded_exhibitors"))
    if set(pred_rows) != set(exp_rows):
        return False
    for company_id, exp_row in exp_rows.items():
        pred_row = pred_rows[company_id]
        for field in (
            "company_name",
            "relationship_type",
            "exclusion_reason",
            "requested_demo",
            "interest_score",
            "crm_action",
        ):
            if pred_row.get(field) != exp_row.get(field):
                return False
    return summary(pred).get("excluded_count") == summary(exp).get("excluded_count")


def check_pipeline_and_meetings(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    pred_summary = summary(pred)
    exp_summary = summary(exp)
    for field in (
        "meeting_interest_records_count",
        "qualified_meeting_count",
        "excluded_meeting_count",
        "total_estimated_pipeline_usd",
    ):
        if pred_summary.get(field) != exp_summary.get(field):
            return False
    pred_rows = rows_by_company_id(pred.get("ranked_target_accounts"))
    exp_rows = rows_by_company_id(exp.get("ranked_target_accounts"))
    for company_id, exp_row in exp_rows.items():
        pred_row = pred_rows.get(company_id, {})
        if pred_row.get("priority_tier") != exp_row.get("priority_tier"):
            return False
        if pred_row.get("pipeline_estimate_usd") != exp_row.get("pipeline_estimate_usd"):
            return False
    return True


def check_crm_overlap(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    pred_summary = summary(pred)
    exp_summary = summary(exp)
    return (
        pred_summary.get("existing_crm_overlap_count") == exp_summary.get("existing_crm_overlap_count")
        and sorted(pred_summary.get("existing_crm_overlap_account_ids", []))
        == exp_summary.get("existing_crm_overlap_account_ids")
        and pred_summary.get("update_existing_count") == exp_summary.get("update_existing_count")
    )


CHECKS = {
    "SP001": check_ranked_order,
    "SP002": check_platforms_and_fit,
    "SP003": check_crm_actions,
    "SP004": check_exclusions,
    "SP005": check_pipeline_and_meetings,
    "SP006": check_crm_overlap,
}


def evaluate(prediction_path: Path) -> dict[str, Any]:
    expected, expected_error = load_json(STANDARD_ANSWER)
    prediction, prediction_error = load_json(prediction_path)
    if expected_error:
        raise RuntimeError(expected_error)

    total_weight = sum(weight for _, _, weight in POINTS)
    total_score = 0.0
    results = []

    for point_id, goal, weight in POINTS:
        passed = False
        if prediction_error is None and prediction is not None and expected is not None:
            passed = bool(CHECKS[point_id](prediction, expected))
        point_score = weight / total_weight if passed else 0.0
        total_score += point_score
        results.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "pass": passed,
                "score": round(point_score, 6),
            }
        )

    payload: dict[str, Any] = {
        "total_score": round(total_score, 6),
        "points": results,
    }
    if prediction_error:
        payload["error"] = prediction_error
    return payload


def main() -> None:
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else STANDARD_ANSWER
    print(json.dumps(evaluate(prediction_path), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
