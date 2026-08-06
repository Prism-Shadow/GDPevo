#!/usr/bin/env python3
"""Installment-plan and schedule-date helper for court-ops closeout packets.

Computes the payment breakdown and schedule dates that these tasks repeatedly
ask for (full installments, final smaller payment, first/final due dates,
return-to-court date). Pure standard library, no task-specific values baked in.

Examples (illustrative numbers only)
------------------------------------
# Balance B, $M/mo, explicit first due date, with a return-to-court offset:
python3 installments.py --total 1000 --monthly 90 --first-due 2025-01-10 --return-offset 60

# Plan with no return-to-court date (e.g. a traffic EPP):
python3 installments.py --total 600 --monthly 55 --first-due 2025-02-15

# Derive the first due date from a policy offset instead of stating it:
python3 installments.py --total 900 --monthly 80 --anchor-date 2025-03-01 --first-due-days 30 --return-offset 60
"""
import argparse
import calendar
import datetime as dt
import json


def parse_date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def add_days(d: dt.date, n: int) -> dt.date:
    return d + dt.timedelta(days=n)


def add_months(d: dt.date, n: int) -> dt.date:
    """Advance by n calendar months, clamping the day to the month's last day."""
    total = (d.year * 12 + (d.month - 1)) + n
    year, month = divmod(total, 12)
    month += 1
    last = calendar.monthrange(year, month)[1]
    return dt.date(year, month, min(d.day, last))


def round2(x: float) -> float:
    # round half up to cents, then normalise -0.0 -> 0.0
    return float(f"{x + 1e-9:.2f}") if x >= 0 else float(f"{x - 1e-9:.2f}")


def plan(total, monthly, first_due, interval="monthly", return_offset_days=None):
    """Return the installment breakdown + schedule.

    total_installments = number of scheduled payments (full + one smaller final).
    full_installment_count = number of full-size payments.
    final_payment_amount = amount of the last payment (== monthly when it divides
    evenly, otherwise the remainder).
    """
    total = round2(total)
    monthly = round2(monthly)
    if monthly <= 0:
        raise ValueError("monthly must be > 0")

    full = int(total // monthly)          # number of full-size payments
    remainder = round2(total - full * monthly)

    if remainder > 0:
        total_installments = full + 1
        full_installment_count = full
        final_payment_amount = remainder
    else:
        total_installments = full
        full_installment_count = full
        final_payment_amount = monthly

    step = {"monthly": 1}.get(interval)
    if step is None:
        # weekly/biweekly handled by caller if ever needed; default to months
        step = 1
        advance = lambda base, k: add_months(base, k)
    else:
        advance = lambda base, k: add_months(base, k)

    final_due = advance(first_due, total_installments - 1)
    result = {
        "total_due_scheduled": total,
        "regular_installment_amount": monthly,
        "full_installment_count": full_installment_count,
        "final_payment_amount": final_payment_amount,
        "total_installments": total_installments,
        "payment_count": total_installments,
        "first_due_date": first_due.isoformat(),
        "final_due_date": final_due.isoformat(),
    }
    if return_offset_days is not None:
        result["return_to_court_date"] = add_days(final_due, return_offset_days).isoformat()
    return result


def main():
    ap = argparse.ArgumentParser(description="Installment + schedule-date helper.")
    ap.add_argument("--total", type=float, required=True, help="Balance to schedule (after any down payment).")
    ap.add_argument("--monthly", type=float, required=True, help="Approved regular installment amount.")
    ap.add_argument("--first-due", type=parse_date, default=None, help="Explicit first due date (YYYY-MM-DD).")
    ap.add_argument("--anchor-date", type=parse_date, default=None, help="Date to offset from when --first-due absent (e.g. submitted/disposition date).")
    ap.add_argument("--first-due-days", type=int, default=None, help="Policy first_due_days offset added to --anchor-date.")
    ap.add_argument("--interval", default="monthly", choices=["monthly"], help="Payment interval.")
    ap.add_argument("--return-offset", type=int, default=None, help="Policy return_to_court_offset_days added to final due date.")
    args = ap.parse_args()

    first_due = args.first_due
    if first_due is None:
        if args.anchor_date is None or args.first_due_days is None:
            ap.error("provide --first-due, or both --anchor-date and --first-due-days")
        first_due = add_days(args.anchor_date, args.first_due_days)

    print(json.dumps(plan(args.total, args.monthly, first_due, args.interval, args.return_offset), indent=2))


if __name__ == "__main__":
    main()
