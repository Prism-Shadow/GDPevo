#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


EXPECTED = {
    "petitions": {
        "VA-PET-884A": {
            "case_number": "VA-CR25-0884-00",
            "defendant_name": "Lena Walsh",
            "petition_classification": "initial_installment",
            "support_classification": "supportable",
            "approved_monthly_amount": 85.00,
            "down_payment_amount": 0.00,
            "total_due": 1435.00,
            "restitution_balance": 0.00,
            "fines_costs_balance": 1435.00,
            "account_fee_amount": 0.00,
            "account_fee_treatment": "excluded_by_policy",
            "payment_application_order": "fines_costs_only",
            "payment_schedule": {
                "interval": "monthly",
                "first_due_date": "2025-04-11",
                "regular_installment_amount": 85.00,
                "total_installments": 17,
                "final_due_date": "2026-08-11",
                "final_payment_amount": 75.00,
                "return_to_court_date": "2026-10-10",
            },
        },
        "VA-PET-913A": {
            "case_number": "VA-CR25-0913-00",
            "defendant_name": "Marcus Hill",
            "petition_classification": "initial_installment",
            "support_classification": "supportable",
            "approved_monthly_amount": 50.00,
            "down_payment_amount": 0.00,
            "total_due": 1540.00,
            "restitution_balance": 360.00,
            "fines_costs_balance": 1180.00,
            "account_fee_amount": 0.00,
            "account_fee_treatment": "excluded_by_policy",
            "payment_application_order": "restitution_before_fines_costs",
            "payment_schedule": {
                "interval": "monthly",
                "first_due_date": "2025-04-17",
                "regular_installment_amount": 50.00,
                "total_installments": 31,
                "final_due_date": "2027-10-17",
                "final_payment_amount": 40.00,
                "return_to_court_date": "2027-12-16",
            },
        },
    },
    "probation": {
        "VA-CR25-0884-00": {
            "form_id": "VA_CC1375",
            "cc1375_status": "prepare_referral",
            "conviction_date": "2025-03-11",
            "probation_term_months": 12,
            "report_datetime": "2025-03-14T08:30:00",
        },
        "VA-CR25-0913-00": {
            "form_id": "VA_CC1375",
            "cc1375_status": "not_ordered",
            "conviction_date": "2025-03-17",
            "probation_term_months": 0,
            "report_datetime": None,
        },
    },
    "license": {
        "VA-CR25-0884-00": {
            "form_id": "VA_CC1379",
            "license_start_basis": "conviction_date",
            "suspension_start_date": "2025-03-11",
            "suspension_months": 12,
            "suspension_end_date": "2026-03-11",
            "driver_license_number": "TBD from case file",
        },
        "VA-CR25-0913-00": {
            "form_id": "VA_CC1379",
            "license_start_basis": "conviction_date",
            "suspension_start_date": "2025-03-17",
            "suspension_months": 6,
            "suspension_end_date": "2025-09-17",
            "driver_license_number": "TBD from case file",
        },
    },
    "placeholders": {
        "VA-CR25-0884-00": {
            "driver_license_number",
            "mailing_address",
            "phone_number",
            "probation_office_location",
            "probation_officer",
            "residence_address",
            "ssn",
        },
        "VA-CR25-0913-00": {
            "driver_license_number",
            "mailing_address",
            "phone_number",
            "residence_address",
            "ssn",
        },
    },
}


POINTS = [
    (
        "SP001",
        "Correctly identifies both target petitions, links them to the correct cases, and classifies both as initial installment petitions.",
        2,
    ),
    ("SP002", "Selects supportable Gloucester monthly payment terms with no down payment for both petitions.", 2),
    ("SP003", "Handles balances and Marcus Hill restitution priority correctly.", 3),
    ("SP004", "Excludes account-management fees under Gloucester policy for both petitions.", 2),
    (
        "SP005",
        "Computes complete payment schedule counts, final payment amounts, final due dates, and return dates for both petitions.",
        3,
    ),
    ("SP006", "Prepares the correct CC-1375 probation referral status and probation dates for both cases.", 2),
    ("SP007", "Prepares the correct CC-1379 license suspension dates and durations for both cases.", 2),
    (
        "SP008",
        "Uses case-file placeholders for missing identifiers and contact/location fields without inventing values.",
        2,
    ),
]


