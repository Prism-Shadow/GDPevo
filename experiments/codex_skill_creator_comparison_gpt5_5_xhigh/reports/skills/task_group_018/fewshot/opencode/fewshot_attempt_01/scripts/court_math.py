#!/usr/bin/env python3
"""Small deterministic helpers for court packet payment and date math."""

from __future__ import annotations

import argparse
import calendar
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")


def money(value: str) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def date_arg(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def dec_to_number(value: Decimal) -> float:
    return float(value.quantize(CENT, rounding=ROUND_HALF_UP))


def installments(args: argparse.Namespace) -> dict:
    total = money(args.total)
    down_payment = money(args.down_payment)
    installment = money(args.installment)
    if installment <= 0:
        raise SystemExit("installment must be greater than zero")

    remaining = total - down_payment
    if remaining < 0:
        raise SystemExit("down payment cannot exceed total")

    full_count = int(remaining // installment)
    remainder = (remaining - (installment * full_count)).quantize(CENT)
    if remaining == 0:
        total_count = 0
        final_amount = Decimal("0.00")
        final_due = None
    elif remainder == 0:
        total_count = full_count
        final_amount = installment
        final_due = add_months(date_arg(args.first_due), total_count - 1)
    else:
        total_count = full_count + 1
        final_amount = remainder
        final_due = add_months(date_arg(args.first_due), total_count - 1)

    result = {
        "remaining_balance": dec_to_number(remaining),
        "regular_installment_amount": dec_to_number(installment),
        "down_payment": dec_to_number(down_payment),
        "total_installments": total_count,
        "full_installment_count": full_count,
        "final_payment_amount": dec_to_number(final_amount),
        "final_due_date": final_due.isoformat() if final_due else None,
    }
    if final_due and args.return_offset_days is not None:
        result["return_to_court_date"] = (final_due + timedelta(days=args.return_offset_days)).isoformat()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add-months")
    add.add_argument("--date", required=True)
    add.add_argument("--months", required=True, type=int)

    inst = sub.add_parser("installments")
    inst.add_argument("--total", required=True)
    inst.add_argument("--installment", required=True)
    inst.add_argument("--first-due", required=True)
    inst.add_argument("--down-payment", default="0")
    inst.add_argument("--return-offset-days", type=int)

    args = parser.parse_args()
    if args.command == "add-months":
        print(add_months(date_arg(args.date), args.months).isoformat())
    elif args.command == "installments":
        print(json.dumps(installments(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
