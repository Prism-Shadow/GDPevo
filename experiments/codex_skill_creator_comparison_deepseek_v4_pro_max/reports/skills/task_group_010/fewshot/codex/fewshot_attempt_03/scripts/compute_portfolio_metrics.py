#!/usr/bin/env python3
"""Deterministic fixed-income portfolio metrics from holdings + bond master.

Usage:
  python3 compute_portfolio_metrics.py <holdings.json> <bonds.json> [<issuers.json>]

  holdings.json: {"holdings": [{"instrument_id":..., "quantity_usd_m":...},...]}
  bonds.json: array of bond objects (as from /api/instruments/bonds)
  issuers.json: optional array of issuer objects (for watchlist checks)

Output (stdout): JSON object with:
  - "total_market_value_usd_m": sum of quantities
  - "hy_allocation_pct": % of market value in HY-rated bonds
  - "weighted_modified_duration_years": quantity-weighted avg duration
  - "weighted_yield_to_maturity_pct": quantity-weighted avg YTM
  - "watchlist_exposure_usd_m": total quantity in watchlisted bonds
  - "issuer_exposures": {issuer_id: total_usd_m} for concentration checks
  - "subsector_exposures": {subsector: total_usd_m} for diversification checks
"""

import json
import sys


def main():
    if len(sys.argv) < 3:
        print("Usage: compute_portfolio_metrics.py <holdings.json> <bonds.json> [<issuers.json>]", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        holdings_data = json.load(f)
    with open(sys.argv[2]) as f:
        bonds = json.load(f)

    holdings = holdings_data.get("holdings", [])
    bond_map = {b["instrument_id"]: b for b in bonds}

    issuers = []
    if len(sys.argv) >= 4:
        with open(sys.argv[3]) as f:
            issuers = json.load(f)
    issuer_map = {i["issuer_id"]: i for i in issuers}

    # Watchlist set
    watchlist_ids = {i["issuer_id"] for i in issuers if i.get("watchlist")}

    total_mv = 0.0
    hy_mv = 0.0
    duration_weighted = 0.0
    ytm_weighted = 0.0
    watchlist_exposure = 0.0
    issuer_exposures: dict[str, float] = {}
    subsector_exposures: dict[str, float] = {}

    for h in holdings:
        iid = h["instrument_id"]
        qty = float(h["quantity_usd_m"])
        b = bond_map.get(iid)
        if b is None:
            print(f"Warning: bond {iid} not found in master", file=sys.stderr)
            continue

        total_mv += qty
        if b["rating_bucket"] == "HY":
            hy_mv += qty
        duration_weighted += qty * b["modified_duration_years"]
        ytm_weighted += qty * b["yield_to_maturity_pct"]

        iss_id = b["issuer_id"]
        issuer_exposures[iss_id] = issuer_exposures.get(iss_id, 0.0) + qty

        sub = b.get("subsector", "Other")
        subsector_exposures[sub] = subsector_exposures.get(sub, 0.0) + qty

        if iss_id in watchlist_ids:
            watchlist_exposure += qty

    result = {
        "total_market_value_usd_m": round(total_mv, 2),
        "hy_allocation_pct": round((hy_mv / total_mv * 100) if total_mv > 0 else 0.0, 2),
        "weighted_modified_duration_years": round((duration_weighted / total_mv) if total_mv > 0 else 0.0, 2),
        "weighted_yield_to_maturity_pct": round((ytm_weighted / total_mv) if total_mv > 0 else 0.0, 2),
        "watchlist_exposure_usd_m": round(watchlist_exposure, 1),
        "issuer_exposures": {k: round(v, 2) for k, v in issuer_exposures.items()},
        "subsector_exposures": {k: round(v, 2) for k, v in subsector_exposures.items()},
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
