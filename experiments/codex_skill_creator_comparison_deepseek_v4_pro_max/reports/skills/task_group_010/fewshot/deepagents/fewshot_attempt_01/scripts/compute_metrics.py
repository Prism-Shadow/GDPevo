#!/usr/bin/env python3
"""Deterministic portfolio-risk calculations for Asteria Investment Office tasks.

Usage:
  echo '<two_arrays>' | python3 compute_metrics.py pearson
  python3 compute_metrics.py portfolio_stats < input.json

Pearson mode:
  Read a JSON array of two sub-arrays from stdin. Each sub-array contains
  [date_string, level] pairs. Compute monthly simple returns, then the Pearson
  correlation coefficient. Output {"correlation": <float>} rounded to 3 decimals.

Portfolio stats mode:
  Read a JSON object from stdin with keys:
    holdings: list of {instrument_id, quantity_usd_m}
    bonds:    list of bond records matching instrument_id
    issuers:  list of issuer records matching each bond's issuer_id
    trades (optional): list of {action: BUY|SELL, instrument_id, quantity_usd_m}
  Apply trades to holdings, then compute aggregate statistics.
  Output a JSON object with:
    total_market_value_usd_m (2 decimals)
    hy_allocation_pct (2 decimals)
    weighted_modified_duration_years (2 decimals)
    weighted_yield_to_maturity_pct (2 decimals)
    watchlist_exposure_usd_m (1 decimal)
"""

import json
import math
import sys


def simple_returns(levels):
    """Convert [date, level] pairs to list of simple returns."""
    values = [p[1] for p in levels]
    returns = []
    for i in range(1, len(values)):
        r = (values[i] - values[i-1]) / values[i-1]
        returns.append(round(r, 10))
    return returns


def pearson_correlation(xs, ys):
    """Compute Pearson r from two equal-length lists."""
    n = len(xs)
    if n < 2:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    std_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    std_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if std_x == 0 or std_y == 0:
        return None
    return cov / (std_x * std_y)


def cmd_pearson():
    """Read two level arrays from stdin and print Pearson r."""
    raw = sys.stdin.read().strip()
    if not raw:
        print(json.dumps({"error": "no input"}))
        sys.exit(1)
    data = json.loads(raw)
    if len(data) != 2:
        print(json.dumps({"error": "expected exactly 2 arrays"}))
        sys.exit(1)
    a_returns = simple_returns(data[0])
    b_returns = simple_returns(data[1])
    if len(a_returns) != len(b_returns):
        print(json.dumps({"error": "arrays produce different return counts"}))
        sys.exit(1)
    r = pearson_correlation(a_returns, b_returns)
    if r is None:
        print(json.dumps({"correlation": 0.0}))
    else:
        print(json.dumps({"correlation": round(r, 3)}))


def cmd_portfolio_stats():
    """Read holdings+bonds+issuers+trades and output portfolio statistics."""
    raw = sys.stdin.read().strip()
    if not raw:
        print(json.dumps({"error": "no input"}))
        sys.exit(1)
    inp = json.loads(raw)
    holdings = inp.get("holdings", [])
    bonds = {b["instrument_id"]: b for b in inp.get("bonds", [])}
    issuers = {i["issuer_id"]: i for i in inp.get("issuers", [])}
    trades = inp.get("trades", [])

    positions = {}
    for h in holdings:
        positions[h["instrument_id"]] = h["quantity_usd_m"]

    for t in trades:
        tid = t["instrument_id"]
        qty = t["quantity_usd_m"]
        old = positions.get(tid, 0.0)
        if t["action"] == "BUY":
            positions[tid] = old + qty
        elif t["action"] == "SELL":
            new_val = old - qty
            if new_val < 0:
                new_val = 0.0
            positions[tid] = new_val

    total_mv = 0.0
    weighted_dur_sum = 0.0
    weighted_ytm_sum = 0.0
    hy_mv = 0.0
    watchlist_mv = 0.0

    for inst_id, qty in positions.items():
        if qty <= 0:
            continue
        total_mv += qty
        bond = bonds.get(inst_id)
        if not bond:
            continue
        weighted_dur_sum += qty * bond.get("modified_duration_years", 0)
        weighted_ytm_sum += qty * bond.get("yield_to_maturity_pct", 0)
        if bond.get("rating_bucket") == "HY":
            hy_mv += qty
        issuer_id = bond.get("issuer_id", "")
        issuer = issuers.get(issuer_id)
        if issuer and issuer.get("watchlist"):
            watchlist_mv += qty

    dur = weighted_dur_sum / total_mv if total_mv > 0 else 0.0
    ytm = weighted_ytm_sum / total_mv if total_mv > 0 else 0.0
    hy_pct = (hy_mv / total_mv * 100) if total_mv > 0 else 0.0

    print(json.dumps({
        "total_market_value_usd_m": round(total_mv, 2),
        "hy_allocation_pct": round(hy_pct, 2),
        "weighted_modified_duration_years": round(dur, 2),
        "weighted_yield_to_maturity_pct": round(ytm, 2),
        "watchlist_exposure_usd_m": round(watchlist_mv, 1),
    }))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: compute_metrics.py pearson|portfolio_stats", file=sys.stderr)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "pearson":
        cmd_pearson()
    elif cmd == "portfolio_stats":
        cmd_portfolio_stats()
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
