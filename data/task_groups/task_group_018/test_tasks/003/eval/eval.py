#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


POINTS = [
    ("SP001", "Correct case memo identity, appeal posture, sentence totals, and required work flags.", 1),
    ("SP002", "Correct CC-1375 probation referral fields and report date-time.", 1),
    ("SP003", "Correct CC-1379 license suspension fields tied to the DUI conviction date.", 1),
    ("SP004", "Correct initial installment policy classification and supported balance components.", 1),
    (
        "SP005",
        "Correct payment schedule math including final partial payment, final due date, and return-to-court setting.",
        3,
    ),
    ("SP006", "Correct budget review, policy band, and support classification for the selected monthly amount.", 1),
    ("SP007", "Correct placeholder discipline for missing identifiers, contacts, and probation-office details.", 3),
    ("SP008", "Correct exclusion of unsupported account-management fee and restitution from the order balance.", 1),
]


def get(obj, path, default=None):
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def money_equal(actual, expected):
    try:
        return math.isclose(float(actual), float(expected), abs_tol=0.005)
    except (TypeError, ValueError):
        return False


def exact_fields(candidate, expected):
    return all(get(candidate, path) == value for path, value in expected.items())


def money_fields(candidate, expected):
    return all(money_equal(get(candidate, path), value) for path, value in expected.items())


def placeholder_map(candidate):
    rows = candidate.get("placeholder_fields", [])
    if not isinstance(rows, list):
        return {}
    out = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("field"), str):
            out[row["field"]] = {
                "value": row.get("value"),
                "reason_code": row.get("reason_code"),
            }
    return out


def excluded_map(candidate):
    rows = candidate.get("excluded_financial_items", [])
    if not isinstance(rows, list):
        return {}
    out = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("item"), str):
            out[row["item"]] = {
                "amount": row.get("amount"),
                "reason_code": row.get("reason_code"),
            }
    return out


def check_sp001(c):
    expected_exact = {
        "case_memo.case_number": "VA-CR25-1044-00",
        "case_memo.court": "Gloucester County Circuit Court",
        "case_memo.defendant_name": "Talia Nguyen",
        "case_memo.appeal_posture": "circuit_appeal_conviction",
        "case_memo.conviction_date": "2025-05-08",
        "case_memo.offense": "Driving under the influence, first offense",
        "case_memo.statute": "Va. Code 18.2-266",
        "case_memo.sentence_summary.jail_days_imposed": 30,
        "case_memo.sentence_summary.jail_days_suspended": 25,
        "case_memo.sentence_summary.active_jail_days": 5,
        "case_memo.sentence_summary.supervised_probation_months": 6,
        "case_memo.sentence_summary.license_suspension_months": 12,
        "case_memo.sentence_summary.release_from_active_confinement": "2025-05-09",
        "case_memo.memo_status.probation_referral_required": True,
        "case_memo.memo_status.license_order_required": True,
        "case_memo.memo_status.payment_agreement_required": True,
    }
    expected_money = {
        "case_memo.sentence_summary.fine_imposed": 750.00,
        "case_memo.sentence_summary.court_costs": 230.00,
        "case_memo.sentence_summary.fines_and_costs_total": 980.00,
    }
    return exact_fields(c, expected_exact) and money_fields(
        c, expected_money
    ), "case memo appeal posture, sentence, and work flags"


def check_sp002(c):
    expected = {
        "cc1375.form_id": "VA_CC1375",
        "cc1375.form_label": "CC-1375 Probation Referral",
        "cc1375.case_number": "VA-CR25-1044-00",
        "cc1375.defendant_name": "Talia Nguyen",
        "cc1375.conviction_date": "2025-05-08",
        "cc1375.probation_type": "supervised",
        "cc1375.probation_term_months": 6,
        "cc1375.report_datetime": "2025-05-12T09:30:00",
        "cc1375.probation_officer": "TBD from case file",
        "cc1375.probation_office_location": "TBD from case file",
    }
    return exact_fields(c, expected), "CC-1375 probation referral and reporting instruction"


def check_sp003(c):
    expected = {
        "cc1379.form_id": "VA_CC1379",
        "cc1379.form_label": "CC-1379 Installment/License Order",
        "cc1379.case_number": "VA-CR25-1044-00",
        "cc1379.defendant_name": "Talia Nguyen",
        "cc1379.driver_license_number": "TBD from case file",
        "cc1379.license_suspension.status": "suspended",
        "cc1379.license_suspension.effective_date": "2025-05-08",
        "cc1379.license_suspension.months": 12,
        "cc1379.license_suspension.basis": "dui_conviction",
    }
    return exact_fields(c, expected), "CC-1379 license suspension"


