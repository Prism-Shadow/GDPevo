#!/usr/bin/env python3
"""Reusable Asteria API helper for correlation, allocation, and credit tasks."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://task-env:9010/"


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(data: Any, stream: Any = sys.stdout) -> None:
    json.dump(data, stream, indent=2, sort_keys=False)
    stream.write("\n")


def fetch_json(base_url: str, path: str) -> Any:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        return json.load(resp)


def find_access_file(start: Optional[Path] = None) -> Optional[Path]:
    cursor = (start or Path.cwd()).resolve()
    for candidate_dir in [cursor, *cursor.parents]:
        candidate = candidate_dir / "environment_access.md"
        if candidate.exists():
            return candidate
    return None


def parse_base_url(access_file: Path) -> Optional[str]:
    for line in access_file.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^base_url:\s*(\S+)\s*$", line.strip())
        if match:
            return match.group(1)
    return None


def discover_base_url(explicit: Optional[str] = None) -> str:
    if explicit:
        return explicit
    env_url = os.environ.get("ASTERIA_BASE_URL")
    if env_url:
        return env_url
    access_file = find_access_file()
    if access_file:
        parsed = parse_base_url(access_file)
        if parsed:
            return parsed
    return DEFAULT_BASE_URL


def round_float(value: float, digits: int) -> float:
    return round(float(value), digits)


def pearson_corr(xs: Sequence[float], ys: Sequence[float]) -> float:
    if len(xs) != len(ys):
        raise ValueError("Series lengths must match")
    if len(xs) < 2:
        raise ValueError("Need at least two observations")
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    cov = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    x_var = sum((x - x_mean) ** 2 for x in xs)
    y_var = sum((y - y_mean) ** 2 for y in ys)
    if x_var == 0 or y_var == 0:
        return 0.0
    return cov / math.sqrt(x_var * y_var)


def align_return_series(levels_by_index: Dict[str, List[Dict[str, Any]]], index_ids: Sequence[str]) -> Tuple[List[str], Dict[str, List[float]]]:
    index_ids = list(index_ids)
    if not index_ids:
        raise ValueError("No index ids supplied")

    date_sets = []
    for index_id in index_ids:
        series = levels_by_index[index_id]
        if len(series) < 2:
            raise ValueError(f"Index {index_id} needs at least two levels")
        date_sets.append({row["date"] for row in series})

    common_dates = set.intersection(*date_sets)
    ordered_dates = [row["date"] for row in levels_by_index[index_ids[0]] if row["date"] in common_dates]
    ordered_dates.sort()

    returns: Dict[str, List[float]] = {}
    for index_id in index_ids:
        by_date = {row["date"]: float(row["level"]) for row in levels_by_index[index_id] if row["date"] in common_dates}
        aligned_levels = [by_date[date] for date in ordered_dates]
        returns[index_id] = [aligned_levels[i] / aligned_levels[i - 1] - 1 for i in range(1, len(aligned_levels))]
    return ordered_dates, returns


def classify_view(score: float) -> str:
    if score >= 0.35:
        return "OW"
    if score <= -0.35:
        return "UW"
    return "N"


def classify_conviction(score: float) -> str:
    abs_score = abs(score)
    if abs_score >= 0.65:
        return "HIGH"
    if abs_score >= 0.35:
        return "MEDIUM"
    return "LOW"


def view_rank(view: str) -> int:
    order = {"UW": 0, "N": 1, "OW": 2}
    return order[view]


def classify_change(prior_view: Optional[str], current_view: str) -> str:
    if prior_view is None:
        return "UNCHANGED"
    prior_rank = view_rank(prior_view)
    current_rank = view_rank(current_view)
    if current_rank > prior_rank:
        return "UP"
    if current_rank < prior_rank:
        return "DOWN"
    return "UNCHANGED"


def build_lookup(rows: Iterable[Dict[str, Any]], key_fields: Sequence[str]) -> Dict[Tuple[Any, ...], Dict[str, Any]]:
    out: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    for row in rows:
        key = tuple(row[field] for field in key_fields)
        out[key] = row
    return out


def get_bond_maps(base_url: str) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    bonds = fetch_json(base_url, "/api/instruments/bonds")
    issuers = fetch_json(base_url, "/api/issuers")
    bond_map = {row["instrument_id"]: row for row in bonds}
    issuer_map = {row["issuer_id"]: row for row in issuers}
    return bond_map, issuer_map


def bond_record(bond_map: Dict[str, Dict[str, Any]], issuer_map: Dict[str, Dict[str, Any]], instrument_id: str) -> Dict[str, Any]:
    bond = bond_map[instrument_id]
    issuer = issuer_map.get(bond["issuer_id"], {})
    return {
        **bond,
        "issuer_watchlist": bool(issuer.get("watchlist", False)),
        "issuer_credit_outlook": issuer.get("credit_outlook"),
        "issuer_research_tags": issuer.get("research_tags", []),
    }


def summarize_positions(positions: Dict[str, float], bond_map: Dict[str, Dict[str, Any]], issuer_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    total_value = sum(positions.values())
    weighted_duration = 0.0
    weighted_ytm = 0.0
    hy_value = 0.0
    watchlist_value = 0.0
    annotated: List[Dict[str, Any]] = []

    for instrument_id, quantity in positions.items():
        if quantity <= 0:
            continue
        rec = bond_record(bond_map, issuer_map, instrument_id)
        if rec["rating_bucket"] == "HY":
            hy_value += quantity
        if rec["issuer_watchlist"]:
            watchlist_value += quantity
        weighted_duration += quantity * float(rec["modified_duration_years"])
        weighted_ytm += quantity * float(rec["yield_to_maturity_pct"])
        annotated.append({
            "instrument_id": instrument_id,
            "quantity_usd_m": round_float(quantity, 1),
            "issuer_id": rec["issuer_id"],
            "issuer_name": rec["issuer_name"],
            "rating_bucket": rec["rating_bucket"],
            "modified_duration_years": float(rec["modified_duration_years"]),
            "yield_to_maturity_pct": float(rec["yield_to_maturity_pct"]),
            "issuer_watchlist": rec["issuer_watchlist"],
            "subsector": rec["subsector"],
            "sector": rec["sector"],
        })

    total_value = float(total_value)
    metrics = {
        "total_market_value_usd_m": round_float(total_value, 2),
        "hy_allocation_pct": round_float((hy_value / total_value * 100.0) if total_value else 0.0, 2),
        "weighted_modified_duration_years": round_float((weighted_duration / total_value) if total_value else 0.0, 2),
        "weighted_yield_to_maturity_pct": round_float((weighted_ytm / total_value) if total_value else 0.0, 2),
        "watchlist_exposure_usd_m": round_float(watchlist_value, 2),
        "holdings": sorted(annotated, key=lambda row: row["instrument_id"]),
    }
    return metrics


def parse_trade_input(trades_json: Optional[str], trades_file: Optional[Path]) -> List[Dict[str, Any]]:
    if trades_json:
        payload = json.loads(trades_json)
    elif trades_file:
        payload = read_json(trades_file)
    else:
        raise ValueError("Provide --trades-json or --trades-file")
    if isinstance(payload, dict) and "trades" in payload:
        payload = payload["trades"]
    if not isinstance(payload, list):
        raise ValueError("Trades input must be a list or an object with a 'trades' list")
    return payload


def apply_trades(current_holdings: List[Dict[str, Any]], trades: List[Dict[str, Any]]) -> Dict[str, float]:
    positions = {row["instrument_id"]: float(row["quantity_usd_m"]) for row in current_holdings}
    for trade in trades:
        instrument_id = trade["instrument_id"]
        amount = float(trade.get("quantity_usd_m", trade.get("notional_usd_m", 0.0)))
        action = trade["action"].upper()
        positions.setdefault(instrument_id, 0.0)
        if action == "BUY":
            positions[instrument_id] += amount
        elif action == "SELL":
            positions[instrument_id] -= amount
        else:
            raise ValueError(f"Unsupported action {action}; expected BUY or SELL")
    negative = {instrument_id: quantity for instrument_id, quantity in positions.items() if quantity < -1e-9}
    if negative:
        raise ValueError(f"Trades create negative positions: {negative}")
    return positions


def candidate_list(base_url: str, args: argparse.Namespace) -> List[Dict[str, Any]]:
    bonds = fetch_json(base_url, "/api/instruments/bonds")
    issuers = fetch_json(base_url, "/api/issuers")
    issuer_map = {row["issuer_id"]: row for row in issuers}

    rows = []
    for bond in bonds:
        issuer = issuer_map.get(bond["issuer_id"], {})
        row = {
            **bond,
            "issuer_watchlist": bool(issuer.get("watchlist", False)),
            "issuer_credit_outlook": issuer.get("credit_outlook"),
            "issuer_research_tags": issuer.get("research_tags", []),
        }
        if args.candidate_only and not row.get("candidate", False):
            continue
        if args.energy_only and not row.get("energy_linked", False):
            continue
        if args.exclude_watchlist and row["issuer_watchlist"]:
            continue
        if args.sector and row.get("sector") != args.sector:
            continue
        if args.subsector and row.get("subsector") != args.subsector:
            continue
        if args.rating_bucket and row.get("rating_bucket") != args.rating_bucket:
            continue
        if args.theme_tag and args.theme_tag not in row.get("recommended_theme_tags", []):
            continue
        rows.append(row)

    sort_key = args.sort
    reverse = args.descending
    if sort_key:
        rows.sort(key=lambda row: row.get(sort_key, 0), reverse=reverse)
    else:
        rows.sort(key=lambda row: (-float(row.get("yield_to_maturity_pct", 0.0)), float(row.get("modified_duration_years", 0.0)), row["instrument_id"]))
    return rows


def cmd_snapshot(args: argparse.Namespace) -> None:
    base_url = discover_base_url(args.base_url)
    data: Dict[str, Any] = {"base_url": base_url}
    try:
        data["portfolios"] = fetch_json(base_url, "/api/portfolios")
        data["indices"] = fetch_json(base_url, "/api/indices")
        data["opportunity_sets"] = fetch_json(base_url, "/api/allocation/opportunity-sets")
        data["prior_views"] = fetch_json(base_url, "/api/allocation/prior-views")
        data["macro_signals"] = fetch_json(base_url, "/api/macro-signals")
        data["bonds"] = fetch_json(base_url, "/api/instruments/bonds")
        data["issuers"] = fetch_json(base_url, "/api/issuers")
        data["index_levels"] = fetch_json(base_url, "/api/index-levels")
        if args.portfolio_id:
            data["holdings"] = fetch_json(base_url, f"/api/portfolios/{args.portfolio_id}/holdings")
    except (HTTPError, URLError) as exc:
        raise SystemExit(f"snapshot fetch failed: {exc}") from exc
    write_json(data)


def cmd_correlations(args: argparse.Namespace) -> None:
    base_url = discover_base_url(args.base_url)
    levels = fetch_json(base_url, "/api/index-levels")
    index_ids = list(args.index_ids)
    ordered_dates, returns = align_return_series(levels, index_ids)

    pair_rows = []
    for left_index in sorted(index_ids):
        for right_index in sorted(index_ids):
            if left_index >= right_index:
                continue
            corr = pearson_corr(returns[left_index], returns[right_index])
            pair_rows.append({
                "pair_id": [left_index, right_index],
                "correlation": round_float(corr, 3),
            })

    if not pair_rows:
        raise SystemExit("Need at least two index ids for correlations")
    highest_positive = max(pair_rows, key=lambda row: row["correlation"])
    lowest = min(pair_rows, key=lambda row: row["correlation"])

    index_meta = fetch_json(base_url, "/api/indices")
    meta_by_id = {row["index_id"]: row for row in index_meta}
    first = meta_by_id[index_ids[0]]
    out = {
        "level_start_date": first.get("level_start_date"),
        "level_end_date": first.get("level_end_date"),
        "return_observations": max(len(ordered_dates) - 1, 0),
        "index_set": sorted(index_ids),
        "pair_correlations": sorted(pair_rows, key=lambda row: (row["pair_id"][0], row["pair_id"][1])),
        "extreme_pairs": {
            "highest_positive": highest_positive,
            "lowest": lowest,
        },
    }
    write_json(out)


def cmd_allocation(args: argparse.Namespace) -> None:
    base_url = discover_base_url(args.base_url)
    opportunity_sets = fetch_json(base_url, "/api/allocation/opportunity-sets")
    prior_views = fetch_json(base_url, "/api/allocation/prior-views")
    macro_signals = fetch_json(base_url, "/api/macro-signals")

    opp_map = {row["opportunity_set"]: row for row in opportunity_sets}
    prior_map = build_lookup((row for row in prior_views if row.get("quarter") == args.quarter), ["opportunity_set"])
    signal_map = build_lookup((row for row in macro_signals if row.get("quarter") == args.quarter), ["opportunity_set"])

    rows = []
    for opportunity_set in args.opportunity_sets:
        if opportunity_set not in opp_map:
            raise SystemExit(f"Unknown opportunity set: {opportunity_set}")
        signal = signal_map.get((opportunity_set,))
        prior = prior_map.get((opportunity_set,))
        if signal is None:
            raise SystemExit(f"No macro signal found for {opportunity_set} in {args.quarter}")
        current_view = classify_view(float(signal["score"]))
        prior_view = prior.get("view") if prior else None
        row = {
            "opportunity_set": opportunity_set,
            "asset_class": opp_map[opportunity_set]["asset_class"],
            "prior_view": prior_view,
            "signal_score": round_float(float(signal["score"]), 3),
            "view": current_view,
            "change": classify_change(prior_view, current_view),
            "conviction": classify_conviction(float(signal["score"])),
            "rationale_code": signal["rationale_code"],
        }
        rows.append(row)

    out = {
        "quarter": args.quarter,
        "policy_id": args.policy_id,
        "allocation_views": rows,
    }
    write_json(out)


def cmd_trade_metrics(args: argparse.Namespace) -> None:
    base_url = discover_base_url(args.base_url)
    portfolio = fetch_json(base_url, f"/api/portfolios/{args.portfolio_id}/holdings")
    current_holdings = portfolio["holdings"]
    trades = parse_trade_input(args.trades_json, args.trades_file)
    bond_map, issuer_map = get_bond_maps(base_url)

    current_positions = {row["instrument_id"]: float(row["quantity_usd_m"]) for row in current_holdings}
    post_positions = apply_trades(current_holdings, trades)

    current_metrics = summarize_positions(current_positions, bond_map, issuer_map)
    post_metrics = summarize_positions(post_positions, bond_map, issuer_map)

    buy_trades = [trade for trade in trades if trade["action"].upper() == "BUY"]
    buy_instruments = [trade["instrument_id"] for trade in buy_trades]
    buy_issuers = []
    buy_subsectors = []
    watchlist_buy_ids = []
    for instrument_id in buy_instruments:
        rec = bond_record(bond_map, issuer_map, instrument_id)
        buy_issuers.append(rec["issuer_id"])
        buy_subsectors.append(rec["subsector"])
        if rec["issuer_watchlist"]:
            watchlist_buy_ids.append(instrument_id)

    hy_cap_pass = None
    if args.hy_cap is not None:
        hy_cap_pass = post_metrics["hy_allocation_pct"] <= float(args.hy_cap)

    duration_band_pass = None
    if args.duration_min is not None and args.duration_max is not None:
        duration_band_pass = float(args.duration_min) <= post_metrics["weighted_modified_duration_years"] <= float(args.duration_max)

    out = {
        "portfolio_id": args.portfolio_id,
        "as_of_date": portfolio["as_of_date"],
        "current": current_metrics,
        "post_trade": post_metrics,
        "delta": {
            "hy_reduction_pct_points": round_float(current_metrics["hy_allocation_pct"] - post_metrics["hy_allocation_pct"], 2),
            "market_value_change_usd_m": round_float(post_metrics["total_market_value_usd_m"] - current_metrics["total_market_value_usd_m"], 2),
        },
        "selected_buys": sorted(
            [
                {
                    "instrument_id": instrument_id,
                    "issuer_id": bond_record(bond_map, issuer_map, instrument_id)["issuer_id"],
                    "issuer_name": bond_record(bond_map, issuer_map, instrument_id)["issuer_name"],
                    "subsector": bond_record(bond_map, issuer_map, instrument_id)["subsector"],
                    "rating_bucket": bond_record(bond_map, issuer_map, instrument_id)["rating_bucket"],
                    "issuer_watchlist": bond_record(bond_map, issuer_map, instrument_id)["issuer_watchlist"],
                }
                for instrument_id in buy_instruments
            ],
            key=lambda row: row["instrument_id"],
        ),
        "constraint_checks": {
            "hy_cap_pass": hy_cap_pass,
            "duration_band_pass": duration_band_pass,
            "selected_issuer_diversification_pass": len(set(buy_issuers)) == len(buy_issuers) if buy_issuers else None,
            "selected_subsector_diversification_pass": len(set(buy_subsectors)) == len(buy_subsectors) if buy_subsectors else None,
            "watchlist_avoidance_pass": len(watchlist_buy_ids) == 0,
        },
        "watchlist_buy_ids": sorted(watchlist_buy_ids),
    }
    write_json(out)


def cmd_candidates(args: argparse.Namespace) -> None:
    base_url = discover_base_url(args.base_url)
    rows = candidate_list(base_url, args)
    write_json({"count": len(rows), "candidates": rows})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Asteria helper toolkit")
    parser.add_argument("--base-url", help="Override the Asteria API base URL")

    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("snapshot", help="Fetch a current API snapshot")
    snap.add_argument("--portfolio-id", help="Optional portfolio id to include holdings for")
    snap.set_defaults(func=cmd_snapshot)

    corr = sub.add_parser("correlations", help="Compute pairwise correlations for an index set")
    corr.add_argument("--index-ids", nargs="+", required=True, help="Index ids to evaluate")
    corr.set_defaults(func=cmd_correlations)

    alloc = sub.add_parser("allocation", help="Build allocation-view rows for a quarter")
    alloc.add_argument("--quarter", required=True, help="Quarter label, for example Q2_2026")
    alloc.add_argument("--policy-id", help="Optional policy id to echo into the output")
    alloc.add_argument("--opportunity-sets", nargs="+", required=True, help="Opportunity sets in desired row order")
    alloc.set_defaults(func=cmd_allocation)

    trade = sub.add_parser("trade-metrics", help="Apply trades to a portfolio and recompute metrics")
    trade.add_argument("--portfolio-id", required=True)
    trade.add_argument("--trades-file", type=Path, help="Path to a JSON file containing trades")
    trade.add_argument("--trades-json", help="Inline JSON string containing trades")
    trade.add_argument("--hy-cap", type=float, help="Optional HY cap for pass/fail")
    trade.add_argument("--duration-min", type=float, help="Optional duration floor")
    trade.add_argument("--duration-max", type=float, help="Optional duration ceiling")
    trade.set_defaults(func=cmd_trade_metrics)

    cand = sub.add_parser("candidates", help="List eligible bond candidates")
    cand.add_argument("--candidate-only", action=argparse.BooleanOptionalAction, default=True)
    cand.add_argument("--energy-only", action=argparse.BooleanOptionalAction, default=False)
    cand.add_argument("--exclude-watchlist", action=argparse.BooleanOptionalAction, default=False)
    cand.add_argument("--sector")
    cand.add_argument("--subsector")
    cand.add_argument("--rating-bucket", choices=["IG", "HY"])
    cand.add_argument("--theme-tag")
    cand.add_argument("--sort")
    cand.add_argument("--descending", action="store_true")
    cand.set_defaults(func=cmd_candidates)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except (HTTPError, URLError) as exc:
        raise SystemExit(f"Asteria API request failed: {exc}") from exc


if __name__ == "__main__":
    main()
