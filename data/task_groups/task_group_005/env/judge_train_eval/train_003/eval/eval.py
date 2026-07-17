import json
import sys
from pathlib import Path


REFERENCE = {
    "selected_invoice_ids": [
        "PPD-AUR-1250-JAN-001",
        "PPD-AUR-1251-GOOD-001",
        "PPD-2025-0001",
        "PPD-2025-0002",
        "PPD-2025-0008",
        "PPD-2025-0013",
        "PPD-2025-0014",
        "PPD-2025-0024",
    ],
    "rollup_1250": {
        "selected_invoice_count": 5,
        "original_amount_total": 287918.71,
        "march_amortization_total": 53946.41,
        "cumulative_amortization_through_march": 105118.21,
        "schedule_ending_balance": 182800.50,
        "gl_ending_balance": 473655.55,
    },
    "rollup_1251": {
        "selected_invoice_count": 3,
        "original_amount_total": 714319.13,
        "march_amortization_total": 80216.04,
        "cumulative_amortization_through_march": 219439.06,
        "schedule_ending_balance": 494880.07,
        "gl_ending_balance": 415537.13,
    },
    "variance_1250": {
        "variance_amount": -290855.05,
        "variance_flag": True,
        "account_status": "requires_reconciliation",
    },
    "variance_1251": {
        "variance_amount": 79342.94,
        "variance_flag": True,
        "account_status": "requires_reconciliation",
    },
    "default_missing_term_invoice_ids": ["PPD-2025-0002", "PPD-2025-0013"],
    "exception_invoice_ids": [
        "PPD-2025-0001",
        "PPD-2025-0002",
        "PPD-2025-0013",
        "PPD-2025-0014",
        "PPD-AUR-1251-GOOD-001",
    ],
    "invoice_balances": {
        "PPD-AUR-1250-JAN-001": {
            "account": "1250",
            "march_amortization": 12000.00,
            "cumulative_amortization_through_march": 36000.00,
            "ending_balance": 108000.00,
        },
        "PPD-AUR-1251-GOOD-001": {
            "account": "1251",
            "march_amortization": 45560.43,
            "cumulative_amortization_through_march": 136681.29,
            "ending_balance": 410043.81,
        },
        "PPD-2025-0001": {
            "account": "1250",
            "march_amortization": 848.63,
            "cumulative_amortization_through_march": 848.63,
            "ending_balance": 6789.05,
        },
        "PPD-2025-0002": {
            "account": "1250",
            "march_amortization": 4329.23,
            "cumulative_amortization_through_march": 4329.23,
            "ending_balance": 21646.14,
        },
        "PPD-2025-0008": {
            "account": "1251",
            "march_amortization": 10604.53,
            "cumulative_amortization_through_march": 10604.53,
            "ending_balance": 84836.25,
        },
        "PPD-2025-0013": {
            "account": "1250",
            "march_amortization": 23182.65,
            "cumulative_amortization_through_march": 23182.65,
            "ending_balance": 46365.31,
        },
        "PPD-2025-0014": {
            "account": "1250",
            "march_amortization": 13585.90,
            "cumulative_amortization_through_march": 40757.70,
            "ending_balance": 0.00,
        },
        "PPD-2025-0024": {
            "account": "1251",
            "march_amortization": 24051.08,
            "cumulative_amortization_through_march": 72153.24,
            "ending_balance": 0.01,
        },
    },
    "invoice_flags": {
        "PPD-AUR-1250-JAN-001": {"default_missing_term_flag": False, "exception_flag": False},
        "PPD-AUR-1251-GOOD-001": {"default_missing_term_flag": False, "exception_flag": True},
        "PPD-2025-0001": {"default_missing_term_flag": False, "exception_flag": True},
        "PPD-2025-0002": {"default_missing_term_flag": True, "exception_flag": True},
        "PPD-2025-0008": {"default_missing_term_flag": False, "exception_flag": False},
        "PPD-2025-0013": {"default_missing_term_flag": True, "exception_flag": True},
        "PPD-2025-0014": {"default_missing_term_flag": False, "exception_flag": True},
        "PPD-2025-0024": {"default_missing_term_flag": False, "exception_flag": False},
    },
}


