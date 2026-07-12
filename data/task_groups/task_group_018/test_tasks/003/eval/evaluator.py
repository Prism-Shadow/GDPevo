#!/usr/bin/env python3
"""Exact-match evaluator for task_group_018 test_003."""

from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any


TASK_DIR = Path(__file__).resolve().parents[1]
ANSWER_PATH = TASK_DIR / "output" / "answer.json"

POINTS = [
    {
        "id": "SP001",
        "weight": 1,
        "goal": "Correct packet scope, defendant ordering, names, conviction postures, order dates, and charge outcomes.",
    },
    {
        "id": "SP002",
        "weight": 2,
        "goal": "Correct packet-vs-live source precedence and stale collateral extract rejection.",
    },
    {
        "id": "SP003",
        "weight": 2,
        "goal": "Correct identity fields and official case-file placeholder audit.",
    },
    {
        "id": "SP004",
        "weight": 3,
        "goal": "Correct collateral orders and rejected license-start candidate sources.",
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Correct ledger-versus-schedule financial source and amount fields.",
    },
    {
        "id": "SP006",
        "weight": 2,
        "goal": "Correct assessed fees and unsupported fee or charge exclusions.",
    },
    {
        "id": "SP007",
        "weight": 3,
        "goal": "Correct payment-plan authority, original-principal math, and rejected monthly candidates.",
    },
    {
        "id": "SP008",
        "weight": 2,
        "goal": "Correct return-to-court routing and follow-up actions.",
    },
    {
        "id": "SP009",
        "weight": 2,
        "goal": "Correct packet-level aggregate recomputation from final rows.",
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


def sorted_strings(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    return sorted(str(item) for item in value)


def item_list(doc: dict[str, Any]) -> list[dict[str, Any]]:
    value = doc.get("defendants")
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def by_case(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in item_list(doc):
        case_number = item.get("case_number")
        if isinstance(case_number, str):
            result[case_number] = item
    return result


def case_order(doc: dict[str, Any]) -> list[Any]:
    return [item.get("case_number") for item in item_list(doc)]


def totals(doc: dict[str, Any]) -> dict[str, Any]:
    value = doc.get("packet_totals")
    return value if isinstance(value, dict) else {}


def block(item: dict[str, Any], key: str) -> dict[str, Any]:
    value = item.get(key)
    return value if isinstance(value, dict) else {}


def rowset(
    value: Any,
    keys: tuple[str, ...],
    sort_key: str,
    money_keys: tuple[str, ...] = (),
) -> list[dict[str, Any]] | None:
    if not isinstance(value, list):
        return None
    rows = []
    for row in value:
        if not isinstance(row, dict):
            return None
        out: dict[str, Any] = {}
        for key in keys:
            raw = row.get(key)
            out[key] = money(raw) if key in money_keys else raw
        rows.append(out)
    return sorted(rows, key=lambda item: (str(item.get(sort_key)), json.dumps(item, sort_keys=True)))


def charge_rows(item: dict[str, Any]) -> list[dict[str, Any]] | None:
    return rowset(item.get("charge_outcomes"), ("charge_id", "statute", "disposition"), "charge_id")


def source_rows(item: dict[str, Any]) -> list[dict[str, Any]] | None:
    return rowset(
        block(item, "source_resolution").get("rejected_disposition_source_details"), ("source", "reason"), "source"
    )


def license_candidate_rows(item: dict[str, Any]) -> list[dict[str, Any]] | None:
    return rowset(
        block(item, "collateral_orders").get("rejected_license_start_candidates"),
        ("source", "date"),
        "source",
    )


def excluded_line_rows(item: dict[str, Any]) -> list[dict[str, Any]] | None:
    return rowset(
        block(item, "financial_order").get("excluded_fee_or_charge_details"),
        ("code", "amount"),
        "code",
        money_keys=("amount",),
    )


def monthly_candidate_rows(item: dict[str, Any]) -> list[dict[str, Any]] | None:
    return rowset(
        block(item, "payment_plan").get("rejected_monthly_candidates"),
        ("source", "amount"),
        "source",
        money_keys=("amount",),
    )


def fields_match(
    pred_case: dict[str, Any],
    exp_case: dict[str, Any],
    block_name: str,
    fields: list[str],
    currency_fields: set[str] | None = None,
) -> bool:
    currency_fields = currency_fields or set()
    pred_block = block(pred_case, block_name)
    exp_block = block(exp_case, block_name)
    for field in fields:
        actual = pred_block.get(field)
        expected = exp_block.get(field)
        if field in currency_fields:
            if money(actual) != money(expected):
                return False
        elif actual != expected:
            return False
    return True


def direct_fields_match(
    pred_case: dict[str, Any],
    exp_case: dict[str, Any],
    fields: list[str],
) -> bool:
    return all(pred_case.get(field) == exp_case.get(field) for field in fields)


def sorted_field_values(item: dict[str, Any], block_name: str, key: str) -> list[str] | None:
    return sorted_strings(block(item, block_name).get(key))


def totals_value(doc: dict[str, Any], key: str, currency: bool = False) -> Any:
    value = totals(doc).get(key)
    if currency:
        return money(value)
    if isinstance(value, list):
        return sorted(value)
    return value


def totals_match(
    pred: dict[str, Any], exp: dict[str, Any], fields: list[str], currency_fields: set[str] | None = None
) -> bool:
    currency_fields = currency_fields or set()
    return all(
        totals_value(pred, field, field in currency_fields) == totals_value(exp, field, field in currency_fields)
        for field in fields
    )


def score_prediction(pred: dict[str, Any], exp: dict[str, Any]) -> dict[str, Any]:
    pred_cases = by_case(pred)
    exp_cases = by_case(exp)
    expected_case_numbers = sorted(exp_cases)

    checks: dict[str, bool] = {}

    checks["SP001"] = (
        pred.get("task_id") == exp.get("task_id")
        and pred.get("packet_id") == exp.get("packet_id")
        and pred.get("county") == exp.get("county")
        and case_order(pred) == expected_case_numbers
        and all(
            direct_fields_match(pred_cases.get(case, {}), exp_cases[case], ["case_number", "defendant_name"])
            and fields_match(
                pred_cases.get(case, {}), exp_cases[case], "source_resolution", ["conviction_posture", "order_date"]
            )
            and charge_rows(pred_cases.get(case, {})) == charge_rows(exp_cases[case])
            for case in expected_case_numbers
        )
    )

    checks["SP002"] = all(
        fields_match(
            pred_cases.get(case, {}),
            exp_cases[case],
            "source_resolution",
            [
                "controlling_source",
                "live_case_status",
                "collateral_extract_used_as_final",
            ],
        )
        and source_rows(pred_cases.get(case, {})) == source_rows(exp_cases[case])
        for case in expected_case_numbers
    ) and totals_match(
        pred,
        exp,
        [
            "excluded_extract_case_numbers",
            "live_disposition_case_count",
            "local_packet_disposition_case_count",
            "source_rejection_count",
            "collateral_extract_used_count",
        ],
    )

    identity_fields = [
        "sid_number",
        "driver_license_number",
        "defendant_phone",
        "defendant_email",
        "mailing_address",
        "probation_officer",
    ]
    checks["SP003"] = all(
        fields_match(pred_cases.get(case, {}), exp_cases[case], "identity_fields", identity_fields)
        and fields_match(
            pred_cases.get(case, {}),
            exp_cases[case],
            "placeholder_audit",
            ["placeholder_policy", "placeholder_count", "case_file_pull_required"],
        )
        and sorted_field_values(pred_cases.get(case, {}), "placeholder_audit", "placeholder_fields")
        == sorted_field_values(exp_cases[case], "placeholder_audit", "placeholder_fields")
        for case in expected_case_numbers
    ) and totals_match(pred, exp, ["placeholder_field_count", "case_file_pull_case_count"])

    collateral_fields = [
        "probation_required",
        "probation_term_months",
        "probation_report_date",
        "probation_report_time",
        "probation_report_location",
        "license_suspension_required",
        "license_suspension_months",
        "license_suspension_start_date",
        "license_start_basis",
        "treatment_referral_required",
    ]
    checks["SP004"] = all(
        fields_match(pred_cases.get(case, {}), exp_cases[case], "collateral_orders", collateral_fields)
        and license_candidate_rows(pred_cases.get(case, {})) == license_candidate_rows(exp_cases[case])
        for case in expected_case_numbers
    ) and totals_match(pred, exp, ["rejected_license_start_candidate_count"])

    financial_fields = [
        "financial_source_resolution",
        "amount_source",
        "ledger_status",
        "principal_amount",
        "amount_paid_as_of_packet",
        "current_balance_due",
    ]
    checks["SP005"] = all(
        fields_match(
            pred_cases.get(case, {}),
            exp_cases[case],
            "financial_order",
            financial_fields,
            currency_fields={"principal_amount", "amount_paid_as_of_packet", "current_balance_due"},
        )
        for case in expected_case_numbers
    ) and totals_match(pred, exp, ["ledger_based_case_count", "schedule_based_case_count"])

    checks["SP006"] = all(
        sorted_field_values(pred_cases.get(case, {}), "financial_order", "assessed_fee_codes")
        == sorted_field_values(exp_cases[case], "financial_order", "assessed_fee_codes")
        and sorted_field_values(pred_cases.get(case, {}), "financial_order", "excluded_fee_or_charge_codes")
        == sorted_field_values(exp_cases[case], "financial_order", "excluded_fee_or_charge_codes")
        and excluded_line_rows(pred_cases.get(case, {})) == excluded_line_rows(exp_cases[case])
        and fields_match(
            pred_cases.get(case, {}),
            exp_cases[case],
            "financial_order",
            ["unsupported_rejected_amount"],
            currency_fields={"unsupported_rejected_amount"},
        )
        for case in expected_case_numbers
    ) and totals_match(
        pred,
        exp,
        ["excluded_candidate_line_count", "unsupported_rejected_amount_total"],
        currency_fields={"unsupported_rejected_amount_total"},
    )

    plan_fields = [
        "plan_action",
        "monthly_amount",
        "selected_amount_source",
        "plan_basis",
        "payment_math_rule",
        "plan_basis_amount",
        "first_due_date",
        "regular_payment_count",
        "regular_payment_total",
        "final_payment_amount",
        "total_installments",
        "final_due_date",
    ]
    checks["SP007"] = all(
        fields_match(
            pred_cases.get(case, {}),
            exp_cases[case],
            "payment_plan",
            plan_fields,
            currency_fields={"monthly_amount", "plan_basis_amount", "regular_payment_total", "final_payment_amount"},
        )
        and monthly_candidate_rows(pred_cases.get(case, {})) == monthly_candidate_rows(exp_cases[case])
        for case in expected_case_numbers
    ) and totals_match(
        pred,
        exp,
        [
            "payment_plan_count",
            "new_account_plan_count",
            "live_plan_retained_count",
            "original_principal_plan_count",
            "rejected_monthly_candidate_count",
        ],
    )

    checks["SP008"] = all(
        fields_match(
            pred_cases.get(case, {}),
            exp_cases[case],
            "return_to_court",
            ["required", "status", "notice_date", "basis"],
        )
        and pred_cases.get(case, {}).get("follow_up_action") == exp_cases[case].get("follow_up_action")
        for case in expected_case_numbers
    ) and totals_match(pred, exp, ["return_to_court_case_numbers"])

    checks["SP009"] = totals_match(
        pred,
        exp,
        [
            "included_case_numbers",
            "excluded_extract_case_numbers",
            "live_disposition_case_count",
            "local_packet_disposition_case_count",
            "source_rejection_count",
            "ledger_based_case_count",
            "schedule_based_case_count",
            "payment_plan_count",
            "new_account_plan_count",
            "live_plan_retained_count",
            "original_principal_plan_count",
            "return_to_court_case_numbers",
            "principal_amount_total",
            "current_balance_due_total",
            "placeholder_field_count",
            "case_file_pull_case_count",
            "excluded_candidate_line_count",
            "unsupported_rejected_amount_total",
            "collateral_extract_used_count",
            "rejected_monthly_candidate_count",
            "rejected_license_start_candidate_count",
        ],
        currency_fields={
            "principal_amount_total",
            "current_balance_due_total",
            "unsupported_rejected_amount_total",
        },
    )

    results = []
    total = 0
    for point in POINTS:
        matched = bool(checks.get(point["id"]))
        earned = point["weight"] if matched else 0
        total += earned
        results.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "matched": matched,
                "score": earned,
            }
        )

    max_score = sum(point["weight"] for point in POINTS)
    return {
        "score": total,
        "max_score": max_score,
        "normalized_score": round(total / max_score, 6),
        "points": results,
    }


def error_result(message: str) -> dict[str, Any]:
    return {
        "score": 0,
        "max_score": sum(point["weight"] for point in POINTS),
        "normalized_score": 0.0,
        "error": message,
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


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps(error_result("usage: evaluator.py <prediction.json>"), indent=2))
        return 2

    prediction_path = Path(sys.argv[1])
    if not prediction_path.is_absolute():
        prediction_path = Path.cwd() / prediction_path

    try:
        prediction = load_json(prediction_path)
        expected = load_json(ANSWER_PATH)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(error_result(str(exc)), indent=2))
        return 1

    if not isinstance(prediction, dict):
        prediction = {}
    print(json.dumps(score_prediction(prediction, expected), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
