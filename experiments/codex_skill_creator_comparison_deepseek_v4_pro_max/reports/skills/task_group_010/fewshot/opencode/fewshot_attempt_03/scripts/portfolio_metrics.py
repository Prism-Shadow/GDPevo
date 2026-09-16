#!/usr/bin/env python3
"""Post-trade portfolio metrics for Asteria credit tasks.

Usage:
  python3 portfolio_metrics.py <holdings.json> <bonds.json> <issuers.json> <trades.json>

Where:
  holdings.json  = response from GET /api/portfolios/{id}/holdings
  bonds.json     = response from GET /api/instruments/bonds
  issuers.json   = response from GET /api/issuers
  trades.json    = array of proposed trades, each with action, instrument_id,
                   and quantity_usd_m or notional_usd_m

Output: JSON object with post_trade_metrics and constraint_check fields.
"""

import json
import sys


def load_json(path):
    with open(path) as f:
        return json.load(f)


def main():
    if len(sys.argv) != 5:
        print(
            "Usage: portfolio_metrics.py <holdings.json> <bonds.json>"
            " <issuers.json> <trades.json>",
            file=sys.stderr,
        )
        sys.exit(1)

    holdings_raw = load_json(sys.argv[1])
    bonds_raw = load_json(sys.argv[2])
    issuers_raw = load_json(sys.argv[3])
    trades = load_json(sys.argv[4])

    # Build lookup maps
    bonds = {b["instrument_id"]: b for b in bonds_raw}
    issuers = {i["issuer_id"]: i for i in issuers_raw}

    # Build current holdings map: instrument_id -> quantity
    current = {}
    for h in holdings_raw["holdings"]:
        current[h["instrument_id"]] = h["quantity_usd_m"]

    # Apply trades
    for t in trades:
        iid = t["instrument_id"]
        qty = t.get("quantity_usd_m", t.get("notional_usd_m", 0))
        if t["action"] == "BUY":
            current[iid] = current.get(iid, 0) + qty
        elif t["action"] == "SELL":
            current[iid] = current.get(iid, 0) - qty
            if current[iid] <= 0:
                del current[iid]

    # Compute metrics
    total_mv = sum(current.values())

    hy_mv = 0.0
    weighted_dur = 0.0
    weighted_ytm = 0.0

    for iid, qty in current.items():
        bond = bonds.get(iid, {})
        dur = bond.get("modified_duration_years", 0)
        ytm = bond.get("yield_to_maturity_pct", 0)

        if bond.get("rating_bucket") == "HY":
            hy_mv += qty
        weighted_dur += qty * dur
        weighted_ytm += qty * ytm

    hy_pct = (hy_mv / total_mv * 100) if total_mv > 0 else 0.0
    avg_dur = (weighted_dur / total_mv) if total_mv > 0 else 0.0
    avg_ytm = (weighted_ytm / total_mv) if total_mv > 0 else 0.0

    # Pre-trade HY
    pre_total = sum(
        h["quantity_usd_m"] for h in holdings_raw["holdings"]
    )
    pre_hy = sum(
        h["quantity_usd_m"]
        for h in holdings_raw["holdings"]
        if bonds.get(h["instrument_id"], {}).get("rating_bucket") == "HY"
    )
    pre_hy_pct = (pre_hy / pre_total * 100) if pre_total > 0 else 0.0

    # Watchlist exposure
    watchlist_mv = 0.0
    for iid, qty in current.items():
        bond = bonds.get(iid, {})
        issuer = issuers.get(bond.get("issuer_id", ""), {})
        if issuer.get("watchlist", False):
            watchlist_mv += qty

    result = {
        "post_trade_metrics": {
            "total_market_value_usd_m": round(total_mv, 2),
            "hy_allocation_pct": round(hy_pct, 2),
            "weighted_modified_duration_years": round(avg_dur, 2),
            "weighted_yield_to_maturity_pct": round(avg_ytm, 2),
            "hy_reduction_pct_points": round(pre_hy_pct - hy_pct, 2),
        },
        "post_trade_watchlist_exposure_usd_m": round(watchlist_mv, 1),
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
