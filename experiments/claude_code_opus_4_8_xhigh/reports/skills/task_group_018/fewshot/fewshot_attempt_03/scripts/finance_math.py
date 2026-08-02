#!/usr/bin/env python3
"""Deterministic helpers for court-closeout financial packets.

These are GENERIC calculators for the "Court Operations Portal" closeout task
family. No task-specific data or answer values are baked in -- every number is
passed in at call time. Use them to avoid hand-arithmetic mistakes on
installment plans and date offsets, then map the results onto whatever field
names the current task's answer_template.json uses.

CLI:
    python3 finance_math.py plan  --balance 1000 --monthly 90 \
        --first-due 2025-01-15 --return-offset-days 60
    python3 finance_math.py support --income 1920 --obligations 1340 \
        --monthly 75 --min 50 --max 100
    python3 finance_math.py addmonths --date 2025-01-15 --n 16
    python3 finance_math.py adddays   --date 2025-01-15 --n 30

All money is handled in integer cents internally to avoid float drift.
"""
from __future__ import annotations

import argparse
import calendar
import datetime as _dt
import json


def _d(s: str) -> _dt.date:
    return _dt.date.fromisoformat(s)


def add_days(date: str, n: int) -> str:
    return (_d(date) + _dt.timedelta(days=int(n))).isoformat()


def add_months(date: str, n: int) -> str:
    """Add n calendar months, keeping the day-of-month (clamped to month length)."""
    d = _d(date)
    n = int(n)
    total = (d.year * 12 + (d.month - 1)) + n
    year, month = divmod(total, 12)
    month += 1
    last = calendar.monthrange(year, month)[1]
    return _dt.date(year, month, min(d.day, last)).isoformat()


def _cents(x) -> int:
    return int(round(float(x) * 100))


def installment_plan(balance, monthly):
    """Level monthly installments with a smaller final catch-up payment.

    Returns full_installments (count of regular payments), total_installments
    (full + 1 when there is a remainder), and final_payment_amount.
    Example: balance 1000 at 90/mo -> full 11 (=990), remainder 10,
             total 12, final 10.00.
    """
    b = _cents(balance)
    m = _cents(monthly)
    if m <= 0:
        raise ValueError("monthly installment must be > 0")
    full = b // m
    remainder = b - full * m
    if remainder == 0:
        total = full
        final = m
    else:
        total = full + 1
        final = remainder
    return {
        "balance": round(b / 100, 2),
        "monthly": round(m / 100, 2),
        "full_installments": full,          # regular full-amount payments
        "total_installments": total,        # includes the final catch-up payment
        "final_payment_amount": round(final / 100, 2),
        "regular_installment_amount": round(m / 100, 2),
    }


def schedule(balance, monthly, first_due, return_offset_days=None, base_date=None,
             first_due_days=None):
    """Full plan + dates.

    Provide first_due directly (court-ordered date), OR provide base_date +
    first_due_days to compute it (base_date + first_due_days).
    final_due_date = first_due + (total_installments - 1) months.
    return_to_court_date = final_due + return_offset_days (if given).
    """
    if first_due is None:
        if base_date is None or first_due_days is None:
            raise ValueError("need first_due, or base_date + first_due_days")
        first_due = add_days(base_date, first_due_days)
    plan = installment_plan(balance, monthly)
    final_due = add_months(first_due, plan["total_installments"] - 1)
    plan["first_due_date"] = first_due
    plan["final_due_date"] = final_due
    if return_offset_days is not None:
        plan["return_to_court_date"] = add_days(final_due, return_offset_days)
    return plan


def support_classification(income, obligations, monthly, min_monthly, max_monthly):
    """Classify an installment against budget + policy band.

    disposable = income - obligations. Templates differ on the exact enum
    tokens; map the returned category onto the current template's enum.
    """
    disposable = round(float(income) - float(obligations), 2)
    monthly = float(monthly)
    if monthly < float(min_monthly):
        cat = "below_policy_minimum"
    elif monthly > float(max_monthly):
        cat = "above_policy_maximum"
    elif monthly > disposable:
        cat = "unsupported_by_budget"
    else:
        cat = "supportable"          # a.k.a. supported_by_budget
    return {
        "monthly_disposable_income": disposable,
        "selected_installment_amount": monthly,
        "policy_min": float(min_monthly),
        "policy_max": float(max_monthly),
        "category": cat,
    }


def _main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("plan", help="installment plan + schedule dates")
    sp.add_argument("--balance", type=float, required=True)
    sp.add_argument("--monthly", type=float, required=True)
    sp.add_argument("--first-due")
    sp.add_argument("--base-date")
    sp.add_argument("--first-due-days", type=int)
    sp.add_argument("--return-offset-days", type=int)

    ss = sub.add_parser("support", help="budget/policy-band classification")
    ss.add_argument("--income", type=float, required=True)
    ss.add_argument("--obligations", type=float, required=True)
    ss.add_argument("--monthly", type=float, required=True)
    ss.add_argument("--min", type=float, required=True)
    ss.add_argument("--max", type=float, required=True)

    sm = sub.add_parser("addmonths")
    sm.add_argument("--date", required=True)
    sm.add_argument("--n", type=int, required=True)

    sd = sub.add_parser("adddays")
    sd.add_argument("--date", required=True)
    sd.add_argument("--n", type=int, required=True)

    a = p.parse_args()
    if a.cmd == "plan":
        out = schedule(a.balance, a.monthly, a.first_due, a.return_offset_days,
                       a.base_date, a.first_due_days)
    elif a.cmd == "support":
        out = support_classification(a.income, a.obligations, a.monthly, a.min, a.max)
    elif a.cmd == "addmonths":
        out = {"result": add_months(a.date, a.n)}
    elif a.cmd == "adddays":
        out = {"result": add_days(a.date, a.n)}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    _main()
