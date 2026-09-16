#!/usr/bin/env python3
"""Utilities for Asteria JSON portfolio tasks.

Stdlib-only helper functions for:
- fetching the public task environment
- computing monthly-return correlations
- computing credit portfolio metrics
- ranking equal-size energy-credit buy pairs
- assembling allocation-view rows from live signals
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def load_env_file(path: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    if "base_url" in data:
        data["base_url"] = data["base_url"].rstrip("/")
    return data


def resolve_base_url(args: argparse.Namespace) -> str:
    if getattr(args, "base_url", None):
        return str(args.base_url).rstrip("/")
    env_file = getattr(args, "env_file", None)
    if env_file:
        env = load_env_file(env_file)
        base_url = env.get("base_url")
        if base_url:
            return str(base_url).rstrip("/")
    raise SystemExit("base_url is required (pass --base-url or --env-file)")


def fetch_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed to reach {url}: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON from {url}: {exc}") from exc


def api_get(base_url: str, path: str) -> Any:
    return fetch_json(base_url.rstrip("/") + path)


def dump_json(data: Any) -> None:
    json.dump(data, sys.stdout, indent=2, ensure_ascii=True, sort_keys=False)
    sys.stdout.write("\n")


def iso_sort(rows: Iterable[Mapping[str, Any]], key: str = "date") -> List[Mapping[str, Any]]:
    return sorted(rows, key=lambda row: row[key])


def round_float(value: float, digits: int) -> float:
    return round(float(value), digits)


def mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def theme_tokens(text: str) -> set[str]:
    tokens = set()
    for token in re.split(r"[^A-Z0-9]+", text.upper()):
        if not token:
            continue
        if token.endswith("S") and len(token) > 3:
            token = token[:-1]
        tokens.add(token)
    return tokens


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    xs = list(xs[:n])
    ys = list(ys[:n])
    mx = mean(xs)
    my = mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs)
    dy = sum((y - my) ** 2 for y in ys)
    if dx == 0.0 or dy == 0.0:
        return 0.0
    return num / math.sqrt(dx * dy)


def simple_returns(level_rows: Sequence[Mapping[str, Any]]) -> Dict[str, float]:
    rows = iso_sort(level_rows)
    returns: Dict[str, float] = {}
    for prev, curr in zip(rows, rows[1:]):
        prev_level = float(prev["level"])
        curr_level = float(curr["level"])
        if prev_level == 0.0:
            continue
        returns[str(curr["date"])] = curr_level / prev_level - 1.0
    return returns


def filter_levels(level_rows: Sequence[Mapping[str, Any]], start: str | None, end: str | None) -> List[Mapping[str, Any]]:
    rows = iso_sort(level_rows)
    filtered = []
    for row in rows:
        date = str(row["date"])
        if start and date < start:
            continue
        if end and date > end:
            continue
        filtered.append(row)
    return filtered


def build_portfolio_lookup(portfolios: Sequence[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    return {str(row["portfolio_id"]): row for row in portfolios}


def build_bond_lookup(bonds: Sequence[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    return {str(row["instrument_id"]): row for row in bonds}


def build_issuer_lookup(issuers: Sequence[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    return {str(row["issuer_id"]): row for row in issuers}


def quantity_from_trade(trade: Mapping[str, Any]) -> float:
    if "quantity_usd_m" in trade:
        return float(trade["quantity_usd_m"])
    if "notional_usd_m" in trade:
        return float(trade["notional_usd_m"])
    raise SystemExit(f"Trade missing quantity field: {trade}")


def apply_trades(
    holdings: Sequence[Mapping[str, Any]],
    trades: Sequence[Mapping[str, Any]],
) -> Dict[str, float]:
    positions: Dict[str, float] = {str(row["instrument_id"]): float(row["quantity_usd_m"]) for row in holdings}
    for trade in trades:
        action = str(trade["action"]).upper()
        instrument_id = str(trade["instrument_id"])
        qty = quantity_from_trade(trade)
        positions.setdefault(instrument_id, 0.0)
        if action == "BUY":
            positions[instrument_id] += qty
        elif action == "SELL":
            positions[instrument_id] -= qty
        elif action in {"HOLD", "NO_TRADE"}:
            continue
        else:
            raise SystemExit(f"Unsupported trade action: {action}")
    return {iid: qty for iid, qty in positions.items() if qty > 1e-12}


def portfolio_metrics(
    positions: Mapping[str, float],
    bonds: Mapping[str, Mapping[str, Any]],
    issuers: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    total = sum(positions.values())
    if total <= 0.0:
        raise SystemExit("Portfolio value must be positive after applying trades")

    hy = 0.0
    watchlist = 0.0
    duration = 0.0
    ytm = 0.0
    sector_qty = Counter()
    issuer_qty = Counter()
    subsector_qty = Counter()

    for instrument_id, qty in positions.items():
        bond = bonds.get(instrument_id, {})
        issuer_id = str(bond.get("issuer_id", ""))
        issuer = issuers.get(issuer_id, {})
        duration += qty * float(bond.get("modified_duration_years", 0.0))
        ytm += qty * float(bond.get("yield_to_maturity_pct", 0.0))
        if str(bond.get("rating_bucket", "")).upper() == "HY":
            hy += qty
        if bool(issuer.get("watchlist")):
            watchlist += qty
        sector_qty[str(bond.get("sector", ""))] += qty
        issuer_qty[issuer_id] += qty
        subsector_qty[str(bond.get("subsector", ""))] += qty

    return {
        "total_market_value_usd_m": round_float(total, 2),
        "hy_allocation_pct": round_float((hy / total) * 100.0, 2),
        "weighted_modified_duration_years": round_float(duration / total, 2),
        "weighted_yield_to_maturity_pct": round_float(ytm / total, 2),
        "watchlist_exposure_usd_m": round_float(watchlist, 1),
        "issuer_count": len([k for k, v in issuer_qty.items() if v > 0]),
        "subsector_count": len([k for k, v in subsector_qty.items() if v > 0]),
    }


def correlation_payload(
    base_url: str,
    index_ids: Sequence[str],
    start: str | None,
    end: str | None,
) -> Dict[str, Any]:
    all_levels = api_get(base_url, "/api/index-levels")
    level_map: Dict[str, Sequence[Mapping[str, Any]]] = {}
    for idx in index_ids:
        if idx not in all_levels:
            raise SystemExit(f"Missing index levels for {idx}")
        level_map[idx] = filter_levels(all_levels[idx], start, end)

    return_rows: Dict[str, Dict[str, float]] = {}
    observation_counts: List[int] = []
    for idx, rows in level_map.items():
        returns = simple_returns(rows)
        return_rows[idx] = returns
        observation_counts.append(len(returns))
    if not observation_counts:
        raise SystemExit("No indices supplied")

    pair_rows = []
    for a, b in itertools.combinations(sorted(index_ids), 2):
        ra = return_rows[a]
        rb = return_rows[b]
        common_dates = sorted(set(ra).intersection(rb))
        xs = [ra[d] for d in common_dates]
        ys = [rb[d] for d in common_dates]
        corr = pearson(xs, ys)
        pair_rows.append(
            {
                "pair_id": [a, b],
                "correlation": round_float(corr, 3),
                "observations": len(common_dates),
            }
        )

    if not pair_rows:
        raise SystemExit("At least two indices are required")

    highest_positive = max(pair_rows, key=lambda row: (row["correlation"], row["pair_id"]))
    lowest = min(pair_rows, key=lambda row: (row["correlation"], row["pair_id"]))

    return {
        "review_window": {
            "level_start_date": start,
            "level_end_date": end,
            "return_observations": max(observation_counts),
        },
        "index_set": sorted(index_ids),
        "pairwise_correlations": pair_rows,
        "extreme_pairs": {
            "highest_positive": {
                "pair_id": highest_positive["pair_id"],
                "correlation": highest_positive["correlation"],
            },
            "lowest": {
                "pair_id": lowest["pair_id"],
                "correlation": lowest["correlation"],
            },
        },
    }


def score_energy_pair(
    pair: Tuple[Mapping[str, Any], Mapping[str, Any]],
    positions: Mapping[str, float],
    bonds: Mapping[str, Mapping[str, Any]],
    issuers: Mapping[str, Mapping[str, Any]],
    ticket_notional: float,
    duration_target: float | None = None,
    duration_min: float | None = None,
    duration_max: float | None = None,
    theme_terms: Sequence[str] = (),
    require_distinct_issuer: bool = True,
    require_distinct_subsector: bool = True,
    avoid_watchlist: bool = True,
) -> Dict[str, Any] | None:
    a, b = pair
    if require_distinct_issuer and str(a["issuer_id"]) == str(b["issuer_id"]):
        return None
    if require_distinct_subsector and str(a.get("subsector", "")) == str(b.get("subsector", "")):
        return None

    issuer_a = issuers.get(str(a["issuer_id"]), {})
    issuer_b = issuers.get(str(b["issuer_id"]), {})
    if avoid_watchlist and (bool(issuer_a.get("watchlist")) or bool(issuer_b.get("watchlist"))):
        return None

    trades = [
        {"action": "BUY", "instrument_id": str(a["instrument_id"]), "quantity_usd_m": ticket_notional},
        {"action": "BUY", "instrument_id": str(b["instrument_id"]), "quantity_usd_m": ticket_notional},
    ]
    post = apply_trades(
        [{"instrument_id": iid, "quantity_usd_m": qty} for iid, qty in positions.items()],
        trades,
    )
    metrics = portfolio_metrics(post, bonds, issuers)

    duration = metrics["weighted_modified_duration_years"]
    ytm = metrics["weighted_yield_to_maturity_pct"]
    hy_pct = metrics["hy_allocation_pct"]
    theme_hits = 0
    rating_buckets = {str(a.get("rating_bucket", "")).upper(), str(b.get("rating_bucket", "")).upper()}
    for bond in pair:
        tags = set()
        for tag in bond.get("recommended_theme_tags", []):
            tags |= theme_tokens(str(tag))
        for term in theme_terms:
            overlap = tags & theme_tokens(str(term))
            if overlap:
                theme_hits += len(overlap)
                break

    score = ytm + theme_hits * 0.25 - hy_pct * 0.02
    if rating_buckets == {"IG", "HY"}:
        score += 0.2
    elif rating_buckets == {"IG"}:
        score -= 0.05
    elif rating_buckets == {"HY"}:
        score -= 0.1
    if duration_target is not None:
        score -= abs(duration - duration_target) * 1.0
    if duration_min is not None and duration < duration_min:
        score -= (duration_min - duration) * 1.5
    if duration_max is not None and duration > duration_max:
        score -= (duration - duration_max) * 1.5

    return {
        "buy_ids": sorted([str(a["instrument_id"]), str(b["instrument_id"])]),
        "score": round_float(score, 4),
        "theme_hits": theme_hits,
        "projected_metrics": metrics,
    }


def command_snapshot(args: argparse.Namespace) -> None:
    base_url = resolve_base_url(args)
    payload: Dict[str, Any] = {
        "portfolios": api_get(base_url, "/api/portfolios"),
        "bonds": api_get(base_url, "/api/instruments/bonds"),
        "issuers": api_get(base_url, "/api/issuers"),
        "market_energy": api_get(base_url, "/api/market/energy"),
        "indices": api_get(base_url, "/api/indices"),
        "index_levels": api_get(base_url, "/api/index-levels"),
        "allocation_opportunity_sets": api_get(base_url, "/api/allocation/opportunity-sets"),
        "allocation_prior_views": api_get(base_url, "/api/allocation/prior-views"),
        "macro_signals": api_get(base_url, "/api/macro-signals"),
    }
    if args.portfolio_id:
        payload["portfolio_holdings"] = api_get(base_url, f"/api/portfolios/{args.portfolio_id}/holdings")
    dump_json(payload)


def command_correlations(args: argparse.Namespace) -> None:
    base_url = resolve_base_url(args)
    data = correlation_payload(base_url, args.index_id, args.start_date, args.end_date)
    dump_json(data)


def command_credit_metrics(args: argparse.Namespace) -> None:
    base_url = resolve_base_url(args)
    portfolio = api_get(base_url, f"/api/portfolios/{args.portfolio_id}")
    holdings_payload = api_get(base_url, f"/api/portfolios/{args.portfolio_id}/holdings")
    bonds = build_bond_lookup(api_get(base_url, "/api/instruments/bonds"))
    issuers = build_issuer_lookup(api_get(base_url, "/api/issuers"))
    trades = []
    if args.trades_json:
        trades = json.loads(args.trades_json)
    elif args.trades_file:
        with open(args.trades_file, "r", encoding="utf-8") as fh:
            trades = json.load(fh)

    current_positions = {str(row["instrument_id"]): float(row["quantity_usd_m"]) for row in holdings_payload["holdings"]}
    post_positions = apply_trades(holdings_payload["holdings"], trades)
    current_metrics = portfolio_metrics(current_positions, bonds, issuers)
    post_metrics = portfolio_metrics(post_positions, bonds, issuers)

    out: Dict[str, Any] = {
        "portfolio": portfolio,
        "current_metrics": current_metrics,
        "post_metrics": post_metrics,
        "trades": trades,
    }
    if args.hy_cap_pct is not None or args.duration_min is not None or args.duration_max is not None or args.require_watchlist_clear:
        checks: Dict[str, bool] = {}
        if args.hy_cap_pct is not None:
            checks["hy_cap_pass"] = post_metrics["hy_allocation_pct"] <= args.hy_cap_pct
        if args.duration_min is not None or args.duration_max is not None:
            lo = args.duration_min if args.duration_min is not None else -math.inf
            hi = args.duration_max if args.duration_max is not None else math.inf
            checks["duration_band_pass"] = lo <= post_metrics["weighted_modified_duration_years"] <= hi
        if args.require_watchlist_clear:
            checks["watchlist_clear_pass"] = post_metrics["watchlist_exposure_usd_m"] == 0.0
        if args.require_distinct_issuer:
            buy_ids = [str(t["instrument_id"]) for t in trades if str(t["action"]).upper() == "BUY"]
            issuer_ids = [str(bonds.get(iid, {}).get("issuer_id", "")) for iid in buy_ids]
            checks["selected_issuer_diversification_pass"] = len(issuer_ids) == len(set(issuer_ids))
        if args.require_distinct_subsector:
            buy_ids = [str(t["instrument_id"]) for t in trades if str(t["action"]).upper() == "BUY"]
            subsectors = [str(bonds.get(iid, {}).get("subsector", "")) for iid in buy_ids]
            checks["selected_subsector_diversification_pass"] = len(subsectors) == len(set(subsectors))
        out["constraint_checks"] = checks
    dump_json(out)


def command_rank_energy_pairs(args: argparse.Namespace) -> None:
    base_url = resolve_base_url(args)
    holdings_payload = api_get(base_url, f"/api/portfolios/{args.portfolio_id}/holdings")
    bonds_lookup = build_bond_lookup(api_get(base_url, "/api/instruments/bonds"))
    issuers_lookup = build_issuer_lookup(api_get(base_url, "/api/issuers"))
    market_energy = api_get(base_url, "/api/market/energy")
    positions = {str(row["instrument_id"]): float(row["quantity_usd_m"]) for row in holdings_payload["holdings"]}
    current_metrics = portfolio_metrics(positions, bonds_lookup, issuers_lookup)
    duration_target = args.duration_target
    if duration_target is None:
        duration_target = float(current_metrics["weighted_modified_duration_years"])

    candidates = []
    for bond in bonds_lookup.values():
        if args.energy_only and not bool(bond.get("energy_linked")):
            continue
        if not bool(bond.get("candidate", False)):
            continue
        issuer = issuers_lookup.get(str(bond.get("issuer_id", "")), {})
        if args.avoid_watchlist and bool(issuer.get("watchlist")):
            continue
        candidates.append(bond)
    candidates = sorted(candidates, key=lambda row: str(row["instrument_id"]))

    theme_terms = tuple(args.theme_term or market_energy.get("pitch_themes", []))
    scored = []
    for pair in itertools.combinations(candidates, 2):
        result = score_energy_pair(
            pair,
            positions,
            bonds_lookup,
            issuers_lookup,
            args.ticket_notional,
            duration_target=duration_target,
            duration_min=args.duration_min,
            duration_max=args.duration_max,
            theme_terms=theme_terms,
            require_distinct_issuer=args.require_distinct_issuer,
            require_distinct_subsector=args.require_distinct_subsector,
            avoid_watchlist=args.avoid_watchlist,
        )
        if result is not None:
            scored.append(result)

    scored.sort(key=lambda row: (-row["score"], row["buy_ids"]))
    dump_json(
        {
            "portfolio_id": args.portfolio_id,
            "ticket_notional_usd_m": args.ticket_notional,
            "pair_rankings": scored[: args.limit],
        }
    )


def derive_view(score: float) -> str:
    if score >= 0.3:
        return "OW"
    if score <= -0.3:
        return "UW"
    return "N"


def derive_conviction(score: float) -> str:
    abs_score = abs(score)
    if abs_score >= 0.65:
        return "HIGH"
    if abs_score >= 0.3:
        return "MEDIUM"
    return "LOW"


def view_order(view: str) -> int:
    return {"UW": 0, "N": 1, "OW": 2}[view]


def command_allocation_views(args: argparse.Namespace) -> None:
    base_url = resolve_base_url(args)
    prior_views = api_get(base_url, "/api/allocation/prior-views")
    signals = api_get(base_url, "/api/macro-signals")
    opportunity_sets = api_get(base_url, "/api/allocation/opportunity-sets")

    opportunity_lookup = {str(row["opportunity_set"]): row for row in opportunity_sets}
    prior_lookup = {
        (str(row.get("quarter")), str(row["opportunity_set"])): row
        for row in prior_views
    }
    signal_lookup = {
        (str(row.get("quarter")), str(row["opportunity_set"])): row
        for row in signals
    }

    rows = []
    for opportunity_set in args.opportunity_set:
        prior = prior_lookup.get((args.quarter, opportunity_set))
        signal = signal_lookup.get((args.quarter, opportunity_set))
        score = float(signal["score"]) if signal and "score" in signal else 0.0
        view = derive_view(score)
        prior_view = str(prior["view"]) if prior else "N"
        change = "UNCHANGED"
        if view_order(view) > view_order(prior_view):
            change = "UP"
        elif view_order(view) < view_order(prior_view):
            change = "DOWN"
        rows.append(
            {
                "opportunity_set": opportunity_set,
                "asset_class": opportunity_lookup.get(opportunity_set, {}).get("asset_class"),
                "prior_view": prior_view,
                "signal_score": round_float(score, 3),
                "view": view,
                "change": change,
                "conviction": derive_conviction(score),
                "rationale_code": signal["rationale_code"] if signal else "NEUTRAL_BALANCE",
            }
        )

    dump_json(
        {
            "portfolio_id": args.portfolio_id,
            "as_of_date": args.as_of_date,
            "review_quarter": args.quarter,
            "allocation_views": rows,
        }
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Asteria task-environment helper")
    parser.add_argument("--base-url", help="Task environment base URL")
    parser.add_argument("--env-file", help="Path to environment_access.md or a similar file")

    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("snapshot", help="Fetch the core Asteria environment objects")
    p.add_argument("--portfolio-id", help="Optional portfolio id to fetch holdings for")
    p.set_defaults(func=command_snapshot)

    p = sub.add_parser("correlations", help="Compute pairwise correlations for indices")
    p.add_argument("--index-id", action="append", required=True, help="Index id to include")
    p.add_argument("--start-date", help="Optional start date YYYY-MM-DD")
    p.add_argument("--end-date", help="Optional end date YYYY-MM-DD")
    p.set_defaults(func=command_correlations)

    p = sub.add_parser("credit-metrics", help="Compute credit portfolio metrics before and after trades")
    p.add_argument("--portfolio-id", required=True, help="Portfolio id")
    p.add_argument("--trades-json", help="JSON array of trades")
    p.add_argument("--trades-file", help="Path to JSON trades file")
    p.add_argument("--hy-cap-pct", type=float, help="Optional HY cap to check")
    p.add_argument("--duration-min", type=float, help="Optional duration floor")
    p.add_argument("--duration-max", type=float, help="Optional duration ceiling")
    p.add_argument("--require-watchlist-clear", action="store_true", help="Check watchlist exposure is zero")
    p.add_argument("--require-distinct-issuer", action="store_true", help="Check BUY trades do not reuse issuers")
    p.add_argument("--require-distinct-subsector", action="store_true", help="Check BUY trades do not reuse subsectors")
    p.set_defaults(func=command_credit_metrics)

    p = sub.add_parser("rank-energy-pairs", help="Rank equal-size energy-credit buy pairs")
    p.add_argument("--portfolio-id", required=True, help="Portfolio id")
    p.add_argument("--ticket-notional", type=float, required=True, help="Notional per buy ticket in USD millions")
    p.add_argument("--limit", type=int, default=10, help="How many pairs to show")
    p.add_argument("--duration-target", type=float, help="Optional target duration")
    p.add_argument("--duration-min", type=float, help="Optional duration floor")
    p.add_argument("--duration-max", type=float, help="Optional duration ceiling")
    p.add_argument("--theme-term", action="append", help="Optional theme keyword to reward", default=[])
    p.add_argument("--energy-only", action="store_true", default=True, help="Restrict to energy-linked candidates")
    p.add_argument("--avoid-watchlist", action="store_true", default=True, help="Exclude watchlisted issuers")
    p.add_argument("--require-distinct-issuer", action="store_true", default=True, help="Require different issuers")
    p.add_argument("--require-distinct-subsector", action="store_true", default=True, help="Require different subsectors")
    p.set_defaults(func=command_rank_energy_pairs)

    p = sub.add_parser("allocation-views", help="Build allocation-view rows from live signals")
    p.add_argument("--portfolio-id", required=True, help="Portfolio id")
    p.add_argument("--as-of-date", required=True, help="As-of date to place in the output")
    p.add_argument("--quarter", required=True, help="Quarter key, e.g. Q2_2026")
    p.add_argument("--opportunity-set", action="append", required=True, help="Opportunity set in requested order")
    p.set_defaults(func=command_allocation_views)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
