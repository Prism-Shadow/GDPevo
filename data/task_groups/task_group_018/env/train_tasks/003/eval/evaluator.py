#!/usr/bin/env python3
import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path


POINTS = [
    {
        "id": "SP001",
        "weight": 2,
        "goal": "Correct target defendant set, ordering, names, and conviction posture.",
    },
    {
        "id": "SP002",
        "weight": 2,
        "goal": "Correct charge-level outcomes and unsupported DUI-104 exclusion treatment.",
    },
    {
        "id": "SP003",
        "weight": 3,
        "goal": "Correct Darla Nguyen probation, license, and treatment collateral order fields.",
    },
    {
        "id": "SP004",
        "weight": 3,
        "goal": "Correct Hannah Foster probation, license, and treatment collateral order fields.",
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Correct use of the required placeholder for missing identity/contact/order fields.",
    },
    {
        "id": "SP006",
        "weight": 2,
        "goal": "Correct Darla Nguyen fee-code selection, principal, paid amount, and current balance.",
    },
    {
        "id": "SP007",
        "weight": 3,
        "goal": "Correct Hannah Foster fee-code selection, principal, paid amount, and current balance.",
    },
    {
        "id": "SP008",
        "weight": 3,
        "goal": "Correct installment plan basis, monthly amount, counts, first dates, final dates, and final payments for both defendants.",
    },
    {
        "id": "SP009",
        "weight": 1,
        "goal": "Correct packet totals and follow-up action codes.",
    },
]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return None


def by_case(doc):
    defendants = doc.get("defendants")
    if not isinstance(defendants, list):
        return {}
    result = {}
    for item in defendants:
        if isinstance(item, dict) and isinstance(item.get("case_number"), str):
            result[item["case_number"]] = item
    return result


def sorted_codes(value):
    if not isinstance(value, list):
        return None
    return sorted(str(v) for v in value)


def sorted_charge_rows(value):
    if not isinstance(value, list):
        return None
    rows = []
    for row in value:
        if not isinstance(row, dict):
            return None
        rows.append(
            {
                "charge_id": row.get("charge_id"),
                "statute": row.get("statute"),
                "disposition": row.get("disposition"),
            }
        )
    return sorted(rows, key=lambda r: str(r.get("charge_id")))


def get_path(obj, path):
    cur = obj
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def values_match(pred, exp, path, currency=False):
    pv = get_path(pred, path)
    ev = get_path(exp, path)
    if currency:
        return money(pv) == money(ev)
    return pv == ev


def fields_match(pred, exp, paths, currency_paths=()):
    currency_paths = {tuple(p) for p in currency_paths}
    return all(values_match(pred, exp, p, tuple(p) in currency_paths) for p in paths)


