#!/usr/bin/env python3
"""Compute an installment / extended-payment-plan schedule.

Encodes the mechanics used by these closeout tasks so you don't do the arithmetic
by hand. It does NOT decide policy — you pass in the values you read from the
portal payment policy and the reconciled balance. Map the printed quantities onto
whatever field names the task's answer_template.json uses.

Money is handled in integer cents to avoid float drift.

Examples (illustrative numbers only — plug in the values you reconciled):
# total known, monthly known, first due explicit:
  installments.py --total 900 --monthly 100 --first-due 2025-01-15 --return-offset 30

# first due derived from the policy (submitted_date + first_due_days):
  installments.py --total 1200 --monthly 75 --submitted 2025-01-10 \
      --first-due-days 30 --return-offset 60

# with a policy band + budget, to also classify support:
  installments.py --total 1500 --monthly 90 --submitted 2025-01-10 \
      --first-due-days 30 --return-offset 60 --min-monthly 50 --max-monthly 100 \
      --income 2000 --obligations 1500
"""
import argparse
import json
from calendar import monthrange
from datetime import date, timedelta


def parse_date(s):
    return date.fromisoformat(s)


def add_months(d, n):
    """Add n calendar months, keeping the day-of-month (clamped to month end)."""
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, monthrange(y, m)[1])
    return date(y, m, day)


def to_cents(x):
    return int(round(float(x) * 100))


def money(cents):
    return round(cents / 100, 2)


def schedule(total, down, monthly):
    """Return (regular_count, regular_amount, final_amount, total_count) in dollars.

    regular_count installments of `monthly`, then one `final_amount`.
    If the balance divides evenly, the last full payment is treated as the final.
    """
    remaining = to_cents(total) - to_cents(down)
    m = to_cents(monthly)
    if m <= 0:
        raise SystemExit("monthly must be > 0")
    if remaining <= 0:
        return 0, money(m), 0.0, 0
    full = remaining // m
    part = remaining - full * m
    if part == 0:
        # even: final == a regular installment
        return max(full - 1, 0), money(m), money(m), full
    return full, money(m), money(part), full + 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--total", type=float, required=True,
                    help="reconciled total due (fines+costs+restitution+surcharge+supported fees)")
    ap.add_argument("--monthly", type=float, required=True, help="approved monthly installment")
    ap.add_argument("--down", type=float, default=0.0, help="down payment (default 0)")
    ap.add_argument("--first-due", help="explicit approved first due date YYYY-MM-DD")
    ap.add_argument("--submitted", help="petition submitted date YYYY-MM-DD (for derived first due)")
    ap.add_argument("--first-due-days", type=int, help="policy first_due_days offset from submitted")
    ap.add_argument("--return-offset", type=int, help="policy return_to_court_offset_days from final due")
    ap.add_argument("--min-monthly", type=float, help="policy band minimum")
    ap.add_argument("--max-monthly", type=float, help="policy band maximum")
    ap.add_argument("--income", type=float, help="monthly income (for support check)")
    ap.add_argument("--obligations", type=float, help="monthly obligations (for support check)")
    args = ap.parse_args()

    reg_count, reg_amt, final_amt, total_count = schedule(args.total, args.down, args.monthly)

    out = {
        "total_due": money(to_cents(args.total)),
        "down_payment": money(to_cents(args.down)),
        "monthly": money(to_cents(args.monthly)),
        "regular_installment_count": reg_count,   # full_payment_count / full_installment_count
        "regular_installment_amount": reg_amt,
        "final_payment_amount": final_amt,
        "total_installments": total_count,        # regular_count + 1 (or full when even)
    }

    first_due = None
    if args.first_due:
        first_due = parse_date(args.first_due)
    elif args.submitted and args.first_due_days is not None:
        first_due = parse_date(args.submitted) + timedelta(days=args.first_due_days)
    if first_due is not None:
        out["first_due_date"] = first_due.isoformat()
        if total_count > 0:
            final_due = add_months(first_due, total_count - 1)
            out["final_due_date"] = final_due.isoformat()
            if args.return_offset is not None:
                out["return_to_court_date"] = (final_due + timedelta(days=args.return_offset)).isoformat()

    if args.min_monthly is not None and args.max_monthly is not None:
        if args.monthly < args.min_monthly:
            band = "below_policy_minimum"
        elif args.monthly > args.max_monthly:
            band = "above_policy_maximum"
        else:
            band = "within_band"
        out["policy_band"] = {"min_monthly": money(to_cents(args.min_monthly)),
                              "max_monthly": money(to_cents(args.max_monthly)),
                              "result": band}

    if args.income is not None and args.obligations is not None:
        disposable = money(to_cents(args.income) - to_cents(args.obligations))
        out["monthly_disposable_income"] = disposable
        out["fits_disposable_income"] = args.monthly <= disposable

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
