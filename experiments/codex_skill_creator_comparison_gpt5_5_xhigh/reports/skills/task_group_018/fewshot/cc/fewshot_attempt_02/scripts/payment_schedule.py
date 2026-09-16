#!/usr/bin/env python3
"""Compute court installment schedule fields from total, monthly amount, and dates."""

from __future__ import annotations

import argparse
import calendar
import json
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")


def money(value: str) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def money_float(value: Decimal) -> float:
    return float(value.quantize(CENT, rounding=ROUND_HALF_UP))


def add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def build_schedule(
    total: Decimal,
    monthly: Decimal,
    first_due: date,
    down: Decimal,
    return_offset_days: int | None,
    return_date: date | None,
) -> dict:
    remaining = total - down
    if remaining < 0:
        raise ValueError("down payment cannot exceed total")
    if remaining > 0 and monthly <= 0:
        raise ValueError("monthly payment must be positive when a balance remains")

    if remaining == 0:
        full_count = 0
        total_installments = 0
        final_amount = Decimal("0.00")
        final_due = None
    else:
        full_count = int(remaining // monthly)
        remainder = (remaining - (monthly * full_count)).quantize(CENT)
        if remainder == 0:
            total_installments = full_count
            final_amount = monthly
        else:
            total_installments = full_count + 1
            final_amount = remainder
        final_due = add_months(first_due, total_installments - 1)

    if return_date is None and return_offset_days is not None and final_due is not None:
        return_date = final_due + timedelta(days=return_offset_days)

    return {
        "remaining_balance": money_float(remaining),
        "down_payment": money_float(down),
        "monthly_payment": money_float(monthly),
        "first_due_date": first_due.isoformat(),
        "full_installment_count": full_count,
        "full_payment_count": full_count,
        "total_installments": total_installments,
        "payment_count": total_installments,
        "final_payment_amount": money_float(final_amount),
        "final_due_date": final_due.isoformat() if final_due else None,
        "return_to_court_date": return_date.isoformat() if return_date else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--total", required=True, help="Total balance before down payment")
    parser.add_argument("--monthly", required=True, help="Regular installment amount")
    parser.add_argument("--down", default="0", help="Down payment amount")
    due_group = parser.add_mutually_exclusive_group(required=True)
    due_group.add_argument("--first-due", help="First due date, YYYY-MM-DD")
    due_group.add_argument("--start-date", help="Base date used with --first-due-days")
    parser.add_argument("--first-due-days", type=int, help="Days after --start-date for first due date")
    parser.add_argument("--return-offset-days", type=int, help="Days after final due date")
    parser.add_argument("--return-date", help="Explicit return-to-court date, YYYY-MM-DD")
    args = parser.parse_args()

    if args.first_due:
        first_due = parse_date(args.first_due)
    else:
        if args.first_due_days is None:
            parser.error("--first-due-days is required with --start-date")
        first_due = parse_date(args.start_date) + timedelta(days=args.first_due_days)

    result = build_schedule(
        total=money(args.total),
        monthly=money(args.monthly),
        first_due=first_due,
        down=money(args.down),
        return_offset_days=args.return_offset_days,
        return_date=parse_date(args.return_date) if args.return_date else None,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