def main() -> int:
    candidate_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../output/answer.json")
    try:
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return emit_parse_failure(str(exc))

    total_weight = sum(weight for _, _, weight in POINTS)
    checks = [
        check_petition_classification(candidate),
        check_supportable_amounts(candidate),
        check_restitution_priority(candidate),
        check_account_fee_exclusion(candidate),
        check_payment_schedules(candidate),
        check_probation(candidate),
        check_license(candidate),
        check_placeholders(candidate),
    ]

    results = []
    total = 0.0
    for (point_id, goal, weight), (passed, detail) in zip(POINTS, checks):
        assigned = weight / total_weight
        earned = assigned if passed else 0.0
        total += earned
        results.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": round(assigned, 6),
                "passed": bool(passed),
                "earned": round(earned, 6),
                "details": detail,
            }
        )

    print(json.dumps({"score": round(total, 6), "points": results}, indent=2, sort_keys=True))
    return 0


def emit_parse_failure(message: str) -> int:
    total_weight = sum(weight for _, _, weight in POINTS)
    points = []
    for point_id, goal, weight in POINTS:
        assigned = weight / total_weight
        points.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": round(assigned, 6),
                "passed": False,
                "earned": 0.0,
                "details": f"Could not parse candidate JSON: {message}",
            }
        )
    print(json.dumps({"score": 0.0, "points": points}, indent=2, sort_keys=True))
    return 0


def as_money(value):
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def money_eq(actual, expected):
    actual_money = as_money(actual)
    return actual_money is not None and math.isclose(actual_money, round(float(expected), 2), abs_tol=0.005)


def get_petitions(candidate):
    rows = candidate.get("petitions", [])
    if not isinstance(rows, list):
        return {}
    return {str(row.get("petition_id")): row for row in rows if isinstance(row, dict)}


def get_by_case(candidate, key):
    rows = candidate.get(key, [])
    if not isinstance(rows, list):
        return {}
    return {str(row.get("case_number")): row for row in rows if isinstance(row, dict)}


def check_petition_classification(candidate):
    petitions = get_petitions(candidate)
    if set(petitions) != set(EXPECTED["petitions"]):
        return False, f"Expected petition ids {sorted(EXPECTED['petitions'])}; got {sorted(petitions)}."
    for petition_id, expected in EXPECTED["petitions"].items():
        row = petitions[petition_id]
        for field in ("case_number", "defendant_name", "petition_classification"):
            if row.get(field) != expected[field]:
                return False, f"{petition_id} {field} expected {expected[field]!r}; got {row.get(field)!r}."
    return True, "Both target petitions are linked and classified as initial installments."


def check_supportable_amounts(candidate):
    petitions = get_petitions(candidate)
    for petition_id, expected in EXPECTED["petitions"].items():
        row = petitions.get(petition_id, {})
        if row.get("support_classification") != "supportable":
            return False, f"{petition_id} support_classification is {row.get('support_classification')!r}."
        if not money_eq(row.get("approved_monthly_amount"), expected["approved_monthly_amount"]):
            return False, f"{petition_id} approved monthly amount mismatch."
        if not money_eq(row.get("down_payment_amount"), 0):
            return False, f"{petition_id} should have no down payment."
        schedule = row.get("payment_schedule", {})
        if schedule.get("interval") != "monthly" or not money_eq(
            schedule.get("regular_installment_amount"), expected["approved_monthly_amount"]
        ):
            return False, f"{petition_id} monthly schedule interval or regular amount mismatch."
    return True, "Both approved monthly terms fit the Gloucester band and budget facts with no down payment."


