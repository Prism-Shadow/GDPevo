#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


EXPECTED = {
    "court_packet": {
        "jurisdiction_code": "VA-HAM",
        "court_name": "Hampton Circuit Court",
        "policy_id": "POL-VA-HAM-FIRST",
        "packet_date": "2025-06-10",
    },
    "petitions": {
        "VA-PET-1172B": {
            "case_number": "VA-CR25-1172-00",
            "defendant_name": "Owen Reeves",
            "petition_classification": "subsequent_review",
            "review_routing": "judge_or_supervisor_review",
            "support_classification": "needs_judge_review",
            "approved_monthly_amount": 75.00,
            "down_payment_amount": 0.00,
            "total_due": 1130.00,
            "restitution_balance": 240.00,
            "fines_costs_balance": 890.00,
            "account_fee_amount": 0.00,
            "account_fee_treatment": "excluded_by_policy",
            "payment_application_order": "restitution_before_fines_costs",
            "payment_schedule": {
                "interval": "monthly",
                "first_due_date": "2025-07-10",
                "regular_installment_amount": 75.00,
                "total_installments": 15,
                "final_due_date": "2026-09-10",
                "final_payment_amount": 80.00,
                "return_to_court_date": "2026-11-09",
            },
        },
        "VA-PET-1186A": {
            "case_number": "VA-CR25-1186-00",
            "defendant_name": "Camila Ortiz",
            "petition_classification": "initial_installment",
            "review_routing": "clerk_can_enter",
            "support_classification": "supportable",
            "approved_monthly_amount": 125.00,
            "down_payment_amount": 0.00,
            "total_due": 1585.00,
            "restitution_balance": 0.00,
            "fines_costs_balance": 1560.00,
            "account_fee_amount": 25.00,
            "account_fee_treatment": "included_by_policy",
            "payment_application_order": "fines_costs_only",
            "payment_schedule": {
                "interval": "monthly",
                "first_due_date": "2025-07-10",
                "regular_installment_amount": 125.00,
                "total_installments": 13,
                "final_due_date": "2026-07-10",
                "final_payment_amount": 85.00,
                "return_to_court_date": "2026-09-08",
            },
        },
    },
    "probation": {
        "VA-CR25-1172-00": {
            "form_id": "VA_CC1375",
            "cc1375_status": "prepare_referral",
            "conviction_date": "2025-06-06",
            "probation_term_months": 12,
            "report_datetime": "2025-06-12T13:00:00",
        },
        "VA-CR25-1186-00": {
            "form_id": "VA_CC1375",
            "cc1375_status": "prepare_referral",
            "conviction_date": "2025-06-06",
            "probation_term_months": 24,
            "report_datetime": "2025-06-13T09:00:00",
        },
    },
    "license": {
        "VA-CR25-1172-00": {
            "form_id": "VA_HAM_CC1379",
            "license_start_basis": "conviction_date",
            "suspension_start_date": "2025-06-06",
            "suspension_months": 6,
            "suspension_end_date": "2025-12-06",
            "driver_license_number": "TBD from case file",
        },
        "VA-CR25-1186-00": {
            "form_id": "VA_HAM_CC1379",
            "license_start_basis": "conviction_date",
            "suspension_start_date": "2025-06-06",
            "suspension_months": 12,
            "suspension_end_date": "2026-06-06",
            "driver_license_number": "TBD from case file",
        },
    },
    "placeholders": {
        "VA-CR25-1172-00": {
            "driver_license_number",
            "mailing_address",
            "phone_number",
            "probation_office_location",
            "probation_officer",
            "residence_address",
            "ssn",
        },
        "VA-CR25-1186-00": {
            "driver_license_number",
            "mailing_address",
            "phone_number",
            "probation_office_location",
            "probation_officer",
            "residence_address",
            "ssn",
        },
    },
}


POINTS = [
    ("SP001", "Correct Hampton packet metadata and target petition/case identity set.", 2),
    (
        "SP002",
        "Correctly routes Owen Reeves as a second/default-review petition requiring judge or supervisor review.",
        3,
    ),
    ("SP003", "Correctly treats Owen Reeves with no account fee and restitution priority.", 3),
    ("SP004", "Correctly treats Camila Ortiz as a first petition with the Hampton account fee included.", 3),
    (
        "SP005",
        "Correct support classifications, approved monthly amounts, and no down payments for both petitions.",
        2,
    ),
    (
        "SP006",
        "Correct payment schedule dates, installment counts, final payments, and return-to-court dates for both petitions.",
        3,
    ),
    (
        "SP007",
        "Correct CC-1375 probation referral status, terms, and reporting datetimes while keeping probation separate from payment.",
        2,
    ),
    (
        "SP008",
        "Correct Hampton CC-1379 license orders with conviction-date starts, durations, end dates, and no invented license numbers.",
        2,
    ),
    (
        "SP009",
        "Uses case-file placeholders for all missing identifiers and contact/location fields without inventing values.",
        2,
    ),
]


