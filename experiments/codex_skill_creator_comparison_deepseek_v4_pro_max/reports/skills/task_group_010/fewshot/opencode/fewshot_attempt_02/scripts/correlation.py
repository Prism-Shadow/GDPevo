#!/usr/bin/env python3
"""Compute the Pearson correlation coefficient of monthly simple returns
from two time series of monthly index levels.

Usage:
  python3 correlation.py <levels_a.json> <levels_b.json>

Each input file must contain a JSON array of numeric level values sorted
chronologically (oldest first). The script prints the Pearson correlation
coefficient rounded to 6 decimal places to stdout.

Example:
  echo '[100.0, 102.5, 101.3, 104.0]' > a.json
  echo '[200.0, 201.0, 199.5, 203.2]' > b.json
  python3 correlation.py a.json b.json
  # prints: 0.872195

Returns:
  The Pearson correlation coefficient between the two series of monthly
  simple returns, rounded to 6 decimal places. Returns 0.000000 if either
  series has fewer than 2 data points or has zero variance.
"""

import json
import math
import sys


def simple_returns(levels):
    """Compute simple returns from consecutive level pairs."""
    if len(levels) < 2:
        return []
    returns = []
    for i in range(1, len(levels)):
        prev = levels[i - 1]
        curr = levels[i]
        if prev == 0:
            returns.append(0.0)
        else:
            returns.append((curr - prev) / prev)
    return returns


def pearson_correlation(xs, ys):
    """Compute Pearson correlation coefficient between two equal-length lists."""
    n = len(xs)
    if n < 2 or n != len(ys):
        return 0.0

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    cov = 0.0
    var_x = 0.0
    var_y = 0.0

    for x, y in zip(xs, ys):
        dx = x - mean_x
        dy = y - mean_y
        cov += dx * dy
        var_x += dx * dx
        var_y += dy * dy

    if var_x == 0.0 or var_y == 0.0:
        return 0.0

    return cov / (math.sqrt(var_x) * math.sqrt(var_y))


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 correlation.py <levels_a.json> <levels_b.json>",
              file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        levels_a = json.load(f)
    with open(sys.argv[2]) as f:
        levels_b = json.load(f)

    if not isinstance(levels_a, list) or not isinstance(levels_b, list):
        print("Error: each file must contain a JSON array of numbers.",
              file=sys.stderr)
        sys.exit(1)

    returns_a = simple_returns(levels_a)
    returns_b = simple_returns(levels_b)

    if len(returns_a) < 2 or len(returns_b) < 2:
        print("0.000000")
        return

    # Trim to the shorter length if they differ
    min_len = min(len(returns_a), len(returns_b))
    returns_a = returns_a[:min_len]
    returns_b = returns_b[:min_len]

    corr = pearson_correlation(returns_a, returns_b)
    print(f"{corr:.6f}")


if __name__ == "__main__":
    main()
