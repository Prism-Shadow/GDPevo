#!/usr/bin/env python3
"""Calculation helpers for Asteria Investment Office JSON tasks."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
import urllib.request
from typing import Any


def fetch_json(base_url: str, path: str) -> Any:
    base = base_url.rstrip("/")
    with urllib.request.urlopen(f"{base}{path}", timeout=20) as response:
        return json.load(response)


def load_json_arg(value: str | None, file_path: str | None) -> Any:
    if file_path:
        with open(file_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    if value:
        return json.loads(value)
    return None


def simple_returns(level_rows: list[dict[str, Any]], start: str | None, end: str | None) -> list[float]:
    rows = sorted(level_rows, key=lambda row: row["date"])
    if start:
        rows = [row for row in rows if row["date"] >= start]
    if end:
        rows = [row for row in rows if row["date"] <= end]
    if len(rows) < 2:
        raise ValueError("at least two level observations are required")
    levels = [float(row["level"]) for row in rows]
    return [levels[i] / levels[i - 1] - 1.0 for i in range(1, len(levels))]


def pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys):
        raise ValueError("return vectors must have equal length")
    if len(xs) < 2:
        raise ValueError("at least two returns are required")
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    x_den = sum((x - x_mean) ** 2 for x in xs)
    y_den = sum((y - y_mean) ** 2 for y in ys)
    if x_den == 0 or y_den == 0:
        raise ValueError("cannot correlate a constant return vector")
    return numerator / math.sqrt(x_den * y_den)


def command_correlations(args: argparse.Namespace) -> dict[str, Any]:
    levels_by_id = fetch_json(args.base_url, "/api/index-levels")
    returns = {
        index_id: simple_returns(levels_by_id[index_id], args.start, args.end)
        for index_id in args.index
    }
    pairs = []
    for left, right in itertools.combinations(sorted(args.index), 2):
        corr = pearson(returns[left], returns[right])
        pairs.append({"pair_id": [left, right], "correlation": corr})
    rounded_pairs = [
        {"pair_id": pair["pair_id"], "correlation": round(pair["correlation"], args.precision)}
        for pair in pairs
    ]
    highest = max(pairs, key=lambda pair: pair["correlation"])
    lowest = min(pairs, key=lambda pair: pair["correlation"])
    return {
        "return_observations": len(next(iter(returns.values()))),
        "pairs": rounded_pairs,
        "highest_positive": {
            "pair_id": highest["pair_id"],
            "correlation": round(highest["correlation"], args.precision),
        },
        "lowest": {
            "pair_id": lowest["pair_id"],
            "correlation": round(lowest["correlation"], args.precision),
        },
    }


def map_view(score: float, thresholds: dict[str, Any]) -> str:
    if score >= float(thresholds["OW_min"]):
        return "OW"
    if score <= float(thresholds["UW_max"]):
        return "UW"
    return "N"


def map_conviction(score: float, thresholds: dict[str, Any]) -> str:
    absolute = abs(score)
    if absolute >= float(thresholds["HIGH_abs_min"]):
        return "HIGH"
    if absolute >= float(thresholds["MEDIUM_abs_min"]):
        return "MEDIUM"
    return "LOW"


def map_change(prior_view: str, current_view: str, rank: dict[str, int]) -> str:
    prior_rank = int(rank[prior_view])
    current_rank = int(rank[current_view])
    if current_rank > prior_rank:
        return "UP"
    if current_rank < prior_rank:
        return "DOWN"
    return "UNCHANGED"


def command_allocation(args: argparse.Namespace) -> dict[str, Any]:
    policies = fetch_json(args.base_url, "/api/policies")
    taxonomy = {
        row["opportunity_set"]: row
        for row in fetch_json(args.base_url, "/api/allocation/opportunity-sets")
    }
    prior = {
        row["opportunity_set"]: row
        for row in fetch_json(args.base_url, "/api/allocation/prior-views")
        if row["quarter"] == args.quarter
    }
    signals = {
        row["opportunity_set"]: row
        for row in fetch_json(args.base_url, "/api/macro-signals")
        if row["quarter"] == args.quarter
    }
    mapping = policies["allocation_mapping"]
    rows = []
    for name in args.opportunity_set:
        signal = signals[name]
        prior_view = prior[name]["view"]
        score = float(signal["score"])
        view = map_view(score, mapping["view_score_thresholds"])
        rows.append(
            {
                "opportunity_set": name,
                "asset_class": taxonomy[name]["asset_class"],
                "prior_view": prior_view,
                "signal_score": round(score, args.precision),
                "view": view,
                "change": map_change(prior_view, view, mapping["view_rank"]),
                "conviction": map_conviction(score, mapping["conviction_thresholds"]),
                "rationale_code": signal["rationale_code"],
            }
        )
    return {
        "as_of_date": policies.get("as_of_date"),
        "policy_id": policies.get("policy_id"),
        "quarter": args.quarter,
        "allocation_views": rows,
    }


def trade_quantity(trade: dict[str, Any]) -> float:
    for key in ("quantity_usd_m", "notional_usd_m"):
        if key in trade:
            return float(trade[key])
    raise KeyError("trade requires quantity_usd_m or notional_usd_m")


def command_credit_metrics(args: argparse.Namespace) -> dict[str, Any]:
    portfolio = fetch_json(args.base_url, f"/api/portfolios/{args.portfolio_id}")
    bonds = {
        row["instrument_id"]: row
        for row in fetch_json(args.base_url, "/api/instruments/bonds")
    }
    issuers = {
        row["issuer_id"]: row
        for row in fetch_json(args.base_url, "/api/issuers")
    }
    trades = load_json_arg(args.trades, args.trades_file) or []
    quantities = {
        holding["instrument_id"]: float(holding["quantity_usd_m"])
        for holding in portfolio["holdings"]
    }
    pre_total = sum(quantities.values())
    for trade in trades:
        instrument_id = trade["instrument_id"]
        action = trade["action"]
        quantity = trade_quantity(trade)
        quantities.setdefault(instrument_id, 0.0)
        if action == "BUY":
            quantities[instrument_id] += quantity
        elif action == "SELL":
            quantities[instrument_id] -= quantity
        else:
            raise ValueError(f"unsupported trade action: {action}")
        if quantities[instrument_id] < -1e-9:
            raise ValueError(f"negative post-trade quantity for {instrument_id}")
    quantities = {key: value for key, value in quantities.items() if abs(value) > 1e-9}
    post_total = sum(quantities.values())

    def weighted(field: str) -> float:
        return sum(quantity * float(bonds[instrument_id][field]) for instrument_id, quantity in quantities.items()) / post_total

    def hy_amount(qty_map: dict[str, float]) -> float:
        return sum(
            quantity
            for instrument_id, quantity in qty_map.items()
            if bonds[instrument_id]["rating_bucket"] == "HY"
        )

    pre_hy_pct = 100.0 * hy_amount({
        holding["instrument_id"]: float(holding["quantity_usd_m"])
        for holding in portfolio["holdings"]
    }) / pre_total
    post_hy_pct = 100.0 * hy_amount(quantities) / post_total
    watchlist_exposure = sum(
        quantity
        for instrument_id, quantity in quantities.items()
        if issuers[bonds[instrument_id]["issuer_id"]]["watchlist"]
    )
    return {
        "portfolio_id": args.portfolio_id,
        "as_of_date": portfolio.get("as_of_date"),
        "total_market_value_usd_m": round(post_total, args.precision),
        "hy_allocation_pct": round(post_hy_pct, args.precision),
        "weighted_modified_duration_years": round(weighted("modified_duration_years"), args.precision),
        "weighted_yield_to_maturity_pct": round(weighted("yield_to_maturity_pct"), args.precision),
        "hy_reduction_pct_points": round(pre_hy_pct - post_hy_pct, args.precision),
        "watchlist_exposure_usd_m": round(watchlist_exposure, args.precision),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    corr = subparsers.add_parser("correlations")
    corr.add_argument("--base-url", required=True)
    corr.add_argument("--index", nargs="+", required=True)
    corr.add_argument("--start")
    corr.add_argument("--end")
    corr.add_argument("--precision", type=int, default=3)
    corr.set_defaults(func=command_correlations)

    alloc = subparsers.add_parser("allocation")
    alloc.add_argument("--base-url", required=True)
    alloc.add_argument("--quarter", required=True)
    alloc.add_argument("--opportunity-set", nargs="+", required=True)
    alloc.add_argument("--precision", type=int, default=3)
    alloc.set_defaults(func=command_allocation)

    credit = subparsers.add_parser("credit-metrics")
    credit.add_argument("--base-url", required=True)
    credit.add_argument("--portfolio-id", required=True)
    credit.add_argument("--trades")
    credit.add_argument("--trades-file")
    credit.add_argument("--precision", type=int, default=2)
    credit.set_defaults(func=command_credit_metrics)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = args.func(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