def main() -> int:
    candidate_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../output/answer.json")
    try:
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return emit_parse_failure(str(exc))

    checks = [
        check_packet_and_identity(candidate),
        check_owen_review(candidate),
        check_owen_fee_and_priority(candidate),
        check_camila_account_fee(candidate),
        check_support_terms(candidate),
        check_payment_schedules(candidate),
        check_probation(candidate),
        check_license(candidate),
        check_placeholders(candidate),
    ]
    total_weight = sum(weight for _, _, weight in POINTS)
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


def check_packet_and_identity(candidate):
    packet = candidate.get("court_packet", {})
    if not isinstance(packet, dict):
        return False, "court_packet is missing or not an object."
    for field, expected in EXPECTED["court_packet"].items():
        if packet.get(field) != expected:
            return False, f"court_packet.{field} expected {expected!r}; got {packet.get(field)!r}."
    petitions = get_petitions(candidate)
    if set(petitions) != set(EXPECTED["petitions"]):
        return False, f"Expected petition ids {sorted(EXPECTED['petitions'])}; got {sorted(petitions)}."
    for petition_id, expected in EXPECTED["petitions"].items():
        row = petitions[petition_id]
        for field in ("case_number", "defendant_name"):
            if row.get(field) != expected[field]:
                return False, f"{petition_id} {field} expected {expected[field]!r}; got {row.get(field)!r}."
    return True, "Hampton packet metadata and both target petition identities are correct."


def check_owen_review(candidate):
    row = get_petitions(candidate).get("VA-PET-1172B", {})
    expected = EXPECTED["petitions"]["VA-PET-1172B"]
    for field in ("petition_classification", "review_routing", "support_classification"):
        if row.get(field) != expected[field]:
            return False, f"Owen {field} expected {expected[field]!r}; got {row.get(field)!r}."
    return True, "Owen is classified as subsequent/default review and routed to judge or supervisor review."


def check_owen_fee_and_priority(candidate):
    row = get_petitions(candidate).get("VA-PET-1172B", {})
    expected = EXPECTED["petitions"]["VA-PET-1172B"]
    for field in ("total_due", "restitution_balance", "fines_costs_balance", "account_fee_amount"):
        if not money_eq(row.get(field), expected[field]):
            return False, f"Owen {field} expected {expected[field]:.2f}; got {row.get(field)!r}."
    if row.get("account_fee_treatment") != "excluded_by_policy":
        return False, f"Owen account_fee_treatment was {row.get('account_fee_treatment')!r}."
    if row.get("payment_application_order") != "restitution_before_fines_costs":
        return False, f"Owen payment_application_order was {row.get('payment_application_order')!r}."
    return True, "Owen total due excludes account fee and preserves restitution-before-fines priority."


def check_camila_account_fee(candidate):
    row = get_petitions(candidate).get("VA-PET-1186A", {})
    expected = EXPECTED["petitions"]["VA-PET-1186A"]
    exact = {
        "petition_classification": "initial_installment",
        "review_routing": "clerk_can_enter",
        "account_fee_treatment": "included_by_policy",
        "payment_application_order": "fines_costs_only",
    }
    for field, value in exact.items():
        if row.get(field) != value:
            return False, f"Camila {field} expected {value!r}; got {row.get(field)!r}."
    for field in ("total_due", "fines_costs_balance", "restitution_balance", "account_fee_amount"):
        if not money_eq(row.get(field), expected[field]):
            return False, f"Camila {field} expected {expected[field]:.2f}; got {row.get(field)!r}."
    return True, "Camila is a first petition with the Hampton account fee included in total due."


def check_support_terms(candidate):
    petitions = get_petitions(candidate)
    for petition_id, expected in EXPECTED["petitions"].items():
        row = petitions.get(petition_id, {})
        for field in ("support_classification", "approved_monthly_amount", "down_payment_amount"):
            if field.endswith("amount"):
                if not money_eq(row.get(field), expected[field]):
                    return False, f"{petition_id} {field} mismatch."
            elif row.get(field) != expected[field]:
                return False, f"{petition_id} {field} expected {expected[field]!r}; got {row.get(field)!r}."
        schedule = row.get("payment_schedule", {})
        if schedule.get("interval") != "monthly":
            return False, f"{petition_id} schedule interval should be monthly."
        if not money_eq(schedule.get("regular_installment_amount"), expected["approved_monthly_amount"]):
            return False, f"{petition_id} regular installment amount mismatch."
    return True, "Both petitions use the expected support classification, monthly amount, and no down payment."


