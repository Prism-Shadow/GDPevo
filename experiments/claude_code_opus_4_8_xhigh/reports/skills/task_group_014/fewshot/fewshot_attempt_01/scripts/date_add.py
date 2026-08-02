#!/usr/bin/env python3
"""Add a whole number of calendar days to an ISO date (YYYY-MM-DD).

Used for deadline arithmetic such as an internal-appeal window measured in days
from a final adverse determination date.

Usage:
    python3 date_add.py 2026-01-10 30   ->   2026-02-09
"""
import sys
from datetime import date, timedelta


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: date_add.py <YYYY-MM-DD> <days>", file=sys.stderr)
        return 2
    try:
        start = date.fromisoformat(sys.argv[1])
        days = int(sys.argv[2])
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print((start + timedelta(days=days)).isoformat())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
