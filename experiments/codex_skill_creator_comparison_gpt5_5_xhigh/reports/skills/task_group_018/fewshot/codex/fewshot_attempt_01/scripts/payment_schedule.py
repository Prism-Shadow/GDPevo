#!/usr/bin/env python3
"""Compute monthly installment counts and due dates for court payment plans."""

import argparse
import calendar
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")


def money(value):
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def add_months(start, months):
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def compute(total_due, installment_amount, first_due_date, down_payment, return_offset_days):
    total = money(total_due)
    installment = money(installment_amount)
    down = money(down_payment)
    if installment <= 0:
        raise ValueError("installment amount must be greater than zero")
    remaining = total - down
    if remaining < 0:
        raise ValueError("down payment cannot exceed total due")

    full_count = int(remaining // installment)
    remainder = (remaining - installment * full_count).quantize(CENT)
    if remainder:
        total_installments = full_count + 1
        final_payment = remainder
    else:
        total_installments = full_count
        final_payment = installment if total_installments else Decimal("0.00")

    first_due = datetime.strptime(first_due_date, "%Y-%m-%d").date()
    final_due = add_months(first_due, max(total_installments - 1, 0))
    result = {
        "remaining_balance": float(remaining),
        "full_installment_count": full_count,
        "final_payment_amount": float(final_payment),
        "total_installments": total_installments,
        "final_due_date": final_due.isoformat(),
    }
    if return_offset_days is not None:
        result["return_to_court_date"] = (final_due + timedelta(days=return_offset_days)).isoformat()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--total-due", required=True, type=Decimal)
    parser.add_argument("--installment-amount", required=True, type=Decimal)
    parser.add_argument("--first-due-date", required=True)
    parser.add_argument("--down-payment", default=Decimal("0.00"), type=Decimal)
    parser.add_argument("--return-offset-days", type=int)
    args = parser.parse_args()

    result = compute(
        args.total_due,
        args.installment_amount,
        args.first_due_date,
        args.down_payment,
        args.return_offset_days,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
