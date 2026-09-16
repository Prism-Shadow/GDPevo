#!/usr/bin/env python3
"""
Pearson correlation from two series of index levels.

Usage:
  echo '{"series_a": [{"date": "...", "level": N}, ...], "series_b": [...]}' \
    | python3 compute_correlation.py

Input: JSON with "series_a" and "series_b", each an array of {date, level}
       objects sorted ascending by date. Both series must have the same length
       and matching dates.

Output: JSON {"correlation": number, "observations": integer} rounded to 3 decimal places.
"""

import json
import math
import sys


def monthly_simple_returns(levels):
    """Convert sorted levels to monthly simple returns: (L_t / L_{t-1}) - 1."""
    values = [entry["level"] for entry in levels]
    returns = []
    for i in range(1, len(values)):
        if values[i - 1] == 0:
            raise ValueError("Zero level at index %d; cannot compute return." % (i - 1))
        returns.append((values[i] / values[i - 1]) - 1.0)
    return returns


def pearson_correlation(x, y):
    """Sample Pearson correlation of two aligned return series."""
    n = len(x)
    if n != len(y):
        raise ValueError("Series must have equal length.")
    if n < 2:
        raise ValueError("Need at least 2 observations for correlation.")
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / (n - 1)
    std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / (n - 1))
    std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / (n - 1))
    if std_x == 0 or std_y == 0:
        raise ValueError("Variance is zero; correlation is undefined.")
    return cov / (std_x * std_y)


def main():
    raw = sys.stdin.read()
    data = json.loads(raw)
    levels_a = data["series_a"]
    levels_b = data["series_b"]
    if len(levels_a) != len(levels_b):
        raise ValueError(
            "Series length mismatch: %d vs %d" % (len(levels_a), len(levels_b))
        )
    returns_a = monthly_simple_returns(levels_a)
    returns_b = monthly_simple_returns(levels_b)
    corr = pearson_correlation(returns_a, returns_b)
    result = {
        "correlation": round(corr, 3),
        "observations": len(returns_a),
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
