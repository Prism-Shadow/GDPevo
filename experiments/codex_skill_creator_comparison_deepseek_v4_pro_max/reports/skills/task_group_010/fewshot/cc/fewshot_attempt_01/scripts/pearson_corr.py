#!/usr/bin/env python3
"""Compute Pearson correlation from two series of index levels.

Reads two lines from stdin, each a JSON array of numeric index levels
in chronological order. Outputs the Pearson correlation coefficient
rounded to three decimal places.

Usage:
    echo '[100, 102, 105, ...]' $'\n' '[95, 98, 100, ...]' | python3 pearson_corr.py
"""

import json
import math
import sys


def monthly_simple_returns(levels):
    """Return series of (L[t] / L[t-1]) - 1 for consecutive level pairs."""
    if len(levels) < 2:
        raise ValueError(f"Need at least 2 levels, got {len(levels)}")
    return [(levels[i] / levels[i-1]) - 1.0 for i in range(1, len(levels))]


def pearson_r(xs, ys):
    """Compute Pearson correlation coefficient."""
    n = len(xs)
    if n != len(ys):
        raise ValueError(f"Series lengths differ: {n} vs {len(ys)}")
    if n < 2:
        raise ValueError(f"Need at least 2 return observations, got {n}")

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    cov = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n)) / (n - 1)

    std_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs) / (n - 1))
    std_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys) / (n - 1))

    if std_x == 0.0 or std_y == 0.0:
        return 0.0

    return cov / (std_x * std_y)


def main():
    lines = sys.stdin.read().strip().splitlines()
    if len(lines) < 2:
        print("Error: expected two lines of JSON arrays on stdin", file=sys.stderr)
        sys.exit(1)

    levels_a = json.loads(lines[0])
    levels_b = json.loads(lines[1])

    returns_a = monthly_simple_returns(levels_a)
    returns_b = monthly_simple_returns(levels_b)

    r = pearson_r(returns_a, returns_b)
    print(f"{r:.3f}")


if __name__ == "__main__":
    main()
