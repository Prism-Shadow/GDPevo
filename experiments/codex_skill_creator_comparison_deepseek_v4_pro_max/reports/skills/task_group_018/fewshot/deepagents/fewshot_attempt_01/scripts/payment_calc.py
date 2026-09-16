#!/usr/bin/env python3
"""Compute installment payment schedules for court payment plans.

Usage:
    python3 payment_calc.py <total_due> <monthly_amount> <first_due_date>

Outputs JSON with:
    total_due, monthly_amount, first_due_date, full_payment_count,
    final_payment_amount, total_installments, final_due_date.

All currency values are rounded to two decimal places.
No external dependencies beyond the Python stdlib.
"""

import sys
import json
import calendar
from datetime import date, datetime


def parse_date(raw: str) -> date:
    """Parse ISO date string (YYYY-MM-DD)."""
    return datetime.strptime(raw.strip(), "%Y-%m-%d").date()


def add_months(d: date, months: int) -> date:
    """Add N months to a date using year/month arithmetic.

    When the target month has fewer days than the source day, the day is
    clamped to the last valid day of the target month.
    """
    total_months = d.year * 12 + (d.month - 1) + months
    y = total_months // 12
    m = (total_months % 12) + 1
    max_day = calendar.monthrange(y, m)[1]
    day = min(d.day, max_day)
    return date(y, m, day)


def compute_schedule(total: float, monthly: float, first_due: date):
    """Compute the full installment schedule."""
    total = round(total, 2)
    monthly = round(monthly, 2)

    if monthly <= 0:
        raise ValueError("monthly_amount must be positive")

    full_count = int(total // monthly)
    remainder = round(total - (full_count * monthly), 2)

    if remainder > 0.005:
        total_installments = full_count + 1
        final_payment = remainder
    else:
        total_installments = full_count
        final_payment = 0.0

    # final_due_date is (total_installments - 1) months after first_due
    final_due = add_months(first_due, total_installments - 1)

    return {
        "total_due": total,
        "monthly_amount": monthly,
        "first_due_date": first_due.isoformat(),
        "full_payment_count": full_count,
        "final_payment_amount": round(final_payment, 2),
        "total_installments": total_installments,
        "final_due_date": final_due.isoformat(),
    }


def main():
    if len(sys.argv) != 4:
        print("Usage: python3 payment_calc.py <total_due> <monthly_amount> <first_due_date>")
        sys.exit(1)

    total = float(sys.argv[1])
    monthly = float(sys.argv[2])
    first_due = parse_date(sys.argv[3])

    result = compute_schedule(total, monthly, first_due)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
