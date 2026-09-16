#!/usr/bin/env python3
"""Compute Pearson correlation from two comma-separated monthly level series.

Each series represents consecutive monthly index levels. The script computes
monthly simple returns: (level_t / level_{t-1}) - 1, then Pearson r over the
paired return vectors. Output is a single number rounded to 3 decimal places.

Usage:
  python3 compute_correlation.py --levels-a "100,101,102" --levels-b "200,201,203"
"""

import argparse
import math
import sys


def parse_levels(raw: str):
    """Parse comma-separated level strings into float list."""
    return [float(x.strip()) for x in raw.split(",") if x.strip()]


def monthly_returns(levels):
    """Convert level series to monthly simple return series."""
    if len(levels) < 2:
        return []
    ret = []
    for i in range(1, len(levels)):
        ret.append((levels[i] / levels[i - 1]) - 1.0)
    return ret


def pearson_r(xs, ys):
    """Compute Pearson correlation coefficient for two equal-length lists."""
    n = len(xs)
    if n < 2:
        raise ValueError("need at least two observations")
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    std_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    std_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if std_x == 0.0 or std_y == 0.0:
        return 0.0
    return round(cov / (std_x * std_y), 3)


def main():
    parser = argparse.ArgumentParser(description="Pearson correlation from monthly index levels.")
    parser.add_argument("--levels-a", required=True, help="Comma-separated level series A")
    parser.add_argument("--levels-b", required=True, help="Comma-separated level series B")
    args = parser.parse_args()

    la = parse_levels(args.levels_a)
    lb = parse_levels(args.levels_b)

    if len(la) != len(lb):
        print(f"Error: series must have equal length, got {len(la)} vs {len(lb)}", file=sys.stderr)
        sys.exit(1)

    ra = monthly_returns(la)
    rb = monthly_returns(lb)

    if len(ra) < 2:
        print("Error: need at least 2 return observations (3 level points)", file=sys.stderr)
        sys.exit(1)

    r = pearson_r(ra, rb)
    print(r)


if __name__ == "__main__":
    main()
