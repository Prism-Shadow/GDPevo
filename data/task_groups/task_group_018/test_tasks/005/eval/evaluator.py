#!/usr/bin/env python3
"""Exact-match evaluator for task_group_018 test_005."""

from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any


TASK_DIR = Path(__file__).resolve().parents[1]
ANSWER_PATH = TASK_DIR / "output" / "answer.json"

CURRENCY_FIELDS = {
    "live_balance_due",
    "correction_amount",
    "corrected_balance_due",
    "monthly_payment_amount",
    "final_payment_amount",
    "plan_exposure_amount",
    "default_exposure_amount",
    "total_live_balance_due",
    "total_correction_amount",
    "total_corrected_balance_due",
    "total_plan_exposure_amount",
    "total_default_exposure_amount",
}

SCORING_POINTS = [
    {
        "id": "SP001",
        "weight": 1,
        "goal": "Correct register identifiers, included/excluded case sets, and final register rank order.",
        "kind": "overview",
    },
    {
        "id": "SP002",
        "weight": 1,
        "goal": "Correct basic row priority buckets, row classifications, and action codes.",
        "kind": "row_fields",
        "fields": [
            "rank",
            "priority_bucket",
            "priority_reason_code",
            "inclusion_basis_code",
            "exception_type",
            "main_exception_code",
            "action_code",
        ],
    },
    {
        "id": "SP003",
        "weight": 2,
        "goal": "Correct candidate-level June actionability, scope reason, exclusion basis, and source family audit.",
        "kind": "candidate_fields",
        "fields": [
            "case_number",
            "scope_decision",
            "scope_reason_code",
            "june_actionability_code",
            "exclusion_basis_code",
            "scope_source_code",
        ],
    },
    {
        "id": "SP004",
        "weight": 3,
        "goal": "Correct source precedence, live/local/stale source audit, and neutral reconciliation family codes.",
        "kind": "row_fields",
        "fields": [
            "source_conflict_code",
            "source_precedence_code",
            "stale_live_resolution",
            "source_basis_tags",
            "reconciliation_code",
        ],
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Correct live ledger facts, amount basis, correction components, correction amounts, and corrected balances.",
        "kind": "row_fields",
        "fields": [
            "live_balance_due",
            "live_payment_status",
            "missed_payments",
            "amount_basis_code",
            "correction_component_codes",
            "correction_amount",
            "corrected_balance_due",
        ],
    },
    {
        "id": "SP006",
        "weight": 3,
        "goal": "Correct new-plan, existing-schedule, and return-to-court plan bases with installment math and exposure audit.",
        "kind": "specific_row_fields",
        "case_numbers": ["25-COL-00112", "24-LAN-01003", "24-JEF-01005"],
        "fields": [
            "payment_plan_action",
            "plan_basis_code",
            "plan_recalculation_code",
            "monthly_payment_amount",
            "full_payment_count",
            "final_payment_amount",
            "total_payment_count",
            "first_due_date",
            "final_due_date",
            "plan_exposure_amount",
            "default_exposure_amount",
            "exposure_basis_code",
            "exposure_audit_code",
        ],
    },
    {
        "id": "SP007",
        "weight": 2,
        "goal": "Correct no-plan credit closeout and collateral-only zero-exposure handling.",
        "kind": "specific_row_fields",
        "case_numbers": ["24-MID-01003", "25-BEN-01004", "24-MID-00077"],
        "fields": [
            "payment_plan_action",
            "plan_basis_code",
            "plan_recalculation_code",
            "monthly_payment_amount",
            "full_payment_count",
            "final_payment_amount",
            "total_payment_count",
            "first_due_date",
            "final_due_date",
            "plan_exposure_amount",
            "default_exposure_amount",
            "exposure_basis_code",
            "exposure_audit_code",
            "collateral_issue_code",
            "collateral_trigger_date",
        ],
    },
    {
        "id": "SP008",
        "weight": 3,
        "goal": "Correct aggregate counts, monetary totals, row-audit counts, and recomputed case-number sets.",
        "kind": "aggregate_fields",
        "fields": [
            "exception_count",
            "included_candidate_case_numbers",
            "excluded_candidate_case_numbers",
            "counties_represented",
            "scope_reason_counts",
            "actionability_counts",
            "exclusion_basis_counts",
            "source_precedence_counts",
            "reconciliation_code_counts",
            "source_basis_tag_counts",
            "statutory_correction_count",
            "payment_default_count",
            "collateral_omission_count",
            "stale_live_conflict_count",
            "fee_correction_count",
            "credit_closeout_count",
            "payment_plan_action_count",
            "return_to_court_count",
            "collateral_action_count",
            "total_live_balance_due",
            "total_correction_amount",
            "total_corrected_balance_due",
            "total_plan_exposure_amount",
            "total_default_exposure_amount",
            "statutory_correction_case_numbers",
            "fee_correction_case_numbers",
            "credit_closeout_case_numbers",
            "payment_default_case_numbers",
            "return_to_court_case_numbers",
            "existing_plan_retained_case_numbers",
            "default_exposure_case_numbers",
            "collateral_followup_case_numbers",
            "plan_basis_case_numbers",
            "plan_recalculation_case_numbers",
            "exposure_audit_case_numbers",
        ],
    },
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def money(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError, ValueError):
        return None


def normalize(field: str, value: Any) -> Any:
    if field in CURRENCY_FIELDS:
        return money(value)
    if isinstance(value, list):
        normalized_items = [normalize(field, item) for item in value]
        if all(isinstance(item, str) for item in normalized_items):
            return sorted(normalized_items)
        return normalized_items
    if isinstance(value, dict):
        return {key: normalize(key, value[key]) for key in sorted(value)}
    return value


def rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    value = payload.get("exceptions")
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def row_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for row in rows(payload):
        case_number = row.get("case_number")
        if isinstance(case_number, str):
            mapped[case_number] = row
    return mapped


def candidate_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    value = payload.get("candidate_audit")
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def candidate_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for row in candidate_rows(payload):
        notice_id = row.get("notice_id")
        if isinstance(notice_id, str):
            mapped[notice_id] = row
    return mapped


def aggregate(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("aggregate")
    return value if isinstance(value, dict) else {}


def compare_overview(prediction: dict[str, Any], answer: dict[str, Any]) -> tuple[bool, Any, Any]:
    expected_included = aggregate(answer).get("included_candidate_case_numbers", [])
    actual_included = aggregate(prediction).get("included_candidate_case_numbers")
    expected_exclusions = aggregate(answer).get("excluded_candidate_case_numbers", [])
    actual_exclusions = aggregate(prediction).get("excluded_candidate_case_numbers")

    expected = {
        "task_id": answer.get("task_id"),
        "register_month": answer.get("register_month"),
        "register_close_date": answer.get("register_close_date"),
        "currency": answer.get("currency"),
        "included_candidate_case_numbers": normalize("included_candidate_case_numbers", expected_included),
        "excluded_candidate_case_numbers": normalize("excluded_candidate_case_numbers", expected_exclusions),
        "case_numbers_in_rank_order": [row.get("case_number") for row in rows(answer)],
    }
    actual = {
        "task_id": prediction.get("task_id"),
        "register_month": prediction.get("register_month"),
        "register_close_date": prediction.get("register_close_date"),
        "currency": prediction.get("currency"),
        "included_candidate_case_numbers": normalize("included_candidate_case_numbers", actual_included),
        "excluded_candidate_case_numbers": normalize("excluded_candidate_case_numbers", actual_exclusions),
        "case_numbers_in_rank_order": [row.get("case_number") for row in rows(prediction)],
    }
    return actual == expected, expected, actual


def compare_candidate_fields(
    prediction: dict[str, Any],
    answer: dict[str, Any],
    fields: list[str],
) -> tuple[bool, Any, Any]:
    expected_candidates = candidate_map(answer)
    actual_candidates = candidate_map(prediction)
    expected = {
        notice_id: {field: normalize(field, expected_candidates.get(notice_id, {}).get(field)) for field in fields}
        for notice_id in sorted(expected_candidates)
    }
    actual = {
        notice_id: {field: normalize(field, actual_candidates.get(notice_id, {}).get(field)) for field in fields}
        for notice_id in sorted(expected_candidates)
    }
    return actual == expected, expected, actual


def compare_priority(prediction: dict[str, Any], answer: dict[str, Any]) -> tuple[bool, Any, Any]:
    expected_rows = rows(answer)
    actual_rows = rows(prediction)
    fields = ["rank", "priority_bucket", "priority_reason_code"]
    expected = {
        "case_numbers_in_rank_order": [row.get("case_number") for row in expected_rows],
        "row_priority": {
            row.get("case_number"): {field: normalize(field, row.get(field)) for field in fields}
            for row in expected_rows
            if isinstance(row.get("case_number"), str)
        },
    }
    actual_map = row_map(prediction)
    actual = {
        "case_numbers_in_rank_order": [row.get("case_number") for row in actual_rows],
        "row_priority": {
            row.get("case_number"): {
                field: normalize(field, actual_map.get(row.get("case_number"), {}).get(field)) for field in fields
            }
            for row in expected_rows
            if isinstance(row.get("case_number"), str)
        },
    }
    return actual == expected, expected, actual


def compare_row_fields(
    prediction: dict[str, Any],
    answer: dict[str, Any],
    fields: list[str],
    case_numbers: list[str] | None = None,
) -> tuple[bool, Any, Any]:
    pred_rows = row_map(prediction)
    ans_rows = row_map(answer)
    target_cases = case_numbers if case_numbers is not None else [row.get("case_number") for row in rows(answer)]

    expected: dict[str, dict[str, Any]] = {}
    actual: dict[str, dict[str, Any]] = {}
    for case_number in target_cases:
        if not isinstance(case_number, str):
            continue
        expected[case_number] = {}
        actual[case_number] = {}
        ans_row = ans_rows.get(case_number, {})
        pred_row = pred_rows.get(case_number, {})
        for field in fields:
            expected[case_number][field] = normalize(field, ans_row.get(field))
            actual[case_number][field] = normalize(field, pred_row.get(field))
    return actual == expected, expected, actual


def compare_aggregate_fields(
    prediction: dict[str, Any], answer: dict[str, Any], fields: list[str]
) -> tuple[bool, Any, Any]:
    pred_agg = aggregate(prediction)
    ans_agg = aggregate(answer)
    expected = {field: normalize(field, ans_agg.get(field)) for field in fields}
    actual = {field: normalize(field, pred_agg.get(field)) for field in fields}
    return actual == expected, expected, actual


def evaluate(prediction: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    points: list[dict[str, Any]] = []
    earned = 0
    max_score = sum(point["weight"] for point in SCORING_POINTS)

    for point in SCORING_POINTS:
        if point["kind"] == "overview":
            matched, expected, actual = compare_overview(prediction, answer)
        elif point["kind"] == "candidate_fields":
            matched, expected, actual = compare_candidate_fields(prediction, answer, point["fields"])
        elif point["kind"] == "priority":
            matched, expected, actual = compare_priority(prediction, answer)
        elif point["kind"] == "row_fields":
            matched, expected, actual = compare_row_fields(prediction, answer, point["fields"])
        elif point["kind"] == "specific_row_fields":
            matched, expected, actual = compare_row_fields(
                prediction,
                answer,
                point["fields"],
                point["case_numbers"],
            )
        elif point["kind"] == "aggregate_fields":
            matched, expected, actual = compare_aggregate_fields(prediction, answer, point["fields"])
        else:
            matched, expected, actual = False, "unknown scoring kind", None

        point_score = point["weight"] if matched else 0
        earned += point_score
        points.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "matched": matched,
                "score": point_score,
                "expected": expected,
                "actual": actual,
            }
        )

    return {
        "score": earned,
        "max_score": max_score,
        "normalized_score": round(earned / max_score if max_score else 0.0, 6),
        "points": points,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "error": "usage: evaluator.py <prediction.json>",
                    "score": 0,
                    "max_score": sum(point["weight"] for point in SCORING_POINTS),
                    "normalized_score": 0.0,
                },
                indent=2,
            )
        )
        return 2

    prediction_path = Path(sys.argv[1])
    if not prediction_path.is_absolute():
        prediction_path = Path.cwd() / prediction_path

    try:
        prediction = load_json(prediction_path)
        answer = load_json(ANSWER_PATH)
        if not isinstance(prediction, dict):
            prediction = {}
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {
                    "error": f"could not load prediction JSON: {exc}",
                    "score": 0,
                    "max_score": sum(point["weight"] for point in SCORING_POINTS),
                    "normalized_score": 0.0,
                    "points": [],
                },
                indent=2,
            )
        )
        return 1

    print(json.dumps(evaluate(prediction, answer), indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
