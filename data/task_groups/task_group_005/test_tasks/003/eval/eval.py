#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


EXPECTED = {
    "period": "2025-04",
    "entity": "Aurisic US",
    "selected_invoice_ids": [
        "PPD-2025-0025",
        "PPD-2025-0026",
        "PPD-2025-0027",
        "PPD-2025-0028",
        "PPD-2025-0029",
        "PPD-2025-0030",
        "PPD-2025-0031",
        "PPD-2025-0032",
        "PPD-2025-0033",
        "PPD-2025-0034",
    ],
    "account_rollup": {
        "1250": {
            "account_name": "Prepaid Expenses",
            "selected_invoice_count": 8,
            "original_amount_total": 355994.61,
            "april_amortization_total": 74359.00,
            "cumulative_amortization_through_april": 183211.32,
            "schedule_ending_balance": 172783.29,
            "gl_ending_balance": 559377.61,
            "variance_amount": -386594.32,
            "variance_flag": True,
            "has_default_missing_term_flag": True,
            "account_status": "requires_reconciliation",
        },
        "1251": {
            "account_name": "Prepaid Insurance",
            "selected_invoice_count": 2,
            "original_amount_total": 179263.83,
            "april_amortization_total": 22404.79,
            "cumulative_amortization_through_april": 74686.88,
            "schedule_ending_balance": 104576.95,
            "gl_ending_balance": 369976.70,
            "variance_amount": -265399.75,
            "variance_flag": True,
            "has_default_missing_term_flag": False,
            "account_status": "requires_reconciliation",
        },
    },
    "invoice_results": {
        "PPD-2025-0025": ("1250", 514.63, 2058.52, 4117.09, True, True, "missing_contract_dates"),
        "PPD-2025-0026": ("1250", 13275.19, 53100.76, 26550.36, False, False, "none"),
        "PPD-2025-0027": ("1250", 9820.09, 9820.09, 78560.73, False, True, "duplicate_invoice_number"),
        "PPD-2025-0028": ("1251", 14932.28, 44796.84, 44796.85, False, False, "none"),
        "PPD-2025-0029": ("1250", 14135.63, 28271.26, 14135.64, False, False, "none"),
        "PPD-2025-0030": ("1250", 5718.30, 11436.60, 22873.20, False, False, "none"),
        "PPD-2025-0031": ("1250", 10033.11, 20066.22, 10033.12, False, True, "duplicate_invoice_number"),
        "PPD-2025-0032": ("1251", 7472.51, 29890.04, 59780.10, False, True, "rounded_amount"),
        "PPD-2025-0033": ("1250", 2064.14, 2064.14, 16513.14, True, True, "missing_contract_dates"),
        "PPD-2025-0034": ("1250", 18797.91, 56393.73, 0.01, False, True, "manual_override"),
    },
    "default_missing_term_invoice_ids": ["PPD-2025-0025", "PPD-2025-0033"],
    "exception_invoice_ids": [
        "PPD-2025-0025",
        "PPD-2025-0027",
        "PPD-2025-0031",
        "PPD-2025-0032",
        "PPD-2025-0033",
        "PPD-2025-0034",
    ],
    "priority_exception_ids": [
        "PPD-2025-0034",
        "PPD-2025-0033",
        "PPD-2025-0025",
        "PPD-2025-0032",
    ],
    "close_status": "blocked",
}

POINTS = [
    ("selected invoice set", 1),
    ("account totals for 1250 and 1251", 1),
    ("April GL ending balances", 1),
    ("variance status for both accounts", 1),
    ("exception invoice set", 2),
    ("default-term invoice set", 2),
    ("priority exception membership", 3),
    ("priority exception ranking", 3),
    ("close status", 3),
]


def money(value):
    try:
        return round(float(value) + 1e-9, 2)
    except (TypeError, ValueError):
        return None


def sorted_strings(value):
    if not isinstance(value, list):
        return None
    return sorted(str(item) for item in value)


def exact_strings(value):
    if not isinstance(value, list):
        return None
    return [str(item) for item in value]


def check_account_totals(answer):
    for account in ("1250", "1251"):
        got = (answer.get("account_rollup") or {}).get(account)
        exp = EXPECTED["account_rollup"][account]
        if not isinstance(got, dict):
            return False
        for key in (
            "selected_invoice_count",
            "original_amount_total",
            "april_amortization_total",
            "cumulative_amortization_through_april",
            "schedule_ending_balance",
        ):
            expected_value = exp[key]
            if isinstance(expected_value, float):
                if money(got.get(key)) != expected_value:
                    return False
            elif got.get(key) != expected_value:
                return False
    return True


def check_gl_balances(answer):
    for account in ("1250", "1251"):
        got = (answer.get("account_rollup") or {}).get(account)
        exp = EXPECTED["account_rollup"][account]
        if not isinstance(got, dict) or money(got.get("gl_ending_balance")) != exp["gl_ending_balance"]:
            return False
    return True


def check_variance_status(answer):
    for account in ("1250", "1251"):
        got = (answer.get("account_rollup") or {}).get(account)
        exp = EXPECTED["account_rollup"][account]
        if not isinstance(got, dict):
            return False
        if money(got.get("variance_amount")) != exp["variance_amount"]:
            return False
        if got.get("variance_flag") is not exp["variance_flag"]:
            return False
        if got.get("account_status") != exp["account_status"]:
            return False
    return True


def run_point(answer, point_name):
    if point_name == "selected invoice set":
        return (
            answer.get("period") == EXPECTED["period"]
            and answer.get("entity") == EXPECTED["entity"]
            and exact_strings(answer.get("selected_invoice_ids")) == EXPECTED["selected_invoice_ids"]
        )
    if point_name == "account totals for 1250 and 1251":
        return check_account_totals(answer)
    if point_name == "April GL ending balances":
        return check_gl_balances(answer)
    if point_name == "variance status for both accounts":
        return check_variance_status(answer)
    if point_name == "exception invoice set":
        return sorted_strings(answer.get("exception_invoice_ids")) == EXPECTED["exception_invoice_ids"]
    if point_name == "default-term invoice set":
        return (
            sorted_strings(answer.get("default_missing_term_invoice_ids"))
            == EXPECTED["default_missing_term_invoice_ids"]
        )
    if point_name == "priority exception membership":
        return sorted_strings(answer.get("priority_exception_ids")) == sorted(EXPECTED["priority_exception_ids"])
    if point_name == "priority exception ranking":
        return exact_strings(answer.get("priority_exception_ids")) == EXPECTED["priority_exception_ids"]
    if point_name == "close status":
        return answer.get("close_status") == EXPECTED["close_status"]
    return False


def prediction_path():
    if len(sys.argv) > 1 and sys.argv[1]:
        return Path(sys.argv[1])
    env_path = os.environ.get("PREDICTION_FILE")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[1] / "output" / "answer.json"


def main():
    total = sum(weight for _, weight in POINTS)
    try:
        with prediction_path().open("r", encoding="utf-8-sig") as handle:
            answer = json.load(handle)
    except Exception as exc:
        print(
            json.dumps({"score": 0.0, "raw_score": 0, "raw_total": total, "error": str(exc), "points": []}, indent=2)
        )
        return 0

    raw = 0
    points = []
    for name, weight in POINTS:
        matched = bool(run_point(answer, name))
        if matched:
            raw += weight
        points.append({"name": name, "weight": weight, "matched": matched})
    print(
        json.dumps(
            {"score": raw / total, "max_score": 1.0, "raw_score": raw, "raw_total": total, "points": points}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
