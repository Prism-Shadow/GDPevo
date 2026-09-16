#!/usr/bin/env python3
"""Compute installment-plan counts, final payment, and due dates."""

import argparse
import calendar
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")


def money(value):
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def add_months(day, months):
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


def add_intervals(day, interval, count):
    if count <= 0:
        return day
    if interval == "monthly":
        return add_months(day, count)
    if interval == "weekly":
        return day + timedelta(days=7 * count)
    if interval == "biweekly":
        return day + timedelta(days=14 * count)
    raise ValueError(f"unsupported interval: {interval}")


def plan(total, regular_amount, first_due_date, down_payment, interval, return_offset_days):
    total_due = money(total)
    regular = money(regular_amount)
    down = money(down_payment)
    if regular <= 0:
        raise ValueError("regular amount must be greater than zero")

    balance = money(total_due - down)
    first_due = parse_date(first_due_date)

    if balance <= 0:
        final_due = None
        return_date = None
        return {
            "balance_after_down_payment": float(money(max(balance, Decimal("0")))),
            "payment_count": 0,
            "full_installment_count": 0,
            "total_installments": 0,
            "final_payment_amount": 0.0,
            "final_due_date": final_due,
            "return_to_court_date": return_date,
        }

    full_count = int(balance // regular)
    remainder = money(balance - (regular * full_count))
    if remainder:
        total_installments = full_count + 1
        final_payment = remainder
    else:
        total_installments = full_count
        final_payment = regular

    final_due = add_intervals(first_due, interval, total_installments - 1)
    return_date = None
    if return_offset_days is not None:
        return_date = final_due + timedelta(days=return_offset_days)

    return {
        "balance_after_down_payment": float(balance),
        "payment_count": total_installments,
        "full_installment_count": full_count,
        "total_installments": total_installments,
        "final_payment_amount": float(money(final_payment)),
        "final_due_date": final_due.isoformat(),
        "return_to_court_date": return_date.isoformat() if return_date else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--total", required=True, help="Total due before down payment")
    parser.add_argument("--regular-amount", required=True, help="Regular installment amount")
    parser.add_argument("--first-due-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--down-payment", default="0", help="Down payment amount")
    parser.add_argument(
        "--interval",
        default="monthly",
        choices=["monthly", "weekly", "biweekly"],
        help="Installment interval",
    )
    parser.add_argument(
        "--return-offset-days",
        type=int,
        default=None,
        help="Optional days after final due date for return-to-court date",
    )
    args = parser.parse_args()

    result = plan(
        args.total,
        args.regular_amount,
        args.first_due_date,
        args.down_payment,
        args.interval,
        args.return_offset_days,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
