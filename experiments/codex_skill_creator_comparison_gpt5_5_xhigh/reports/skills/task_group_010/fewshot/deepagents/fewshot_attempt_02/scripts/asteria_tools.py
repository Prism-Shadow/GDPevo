#!/usr/bin/env python3
"""Reusable helpers for Asteria environment-backed JSON tasks."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_BASE_URL = "http://task-env:9010"
VIEW_RANK = {"UW": -1, "N": 0, "OW": 1}


def fetch_json(path: str, base_url: str = DEFAULT_BASE_URL):
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"GET {url} failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"GET {url} failed: {exc.reason}") from exc


def as_map(rows, key):
    return {row[key]: row for row in rows}


def monthly_returns(level_rows):
    ordered = sorted(level_rows, key=lambda row: row["date"])
    return [
        ordered[i]["level"] / ordered[i - 1]["level"] - 1.0
        for i in range(1, len(ordered))
    ]


def pearson(xs, ys):
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("Pearson correlation requires aligned vectors of length >= 2")
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return math.nan
    return cov / math.sqrt(vx * vy)


def filter_window(level_rows, start=None, end=None):
    rows = sorted(level_rows, key=lambda row: row["date"])
    if start:
        rows = [row for row in rows if row["date"] >= start]
    if end:
        rows = [row for row in rows if row["date"] <= end]
    return rows


def view_from_score(score):
    if score >= 0.35:
        return "OW"
    if score <= -0.35:
        return "UW"
    return "N"


def conviction_from_score(score):
    magnitude = abs(score)
    if magnitude >= 0.70:
        return "HIGH"
    if magnitude >= 0.35:
        return "MEDIUM"
    return "LOW"


def change_from_prior(prior_view, current_view):
    delta = VIEW_RANK[current_view] - VIEW_RANK[prior_view]
    if delta > 0:
        return "UP"
    if delta < 0:
        return "DOWN"
    return "UNCHANGED"


def load_trades(value):
    stripped = value.lstrip()
    if stripped.startswith("[") or stripped.startswith("{"):
        return json.loads(value)
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text())
    return json.loads(value)


def cmd_correlations(args):
    raw_levels = fetch_json("/api/index-levels", args.base_url)
    selected = {}
    for index_id in args.indices:
        if index_id not in raw_levels:
            raise SystemExit(f"Missing index levels for {index_id}")
        rows = filter_window(raw_levels[index_id], args.start, args.end)
        selected[index_id] = {
            "level_start_date": rows[0]["date"],
            "level_end_date": rows[-1]["date"],
            "return_observations": len(rows) - 1,
            "returns": monthly_returns(rows),
        }

    pairs = []
    for left, right in itertools.combinations(sorted(args.indices), 2):
        correlation = pearson(selected[left]["returns"], selected[right]["returns"])
        pairs.append(
            {
                "pair_id": [left, right],
                "correlation": round(correlation, args.precision),
            }
        )

    output = {
        "index_set": sorted(args.indices),
        "review_window": {
            "level_start_date": min(v["level_start_date"] for v in selected.values()),
            "level_end_date": max(v["level_end_date"] for v in selected.values()),
            "return_observations": min(
                v["return_observations"] for v in selected.values()
            ),
        },
        "pairs": sorted(pairs, key=lambda row: row["pair_id"]),
    }
    if pairs:
        output["highest_positive"] = max(pairs, key=lambda row: row["correlation"])
        output["lowest"] = min(pairs, key=lambda row: row["correlation"])
    print(json.dumps(output, indent=2, sort_keys=False))


def cmd_allocation(args):
    opportunity_sets = as_map(
        fetch_json("/api/allocation/opportunity-sets", args.base_url), "opportunity_set"
    )
    prior_rows = fetch_json("/api/allocation/prior-views", args.base_url)
    signal_rows = fetch_json("/api/macro-signals", args.base_url)
    prior = {
        row["opportunity_set"]: row
        for row in prior_rows
        if row.get("quarter") == args.quarter
        and (args.prior_quarter is None or row.get("previous_quarter") == args.prior_quarter)
    }
    signals = {
        row["opportunity_set"]: row
        for row in signal_rows
        if row.get("quarter") == args.quarter
    }

    rows = []
    for opportunity_set in args.sets:
        if opportunity_set not in opportunity_sets:
            raise SystemExit(f"Missing opportunity set: {opportunity_set}")
        if opportunity_set not in prior:
            raise SystemExit(f"Missing prior view: {opportunity_set}")
        if opportunity_set not in signals:
            raise SystemExit(f"Missing macro signal: {opportunity_set}")
        score = signals[opportunity_set]["score"]
        current_view = view_from_score(score)
        prior_view = prior[opportunity_set]["view"]
        rows.append(
            {
                "opportunity_set": opportunity_set,
                "asset_class": opportunity_sets[opportunity_set]["asset_class"],
                "prior_view": prior_view,
                "signal_score": round(score, args.precision),
                "view": current_view,
                "change": change_from_prior(prior_view, current_view),
                "conviction": conviction_from_score(score),
                "rationale_code": signals[opportunity_set]["rationale_code"],
            }
        )
    print(json.dumps(rows, indent=2, sort_keys=False))


def cmd_fi_metrics(args):
    holdings_payload = fetch_json(
        f"/api/portfolios/{args.portfolio}/holdings", args.base_url
    )
    bonds = as_map(fetch_json("/api/instruments/bonds", args.base_url), "instrument_id")
    issuers = as_map(fetch_json("/api/issuers", args.base_url), "issuer_id")
    quantities = {
        row["instrument_id"]: float(row["quantity_usd_m"])
        for row in holdings_payload["holdings"]
    }
    pre_total = sum(quantities.values())

    def hy_quantity(qtys):
        return sum(
            qty
            for instrument_id, qty in qtys.items()
            if qty > 0 and bonds[instrument_id]["rating_bucket"] == "HY"
        )

    pre_hy_pct = hy_quantity(quantities) / pre_total * 100 if pre_total else 0.0

    for trade in load_trades(args.trades):
        instrument_id = trade["instrument_id"]
        if instrument_id not in bonds:
            raise SystemExit(f"Missing bond security master row: {instrument_id}")
        qty = float(trade.get("quantity_usd_m", trade.get("notional_usd_m")))
        action = trade["action"].upper()
        if action == "BUY":
            quantities[instrument_id] = quantities.get(instrument_id, 0.0) + qty
        elif action == "SELL":
            quantities[instrument_id] = quantities.get(instrument_id, 0.0) - qty
        else:
            raise SystemExit(f"Unsupported FI action: {action}")

    quantities = {k: v for k, v in quantities.items() if abs(v) > 1e-9}
    total = sum(quantities.values())

    def weighted(field):
        return sum(quantities[i] * bonds[i][field] for i in quantities) / total

    watchlist_exposure = 0.0
    for instrument_id, qty in quantities.items():
        issuer = issuers[bonds[instrument_id]["issuer_id"]]
        if issuer.get("watchlist"):
            watchlist_exposure += qty

    output = {
        "portfolio_id": args.portfolio,
        "as_of_date": holdings_payload["as_of_date"],
        "total_market_value_usd_m": round(total, 2),
        "hy_allocation_pct": round(hy_quantity(quantities) / total * 100, 2),
        "weighted_modified_duration_years": round(
            weighted("modified_duration_years"), 2
        ),
        "weighted_yield_to_maturity_pct": round(
            weighted("yield_to_maturity_pct"), 2
        ),
        "hy_reduction_pct_points": round(
            pre_hy_pct - hy_quantity(quantities) / total * 100, 2
        ),
        "watchlist_exposure_usd_m": round(watchlist_exposure, 1),
    }
    print(json.dumps(output, indent=2, sort_keys=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    subparsers = parser.add_subparsers(dest="command", required=True)

    correlations = subparsers.add_parser("correlations")
    correlations.add_argument("--indices", nargs="+", required=True)
    correlations.add_argument("--start")
    correlations.add_argument("--end")
    correlations.add_argument("--precision", type=int, default=3)
    correlations.set_defaults(func=cmd_correlations)

    allocation = subparsers.add_parser("allocation")
    allocation.add_argument("--quarter", required=True)
    allocation.add_argument("--prior-quarter")
    allocation.add_argument("--sets", nargs="+", required=True)
    allocation.add_argument("--precision", type=int, default=3)
    allocation.set_defaults(func=cmd_allocation)

    fi_metrics = subparsers.add_parser("fi-metrics")
    fi_metrics.add_argument("--portfolio", required=True)
    fi_metrics.add_argument("--trades", required=True)
    fi_metrics.set_defaults(func=cmd_fi_metrics)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(1)
