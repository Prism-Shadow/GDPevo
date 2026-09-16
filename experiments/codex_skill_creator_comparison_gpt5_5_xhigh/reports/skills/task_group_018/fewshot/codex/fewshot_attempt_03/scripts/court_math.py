#!/usr/bin/env python3
"""Deterministic date, installment, and budget helpers for court closeout tasks."""

import argparse
import calendar
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP


CENT = Decimal("0.01")


def money(value):
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def money_float(value):
    return float(money(value))


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def add_months(start, months):
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def schedule(total, installment, first_due, down_payment=0, return_offset_days=None, return_date=None):
    total_due = money(total)
    regular = money(installment)
    down = money(down_payment)
    if total_due < 0 or regular < 0 or down < 0:
        raise ValueError("money amounts must be nonnegative")

    balance = total_due - down
    if balance < 0:
        balance = Decimal("0.00")

    first_due_date = parse_date(first_due)
    if balance == 0:
        result = {
            "balance_after_down_payment": 0.0,
            "regular_installment_amount": money_float(regular),
            "total_installments": 0,
            "payment_count": 0,
            "full_installment_count": 0,
            "full_payment_count": 0,
            "final_payment_amount": 0.0,
            "final_due_date": None,
        }
    else:
        if regular <= 0:
            raise ValueError("installment must be positive when balance remains")
        total_installments = int((balance / regular).to_integral_value(rounding=ROUND_CEILING))
        remainder = balance % regular
        if remainder == 0:
            full_count = total_installments
            final_amount = regular
        else:
            full_count = total_installments - 1
            final_amount = remainder
        final_due = add_months(first_due_date, total_installments - 1)
        result = {
            "balance_after_down_payment": money_float(balance),
            "regular_installment_amount": money_float(regular),
            "total_installments": total_installments,
            "payment_count": total_installments,
            "full_installment_count": full_count,
            "full_payment_count": full_count,
            "final_payment_amount": money_float(final_amount),
            "final_due_date": final_due.isoformat(),
        }

    if return_date:
        result["return_to_court_date"] = return_date
    elif return_offset_days is not None and result["final_due_date"]:
        final_due_date = parse_date(result["final_due_date"])
        result["return_to_court_date"] = (final_due_date + timedelta(days=return_offset_days)).isoformat()

    return result


def support(income, obligations, installment, min_monthly, max_monthly):
    income = money(income)
    obligations = money(obligations)
    installment = money(installment)
    min_monthly = money(min_monthly)
    max_monthly = money(max_monthly)
    disposable = income - obligations

    if installment < min_monthly:
        classification = "below_policy_minimum"
    elif installment > max_monthly:
        classification = "above_policy_maximum"
    elif installment > disposable:
        classification = "unsupported_by_budget"
    else:
        classification = "supportable"

    return {
        "monthly_income": money_float(income),
        "monthly_obligations": money_float(obligations),
        "monthly_disposable_income": money_float(disposable),
        "selected_installment_amount": money_float(installment),
        "classification": classification,
        "budget_supported": classification == "supportable",
        "policy_band": {
            "minimum_monthly": money_float(min_monthly),
            "maximum_monthly": money_float(max_monthly),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Court closeout math helpers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sched = subparsers.add_parser("schedule", help="Compute an installment schedule")
    sched.add_argument("--total", required=True)
    sched.add_argument("--installment", required=True)
    sched.add_argument("--first-due", required=True)
    sched.add_argument("--down-payment", default="0")
    sched.add_argument("--return-offset-days", type=int)
    sched.add_argument("--return-date")

    months = subparsers.add_parser("add-months", help="Add calendar months to a date")
    months.add_argument("--start-date", required=True)
    months.add_argument("--months", type=int, required=True)

    supp = subparsers.add_parser("support", help="Check installment against budget and policy band")
    supp.add_argument("--income", required=True)
    supp.add_argument("--obligations", required=True)
    supp.add_argument("--installment", required=True)
    supp.add_argument("--min-monthly", required=True)
    supp.add_argument("--max-monthly", required=True)

    args = parser.parse_args()
    if args.command == "schedule":
        output = schedule(
            args.total,
            args.installment,
            args.first_due,
            down_payment=args.down_payment,
            return_offset_days=args.return_offset_days,
            return_date=args.return_date,
        )
    elif args.command == "add-months":
        output = {"date": add_months(parse_date(args.start_date), args.months).isoformat()}
    else:
        output = support(args.income, args.obligations, args.installment, args.min_monthly, args.max_monthly)

    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
