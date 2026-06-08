#!/usr/bin/env python3
"""Rule-based evaluator for train_005."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


TASK_ROOT = Path(__file__).resolve().parents[1]
STANDARD_ANSWER = TASK_ROOT / "output" / "answer.json"
PLATFORM_ORDER = {"AUV": 0, "ROV": 1, "Underwater Camera": 2}


POINTS = [
    ("SP001", "Correct ranked qualified robotics lead order from the five AquaFarm exhibitors.", 3),
    ("SP002", "Correct platform coverage for each ranked lead.", 2),
    ("SP003", "Correct CRM action enum per ranked lead.", 2),
    ("SP004", "Correct excluded non-manufacturer accounts.", 2),
    ("SP005", "Correct aggregate opportunity estimate.", 2),
    ("SP006", "Correct existing CRM overlap count.", 1),
]


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"Could not parse JSON: {exc}"
    if not isinstance(data, dict):
        return None, "Top-level JSON value must be an object."
    return data, None


def by_company_id(rows: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("company_id"), str):
            result[row["company_id"]] = row
    return result


def sorted_platforms(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    valid = [item for item in value if item in PLATFORM_ORDER]
    return sorted(valid, key=lambda item: PLATFORM_ORDER[item])


def ranked_ids(answer: dict[str, Any]) -> list[str]:
    rows = answer.get("ranked_leads")
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


def check_ranked_order(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    if pred.get("show_id") != exp.get("show_id"):
        return False
    expected_ids = ranked_ids(exp)
    predicted_ids = ranked_ids(pred)
    if predicted_ids != expected_ids:
        return False
    pred_rows = by_company_id(pred.get("ranked_leads"))
    exp_rows = by_company_id(exp.get("ranked_leads"))
    return all(pred_rows.get(cid, {}).get("rank") == exp_rows[cid].get("rank") for cid in expected_ids)


def check_platforms(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    pred_rows = by_company_id(pred.get("ranked_leads"))
    exp_rows = by_company_id(exp.get("ranked_leads"))
    for company_id, exp_row in exp_rows.items():
        if sorted_platforms(pred_rows.get(company_id, {}).get("platforms")) != sorted_platforms(
            exp_row.get("platforms")
        ):
            return False
    pred_counts = (
        pred.get("summary", {}).get("platform_coverage_counts") if isinstance(pred.get("summary"), dict) else None
    )
    exp_counts = exp.get("summary", {}).get("platform_coverage_counts")
    return pred_counts == exp_counts


def check_crm_actions(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    pred_rows = by_company_id(pred.get("ranked_leads"))
    exp_rows = by_company_id(exp.get("ranked_leads"))
    for company_id, exp_row in exp_rows.items():
        pred_row = pred_rows.get(company_id, {})
        if pred_row.get("crm_action") != exp_row.get("crm_action"):
            return False
        if pred_row.get("crm_account_id") != exp_row.get("crm_account_id"):
            return False
    return True


def check_exclusions(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    pred_rows = by_company_id(pred.get("excluded_exhibitors"))
    exp_rows = by_company_id(exp.get("excluded_exhibitors"))
    if set(pred_rows) != set(exp_rows):
        return False
    for company_id, exp_row in exp_rows.items():
        pred_row = pred_rows[company_id]
        for field in ("relationship_type", "exclusion_reason", "crm_action"):
            if pred_row.get(field) != exp_row.get(field):
                return False
    pred_summary = pred.get("summary", {}) if isinstance(pred.get("summary"), dict) else {}
    return pred_summary.get("excluded_count") == exp.get("summary", {}).get("excluded_count")


def check_opportunity(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    pred_summary = pred.get("summary", {}) if isinstance(pred.get("summary"), dict) else {}
    if pred_summary.get("total_estimated_opportunity_usd") != exp.get("summary", {}).get(
        "total_estimated_opportunity_usd"
    ):
        return False
    pred_rows = by_company_id(pred.get("ranked_leads"))
    exp_rows = by_company_id(exp.get("ranked_leads"))
    for company_id, exp_row in exp_rows.items():
        pred_row = pred_rows.get(company_id, {})
        if pred_row.get("priority_tier") != exp_row.get("priority_tier"):
            return False
        if pred_row.get("opportunity_estimate_usd") != exp_row.get("opportunity_estimate_usd"):
            return False
    return True


def check_crm_overlap(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    pred_summary = pred.get("summary", {}) if isinstance(pred.get("summary"), dict) else {}
    exp_summary = exp.get("summary", {})
    return (
        pred_summary.get("qualified_lead_count") == exp_summary.get("qualified_lead_count")
        and pred_summary.get("existing_crm_overlap_count") == exp_summary.get("existing_crm_overlap_count")
        and sorted(pred_summary.get("existing_crm_overlap_account_ids", []))
        == exp_summary.get("existing_crm_overlap_account_ids")
    )


CHECKS = {
    "SP001": check_ranked_order,
    "SP002": check_platforms,
    "SP003": check_crm_actions,
    "SP004": check_exclusions,
    "SP005": check_opportunity,
    "SP006": check_crm_overlap,
}


def evaluate(prediction_path: Path) -> dict[str, Any]:
    expected, expected_error = load_json(STANDARD_ANSWER)
    prediction, prediction_error = load_json(prediction_path)
    if expected_error:
        raise RuntimeError(expected_error)

    total_weight = sum(weight for _, _, weight in POINTS)
    results = []
    total_score = 0.0

    for point_id, goal, weight in POINTS:
        passed = False
        if prediction_error is None and prediction is not None and expected is not None:
            passed = bool(CHECKS[point_id](prediction, expected))
        score = weight / total_weight if passed else 0.0
        total_score += score
        results.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "pass": passed,
                "score": round(score, 6),
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
    result = evaluate(prediction_path)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
