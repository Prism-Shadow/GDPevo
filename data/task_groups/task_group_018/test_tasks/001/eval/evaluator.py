#!/usr/bin/env python3
"""Exact-match evaluator for task_group_018 test_001."""

from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any


TASK_DIR = Path(__file__).resolve().parents[1]
ANSWER_PATH = TASK_DIR / "output" / "answer.json"

CURRENCY_FIELD_NAMES = {
    "assessed_total",
    "restitution_amount",
    "fee_component_total",
    "current_ledger_principal",
    "financial_delta",
    "ledger_principal_before",
    "ledger_principal_after",
    "ledger_delta",
    "total_fee_components",
    "total_assessed",
    "total_restitution",
    "total_ledger_principal_before",
    "total_ledger_principal_after",
    "total_financial_delta",
    "row_fee_component_total",
    "row_assessed_total",
    "row_restitution_total",
    "row_ledger_before_total",
    "row_ledger_after_total",
    "row_ledger_delta_total",
}

SORTED_LIST_FIELD_NAMES = {
    "approved_fee_codes",
    "noncontrolling_source_codes",
    "excluded_candidate_fee_codes",
    "added_scheduled_fee_codes",
    "rows_with_excluded_candidate_fee_codes",
    "rows_with_restitution_as_separate_principal",
    "rows_using_counsel_review_source",
    "rows_using_live_record_over_stale_export",
    "rows_using_hearing_packet_disposition_source",
    "rows_with_added_scheduled_fee_codes",
    "rows_with_restitution_principal",
    "rows_reissued_without_principal_delta",
    "rows_ready_for_new_assessment",
}

SCORING_POINTS = [
    {
        "id": "SP001",
        "weight": 1,
        "goal": "Correct metadata, six target cases, defendant names, and row order.",
        "kind": "metadata_and_order",
    },
    {
        "id": "SP002",
        "weight": 2,
        "goal": "Correct case posture, disposition dates, charge-result codes, and probation months.",
        "kind": "row_fields",
        "fields": [
            "register_disposition",
            "disposition_date",
            "charge_result_code",
            "probation_months",
        ],
    },
    {
        "id": "SP003",
        "weight": 3,
        "goal": "Correct defense verification convention: verified defense type and representation source.",
        "kind": "row_fields",
        "fields": [
            "defense_type",
            "source_precedence_audit.representation_source_code",
        ],
    },
    {
        "id": "SP004",
        "weight": 3,
        "goal": "Correct verified-defense source on carry-forward and prior-order rows.",
        "kind": "row_fields_for_cases",
        "case_numbers": [
            "23-COL-01002",
            "24-COL-01003",
            "25-COL-00112",
        ],
        "fields": [
            "defense_type",
            "source_precedence_audit.representation_source_code",
        ],
    },
    {
        "id": "SP005",
        "weight": 1,
        "goal": "Correct disposition source precedence for each register row.",
        "kind": "row_fields",
        "fields": [
            "source_precedence_audit.disposition_source_code",
        ],
    },
    {
        "id": "SP006",
        "weight": 1,
        "goal": "Correct scheduled-fee-only components and restitution-as-principal assessment.",
        "kind": "row_fields",
        "fields": [
            "approved_fee_codes",
            "fee_component_total",
            "fee_component_audit.excluded_candidate_fee_codes",
            "fee_component_audit.added_scheduled_fee_codes",
            "fee_component_audit.restitution_component_policy_code",
            "restitution_amount",
            "assessed_total",
        ],
    },
    {
        "id": "SP007",
        "weight": 1,
        "goal": "Correct live-ledger before/after principal, delta, and ledger action.",
        "kind": "row_fields",
        "fields": [
            "current_ledger_principal",
            "financial_delta",
            "ledger_reconciliation.ledger_principal_before",
            "ledger_reconciliation.ledger_principal_after",
            "ledger_reconciliation.ledger_delta",
            "ledger_reconciliation.ledger_action_code",
        ],
    },
    {
        "id": "SP008",
        "weight": 1,
        "goal": "Correct stable aggregate counts, restitution total, live-ledger before total, and new-assessment count.",
        "kind": "object_fields",
        "object_path": "aggregate_summary",
        "fields": [
            "case_count",
            "conviction_register_count",
            "deferred_entry_count",
            "review_only_or_prior_count",
            "warrant_recall_count",
            "total_restitution",
            "total_ledger_principal_before",
            "new_assessment_count",
        ],
    },
    {
        "id": "SP009",
        "weight": 1,
        "goal": "Correct aggregate recomputation audit for stable row-derived totals and row sets.",
        "kind": "object_fields",
        "object_path": "aggregate_recompute_audit",
        "fields": [
            "recomputed_case_count",
            "row_restitution_total",
            "row_ledger_before_total",
            "rows_with_excluded_candidate_fee_codes",
            "rows_with_restitution_as_separate_principal",
        ],
    },
    {
        "id": "SP010",
        "weight": 2,
        "goal": "Correct reduced source and financial summaries for train-anchored audit row sets.",
        "kind": "object_field_groups",
        "object_field_groups": [
            {
                "object_path": "source_precedence_summary",
                "fields": [
                    "counsel_review_source_count",
                    "rows_using_counsel_review_source",
                    "rows_using_live_record_over_stale_export",
                    "rows_using_hearing_packet_disposition_source",
                ],
            },
            {
                "object_path": "financial_reconciliation_summary",
                "fields": [
                    "rows_with_added_scheduled_fee_codes",
                    "rows_with_restitution_principal",
                    "rows_reissued_without_principal_delta",
                    "rows_ready_for_new_assessment",
                ],
            },
        ],
    },
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def currency(value: Any) -> str | None:
    try:
        return str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError, ValueError):
        return None


