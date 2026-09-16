#!/usr/bin/env python3
"""Calculate installment counts and due dates for court payment plans."""

from __future__ import annotations

import argparse
import calendar
import json
import sys
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


CENTS = Decimal("0.01")


def money(value: str) -> Decimal:
    return Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


def add_interval(day: date, interval: str, count: int) -> date:
    if interval == "monthly":
        return add_months(day, count)
    if interval == "biweekly":
        return day + timedelta(days=14 * count)
    if interval == "weekly":
        return day + timedelta(days=7 * count)
    raise ValueError(f"unsupported interval: {interval}")


def decimal_number(value: Decimal) -> float:
    return float(value.quantize(CENTS, rounding=ROUND_HALF_UP))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--total-due", required=True, type=money)
    parser.add_argument("--regular-installment", required=True, type=money)
    parser.add_argument("--down-payment", default=Decimal("0.00"), type=money)
    parser.add_argument("--first-due-date", required=True)
    parser.add_argument("--interval", choices=["monthly", "biweekly", "weekly"], default="monthly")
    parser.add_argument("--return-offset-days", type=int)
    parser.add_argument("--return-date", help="Use a known return-to-court date instead of calculating one")
    args = parser.parse_args()

    first_due = date.fromisoformat(args.first_due_date)
    balance = (args.total_due - args.down_payment).quantize(CENTS, rounding=ROUND_HALF_UP)
    if balance < 0:
        parser.error("down payment cannot exceed total due")
    if balance > 0 and args.regular_installment <= 0:
        parser.error("regular installment must be positive when a balance remains")

    if balance == 0:
        full_count = 0
        final_payment = Decimal("0.00")
        total_installments = 0
        final_due = None
    else:
        full_count = int(balance // args.regular_installment)
        remainder = (balance - (args.regular_installment * full_count)).quantize(CENTS)
        if remainder == 0:
            total_installments = full_count
            final_payment = args.regular_installment
        else:
            total_installments = full_count + 1
            final_payment = remainder
        final_due = add_interval(first_due, args.interval, total_installments - 1)

    if args.return_date:
        return_date = args.return_date
    elif args.return_offset_days is not None and final_due is not None:
        return_date = (final_due + timedelta(days=args.return_offset_days)).isoformat()
    else:
        return_date = None

    result = {
        "balance_after_down_payment": decimal_number(balance),
        "full_installment_count": full_count,
        "final_payment_amount": decimal_number(final_payment),
        "total_installments": total_installments,
        "final_due_date": final_due.isoformat() if final_due else None,
        "return_to_court_date": return_date,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
