#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any


TASK_DIR = Path(__file__).resolve().parents[1]
ANSWER_PATH = TASK_DIR / "output" / "answer.json"
CENT = Decimal("0.01")


SCORING_POINTS = [
    ("SP1", "Correct target metadata and case set/order.", 2, "check_metadata_and_case_order"),
    ("SP2", "Correct charge-level pleas, dispositions, and verdicts.", 3, "check_charge_results"),
    ("SP3", "Correct final case status and sentence fields.", 3, "check_sentences"),
    ("SP4", "Correct defense attorney, defense type, and discrepancy code.", 2, "check_attorney_discrepancies"),
    ("SP5", "Correct fee component code/amount lists and principal totals.", 3, "check_fee_components"),
    ("SP6", "Correct live credits and corrected balance due per case.", 3, "check_balances"),
    ("SP7", "Correct docket action booleans per case.", 2, "check_docket_actions"),
    ("SP8", "Correct register totals.", 2, "check_register_totals"),
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def money(value: Any) -> str:
    try:
        return str(Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError):
        return "__invalid_money__"


def case_map(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = doc.get("case_audits", [])
    if not isinstance(rows, list):
        return {}
    result = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("case_number"), str):
            result[row["case_number"]] = row
    return result


def sorted_case_numbers(doc: dict[str, Any]) -> list[str]:
    rows = doc.get("case_audits", [])
    if not isinstance(rows, list):
        return []
    return [row.get("case_number") for row in rows if isinstance(row, dict)]


def norm_charges(row: dict[str, Any]) -> list[dict[str, Any]]:
    charges = row.get("charges", [])
    if not isinstance(charges, list):
        return []
    kept = []
    for item in charges:
        if not isinstance(item, dict):
            continue
        kept.append(
            {
                "charge_id": item.get("charge_id"),
                "plea": item.get("plea"),
                "disposition": item.get("disposition"),
                "verdict": item.get("verdict"),
            }
        )
    return sorted(kept, key=lambda x: str(x.get("charge_id")))


def norm_sentence(row: dict[str, Any]) -> dict[str, Any]:
    sentence = row.get("sentence", {})
    if not isinstance(sentence, dict):
        sentence = {}
    return {
        "final_case_status": row.get("final_case_status"),
        "jail_days": sentence.get("jail_days"),
        "suspended_days": sentence.get("suspended_days"),
        "probation_months": sentence.get("probation_months"),
        "community_service_hours": sentence.get("community_service_hours"),
        "treatment_ordered": sentence.get("treatment_ordered"),
        "restitution_ordered": money(sentence.get("restitution_ordered")),
    }


def norm_attorney(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "discrepancy_code": row.get("discrepancy_code"),
        "final_defense_attorney": row.get("final_defense_attorney"),
        "final_defense_type": row.get("final_defense_type"),
    }


def norm_fee_components(row: dict[str, Any]) -> dict[str, Any]:
    financials = row.get("financials", {})
    if not isinstance(financials, dict):
        financials = {}
    components = financials.get("fee_components", [])
    if not isinstance(components, list):
        components = []
    kept = []
    for item in components:
        if not isinstance(item, dict):
            continue
        kept.append({"fee_code": item.get("fee_code"), "amount": money(item.get("amount"))})
    return {
        "fee_components": sorted(kept, key=lambda x: str(x.get("fee_code"))),
        "new_principal_total": money(financials.get("new_principal_total")),
    }


def norm_balances(row: dict[str, Any]) -> dict[str, Any]:
    financials = row.get("financials", {})
    if not isinstance(financials, dict):
        financials = {}
    return {
        "amount_paid_credit": money(financials.get("amount_paid_credit")),
        "corrected_balance_due": money(financials.get("corrected_balance_due")),
    }


def norm_actions(row: dict[str, Any]) -> dict[str, Any]:
    actions = row.get("docket_actions", {})
    if not isinstance(actions, dict):
        actions = {}
    return {
        "enter_plea": actions.get("enter_plea"),
        "enter_sentence": actions.get("enter_sentence"),
        "recall_warrant": actions.get("recall_warrant"),
        "enter_attorney_update": actions.get("enter_attorney_update"),
        "generate_financial_entry": actions.get("generate_financial_entry"),
        "needs_supervisor_review": actions.get("needs_supervisor_review"),
    }


def compare_by_case(expected: dict[str, Any], predicted: dict[str, Any], normalizer) -> bool:
    exp_cases = case_map(expected)
    pred_cases = case_map(predicted)
    if set(exp_cases) != set(pred_cases):
        return False
    for case_number, exp_row in exp_cases.items():
        if normalizer(exp_row) != normalizer(pred_cases[case_number]):
            return False
    return True


def check_metadata_and_case_order(expected: dict[str, Any], predicted: dict[str, Any]) -> bool:
    keys = ["task_id", "county", "court", "hearing_date"]
    if {key: expected.get(key) for key in keys} != {key: predicted.get(key) for key in keys}:
        return False
    return sorted_case_numbers(expected) == sorted_case_numbers(predicted)


def check_charge_results(expected: dict[str, Any], predicted: dict[str, Any]) -> bool:
    return compare_by_case(expected, predicted, norm_charges)


def check_sentences(expected: dict[str, Any], predicted: dict[str, Any]) -> bool:
    return compare_by_case(expected, predicted, norm_sentence)


def check_attorney_discrepancies(expected: dict[str, Any], predicted: dict[str, Any]) -> bool:
    return compare_by_case(expected, predicted, norm_attorney)


def check_fee_components(expected: dict[str, Any], predicted: dict[str, Any]) -> bool:
    return compare_by_case(expected, predicted, norm_fee_components)


def check_balances(expected: dict[str, Any], predicted: dict[str, Any]) -> bool:
    return compare_by_case(expected, predicted, norm_balances)


def check_docket_actions(expected: dict[str, Any], predicted: dict[str, Any]) -> bool:
    return compare_by_case(expected, predicted, norm_actions)


def norm_register(doc: dict[str, Any]) -> dict[str, Any]:
    totals = doc.get("register_totals", {})
    if not isinstance(totals, dict):
        totals = {}
    return {
        "cases_ready_for_entry": totals.get("cases_ready_for_entry"),
        "warrants_recalled": totals.get("warrants_recalled"),
        "financial_entries_to_replace": totals.get("financial_entries_to_replace"),
        "supervisor_review_count": totals.get("supervisor_review_count"),
        "aggregate_principal_total": money(totals.get("aggregate_principal_total")),
        "aggregate_balance_due": money(totals.get("aggregate_balance_due")),
    }


def check_register_totals(expected: dict[str, Any], predicted: dict[str, Any]) -> bool:
    return norm_register(expected) == norm_register(predicted)


def evaluate(prediction_path: Path) -> dict[str, Any]:
    expected = load_json(ANSWER_PATH)
    predicted = load_json(prediction_path)
    results = []
    score = 0
    max_score = sum(point[2] for point in SCORING_POINTS)
    for point_id, goal, weight, function_name in SCORING_POINTS:
        matched = globals()[function_name](expected, predicted)
        earned = weight if matched else 0
        score += earned
        results.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "matched": matched,
                "earned": earned,
            }
        )
    return {
        "score": score,
        "max_score": max_score,
        "normalized_score": score / max_score if max_score else 0.0,
        "scoring_points": results,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: evaluator.py <prediction_json>"}, indent=2))
        return 2
    prediction_path = Path(sys.argv[1]).expanduser()
    if not prediction_path.exists():
        print(json.dumps({"error": f"prediction file not found: {prediction_path}"}, indent=2))
        return 2
    try:
        result = evaluate(prediction_path)
    except json.JSONDecodeError as exc:
        result = {
            "score": 0,
            "max_score": sum(point[2] for point in SCORING_POINTS),
            "normalized_score": 0.0,
            "error": f"invalid JSON: {exc}",
            "scoring_points": [
                {
                    "id": point_id,
                    "goal": goal,
                    "weight": weight,
                    "matched": False,
                    "earned": 0,
                }
                for point_id, goal, weight, _ in SCORING_POINTS
            ],
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
