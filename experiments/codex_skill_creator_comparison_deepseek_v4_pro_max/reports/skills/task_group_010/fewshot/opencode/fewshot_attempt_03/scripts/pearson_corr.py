#!/usr/bin/env python3
"""Pearson correlation from Asteria index-level API responses.

Usage:
  python3 pearson_corr.py <index_a.json> <index_b.json> <start_date> <end_date>

Where each JSON file is the raw response from GET /api/index-levels/{id},
containing a "levels" array of {"date": "...", "level": number}.

Output: the Pearson correlation rounded to 3 decimal places, printed to stdout.
"""

import json
import sys
from math import sqrt


def monthly_returns(levels, start_date, end_date):
    """Extract consecutive monthly simple returns within [start_date, end_date]."""
    # Sort by date and filter to window (inclusive)
    window = sorted(
        [p for p in levels if start_date <= p["date"] <= end_date],
        key=lambda p: p["date"],
    )
    returns = []
    for i in range(1, len(window)):
        prev = window[i - 1]["level"]
        curr = window[i]["level"]
        returns.append((curr - prev) / prev)
    return returns


def pearson(xs, ys):
    """Pearson product-moment correlation coefficient."""
    n = len(xs)
    if n == 0:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return 0.0
    return cov / sqrt(var_x * var_y)


def main():
    if len(sys.argv) != 5:
        print("Usage: pearson_corr.py <a.json> <b.json> <start> <end>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data_a = json.load(f)
    with open(sys.argv[2]) as f:
        data_b = json.load(f)

    start = sys.argv[3]
    end = sys.argv[4]

    ret_a = monthly_returns(data_a["levels"], start, end)
    ret_b = monthly_returns(data_b["levels"], start, end)

    # Truncate to shorter length if date coverage differs
    n = min(len(ret_a), len(ret_b))
    ret_a = ret_a[:n]
    ret_b = ret_b[:n]

    r = pearson(ret_a, ret_b)
    print(round(r, 3))


if __name__ == "__main__":
    main()
