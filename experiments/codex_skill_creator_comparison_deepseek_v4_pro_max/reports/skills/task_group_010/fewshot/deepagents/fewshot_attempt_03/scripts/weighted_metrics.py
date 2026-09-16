#!/usr/bin/env python3
"""Compute portfolio-level weighted-average metrics from holding-level data.

Input: JSON object via stdin with keys:
  "holdings": [{"quantity_usd_m": float, "instrument": {bond fields...}}, ...]

Output: JSON object with:
  total_market_value_usd_m, hy_allocation_pct, weighted_modified_duration_years,
  weighted_yield_to_maturity_pct

All output values rounded to 2 decimal places.
"""
import json
import sys


def compute(holdings):
    total_mv = 0.0
    hy_mv = 0.0
    dur_weighted = 0.0
    ytw_weighted = 0.0

    for h in holdings:
        qty = h["quantity_usd_m"]
        instr = h["instrument"]
        total_mv += qty
        if instr.get("rating_bucket") == "HY":
            hy_mv += qty
        dur_weighted += qty * instr["modified_duration_years"]
        ytw_weighted += qty * instr["yield_to_maturity_pct"]

    if total_mv == 0.0:
        return {
            "total_market_value_usd_m": 0.0,
            "hy_allocation_pct": 0.0,
            "weighted_modified_duration_years": 0.0,
            "weighted_yield_to_maturity_pct": 0.0,
        }

    return {
        "total_market_value_usd_m": round(total_mv, 2),
        "hy_allocation_pct": round((hy_mv / total_mv) * 100.0, 2),
        "weighted_modified_duration_years": round(dur_weighted / total_mv, 2),
        "weighted_yield_to_maturity_pct": round(ytw_weighted / total_mv, 2),
    }


def main():
    data = json.load(sys.stdin)
    result = compute(data["holdings"])
    print(json.dumps(result))


if __name__ == "__main__":
    main()
