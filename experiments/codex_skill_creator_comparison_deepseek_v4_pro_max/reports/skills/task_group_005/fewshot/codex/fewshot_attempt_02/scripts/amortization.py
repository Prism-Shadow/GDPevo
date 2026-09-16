#!/usr/bin/env python3
"""Deterministic straight-line monthly prepaid amortization.

Usage:
    python3 amortization.py <start_date> <term_months> <original_amount> <target_period>

Outputs JSON with monthly_amortization, cumulative_amortization, and
ending_balance as strings with two-decimal precision.

Example:
    python3 amortization.py 2025-01-01 12 144000.00 2025-03
    # {"monthly_amortization": "12000.00", ...}
"""

import sys
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


def months_between(start, end):
    """Full calendar months between two dates, inclusive of end month."""
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def compute_amortization(start_date, term_months, original_amount, target_period):
    start = date.fromisoformat(start_date)
    target = date.fromisoformat(target_period + "-01")
    original = Decimal(str(original_amount))
    terms = int(term_months)
    if terms <= 0:
        raise ValueError("term_months must be positive")
    monthly = (original / terms).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    months_passed = months_between(start, target)
    if months_passed < 0:
        months_passed = 0
    if months_passed > terms:
        months_passed = terms
    cumulative = (monthly * months_passed).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    ending = (original - cumulative).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if ending < 0:
        ending = Decimal("0.00")
    return {
        "monthly_amortization": monthly,
        "cumulative_amortization": cumulative,
        "ending_balance": ending,
    }


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(json.dumps({"error": "Usage: amortization.py <start_date> <term_months> <original_amount> <target_period>"}))
        sys.exit(1)
    start_date, term_months, original_amount, target_period = sys.argv[1:5]
    try:
        result = compute_amortization(start_date, term_months, original_amount, target_period)
        print(json.dumps({k: str(v) for k, v in result.items()}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
