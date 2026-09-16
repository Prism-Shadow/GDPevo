#!/usr/bin/env python3
"""Reusable Asteria environment helpers for JSON portfolio tasks."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://task-env:9010/"


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/"


def fetch_json(base_url: str, path: str) -> Any:
    if not path.startswith("/"):
        path = "/" + path
    if "judge" in path.lower():
        raise SystemExit("Refusing to call judge endpoints.")
    url = normalize_base_url(base_url) + path.lstrip("/")
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            return json.load(response)
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed to fetch {url}: {exc}") from exc


def dump_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=False))


def read_json_file(path: str) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def round_number(value: float, precision: int) -> float:
    return round(float(value), precision)


def by_key(records: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {record[key]: record for record in records}


def common_level_dates(level_sets: dict[str, list[dict[str, Any]]], start: str | None, end: str | None) -> list[str]:
    common: set[str] | None = None
    for levels in level_sets.values():
        dates = {row["date"] for row in levels}
        common = dates if common is None else common & dates
    if not common:
        raise SystemExit("No common level dates across requested indices.")
    dates = sorted(common)
    if start:
        dates = [date for date in dates if date >= start]
    if end:
        dates = [date for date in dates if date <= end]
    if len(dates) < 2:
        raise SystemExit("Need at least two common level dates to compute returns.")
    return dates


def returns_for_dates(levels: list[dict[str, Any]], dates: list[str]) -> list[float]:
    level_by_date = {row["date"]: float(row["level"]) for row in levels}
    return [
        level_by_date[dates[index]] / level_by_date[dates[index - 1]] - 1.0
        for index in range(1, len(dates))
    ]


def pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys):
        raise ValueError("Series lengths differ.")
    if len(xs) < 2:
        raise ValueError("At least two observations are required.")
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denom_x = sum((x - mean_x) ** 2 for x in xs)
    denom_y = sum((y - mean_y) ** 2 for y in ys)
    denominator = math.sqrt(denom_x * denom_y)
    if denominator == 0:
        raise ValueError("Cannot correlate a zero-variance series.")
    return numerator / denominator


def command_correlations(args: argparse.Namespace) -> None:
    all_levels = fetch_json(args.base_url, "/api/index-levels")
    index_ids = sorted(dict.fromkeys(args.index_ids))
    missing = [index_id for index_id in index_ids if index_id not in all_levels]
    if missing:
        raise SystemExit(f"Missing index levels for: {', '.join(missing)}")

    level_sets = {index_id: all_levels[index_id] for index_id in index_ids}
    dates = common_level_dates(level_sets, args.start, args.end)
    return_sets = {
        index_id: returns_for_dates(level_sets[index_id], dates)
        for index_id in index_ids
    }

    pairs = []
    for left, right in itertools.combinations(index_ids, 2):
        corr = pearson(return_sets[left], return_sets[right])
        pairs.append({
            "pair_id": [left, right],
            "correlation": round_number(corr, args.precision),
        })

    highest = max(pairs, key=lambda row: row["correlation"]) if pairs else None
    lowest = min(pairs, key=lambda row: row["correlation"]) if pairs else None
    dump_json({
        "review_window": {
            "level_start_date": dates[0],
            "level_end_date": dates[-1],
            "return_observations": len(dates) - 1,
        },
        "index_set": index_ids,
        "highest_positive": highest,
        "lowest": lowest,
        "pairs": sorted(pairs, key=lambda row: (row["correlation"], row["pair_id"])),
    })


def view_from_score(score: float, thresholds: dict[str, Any]) -> str:
    if score >= float(thresholds["OW_min"]):
        return "OW"
    if score <= float(thresholds["UW_max"]):
        return "UW"
    return "N"


def conviction_from_score(score: float, thresholds: dict[str, Any]) -> str:
    magnitude = abs(score)
    if magnitude >= float(thresholds["HIGH_abs_min"]):
        return "HIGH"
    if magnitude >= float(thresholds["MEDIUM_abs_min"]):
        return "MEDIUM"
    return "LOW"


def change_from_views(prior_view: str, current_view: str, rank: dict[str, int]) -> str:
    prior_rank = int(rank[prior_view])
    current_rank = int(rank[current_view])
    if current_rank > prior_rank:
        return "UP"
    if current_rank < prior_rank:
        return "DOWN"
    return "UNCHANGED"


def command_allocation(args: argparse.Namespace) -> None:
    policies = fetch_json(args.base_url, "/api/policies")
    taxonomy = by_key(fetch_json(args.base_url, "/api/allocation/opportunity-sets"), "opportunity_set")
    prior_views = fetch_json(args.base_url, "/api/allocation/prior-views")
    macro_signals = fetch_json(args.base_url, "/api/macro-signals")

    mapping = policies["allocation_mapping"]
    score_thresholds = mapping["view_score_thresholds"]
    conviction_thresholds = mapping["conviction_thresholds"]
    rank = mapping["view_rank"]

    prior_by_set = {
        row["opportunity_set"]: row
        for row in prior_views
        if row["quarter"] == args.quarter
    }
    signal_by_set = {
        row["opportunity_set"]: row
        for row in macro_signals
        if row["quarter"] == args.quarter
    }

    rows = []
    missing = []
    for opportunity_set in args.sets:
        prior = prior_by_set.get(opportunity_set)
        signal = signal_by_set.get(opportunity_set)
        meta = taxonomy.get(opportunity_set)
        if not prior or not signal or not meta:
            missing.append(opportunity_set)
            continue
        score = float(signal["score"])
        view = view_from_score(score, score_thresholds)
        rows.append({
            "opportunity_set": opportunity_set,
            "asset_class": meta["asset_class"],
            "prior_view": prior["view"],
            "signal_score": round_number(score, args.precision),
            "view": view,
            "change": change_from_views(prior["view"], view, rank),
            "conviction": conviction_from_score(score, conviction_thresholds),
            "rationale_code": signal["rationale_code"],
        })

    result: dict[str, Any] = {
        "policy_id": policies.get("policy_id"),
        "target_quarter": args.quarter,
        "allocation_views": rows,
    }
    prior_quarters = sorted({prior_by_set[row["opportunity_set"]]["previous_quarter"] for row in rows})
    if len(prior_quarters) == 1:
        result["prior_quarter"] = prior_quarters[0]
    if missing:
        result["missing_opportunity_sets"] = missing
    dump_json(result)


def load_trades(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    payload = read_json_file(path)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if "trades" in payload:
            return payload["trades"]
        if "trade_package" in payload:
            return payload["trade_package"]
        if isinstance(payload.get("rotation"), dict) and "trades" in payload["rotation"]:
            return payload["rotation"]["trades"]
    raise SystemExit("Trades file must be a list or contain trades, trade_package, or rotation.trades.")


def quantity_from_trade(trade: dict[str, Any]) -> float:
    if "quantity_usd_m" in trade:
        return float(trade["quantity_usd_m"])
    if "notional_usd_m" in trade:
        return float(trade["notional_usd_m"])
    raise SystemExit(f"Trade is missing quantity_usd_m or notional_usd_m: {trade}")


def policy_for_portfolio(portfolio: dict[str, Any], policies: dict[str, Any]) -> dict[str, Any]:
    if "constraints" in portfolio:
        return portfolio["constraints"]
    policy_id = portfolio.get("constraint_policy_id")
    candidates = [
        policies.get("credit_default", {}),
        policies.get("credit_risk_reduction", {}),
        policies.get("correlation", {}),
        policies.get("multi_asset", {}),
        policies.get("multi_asset_risk", {}),
    ]
    for policy in candidates:
        if policy.get("policy_id") == policy_id:
            return policy
    return {}


def joined_positions(
    positions: dict[str, float],
    bond_by_id: dict[str, dict[str, Any]],
    issuer_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for instrument_id, quantity in sorted(positions.items()):
        if abs(quantity) < 1e-9:
            continue
        bond = bond_by_id.get(instrument_id, {})
        issuer = issuer_by_id.get(bond.get("issuer_id"), {})
        rows.append({
            "instrument_id": instrument_id,
            "quantity_usd_m": quantity,
            "rating_bucket": bond.get("rating_bucket"),
            "issuer_id": bond.get("issuer_id"),
            "issuer_watchlist": bool(issuer.get("watchlist", False)),
            "sector": bond.get("sector"),
            "subsector": bond.get("subsector"),
            "modified_duration_years": bond.get("modified_duration_years"),
            "yield_to_maturity_pct": bond.get("yield_to_maturity_pct"),
        })
    return rows


def portfolio_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = sum(float(row["quantity_usd_m"]) for row in rows)
    if total <= 0:
        return {
            "total_market_value_usd_m": total,
            "hy_allocation_pct": None,
            "weighted_modified_duration_years": None,
            "weighted_yield_to_maturity_pct": None,
            "watchlist_exposure_usd_m": None,
        }

    hy_quantity = sum(
        float(row["quantity_usd_m"])
        for row in rows
        if row.get("rating_bucket") == "HY"
    )
    duration_numerator = sum(
        float(row["quantity_usd_m"]) * float(row["modified_duration_years"])
        for row in rows
        if row.get("modified_duration_years") is not None
    )
    yield_numerator = sum(
        float(row["quantity_usd_m"]) * float(row["yield_to_maturity_pct"])
        for row in rows
        if row.get("yield_to_maturity_pct") is not None
    )
    watchlist = sum(
        float(row["quantity_usd_m"])
        for row in rows
        if row.get("issuer_watchlist")
    )
    return {
        "total_market_value_usd_m": total,
        "hy_allocation_pct": hy_quantity / total * 100.0,
        "weighted_modified_duration_years": duration_numerator / total,
        "weighted_yield_to_maturity_pct": yield_numerator / total,
        "watchlist_exposure_usd_m": watchlist,
    }


def apply_trades(holdings: list[dict[str, Any]], trades: list[dict[str, Any]]) -> tuple[dict[str, float], list[str]]:
    positions = {
        holding["instrument_id"]: float(holding["quantity_usd_m"])
        for holding in holdings
    }
    warnings = []
    for trade in trades:
        action = trade["action"]
        instrument_id = trade["instrument_id"]
        quantity = quantity_from_trade(trade)
        positions.setdefault(instrument_id, 0.0)
        if action == "BUY":
            positions[instrument_id] += quantity
        elif action == "SELL":
            positions[instrument_id] -= quantity
        elif action in {"HOLD", "NO_TRADE"}:
            continue
        else:
            warnings.append(f"Unsupported action {action} for {instrument_id}.")
        if positions[instrument_id] < -1e-9:
            warnings.append(f"Trade leaves negative position in {instrument_id}.")
    return positions, warnings


def round_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    precision = {
        "total_market_value_usd_m": 2,
        "hy_allocation_pct": 2,
        "weighted_modified_duration_years": 2,
        "weighted_yield_to_maturity_pct": 2,
        "watchlist_exposure_usd_m": 1,
        "hy_reduction_pct_points": 2,
    }
    output = {}
    for key, value in metrics.items():
        output[key] = None if value is None else round_number(value, precision.get(key, 3))
    return output


def command_credit_metrics(args: argparse.Namespace) -> None:
    portfolio = fetch_json(args.base_url, f"/api/portfolios/{args.portfolio_id}")
    holdings_payload = fetch_json(args.base_url, f"/api/portfolios/{args.portfolio_id}/holdings")
    bonds = fetch_json(args.base_url, "/api/instruments/bonds")
    issuers = fetch_json(args.base_url, "/api/issuers")
    policies = fetch_json(args.base_url, "/api/policies")
    trades = load_trades(args.trades_file)

    bond_by_id = by_key(bonds, "instrument_id")
    issuer_by_id = by_key(issuers, "issuer_id")
    holdings = holdings_payload["holdings"]

    pre_positions = {
        holding["instrument_id"]: float(holding["quantity_usd_m"])
        for holding in holdings
    }
    post_positions, warnings = apply_trades(holdings, trades)
    pre_rows = joined_positions(pre_positions, bond_by_id, issuer_by_id)
    post_rows = joined_positions(post_positions, bond_by_id, issuer_by_id)
    pre = portfolio_metrics(pre_rows)
    post = portfolio_metrics(post_rows)
    hy_reduction = None
    if pre["hy_allocation_pct"] is not None and post["hy_allocation_pct"] is not None:
        hy_reduction = pre["hy_allocation_pct"] - post["hy_allocation_pct"]

    policy = policy_for_portfolio(portfolio, policies)
    duration_band = policy.get("duration_band_years")
    max_hy = policy.get("max_hy_allocation_pct")
    target_hy_reduction = policy.get("target_hy_reduction_pct", 0.0)

    buy_trades = [trade for trade in trades if trade.get("action") == "BUY"]
    sell_trades = [trade for trade in trades if trade.get("action") == "SELL"]
    buy_issuer_ids = []
    buy_subsectors = []
    buy_watchlist_flags = []
    for trade in buy_trades:
        bond = bond_by_id.get(trade["instrument_id"], {})
        issuer = issuer_by_id.get(bond.get("issuer_id"), {})
        buy_issuer_ids.append(bond.get("issuer_id"))
        buy_subsectors.append(bond.get("subsector"))
        buy_watchlist_flags.append(bool(issuer.get("watchlist", False)))

    watchlist_sell_ids = []
    for trade in sell_trades:
        bond = bond_by_id.get(trade["instrument_id"], {})
        issuer = issuer_by_id.get(bond.get("issuer_id"), {})
        if issuer.get("watchlist", False):
            watchlist_sell_ids.append(trade["instrument_id"])

    flags = {
        "hy_cap_pass": None if max_hy is None or post["hy_allocation_pct"] is None else post["hy_allocation_pct"] <= float(max_hy),
        "duration_band_pass": None if not duration_band or post["weighted_modified_duration_years"] is None else float(duration_band[0]) <= post["weighted_modified_duration_years"] <= float(duration_band[1]),
        "target_hy_reduction_met": None if hy_reduction is None else hy_reduction >= float(target_hy_reduction),
        "watchlist_exposure_cleared": None if post["watchlist_exposure_usd_m"] is None else abs(post["watchlist_exposure_usd_m"]) < 1e-9,
        "buys_avoid_watchlist": not any(buy_watchlist_flags),
        "selected_issuer_diversification_pass": len([issuer for issuer in buy_issuer_ids if issuer]) == len(set(issuer for issuer in buy_issuer_ids if issuer)),
        "selected_subsector_diversification_pass": len(set(sub for sub in buy_subsectors if sub)) >= min(len(buy_trades), int(policy.get("subsector_min_count_for_diversified", 1))),
    }

    result = {
        "portfolio_id": args.portfolio_id,
        "as_of_date": portfolio.get("as_of_date") or holdings_payload.get("as_of_date"),
        "policy": policy,
        "pre_trade_metrics": round_metrics(pre),
        "post_trade_metrics": round_metrics({
            **post,
            "hy_reduction_pct_points": hy_reduction,
        }),
        "constraint_checks": flags,
        "watchlist_sell_ids": sorted(watchlist_sell_ids),
        "post_trade_positions": post_rows,
        "warnings": warnings,
    }
    dump_json(result)


def command_bond_candidates(args: argparse.Namespace) -> None:
    bonds = fetch_json(args.base_url, "/api/instruments/bonds")
    issuers = fetch_json(args.base_url, "/api/issuers")
    issuer_by_id = by_key(issuers, "issuer_id")
    rows = []
    for bond in bonds:
        issuer = issuer_by_id.get(bond["issuer_id"], {})
        if args.candidate_only and not bond.get("candidate", False):
            continue
        if args.energy_linked and not bond.get("energy_linked", False):
            continue
        if args.avoid_watchlist and issuer.get("watchlist", False):
            continue
        if args.rating_bucket and bond.get("rating_bucket") != args.rating_bucket:
            continue
        if args.min_duration is not None and float(bond["modified_duration_years"]) < args.min_duration:
            continue
        if args.max_duration is not None and float(bond["modified_duration_years"]) > args.max_duration:
            continue
        rows.append({
            "instrument_id": bond["instrument_id"],
            "issuer_id": bond["issuer_id"],
            "issuer_watchlist": bool(issuer.get("watchlist", False)),
            "sector": bond.get("sector"),
            "subsector": bond.get("subsector"),
            "rating_bucket": bond.get("rating_bucket"),
            "energy_linked": bond.get("energy_linked"),
            "candidate": bond.get("candidate"),
            "modified_duration_years": bond.get("modified_duration_years"),
            "yield_to_maturity_pct": bond.get("yield_to_maturity_pct"),
            "recommended_theme_tags": bond.get("recommended_theme_tags", []),
        })
    rows.sort(key=lambda row: (-float(row["yield_to_maturity_pct"]), row["instrument_id"]))
    dump_json(rows)


def command_fetch(args: argparse.Namespace) -> None:
    dump_json(fetch_json(args.base_url, args.path))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Asteria environment helper commands.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Asteria environment base URL.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch one allowed GET path as JSON.")
    fetch_parser.add_argument("path")
    fetch_parser.set_defaults(func=command_fetch)

    corr_parser = subparsers.add_parser("correlations", help="Compute pairwise Pearson correlations from index levels.")
    corr_parser.add_argument("--index-ids", nargs="+", required=True)
    corr_parser.add_argument("--start")
    corr_parser.add_argument("--end")
    corr_parser.add_argument("--precision", type=int, default=3)
    corr_parser.set_defaults(func=command_correlations)

    alloc_parser = subparsers.add_parser("allocation", help="Derive allocation views from prior views, macro signals, and policy thresholds.")
    alloc_parser.add_argument("--quarter", required=True)
    alloc_parser.add_argument("--sets", nargs="+", required=True)
    alloc_parser.add_argument("--precision", type=int, default=3)
    alloc_parser.set_defaults(func=command_allocation)

    credit_parser = subparsers.add_parser("credit-metrics", help="Apply trades and compute credit portfolio metrics.")
    credit_parser.add_argument("--portfolio-id", required=True)
    credit_parser.add_argument("--trades-file")
    credit_parser.set_defaults(func=command_credit_metrics)

    candidates_parser = subparsers.add_parser("bond-candidates", help="List bond candidates with issuer watchlist status.")
    candidates_parser.add_argument("--candidate-only", action="store_true")
    candidates_parser.add_argument("--energy-linked", action="store_true")
    candidates_parser.add_argument("--avoid-watchlist", action="store_true")
    candidates_parser.add_argument("--rating-bucket", choices=["IG", "HY"])
    candidates_parser.add_argument("--min-duration", type=float)
    candidates_parser.add_argument("--max-duration", type=float)
    candidates_parser.set_defaults(func=command_bond_candidates)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
