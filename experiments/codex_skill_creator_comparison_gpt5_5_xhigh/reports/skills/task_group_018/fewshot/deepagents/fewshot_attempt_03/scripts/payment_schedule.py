#!/usr/bin/env python3
"""Compute recurring monthly payment schedule fields for court payment plans."""

from __future__ import annotations

import argparse
import calendar
import json
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")


def money(value: str) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def as_number(value: Decimal) -> float:
    return float(value.quantize(CENT, rounding=ROUND_HALF_UP))


def add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def build_schedule(
    total: Decimal,
    monthly: Decimal,
    first_due: date,
    down_payment: Decimal,
    return_offset_days: int | None,
) -> dict[str, object]:
    if monthly <= 0:
        raise ValueError("monthly payment must be greater than zero")
    if down_payment < 0:
        raise ValueError("down payment cannot be negative")

    remaining = (total - down_payment).quantize(CENT, rounding=ROUND_HALF_UP)
    if remaining < 0:
        raise ValueError("down payment cannot exceed total")

    if remaining == 0:
        final_due = None
        return_due = None
        total_installments = 0
        full_count = 0
        final_amount = Decimal("0.00")
    else:
        full_count = int(remaining // monthly)
        remainder = (remaining - (monthly * full_count)).quantize(
            CENT, rounding=ROUND_HALF_UP
        )
        if remainder == 0:
            total_installments = full_count
            final_amount = monthly
        else:
            total_installments = full_count + 1
            final_amount = remainder
        final_due = add_months(first_due, total_installments - 1)
        return_due = (
            final_due + timedelta(days=return_offset_days)
            if return_offset_days is not None
            else None
        )

    return {
        "remaining_balance": as_number(remaining),
        "installment_amount": as_number(monthly),
        "total_installments": total_installments,
        "full_installment_count": full_count,
        "final_payment_amount": as_number(final_amount),
        "final_due_date": final_due.isoformat() if final_due else None,
        "return_to_court_date": return_due.isoformat() if return_due else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute monthly installment counts and final due dates."
    )
    parser.add_argument("--total", required=True, help="Total amount due.")
    parser.add_argument("--monthly", required=True, help="Regular monthly payment.")
    parser.add_argument(
        "--down-payment", default="0", help="Down payment credited before installments."
    )
    parser.add_argument("--first-due", required=True, help="ISO date YYYY-MM-DD.")
    parser.add_argument(
        "--return-offset-days",
        type=int,
        default=None,
        help="Optional days after final due date for return-to-court review.",
    )
    args = parser.parse_args()

    schedule = build_schedule(
        total=money(args.total),
        monthly=money(args.monthly),
        first_due=date.fromisoformat(args.first_due),
        down_payment=money(args.down_payment),
        return_offset_days=args.return_offset_days,
    )
    print(json.dumps(schedule, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