def check_restitution_priority(candidate):
    petitions = get_petitions(candidate)
    for petition_id, expected in EXPECTED["petitions"].items():
        row = petitions.get(petition_id, {})
        for field in ("total_due", "restitution_balance", "fines_costs_balance"):
            if not money_eq(row.get(field), expected[field]):
                return False, f"{petition_id} {field} mismatch."
        if row.get("payment_application_order") != expected["payment_application_order"]:
            return (
                False,
                f"{petition_id} payment application order expected {expected['payment_application_order']!r}; got {row.get('payment_application_order')!r}.",
            )
    return True, "Balances are correct and Marcus Hill is marked restitution-before-fines-costs."


def check_account_fee_exclusion(candidate):
    petitions = get_petitions(candidate)
    for petition_id in EXPECTED["petitions"]:
        row = petitions.get(petition_id, {})
        if not money_eq(row.get("account_fee_amount"), 0):
            return False, f"{petition_id} account_fee_amount should be 0.00."
        if row.get("account_fee_treatment") != "excluded_by_policy":
            return False, f"{petition_id} account_fee_treatment should be excluded_by_policy."
    return True, "Both petitions exclude the account-management fee under Gloucester policy."


def check_payment_schedules(candidate):
    petitions = get_petitions(candidate)
    fields = (
        "first_due_date",
        "regular_installment_amount",
        "total_installments",
        "final_due_date",
        "final_payment_amount",
        "return_to_court_date",
    )
    for petition_id, expected in EXPECTED["petitions"].items():
        schedule = petitions.get(petition_id, {}).get("payment_schedule", {})
        exp_schedule = expected["payment_schedule"]
        if schedule.get("interval") != "monthly":
            return False, f"{petition_id} schedule interval should be monthly."
        for field in fields:
            if field in {"regular_installment_amount", "final_payment_amount"}:
                if not money_eq(schedule.get(field), exp_schedule[field]):
                    return False, f"{petition_id} {field} mismatch."
            elif schedule.get(field) != exp_schedule[field]:
                return False, f"{petition_id} {field} expected {exp_schedule[field]!r}; got {schedule.get(field)!r}."
    return (
        True,
        "Payment schedules match first dates, installment counts, final payments, final dates, and return dates.",
    )


def check_probation(candidate):
    rows = get_by_case(candidate, "probation_referrals")
    if set(rows) != set(EXPECTED["probation"]):
        return False, f"Expected probation rows for {sorted(EXPECTED['probation'])}; got {sorted(rows)}."
    for case_number, expected in EXPECTED["probation"].items():
        row = rows[case_number]
        for field, value in expected.items():
            if row.get(field) != value:
                return False, f"{case_number} probation {field} expected {value!r}; got {row.get(field)!r}."
    return True, "Probation referral status and dates are correct for both cases."


def check_license(candidate):
    rows = get_by_case(candidate, "license_orders")
    if set(rows) != set(EXPECTED["license"]):
        return False, f"Expected license rows for {sorted(EXPECTED['license'])}; got {sorted(rows)}."
    for case_number, expected in EXPECTED["license"].items():
        row = rows[case_number]
        for field, value in expected.items():
            if row.get(field) != value:
                return False, f"{case_number} license {field} expected {value!r}; got {row.get(field)!r}."
    return (
        True,
        "License orders use conviction-date starts, correct durations, and case-file placeholder for license number.",
    )


def check_placeholders(candidate):
    rows = get_by_case(candidate, "placeholder_cases")
    if set(rows) != set(EXPECTED["placeholders"]):
        return False, f"Expected placeholder rows for {sorted(EXPECTED['placeholders'])}; got {sorted(rows)}."
    for case_number, expected_fields in EXPECTED["placeholders"].items():
        row = rows[case_number]
        if row.get("placeholder_value") != "TBD from case file":
            return False, f"{case_number} placeholder_value should be TBD from case file."
        actual_fields = row.get("missing_fields")
        if not isinstance(actual_fields, list):
            return False, f"{case_number} missing_fields should be a list."
        if set(actual_fields) != expected_fields:
            return (
                False,
                f"{case_number} missing_fields expected {sorted(expected_fields)}; got {sorted(map(str, actual_fields))}.",
            )
    return True, "Missing identifiers and contact/location fields use only the required placeholder."


if __name__ == "__main__":
    raise SystemExit(main())
