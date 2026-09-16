#!/usr/bin/env python3
"""
Crummey withdrawal-right timeline computer.

Usage:
  python3 crummey_timeline.py --contribution-date YYYY-MM-DD --beneficiaries N

Output: JSON with contribution_date, notice_due_date, withdrawal_window_end,
        earliest_premium_payment_date, notices_required.
"""
import argparse, json, sys
from datetime import date, timedelta


def main():
    p = argparse.ArgumentParser(description="Crummey timeline computer")
    p.add_argument("--contribution-date", type=str, required=True,
                   help="ISO date YYYY-MM-DD")
    p.add_argument("--beneficiaries", type=int, required=True)
    args = p.parse_args()

    contribution = date.fromisoformat(args.contribution_date)
    notice_due = contribution + timedelta(days=7)
    window_end = notice_due + timedelta(days=30)
    earliest_payment = window_end + timedelta(days=1)

    result = {
        "contribution_date": contribution.isoformat(),
        "notice_due_date": notice_due.isoformat(),
        "withdrawal_window_end": window_end.isoformat(),
        "earliest_premium_payment_date": earliest_payment.isoformat(),
        "notices_required": args.beneficiaries,
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