def score_prediction(pred, exp):
    p_cases = by_case(pred)
    e_cases = by_case(exp)
    expected_case_numbers = sorted(e_cases)
    actual_case_numbers = (
        [d.get("case_number") for d in pred.get("defendants", [])] if isinstance(pred.get("defendants"), list) else []
    )

    checks = {}

    checks["SP001"] = actual_case_numbers == expected_case_numbers and all(
        p_cases.get(case, {}).get("defendant_name") == e_cases[case].get("defendant_name")
        and p_cases.get(case, {}).get("conviction_posture") == e_cases[case].get("conviction_posture")
        for case in expected_case_numbers
    )

    checks["SP002"] = all(
        sorted_charge_rows(p_cases.get(case, {}).get("charge_outcomes"))
        == sorted_charge_rows(e_cases[case].get("charge_outcomes"))
        for case in expected_case_numbers
    ) and sorted_codes(
        p_cases.get("23-GLO-00218", {}).get("financial_order", {}).get("excluded_fee_or_charge_codes")
    ) == ["DUI-104"]

    checks["SP003"] = fields_match(
        p_cases.get("23-GLO-00218", {}),
        e_cases["23-GLO-00218"],
        [
            ("collateral_orders", "probation_required"),
            ("collateral_orders", "probation_term_months"),
            ("collateral_orders", "probation_report_date"),
            ("collateral_orders", "probation_report_time"),
            ("collateral_orders", "probation_report_location"),
            ("collateral_orders", "license_suspension_required"),
            ("collateral_orders", "license_suspension_months"),
            ("collateral_orders", "license_suspension_start_date"),
            ("collateral_orders", "treatment_referral_required"),
        ],
    )

    checks["SP004"] = fields_match(
        p_cases.get("24-GLO-01001", {}),
        e_cases["24-GLO-01001"],
        [
            ("collateral_orders", "probation_required"),
            ("collateral_orders", "probation_term_months"),
            ("collateral_orders", "probation_report_date"),
            ("collateral_orders", "probation_report_time"),
            ("collateral_orders", "probation_report_location"),
            ("collateral_orders", "license_suspension_required"),
            ("collateral_orders", "license_suspension_months"),
            ("collateral_orders", "license_suspension_start_date"),
            ("collateral_orders", "treatment_referral_required"),
        ],
    )

    placeholder = "TBD from case file"
    checks["SP005"] = (
        all(
            get_path(p_cases.get(case, {}), ("identity_fields", field)) == placeholder
            for case in expected_case_numbers
            for field in ("driver_license_number", "defendant_phone", "probation_officer")
        )
        and pred.get("packet_totals", {}).get("placeholder_field_count") == 6
    )

    checks["SP006"] = (
        sorted_codes(p_cases.get("23-GLO-00218", {}).get("financial_order", {}).get("assessed_fee_codes"))
        == sorted_codes(e_cases["23-GLO-00218"]["financial_order"]["assessed_fee_codes"])
        and sorted_codes(
            p_cases.get("23-GLO-00218", {}).get("financial_order", {}).get("excluded_fee_or_charge_codes")
        )
        == ["DUI-104"]
        and fields_match(
            p_cases.get("23-GLO-00218", {}),
            e_cases["23-GLO-00218"],
            [
                ("financial_order", "principal_amount"),
                ("financial_order", "amount_paid_as_of_packet"),
                ("financial_order", "current_balance_due"),
            ],
            currency_paths=[
                ("financial_order", "principal_amount"),
                ("financial_order", "amount_paid_as_of_packet"),
                ("financial_order", "current_balance_due"),
            ],
        )
    )

    checks["SP007"] = (
        sorted_codes(p_cases.get("24-GLO-01001", {}).get("financial_order", {}).get("assessed_fee_codes"))
        == sorted_codes(e_cases["24-GLO-01001"]["financial_order"]["assessed_fee_codes"])
        and sorted_codes(
            p_cases.get("24-GLO-01001", {}).get("financial_order", {}).get("excluded_fee_or_charge_codes")
        )
        == []
        and fields_match(
            p_cases.get("24-GLO-01001", {}),
            e_cases["24-GLO-01001"],
            [
                ("financial_order", "principal_amount"),
                ("financial_order", "amount_paid_as_of_packet"),
                ("financial_order", "current_balance_due"),
            ],
            currency_paths=[
                ("financial_order", "principal_amount"),
                ("financial_order", "amount_paid_as_of_packet"),
                ("financial_order", "current_balance_due"),
            ],
        )
    )

    schedule_paths = [
        ("financial_order", "plan_basis"),
        ("financial_order", "monthly_amount"),
        ("financial_order", "first_due_date"),
        ("financial_order", "regular_payment_count"),
        ("financial_order", "final_payment_amount"),
        ("financial_order", "total_installments"),
        ("financial_order", "final_due_date"),
    ]
    checks["SP008"] = all(
        fields_match(
            p_cases.get(case, {}),
            e_cases[case],
            schedule_paths,
            currency_paths=[
                ("financial_order", "monthly_amount"),
                ("financial_order", "final_payment_amount"),
            ],
        )
        for case in expected_case_numbers
    )

    checks["SP009"] = fields_match(
        pred,
        exp,
        [
            ("packet_totals", "principal_amount_total"),
            ("packet_totals", "current_balance_due_total"),
            ("packet_totals", "payment_plan_count"),
        ],
        currency_paths=[
            ("packet_totals", "principal_amount_total"),
            ("packet_totals", "current_balance_due_total"),
        ],
    ) and all(
        p_cases.get(case, {}).get("follow_up_action") == "enter_probation_license_payment_order"
        for case in expected_case_numbers
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
    max_score = sum(p["weight"] for p in POINTS)
    return {
        "score": total,
        "max_score": max_score,
        "normalized_score": round(total / max_score, 6),
        "points": results,
    }


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: evaluator.py <prediction.json>"}, indent=2))
        return 2
    prediction_path = Path(sys.argv[1])
    answer_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"
    try:
        pred = load_json(prediction_path)
        exp = load_json(answer_path)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": sum(p["weight"] for p in POINTS),
                    "normalized_score": 0.0,
                    "error": str(exc),
                    "points": [
                        {
                            "id": p["id"],
                            "goal": p["goal"],
                            "weight": p["weight"],
                            "matched": False,
                            "score": 0,
                        }
                        for p in POINTS
                    ],
                },
                indent=2,
            )
        )
        return 1
    print(json.dumps(score_prediction(pred, exp), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