def check_sp004(c):
    expected = {
        "cc1379.payment_order.agreement_type": "initial_installment",
        "cc1379.payment_order.policy_id": "POL-VA-GLO-FIRST",
        "cc1379.payment_order.payment_interval": "monthly",
    }
    money = {
        "cc1379.payment_order.total_due": 980.00,
        "cc1379.payment_order.fines_and_costs_balance": 980.00,
        "cc1379.payment_order.restitution_balance": 0.00,
        "cc1379.payment_order.account_fee": 0.00,
        "cc1379.payment_order.down_payment": 0.00,
        "cc1379.payment_order.installment_amount": 60.00,
    }
    return exact_fields(c, expected) and money_fields(c, money), "initial installment policy and balances"


def check_sp005(c):
    expected = {
        "cc1379.payment_order.first_due_date": "2025-06-08",
        "cc1379.payment_order.payment_count": 17,
        "cc1379.payment_order.full_installment_count": 16,
        "cc1379.payment_order.final_due_date": "2026-10-08",
        "cc1379.payment_order.return_to_court_date": "2026-12-07",
        "cc1379.payment_order.return_to_court_time": "09:00",
        "cc1379.payment_order.return_to_court_trigger": "nonpayment",
    }
    money = {
        "cc1379.payment_order.installment_amount": 60.00,
        "cc1379.payment_order.final_payment_amount": 20.00,
    }
    return exact_fields(c, expected) and money_fields(
        c, money
    ), "installment count, final due date, and return-to-court math"


def check_sp006(c):
    expected = {
        "budget_review.support_classification": "supported_by_budget",
    }
    money = {
        "budget_review.monthly_income": 2050.00,
        "budget_review.monthly_obligations": 1785.00,
        "budget_review.monthly_disposable_income": 265.00,
        "budget_review.selected_installment_amount": 60.00,
        "budget_review.policy_band.minimum_monthly": 50.00,
        "budget_review.policy_band.maximum_monthly": 100.00,
    }
    return exact_fields(c, expected) and money_fields(c, money), "budget support and Gloucester policy band"


def check_sp007(c):
    expected = {
        "cc1375.probation_office_location": ("TBD from case file", "missing_office_detail"),
        "cc1375.probation_officer": ("TBD from case file", "missing_office_detail"),
        "cc1379.driver_license_number": ("TBD from case file", "missing_identifier"),
        "defendant.mailing_address": ("TBD from case file", "missing_contact"),
        "defendant.phone": ("TBD from case file", "missing_contact"),
        "defendant.residence_address": ("TBD from case file", "missing_contact"),
        "defendant.ssn": ("TBD from case file", "missing_identifier"),
    }
    actual = placeholder_map(c)
    ok = set(actual) == set(expected)
    if ok:
        ok = all(actual[k]["value"] == v and actual[k]["reason_code"] == r for k, (v, r) in expected.items())
    answerable_paths = [
        "case_memo.case_number",
        "case_memo.defendant_name",
        "cc1375.report_datetime",
        "cc1379.payment_order.total_due",
        "cc1379.license_suspension.effective_date",
    ]
    ok = ok and all(get(c, path) != "TBD from case file" for path in answerable_paths)
    return ok, "placeholder set and no placeholder on answerable fields"


def check_sp008(c):
    expected = {
        "account_management_fee": (25.00, "no_order_or_policy_support"),
        "restitution": (180.00, "no_order_or_policy_support"),
    }
    actual = excluded_map(c)
    ok = set(actual) == set(expected)
    if ok:
        ok = all(
            money_equal(actual[k]["amount"], amount) and actual[k]["reason_code"] == reason
            for k, (amount, reason) in expected.items()
        )
    balances_ok = money_fields(
        c,
        {
            "cc1379.payment_order.total_due": 980.00,
            "cc1379.payment_order.restitution_balance": 0.00,
            "cc1379.payment_order.account_fee": 0.00,
        },
    )
    return ok and balances_ok, "unsupported account fee and restitution are excluded from order balance"


CHECKS = {
    "SP001": check_sp001,
    "SP002": check_sp002,
    "SP003": check_sp003,
    "SP004": check_sp004,
    "SP005": check_sp005,
    "SP006": check_sp006,
    "SP007": check_sp007,
    "SP008": check_sp008,
}


def emit_parse_failure(message):
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
                "details": f"candidate JSON could not be read: {message}",
            }
        )
    print(json.dumps({"score": 0.0, "points": points}, indent=2))
    return 0


def main():
    candidate_path = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
    )
    try:
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return emit_parse_failure(str(exc))

    total_weight = sum(weight for _, _, weight in POINTS)
    results = []
    score = 0.0
    for point_id, goal, weight in POINTS:
        assigned = weight / total_weight
        passed, detail = CHECKS[point_id](candidate)
        earned = assigned if passed else 0.0
        score += earned
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
    print(json.dumps({"score": round(score, 6), "points": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
