#!/usr/bin/env python3
"""Exact-match evaluator for task_group_018 train_002."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any


POINTS = [
    {
        "id": "SP001",
        "weight": 2,
        "goal": "Correct target citation set, ordering, and account references.",
        "fields": ["entries"],
    },
    {
        "id": "SP002",
        "weight": 2,
        "goal": "Correct plea, disposition, and order date for all three citations.",
        "fields": ["entries"],
    },
    {
        "id": "SP003",
        "weight": 3,
        "goal": "Correct assessed traffic fee components for each citation.",
        "fields": ["entries"],
    },
    {
        "id": "SP004",
        "weight": 3,
        "goal": "Correct citation assessed totals and batch assessed total.",
        "fields": ["entries", "batch_totals"],
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Correct excluded candidate fee or charge codes.",
        "fields": ["entries"],
    },
    {
        "id": "SP006",
        "weight": 2,
        "goal": "Correct payment plan status, monthly amounts, and first due dates.",
        "fields": ["entries"],
    },
    {
        "id": "SP007",
        "weight": 3,
        "goal": "Correct installment counts, final payment amounts, total payment counts, and final due dates.",
        "fields": ["entries"],
    },
    {
        "id": "SP008",
        "weight": 1,
        "goal": "Correct batch-level payment-plan aggregate fields.",
        "fields": ["batch_totals"],
    },
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def money_equal(actual: Any, expected: Any) -> bool:
    try:
        return math.isclose(round(float(actual), 2), round(float(expected), 2), abs_tol=0.0001)
    except (TypeError, ValueError):
        return False


def get_entries(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("citation_number"), str):
            result[entry["citation_number"]] = entry
    return result


def sorted_codes(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return sorted(value)


def components_normalized(value: Any) -> list[dict[str, Any]] | None:
    if not isinstance(value, list):
        return None
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            return None
        fee_code = item.get("fee_code")
        amount = item.get("amount")
        if not isinstance(fee_code, str) or not money_equal(amount, amount):
            return None
        normalized.append({"fee_code": fee_code, "amount": round(float(amount), 2)})
    return normalized


def exact_entry_order_and_accounts(pred: dict[str, Any], ans: dict[str, Any]) -> bool:
    pred_entries = pred.get("entries")
    ans_entries = ans.get("entries")
    if not isinstance(pred_entries, list) or not isinstance(ans_entries, list):
        return False
    pred_ids = [entry.get("citation_number") for entry in pred_entries if isinstance(entry, dict)]
    ans_ids = [entry.get("citation_number") for entry in ans_entries]
    if pred_ids != ans_ids:
        return False
    for pred_entry, ans_entry in zip(pred_entries, ans_entries):
        if not isinstance(pred_entry, dict):
            return False
        if pred_entry.get("account_reference") != ans_entry.get("account_reference"):
            return False
        if pred_entry.get("defendant_name") != ans_entry.get("defendant_name"):
            return False
    return True


def check_dispositions(pred: dict[str, Any], ans: dict[str, Any]) -> bool:
    pred_entries = get_entries(pred)
    for ans_entry in ans["entries"]:
        pred_entry = pred_entries.get(ans_entry["citation_number"])
        if not pred_entry:
            return False
        for key in ("plea", "disposition", "order_date"):
            if pred_entry.get(key) != ans_entry.get(key):
                return False
    return True


def check_components(pred: dict[str, Any], ans: dict[str, Any]) -> bool:
    pred_entries = get_entries(pred)
    for ans_entry in ans["entries"]:
        pred_entry = pred_entries.get(ans_entry["citation_number"])
        if not pred_entry:
            return False
        if components_normalized(pred_entry.get("assessed_components")) != components_normalized(
            ans_entry.get("assessed_components")
        ):
            return False
    return True


def check_totals(pred: dict[str, Any], ans: dict[str, Any]) -> bool:
    pred_entries = get_entries(pred)
    for ans_entry in ans["entries"]:
        pred_entry = pred_entries.get(ans_entry["citation_number"])
        if not pred_entry or not money_equal(pred_entry.get("assessed_total"), ans_entry.get("assessed_total")):
            return False
    return money_equal(
        pred.get("batch_totals", {}).get("assessed_total"),
        ans.get("batch_totals", {}).get("assessed_total"),
    )


def check_exclusions(pred: dict[str, Any], ans: dict[str, Any]) -> bool:
    pred_entries = get_entries(pred)
    for ans_entry in ans["entries"]:
        pred_entry = pred_entries.get(ans_entry["citation_number"])
        if not pred_entry:
            return False
        if sorted_codes(pred_entry.get("excluded_candidate_fee_codes")) != sorted_codes(
            ans_entry.get("excluded_candidate_fee_codes")
        ):
            return False
    return True


def check_plan_start(pred: dict[str, Any], ans: dict[str, Any]) -> bool:
    pred_entries = get_entries(pred)
    for ans_entry in ans["entries"]:
        pred_plan = pred_entries.get(ans_entry["citation_number"], {}).get("payment_plan")
        ans_plan = ans_entry["payment_plan"]
        if not isinstance(pred_plan, dict):
            return False
        if pred_plan.get("plan_status") != ans_plan.get("plan_status"):
            return False
        if not money_equal(pred_plan.get("monthly_amount"), ans_plan.get("monthly_amount")):
            return False
        if pred_plan.get("first_due_date") != ans_plan.get("first_due_date"):
            return False
    return True


def check_installments(pred: dict[str, Any], ans: dict[str, Any]) -> bool:
    pred_entries = get_entries(pred)
    for ans_entry in ans["entries"]:
        pred_plan = pred_entries.get(ans_entry["citation_number"], {}).get("payment_plan")
        ans_plan = ans_entry["payment_plan"]
        if not isinstance(pred_plan, dict):
            return False
        for key in ("full_payment_count", "total_payment_count", "final_due_date"):
            if pred_plan.get(key) != ans_plan.get(key):
                return False
        if not money_equal(pred_plan.get("final_payment_amount"), ans_plan.get("final_payment_amount")):
            return False
    return True


def check_batch_plan_aggregates(pred: dict[str, Any], ans: dict[str, Any]) -> bool:
    pred_totals = pred.get("batch_totals")
    ans_totals = ans.get("batch_totals")
    if not isinstance(pred_totals, dict):
        return False
    if pred_totals.get("total_full_payments") != ans_totals.get("total_full_payments"):
        return False
    if not money_equal(pred_totals.get("total_final_payment_amount"), ans_totals.get("total_final_payment_amount")):
        return False
    if pred_totals.get("all_plans_entered_after_disposition") is not ans_totals.get(
        "all_plans_entered_after_disposition"
    ):
        return False
    return True


CHECKS = {
    "SP001": exact_entry_order_and_accounts,
    "SP002": check_dispositions,
    "SP003": check_components,
    "SP004": check_totals,
    "SP005": check_exclusions,
    "SP006": check_plan_start,
    "SP007": check_installments,
    "SP008": check_batch_plan_aggregates,
}


def evaluate(prediction_path: Path) -> dict[str, Any]:
    answer_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"
    max_score = sum(point["weight"] for point in POINTS)
    try:
        prediction = load_json(prediction_path)
    except Exception as exc:
        return {
            "score": 0,
            "max_score": max_score,
            "normalized_score": 0.0,
            "error": f"could not parse prediction JSON: {exc}",
            "points": [
                {
                    "id": point["id"],
                    "goal": point["goal"],
                    "weight": point["weight"],
                    "matched": False,
                    "score": 0,
                }
                for point in POINTS
            ],
        }
    answer = load_json(answer_path)
    if not isinstance(prediction, dict):
        prediction = {}

    point_results = []
    score = 0
    for point in POINTS:
        matched = CHECKS[point["id"]](prediction, answer)
        point_score = point["weight"] if matched else 0
        score += point_score
        point_results.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "matched": matched,
                "score": point_score,
            }
        )
    return {
        "score": score,
        "max_score": max_score,
        "normalized_score": round(score / max_score if max_score else 0.0, 6),
        "points": point_results,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: evaluator.py <prediction.json>"}, indent=2))
        return 2
    result = evaluate(Path(sys.argv[1]))
    print(json.dumps(result, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
