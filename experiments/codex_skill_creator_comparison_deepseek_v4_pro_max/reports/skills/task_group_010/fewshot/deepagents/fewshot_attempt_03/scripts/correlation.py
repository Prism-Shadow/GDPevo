#!/usr/bin/env python3
"""Compute Pearson correlations of monthly simple returns from index level JSON.

Input: JSON object {"levels_a": [...], "levels_b": [...]} via stdin or file.
Each levels list is [{date, level}, ...] in chronological order.

Output: {"correlation": float_rounded_to_3_decimals, "return_observations": int}
"""
import json
import math
import sys


def monthly_returns(levels):
    """Return list of simple returns from consecutive levels."""
    rets = []
    for i in range(1, len(levels)):
        prev = levels[i - 1]["level"]
        curr = levels[i]["level"]
        rets.append((curr - prev) / prev)
    return rets


def pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = 0.0
    var_x = 0.0
    var_y = 0.0
    for i in range(n):
        dx = xs[i] - mean_x
        dy = ys[i] - mean_y
        cov += dx * dy
        var_x += dx * dx
        var_y += dy * dy
    if var_x == 0.0 or var_y == 0.0:
        return 0.0
    return cov / math.sqrt(var_x * var_y)


def main():
    data = json.load(sys.stdin)
    rets_a = monthly_returns(data["levels_a"])
    rets_b = monthly_returns(data["levels_b"])
    if len(rets_a) != len(rets_b):
        raise ValueError(f"Return series lengths differ: {len(rets_a)} vs {len(rets_b)}")
    corr = pearson(rets_a, rets_b)
    print(json.dumps({
        "correlation": round(corr, 3),
        "return_observations": len(rets_a),
    }))


if __name__ == "__main__":
    main()