POINTS = [
    ("selected invoice population is exact and ordered", 1),
    ("account 1250 schedule totals are exact", 2),
    ("account 1251 schedule totals are exact", 2),
    ("account 1250 GL variance decision is exact", 2),
    ("account 1251 GL variance decision is exact", 2),
    ("default or missing-term invoice set is exact", 1),
    ("exception invoice set is exact", 1),
    ("selected invoice amortization and ending balances are exact", 3),
    ("selected invoice default and exception flags are exact", 1),
]


def money(value):
    try:
        return round(float(value) + 0.0, 2)
    except (TypeError, ValueError):
        return None


def same_money(actual, expected):
    return money(actual) == round(float(expected), 2)


def get_rollup(pred, account):
    rollup = pred.get("account_rollup", {})
    if isinstance(rollup, dict):
        return rollup.get(account, {})
    return {}


def invoice_map(pred):
    rows = pred.get("invoice_results", [])
    if not isinstance(rows, list):
        return {}
    result = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("prepaid_invoice_id"), str):
            result[row["prepaid_invoice_id"]] = row
    return result


def list_exact(actual, expected):
    return isinstance(actual, list) and actual == expected


def sorted_list_exact(actual, expected):
    return isinstance(actual, list) and sorted(actual) == expected


def check_rollup(pred, account, key):
    actual = get_rollup(pred, account)
    expected = REFERENCE[key]
    for field, expected_value in expected.items():
        if field == "selected_invoice_count":
            if actual.get(field) != expected_value:
                return False
        elif not same_money(actual.get(field), expected_value):
            return False
    return True


def check_variance(pred, account, key):
    actual = get_rollup(pred, account)
    expected = REFERENCE[key]
    return (
        same_money(actual.get("variance_amount"), expected["variance_amount"])
        and actual.get("variance_flag") is expected["variance_flag"]
        and actual.get("account_status") == expected["account_status"]
    )


def check_invoice_balances(pred):
    rows = invoice_map(pred)
    if set(rows) != set(REFERENCE["invoice_balances"]):
        return False
    for invoice_id, expected in REFERENCE["invoice_balances"].items():
        row = rows[invoice_id]
        if row.get("account") != expected["account"]:
            return False
        for field in ["march_amortization", "cumulative_amortization_through_march", "ending_balance"]:
            if not same_money(row.get(field), expected[field]):
                return False
    return True


def check_invoice_flags(pred):
    rows = invoice_map(pred)
    if set(rows) != set(REFERENCE["invoice_flags"]):
        return False
    for invoice_id, expected in REFERENCE["invoice_flags"].items():
        row = rows[invoice_id]
        for field, expected_value in expected.items():
            if row.get(field) is not expected_value:
                return False
    return True


def score(pred):
    checks = [
        list_exact(pred.get("selected_invoice_ids"), REFERENCE["selected_invoice_ids"]),
        check_rollup(pred, "1250", "rollup_1250"),
        check_rollup(pred, "1251", "rollup_1251"),
        check_variance(pred, "1250", "variance_1250"),
        check_variance(pred, "1251", "variance_1251"),
        sorted_list_exact(pred.get("default_missing_term_invoice_ids"), REFERENCE["default_missing_term_invoice_ids"]),
        sorted_list_exact(pred.get("exception_invoice_ids"), REFERENCE["exception_invoice_ids"]),
        check_invoice_balances(pred),
        check_invoice_flags(pred),
    ]
    total_weight = sum(weight for _, weight in POINTS)
    earned = sum(weight for passed, (_, weight) in zip(checks, POINTS) if passed)
    details = [
        {"goal": goal, "weight": weight, "passed": bool(passed)} for passed, (goal, weight) in zip(checks, POINTS)
    ]
    return {"score": earned / total_weight, "earned_weight": earned, "total_weight": total_weight, "details": details}


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: eval.py <prediction.json>")
    path = Path(sys.argv[1])
    try:
        pred = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(json.dumps({"score": 0.0, "error": f"could not read prediction JSON: {exc}"}))
        return
    print(json.dumps(score(pred), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
