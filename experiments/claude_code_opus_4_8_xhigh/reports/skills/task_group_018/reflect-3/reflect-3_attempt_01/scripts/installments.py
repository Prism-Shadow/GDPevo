#!/usr/bin/env python3
"""Installment-schedule helper for court financial-order closeouts.

Pure arithmetic: no network, no external data. Plug in the balance, the approved
monthly amount, the first-due date, and the policy offsets from the task, and it
returns the installment breakdown and the derived dates that these answer
templates ask for.

Usage (numbers below are illustrative placeholders, not from any real matter):
    python3 installments.py --total 1200 --monthly 100 --first 2030-01-15 \
        --return-offset-days 60
    python3 installments.py --fines 900 --restitution 300 --monthly 75 \
        --first 2030-02-01 --return-offset-days 45 \
        --suspension-start 2029-12-01 --suspension-months 12
"""
import argparse
import calendar
from datetime import date, timedelta


def add_months(d: date, m: int) -> date:
    """Add m months, keeping the day-of-month (clamped to the month's last day)."""
    y = d.year + (d.month - 1 + m) // 12
    mo = (d.month - 1 + m) % 12 + 1
    day = min(d.day, calendar.monthrange(y, mo)[1])
    return date(y, mo, day)


def schedule(total_due, monthly, first_due, return_offset_days=None,
             suspension_start=None, suspension_months=None):
    total_due = round(float(total_due), 2)
    monthly = round(float(monthly), 2)
    full = int(total_due // monthly)
    remainder = round(total_due - full * monthly, 2)
    # Universal convention used by these templates:
    #   total_installments = number of payments,
    #   final_payment_amount = the LAST payment (remainder if uneven, else monthly),
    #   full_installment_count = the count of full-value payments before the last.
    total_installments = full + 1 if remainder > 0.005 else full
    full_installment_count = total_installments - 1
    final_payment_amount = round(total_due - full_installment_count * monthly, 2)
    final_due = add_months(first_due, total_installments - 1)
    out = {
        "total_due": total_due,
        "regular_installment_amount": monthly,
        "full_installment_count": full_installment_count,
        "total_installments": total_installments,
        "final_payment_amount": final_payment_amount,
        "first_due_date": first_due.isoformat(),
        "final_due_date": final_due.isoformat(),
    }
    if return_offset_days is not None:
        out["return_to_court_date"] = (
            final_due + timedelta(days=int(return_offset_days))
        ).isoformat()
    if suspension_start is not None and suspension_months is not None:
        out["suspension_start_date"] = suspension_start.isoformat()
        out["suspension_months"] = int(suspension_months)
        out["suspension_end_date"] = add_months(
            suspension_start, int(suspension_months)
        ).isoformat()
    return out


def _iso(s):
    return date.fromisoformat(s)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--total", type=float, help="total due (overrides fines+restitution)")
    p.add_argument("--fines", type=float, default=0.0)
    p.add_argument("--restitution", type=float, default=0.0)
    p.add_argument("--account-fee", type=float, default=0.0,
                   help="only if policy flags an account fee")
    p.add_argument("--monthly", type=float, required=True)
    p.add_argument("--first", required=True, help="first due date YYYY-MM-DD")
    p.add_argument("--return-offset-days", type=int, default=None)
    p.add_argument("--suspension-start", default=None, help="YYYY-MM-DD")
    p.add_argument("--suspension-months", type=int, default=None)
    a = p.parse_args()
    total = a.total if a.total is not None else (a.fines + a.restitution + a.account_fee)
    res = schedule(
        total, a.monthly, _iso(a.first), a.return_offset_days,
        _iso(a.suspension_start) if a.suspension_start else None,
        a.suspension_months,
    )
    import json
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
