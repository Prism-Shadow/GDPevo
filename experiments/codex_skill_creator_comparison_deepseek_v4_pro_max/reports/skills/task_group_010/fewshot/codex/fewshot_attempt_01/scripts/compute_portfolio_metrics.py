#!/usr/bin/env python3
"""
Portfolio-level HY allocation, weighted duration, and weighted YTM.

Usage:
  echo '{"holdings": [...], "bonds": [...]}' | python3 compute_portfolio_metrics.py

Input: JSON with "holdings" (array of {instrument_id, quantity_usd_m}) and
       "bonds" (array of {instrument_id, rating_bucket, modified_duration_years,
       yield_to_maturity_pct}).

Output: JSON {"total_market_value_usd_m": number, "hy_allocation_pct": number,
        "weighted_modified_duration_years": number, "weighted_yield_to_maturity_pct": number}
        rounded to 2 decimal places.
"""

import json
import sys


def compute_metrics(holdings, bonds):
    # Index bonds by instrument_id for fast lookup
    bond_map = {b["instrument_id"]: b for b in bonds}

    total_mv = 0.0
    hy_mv = 0.0
    duration_sum_product = 0.0
    ytm_sum_product = 0.0

    for h in holdings:
        qty = h["quantity_usd_m"]
        instr_id = h["instrument_id"]
        total_mv += qty
        bond = bond_map.get(instr_id)
        if bond is None:
            raise ValueError("Bond not found for instrument_id: %s" % instr_id)
        if bond["rating_bucket"] == "HY":
            hy_mv += qty
        duration_sum_product += qty * bond["modified_duration_years"]
        ytm_sum_product += qty * bond["yield_to_maturity_pct"]

    if total_mv == 0:
        raise ValueError("Total market value is zero.")

    return {
        "total_market_value_usd_m": round(total_mv, 2),
        "hy_allocation_pct": round((hy_mv / total_mv) * 100, 2),
        "weighted_modified_duration_years": round(duration_sum_product / total_mv, 2),
        "weighted_yield_to_maturity_pct": round(ytm_sum_product / total_mv, 2),
    }


def main():
    raw = sys.stdin.read()
    data = json.loads(raw)
    result = compute_metrics(data["holdings"], data["bonds"])
    print(json.dumps(result))


if __name__ == "__main__":
    main()
