#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


POINTS = [
    ("SP001", "Correct case memo identity, conviction, sentence, and required post-sentencing work flags.", 2),
    ("SP002", "Correct CC-1375 probation referral form fields and reporting instruction.", 2),
    ("SP003", "Correct CC-1379 license suspension fields tied to the DUI conviction date.", 2),
    ("SP004", "Correct initial installment order classification and supported balance components.", 3),
    ("SP005", "Correct installment schedule math including final partial payment and final due date.", 3),
    ("SP006", "Correct budget review, policy band, and support classification for the selected installment.", 2),
    ("SP007", "Correct placeholder discipline for missing identifiers, contacts, and office details.", 2),
    ("SP008", "Correct exclusion of unsupported financial items and restitution from the balance.", 1),
    ("SP009", "Correct return-to-court date, time, and nonpayment trigger.", 1),
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
        "case_memo.case_number": "VA-CR24-0716-00",
        "case_memo.court": "Gloucester County Circuit Court",
        "case_memo.defendant_name": "Jordan Mason",
        "case_memo.conviction_date": "2024-09-18",
        "case_memo.offense": "Driving under the influence, first offense",
        "case_memo.statute": "Va. Code 18.2-266",
        "case_memo.sentence_summary.jail_months_imposed": 12,
        "case_memo.sentence_summary.jail_months_suspended": 11,
        "case_memo.sentence_summary.supervised_probation_months": 12,
        "case_memo.sentence_summary.license_suspension_months": 12,
        "case_memo.sentence_summary.release_from_active_confinement": "2024-10-07",
        "case_memo.memo_status.probation_referral_required": True,
        "case_memo.memo_status.license_order_required": True,
        "case_memo.memo_status.payment_agreement_required": True,
    }
    expected_money = {
        "case_memo.sentence_summary.fine_imposed": 1100.00,
        "case_memo.sentence_summary.court_costs": 160.00,
        "case_memo.sentence_summary.fines_and_costs_total": 1260.00,
    }
    return exact_fields(c, expected_exact) and money_fields(c, expected_money), "case memo sentence posture and flags"


def check_sp002(c):
    expected = {
        "cc1375.form_id": "VA_CC1375",
        "cc1375.form_label": "CC-1375 Probation Referral",
        "cc1375.case_number": "VA-CR24-0716-00",
        "cc1375.defendant_name": "Jordan Mason",
        "cc1375.conviction_date": "2024-09-18",
        "cc1375.probation_type": "supervised",
        "cc1375.probation_term_months": 12,
        "cc1375.report_datetime": "2024-10-10T09:00:00",
        "cc1375.probation_officer": "TBD from case file",
        "cc1375.probation_office_location": "TBD from case file",
    }
    return exact_fields(c, expected), "CC-1375 referral fields"


def check_sp003(c):
    expected = {
        "cc1379.form_id": "VA_CC1379",
        "cc1379.form_label": "CC-1379 Installment/License Order",
        "cc1379.case_number": "VA-CR24-0716-00",
        "cc1379.defendant_name": "Jordan Mason",
        "cc1379.driver_license_number": "TBD from case file",
        "cc1379.license_suspension.status": "suspended",
        "cc1379.license_suspension.effective_date": "2024-09-18",
        "cc1379.license_suspension.months": 12,
        "cc1379.license_suspension.basis": "dui_conviction",
    }
    return exact_fields(c, expected), "CC-1379 license consequence"


def check_sp004(c):
    expected = {
        "cc1379.payment_order.agreement_type": "initial_installment",
        "cc1379.payment_order.policy_id": "POL-VA-GLO-FIRST",
        "cc1379.payment_order.payment_interval": "monthly",
    }
    money = {
        "cc1379.payment_order.total_due": 1260.00,
        "cc1379.payment_order.fines_and_costs_balance": 1260.00,
        "cc1379.payment_order.restitution_balance": 0.00,
        "cc1379.payment_order.account_fee": 0.00,
        "cc1379.payment_order.down_payment": 0.00,
        "cc1379.payment_order.installment_amount": 75.00,
    }
    return exact_fields(c, expected) and money_fields(c, money), "initial installment classification and balances"


def check_sp005(c):
    expected = {
        "cc1379.payment_order.first_due_date": "2024-11-09",
        "cc1379.payment_order.payment_count": 17,
        "cc1379.payment_order.full_installment_count": 16,
        "cc1379.payment_order.final_due_date": "2026-03-09",
    }
    money = {
        "cc1379.payment_order.installment_amount": 75.00,
        "cc1379.payment_order.final_payment_amount": 60.00,
    }
    return exact_fields(c, expected) and money_fields(c, money), "installment count and due-date math"


def check_sp006(c):
    expected = {
        "budget_review.support_classification": "supported_by_budget",
    }
    money = {
        "budget_review.monthly_income": 1920.00,
        "budget_review.monthly_obligations": 1340.00,
        "budget_review.monthly_disposable_income": 580.00,
        "budget_review.selected_installment_amount": 75.00,
        "budget_review.policy_band.minimum_monthly": 50.00,
        "budget_review.policy_band.maximum_monthly": 100.00,
    }
    return exact_fields(c, expected) and money_fields(c, money), "budget support and policy band"


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
    expected_items = {
        "account_management_fee",
        "court_appointed_attorney_fee",
        "court_reporter_fee",
        "dmv_reinstatement_fee",
        "late_fee",
        "restitution",
    }
    actual = excluded_map(c)
    ok = set(actual) == expected_items
    if ok:
        ok = all(money_equal(v["amount"], 0.0) for v in actual.values())
        ok = ok and all(
            v["reason_code"] in {"no_order_or_policy_support", "not_part_of_balance"} for v in actual.values()
        )
    return ok, "unsupported financial items excluded"


def check_sp009(c):
    expected = {
        "cc1379.payment_order.return_to_court_date": "2026-05-08",
        "cc1379.payment_order.return_to_court_time": "09:00",
        "cc1379.payment_order.return_to_court_trigger": "nonpayment",
    }
    return exact_fields(c, expected), "return-to-court setting"


CHECKS = {
    "SP001": check_sp001,
    "SP002": check_sp002,
    "SP003": check_sp003,
    "SP004": check_sp004,
    "SP005": check_sp005,
    "SP006": check_sp006,
    "SP007": check_sp007,
    "SP008": check_sp008,
    "SP009": check_sp009,
}


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0.0, "error": "usage: eval.py /path/to/answer.json"}))
        return 2
    try:
        candidate = json.loads(Path(sys.argv[1]).read_text())
    except Exception as exc:
        total_weight = sum(weight for _, _, weight in POINTS)
        points = [
            {
                "id": pid,
                "goal": goal,
                "weight": weight,
                "assigned_score": round(weight / total_weight, 6),
                "passed": False,
                "earned": 0.0,
                "details": f"candidate JSON could not be read: {exc}",
            }
            for pid, goal, weight in POINTS
        ]
        print(json.dumps({"score": 0.0, "points": points}, indent=2))
        return 0

    total_weight = sum(weight for _, _, weight in POINTS)
    results = []
    score = 0.0
    for pid, goal, weight in POINTS:
        assigned = weight / total_weight
        passed, detail = CHECKS[pid](candidate)
        earned = assigned if passed else 0.0
        score += earned
        results.append(
            {
                "id": pid,
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