def check_payment_schedules(candidate):
    petitions = get_petitions(candidate)
    fields = ("first_due_date", "total_installments", "final_due_date", "return_to_court_date")
    money_fields = ("regular_installment_amount", "final_payment_amount")
    for petition_id, expected in EXPECTED["petitions"].items():
        schedule = petitions.get(petition_id, {}).get("payment_schedule", {})
        exp_schedule = expected["payment_schedule"]
        if schedule.get("interval") != exp_schedule["interval"]:
            return (
                False,
                f"{petition_id} interval expected {exp_schedule['interval']!r}; got {schedule.get('interval')!r}.",
            )
        for field in fields:
            if schedule.get(field) != exp_schedule[field]:
                return False, f"{petition_id} {field} expected {exp_schedule[field]!r}; got {schedule.get(field)!r}."
        for field in money_fields:
            if not money_eq(schedule.get(field), exp_schedule[field]):
                return False, f"{petition_id} {field} expected {exp_schedule[field]:.2f}; got {schedule.get(field)!r}."
    return True, "Payment schedule dates, counts, final payments, and return-to-court dates match."


def check_probation(candidate):
    rows = get_by_case(candidate, "probation_referrals")
    if set(rows) != set(EXPECTED["probation"]):
        return False, f"Expected probation rows for {sorted(EXPECTED['probation'])}; got {sorted(rows)}."
    for case_number, expected in EXPECTED["probation"].items():
        row = rows[case_number]
        for field, value in expected.items():
            if row.get(field) != value:
                return False, f"{case_number} probation {field} expected {value!r}; got {row.get(field)!r}."
    for petition in get_petitions(candidate).values():
        if "probation_term_months" in petition or "report_datetime" in petition:
            return False, "Probation fields should not be embedded in petition rows."
    return True, "Probation referrals are correct and structurally separate from payment petitions."


def check_license(candidate):
    rows = get_by_case(candidate, "license_orders")
    if set(rows) != set(EXPECTED["license"]):
        return False, f"Expected license rows for {sorted(EXPECTED['license'])}; got {sorted(rows)}."
    for case_number, expected in EXPECTED["license"].items():
        row = rows[case_number]
        for field, value in expected.items():
            if row.get(field) != value:
                return False, f"{case_number} license {field} expected {value!r}; got {row.get(field)!r}."
    for petition in get_petitions(candidate).values():
        if "license_suspension_months" in petition or "driver_license_number" in petition:
            return False, "License fields should not be embedded in petition rows."
    return True, "License orders use Hampton CC-1379, conviction-date starts, and license-number placeholders."


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
    answerable_paths = [
        ("court_packet", "court_name"),
        ("petitions", "VA-PET-1172B", "defendant_name"),
        ("petitions", "VA-PET-1186A", "total_due"),
        ("probation_referrals", "VA-CR25-1172-00", "report_datetime"),
        ("license_orders", "VA-CR25-1186-00", "suspension_end_date"),
    ]
    if get_nested_indexed(candidate, answerable_paths[0]) == "TBD from case file":
        return False, "Answerable court name was replaced with a placeholder."
    if get_nested_indexed(candidate, answerable_paths[1]) == "TBD from case file":
        return False, "Answerable Owen name was replaced with a placeholder."
    if get_nested_indexed(candidate, answerable_paths[2]) == "TBD from case file":
        return False, "Answerable Camila total due was replaced with a placeholder."
    if get_nested_indexed(candidate, answerable_paths[3]) == "TBD from case file":
        return False, "Answerable Owen probation report datetime was replaced with a placeholder."
    if get_nested_indexed(candidate, answerable_paths[4]) == "TBD from case file":
        return False, "Answerable Camila license end date was replaced with a placeholder."
    return True, "Missing identifiers and contact/location fields use only the required placeholder."


def get_nested_indexed(candidate, path):
    if len(path) == 2:
        section, field = path
        obj = candidate.get(section, {})
        return obj.get(field) if isinstance(obj, dict) else None
    section, key, field = path
    rows = get_petitions(candidate) if section == "petitions" else get_by_case(candidate, section)
    obj = rows.get(key, {})
    return obj.get(field) if isinstance(obj, dict) else None


if __name__ == "__main__":
    raise SystemExit(main())
