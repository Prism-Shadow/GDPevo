#!/usr/bin/env python3
"""Compute post-trade credit portfolio metrics from holdings and bond data.

Reads a holdings JSON array, bonds JSON array, and issuers JSON array from
command-line arguments. Computes:
  - total_market_value_usd_m (sum of all holdings quantity_usd_m)
  - hy_allocation_pct (HY-rated value / total value * 100)
  - weighted_modified_duration_years (market-value-weighted average duration)
  - weighted_yield_to_maturity_pct (market-value-weighted average YTM)

Also reports per-issuer concentrations, subsector counts, and watchlist exposure.

Usage:
  python3 compute_portfolio_metrics.py \
    --holdings-json '[{"instrument_id":"BND_X","quantity_usd_m":10},...]' \
    --bonds-json '[{"instrument_id":"BND_X","yield_to_maturity_pct":5.5,...},...]' \
    --issuers-json '[{"issuer_id":"ISS_X","watchlist":false,...},...]'
"""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(description="Compute post-trade portfolio metrics.")
    parser.add_argument("--holdings-json", required=True, help="JSON array of holdings")
    parser.add_argument("--bonds-json", required=True, help="JSON array of bond records")
    parser.add_argument("--issuers-json", required=True, help="JSON array of issuer records")
    args = parser.parse_args()

    try:
        holdings = json.loads(args.holdings_json)
        bonds = json.loads(args.bonds_json)
        issuers = json.loads(args.issuers_json)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}", file=sys.stderr)
        sys.exit(1)

    # Index bonds and issuers
    bond_map = {b["instrument_id"]: b for b in bonds}
    issuer_map = {i["issuer_id"]: i for i in issuers}

    total_mv = 0.0
    hy_mv = 0.0
    weighted_dur = 0.0
    weighted_ytm = 0.0
    issuer_mv = {}
    subsectors = set()
    watchlist_mv = 0.0

    for h in holdings:
        inst_id = h.get("instrument_id", "")
        qty = float(h.get("quantity_usd_m", 0))
        total_mv += qty

        bond = bond_map.get(inst_id)
        if bond is None:
            continue

        if bond.get("rating_bucket") == "HY":
            hy_mv += qty

        dur = float(bond.get("modified_duration_years", 0))
        ytm = float(bond.get("yield_to_maturity_pct", 0))
        weighted_dur += qty * dur
        weighted_ytm += qty * ytm

        iss_id = bond.get("issuer_id", "")
        issuer_mv[iss_id] = issuer_mv.get(iss_id, 0.0) + qty

        sub = bond.get("subsector", "")
        if sub:
            subsectors.add(sub)

        iss = issuer_map.get(iss_id)
        if iss and iss.get("watchlist"):
            watchlist_mv += qty

    hy_pct = (hy_mv / total_mv * 100.0) if total_mv > 0 else 0.0
    avg_dur = (weighted_dur / total_mv) if total_mv > 0 else 0.0
    avg_ytm = (weighted_ytm / total_mv) if total_mv > 0 else 0.0

    # Concentration
    max_issuer_pct = 0.0
    max_issuer_id = ""
    for iid, mv in issuer_mv.items():
        pct = (mv / total_mv * 100.0) if total_mv > 0 else 0.0
        if pct > max_issuer_pct:
            max_issuer_pct = pct
            max_issuer_id = iid

    out = {
        "total_market_value_usd_m": round(total_mv, 2),
        "hy_allocation_pct": round(hy_pct, 2),
        "weighted_modified_duration_years": round(avg_dur, 2),
        "weighted_yield_to_maturity_pct": round(avg_ytm, 2),
        "max_issuer_concentration_pct": round(max_issuer_pct, 2),
        "max_issuer_id": max_issuer_id,
        "subsector_count": len(subsectors),
        "watchlist_exposure_usd_m": round(watchlist_mv, 2),
    }

    print(json.dumps(out))


if __name__ == "__main__":
    main()