def get_path(obj: Any, path: str) -> Any:
    current = obj
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def normalized_value(path: str, value: Any) -> Any:
    field_name = path.split(".")[-1]
    if field_name in CURRENCY_FIELD_NAMES:
        return currency(value)
    if field_name in SORTED_LIST_FIELD_NAMES:
        if not isinstance(value, list):
            return None
        return sorted(str(item) for item in value)
    return value


def row_map(rows: Any) -> dict[str, dict[str, Any]] | None:
    if not isinstance(rows, list):
        return None
    mapped: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            return None
        case_number = row.get("case_number")
        if not isinstance(case_number, str) or case_number in mapped:
            return None
        mapped[case_number] = row
    return mapped


def compare_metadata_and_order(prediction: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, str]:
    for field in ["task_id", "county", "register_date", "currency"]:
        if prediction.get(field) != expected.get(field):
            return False, f"top-level field {field} mismatch"

    pred_rows = prediction.get("rows")
    exp_rows = expected.get("rows")
    if not isinstance(pred_rows, list):
        return False, "prediction.rows is not a list"
    if len(pred_rows) != len(exp_rows):
        return False, f"expected {len(exp_rows)} rows, got {len(pred_rows)}"

    for idx, (pred_row, exp_row) in enumerate(zip(pred_rows, exp_rows)):
        if not isinstance(pred_row, dict):
            return False, f"row {idx} is not an object"
        for field in ["case_number", "defendant_name"]:
            if pred_row.get(field) != exp_row.get(field):
                return False, f"row {idx} field {field} mismatch"
    return True, "matched"


def compare_row_fields(prediction: dict[str, Any], expected: dict[str, Any], fields: list[str]) -> tuple[bool, str]:
    pred_by_case = row_map(prediction.get("rows"))
    exp_by_case = row_map(expected.get("rows"))
    if pred_by_case is None:
        return False, "prediction.rows cannot be mapped by unique case_number"
    if exp_by_case is None:
        return False, "expected.rows cannot be mapped by unique case_number"
    if set(pred_by_case) != set(exp_by_case):
        missing = sorted(set(exp_by_case) - set(pred_by_case))
        extra = sorted(set(pred_by_case) - set(exp_by_case))
        return False, f"case set mismatch; missing={missing}; extra={extra}"
    for case_number in sorted(exp_by_case):
        pred_row = pred_by_case[case_number]
        exp_row = exp_by_case[case_number]
        for field in fields:
            pred_value = normalized_value(field, get_path(pred_row, field))
            exp_value = normalized_value(field, get_path(exp_row, field))
            if pred_value != exp_value:
                return False, f"{case_number} field {field} mismatch"
    return True, "matched"


def compare_row_fields_for_cases(
    prediction: dict[str, Any],
    expected: dict[str, Any],
    case_numbers: list[str],
    fields: list[str],
) -> tuple[bool, str]:
    pred_by_case = row_map(prediction.get("rows"))
    exp_by_case = row_map(expected.get("rows"))
    if pred_by_case is None:
        return False, "prediction.rows cannot be mapped by unique case_number"
    if exp_by_case is None:
        return False, "expected.rows cannot be mapped by unique case_number"
    for case_number in case_numbers:
        pred_row = pred_by_case.get(case_number)
        exp_row = exp_by_case.get(case_number)
        if pred_row is None or exp_row is None:
            return False, f"case {case_number} missing"
        for field in fields:
            pred_value = normalized_value(field, get_path(pred_row, field))
            exp_value = normalized_value(field, get_path(exp_row, field))
            if pred_value != exp_value:
                return False, f"{case_number} field {field} mismatch"
    return True, "matched"


def compare_object_fields(
    prediction: dict[str, Any],
    expected: dict[str, Any],
    object_path: str,
    fields: list[str],
) -> tuple[bool, str]:
    pred_obj = get_path(prediction, object_path)
    exp_obj = get_path(expected, object_path)
    if not isinstance(pred_obj, dict):
        return False, f"prediction.{object_path} is not an object"
    if not isinstance(exp_obj, dict):
        return False, f"expected.{object_path} is not an object"
    for field in fields:
        path = f"{object_path}.{field}"
        pred_value = normalized_value(path, pred_obj.get(field))
        exp_value = normalized_value(path, exp_obj.get(field))
        if pred_value != exp_value:
            return False, f"{object_path} field {field} mismatch"
    return True, "matched"


def compare_object_field_groups(
    prediction: dict[str, Any],
    expected: dict[str, Any],
    groups: list[dict[str, Any]],
) -> tuple[bool, str]:
    for group in groups:
        matched, details = compare_object_fields(
            prediction,
            expected,
            group["object_path"],
            group["fields"],
        )
        if not matched:
            return False, details
    return True, "matched"


def evaluate(prediction: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    point_results = []
    earned = 0
    max_score = sum(point["weight"] for point in SCORING_POINTS)

    for point in SCORING_POINTS:
        if point["kind"] == "metadata_and_order":
            matched, details = compare_metadata_and_order(prediction, expected)
        elif point["kind"] == "row_fields":
            matched, details = compare_row_fields(prediction, expected, point["fields"])
        elif point["kind"] == "row_fields_for_cases":
            matched, details = compare_row_fields_for_cases(
                prediction,
                expected,
                point["case_numbers"],
                point["fields"],
            )
        elif point["kind"] == "object_fields":
            matched, details = compare_object_fields(
                prediction,
                expected,
                point["object_path"],
                point["fields"],
            )
        elif point["kind"] == "object_field_groups":
            matched, details = compare_object_field_groups(
                prediction,
                expected,
                point["object_field_groups"],
            )
        else:
            matched, details = False, "unknown scoring point kind"

        point_earned = point["weight"] if matched else 0
        earned += point_earned
        point_results.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "matched": matched,
                "earned": point_earned,
                "details": details,
            }
        )

    return {
        "score": earned,
        "max_score": max_score,
        "normalized_score": earned / max_score if max_score else 0.0,
        "points": point_results,
    }


def error_result(message: str) -> dict[str, Any]:
    return {
        "score": 0,
        "max_score": sum(point["weight"] for point in SCORING_POINTS),
        "normalized_score": 0.0,
        "error": message,
        "points": [
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "matched": False,
                "earned": 0,
                "details": "not evaluated",
            }
            for point in SCORING_POINTS
        ],
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps(error_result("prediction file path is required as the first argument"), indent=2))
        return 2

    prediction_path = Path(sys.argv[1])
    expected = load_json(ANSWER_PATH)
    try:
        prediction = load_json(prediction_path)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(error_result(f"could not load prediction JSON: {exc}"), indent=2))
        return 1

    print(json.dumps(evaluate(prediction, expected), indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
