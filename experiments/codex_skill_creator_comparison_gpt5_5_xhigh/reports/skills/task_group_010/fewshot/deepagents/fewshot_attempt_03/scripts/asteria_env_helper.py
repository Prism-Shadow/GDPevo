#!/usr/bin/env python3
"""Build reusable Asteria environment fact packs for JSON answer tasks."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


VIEW_RANK = {"UW": 0, "N": 1, "OW": 2}
DEFAULT_ALLOWED_ENDPOINTS = {
    "/api/portfolios",
    "/api/portfolios/{portfolio_id}/holdings",
    "/api/instruments/bonds",
    "/api/issuers",
    "/api/market/energy",
    "/api/indices",
    "/api/index-levels",
    "/api/index-levels/{index_id}",
    "/api/allocation/opportunity-sets",
    "/api/allocation/prior-views",
    "/api/macro-signals",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(read_text(path))


def resolve_input_dir(path: Path) -> Path:
    path = path.resolve()
    if (path / "prompt.txt").exists() and (path / "payloads").is_dir():
        return path
    if (path / "input" / "prompt.txt").exists():
        return path / "input"
    if (Path.cwd() / "input" / "prompt.txt").exists():
        return Path.cwd() / "input"
    if (Path.cwd() / "prompt.txt").exists() and (Path.cwd() / "payloads").is_dir():
        return Path.cwd()
    raise SystemExit(f"Could not find task input directory from {path}")


def find_access_file(start: Path) -> Path | None:
    candidates = [start, *start.parents, Path.cwd(), *Path.cwd().parents]
    seen: set[Path] = set()
    for base in candidates:
        if base in seen:
            continue
        seen.add(base)
        access = base / "environment_access.md"
        if access.exists():
            return access
    return None


def parse_access(path: Path | None) -> tuple[str, set[str]]:
    base_url = "http://task-env:9010/"
    allowed: set[str] = set()
    if path is None:
        return base_url, set(DEFAULT_ALLOWED_ENDPOINTS)
    for line in read_text(path).splitlines():
        if line.startswith("base_url:"):
            base_url = line.split(":", 1)[1].strip()
        match = re.match(r"\s*-\s*GET\s+(\S+)", line)
        if match:
            allowed.add(match.group(1))
    if not base_url.endswith("/"):
        base_url += "/"
    return base_url, allowed or set(DEFAULT_ALLOWED_ENDPOINTS)


def endpoint_allowed(path: str, allowed: set[str]) -> bool:
    if path in allowed:
        return True
    for pattern in allowed:
        if "{portfolio_id}" in pattern:
            regex = "^" + re.escape(pattern).replace("\\{portfolio_id\\}", "[^/]+") + "$"
            if re.match(regex, path):
                return True
        if "{index_id}" in pattern:
            regex = "^" + re.escape(pattern).replace("\\{index_id\\}", "[^/]+") + "$"
            if re.match(regex, path):
                return True
    return False


def fetch(base_url: str, path: str, allowed: set[str]) -> Any | None:
    if not endpoint_allowed(path, allowed):
        return None
    url = base_url.rstrip("/") + path
    try:
        with urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"_error": str(exc), "_path": path}


def payloads(input_dir: Path) -> dict[str, Any]:
    payload_dir = input_dir / "payloads"
    result: dict[str, Any] = {}
    if payload_dir.is_dir():
        for path in sorted(payload_dir.glob("*.json")):
            result[path.name] = load_json(path)
    return result


def walk_values(obj: Any, key_names: set[str]) -> list[Any]:
    found: list[Any] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in key_names:
                found.append(value)
            found.extend(walk_values(value, key_names))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(walk_values(item, key_names))
    return found


def flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(flatten_strings(item))
        return out
    return []


def unique_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out


def detect_request(prompt: str, payload_data: dict[str, Any]) -> dict[str, Any]:
    corpus: list[Any] = [prompt, payload_data]
    portfolio_ids = re.findall(r"PF-[A-Z0-9-]+", prompt)
    quarters = re.findall(r"Q[1-4]_\d{4}", prompt)
    for item in payload_data.values():
        portfolio_ids += flatten_strings(walk_values(item, {"portfolio_id"}))
        quarters += flatten_strings(walk_values(item, {"target_quarter", "prior_quarter", "review_quarter", "quarter"}))
    index_ids: list[str] = re.findall(r"IDX_[A-Z0-9_]+", prompt)
    opp_sets: list[str] = []
    level_start = None
    level_end = None
    for item in payload_data.values():
        index_ids += flatten_strings(walk_values(item, {"index_ids", "index_universe"}))
        opp_sets += flatten_strings(
            walk_values(item, {"focus_opportunity_sets", "opportunity_sets"})
        )
        for window in walk_values(item, {"review_window"}):
            if isinstance(window, dict):
                level_start = level_start or window.get("level_start_date")
                level_end = level_end or window.get("level_end_date")
    return {
        "portfolio_ids": unique_ordered(portfolio_ids),
        "quarters": unique_ordered(quarters),
        "index_ids": unique_ordered(index_ids),
        "opportunity_sets": unique_ordered(opp_sets),
        "level_start_date": level_start,
        "level_end_date": level_end,
        "payload_names": sorted(payload_data),
        "prompt_mentions": {
            "energy": "energy" in prompt.lower(),
            "correlation": "correlation" in prompt.lower(),
            "allocation": "allocation" in prompt.lower(),
            "rebalance": "rebalance" in prompt.lower() or "rotation" in prompt.lower(),
            "committee": "committee" in prompt.lower(),
        },
        "_corpus_count": len(corpus),
    }


def simple_returns(levels: list[dict[str, Any]], start: str | None, end: str | None) -> list[float]:
    ordered = sorted(levels, key=lambda row: row["date"])
    if start:
        ordered = [row for row in ordered if row["date"] >= start]
    if end:
        ordered = [row for row in ordered if row["date"] <= end]
    returns: list[float] = []
    for prev, cur in zip(ordered, ordered[1:]):
        returns.append(cur["level"] / prev["level"] - 1.0)
    return returns


def pearson(xs: list[float], ys: list[float]) -> float | None:
    n = min(len(xs), len(ys))
    if n < 2:
        return None
    xs = xs[:n]
    ys = ys[:n]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


def correlations(index_levels: dict[str, Any], index_ids: list[str], start: str | None, end: str | None) -> dict[str, Any]:
    available = [idx for idx in index_ids if idx in index_levels]
    returns = {idx: simple_returns(index_levels[idx], start, end) for idx in available}
    pairs: list[dict[str, Any]] = []
    for left, right in itertools.combinations(sorted(available), 2):
        corr = pearson(returns[left], returns[right])
        if corr is None:
            continue
        pairs.append({"pair_id": [left, right], "correlation": round(corr, 6)})
    highest = max(pairs, key=lambda row: row["correlation"], default=None)
    lowest = min(pairs, key=lambda row: row["correlation"], default=None)
    observations = min((len(v) for v in returns.values()), default=0)
    return {
        "level_start_date": start,
        "level_end_date": end,
        "return_observations": observations,
        "pairwise": pairs,
        "highest_positive": highest,
        "lowest": lowest,
    }


def view_from_score(score: float) -> str:
    if score >= 0.30:
        return "OW"
    if score <= -0.30:
        return "UW"
    return "N"


def conviction_from_score(score: float) -> str:
    magnitude = abs(score)
    if magnitude >= 0.70:
        return "HIGH"
    if magnitude >= 0.30:
        return "MEDIUM"
    return "LOW"


def change_from_views(prior: str | None, current: str) -> str | None:
    if prior not in VIEW_RANK:
        return None
    if VIEW_RANK[current] > VIEW_RANK[prior]:
        return "UP"
    if VIEW_RANK[current] < VIEW_RANK[prior]:
        return "DOWN"
    return "UNCHANGED"


def allocation_rows(
    opp_sets: list[str],
    quarters: list[str],
    opportunity_taxonomy: list[dict[str, Any]],
    prior_views: list[dict[str, Any]],
    macro_signals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not opp_sets or not quarters:
        return []
    target_quarter = quarters[0]
    taxonomy = {row["opportunity_set"]: row for row in opportunity_taxonomy}
    prior = {
        row["opportunity_set"]: row
        for row in prior_views
        if row.get("quarter") == target_quarter
    }
    signals = {
        row["opportunity_set"]: row
        for row in macro_signals
        if row.get("quarter") == target_quarter
    }
    rows: list[dict[str, Any]] = []
    for opp in opp_sets:
        signal = signals.get(opp)
        if not signal:
            continue
        score = float(signal["score"])
        view = view_from_score(score)
        prior_view = prior.get(opp, {}).get("view")
        row = {
            "opportunity_set": opp,
            "asset_class": taxonomy.get(opp, {}).get("asset_class"),
            "prior_view": prior_view,
            "signal_score": round(score, 6),
            "view": view,
            "change": change_from_views(prior_view, view),
            "conviction": conviction_from_score(score),
            "rationale_code": signal.get("rationale_code"),
        }
        rows.append(row)
    return rows


def fixed_income_metrics(holdings: list[dict[str, Any]], bonds_by_id: dict[str, Any], issuers_by_id: dict[str, Any]) -> dict[str, Any]:
    total = 0.0
    hy = 0.0
    duration = 0.0
    ytm = 0.0
    watchlist = 0.0
    for holding in holdings:
        quantity = float(holding.get("quantity_usd_m", 0.0))
        bond = bonds_by_id.get(holding.get("instrument_id"))
        if not bond:
            continue
        total += quantity
        if bond.get("rating_bucket") == "HY":
            hy += quantity
        duration += quantity * float(bond.get("modified_duration_years", 0.0))
        ytm += quantity * float(bond.get("yield_to_maturity_pct", 0.0))
        issuer = issuers_by_id.get(bond.get("issuer_id"), {})
        if issuer.get("watchlist"):
            watchlist += quantity
    return {
        "total_market_value_usd_m": round(total, 6),
        "hy_allocation_pct": round((hy / total * 100.0) if total else 0.0, 6),
        "weighted_modified_duration_years": round((duration / total) if total else 0.0, 6),
        "weighted_yield_to_maturity_pct": round((ytm / total) if total else 0.0, 6),
        "watchlist_exposure_usd_m": round(watchlist, 6),
    }


def enrich_holdings(holdings_response: dict[str, Any], bonds_by_id: dict[str, Any], issuers_by_id: dict[str, Any], indices_by_id: dict[str, Any]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for holding in holdings_response.get("holdings", []):
        row = dict(holding)
        bond = bonds_by_id.get(holding.get("instrument_id"))
        index = indices_by_id.get(holding.get("instrument_id"))
        if bond:
            issuer = issuers_by_id.get(bond.get("issuer_id"), {})
            row["instrument"] = bond
            row["issuer"] = issuer
            row["watchlist"] = bool(issuer.get("watchlist"))
        if index:
            row["index"] = index
        enriched.append(row)
    return enriched


def candidate_bonds(bonds: list[dict[str, Any]], issuers_by_id: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bond in bonds:
        if not bond.get("candidate"):
            continue
        issuer = issuers_by_id.get(bond.get("issuer_id"), {})
        row = {
            "instrument_id": bond.get("instrument_id"),
            "issuer_id": bond.get("issuer_id"),
            "issuer_name": bond.get("issuer_name"),
            "sector": bond.get("sector"),
            "subsector": bond.get("subsector"),
            "energy_linked": bond.get("energy_linked"),
            "rating_bucket": bond.get("rating_bucket"),
            "yield_to_maturity_pct": bond.get("yield_to_maturity_pct"),
            "modified_duration_years": bond.get("modified_duration_years"),
            "theme_tags": bond.get("recommended_theme_tags", []),
            "watchlist": bool(issuer.get("watchlist")),
            "credit_outlook": issuer.get("credit_outlook"),
        }
        rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            row["watchlist"],
            not row["energy_linked"],
            row["rating_bucket"] != "IG",
            -(row["yield_to_maturity_pct"] or 0),
            row["instrument_id"] or "",
        ),
    )


def analyze(args: argparse.Namespace) -> int:
    input_dir = resolve_input_dir(Path(args.path))
    prompt = read_text(input_dir / "prompt.txt")
    payload_data = payloads(input_dir)
    request = detect_request(prompt, payload_data)
    base_url, allowed = parse_access(find_access_file(input_dir))

    endpoints = {
        "portfolios": "/api/portfolios",
        "bonds": "/api/instruments/bonds",
        "issuers": "/api/issuers",
        "energy": "/api/market/energy",
        "indices": "/api/indices",
        "index_levels": "/api/index-levels",
        "opportunity_sets": "/api/allocation/opportunity-sets",
        "prior_views": "/api/allocation/prior-views",
        "macro_signals": "/api/macro-signals",
        "policies": "/api/policies",
    }
    env = {name: fetch(base_url, path, allowed) for name, path in endpoints.items()}

    bonds = env.get("bonds") if isinstance(env.get("bonds"), list) else []
    issuers = env.get("issuers") if isinstance(env.get("issuers"), list) else []
    indices = env.get("indices") if isinstance(env.get("indices"), list) else []
    bonds_by_id = {row["instrument_id"]: row for row in bonds}
    issuers_by_id = {row["issuer_id"]: row for row in issuers}
    indices_by_id = {row["index_id"]: row for row in indices}

    portfolio_facts: dict[str, Any] = {}
    for portfolio_id in request["portfolio_ids"]:
        path = f"/api/portfolios/{portfolio_id}/holdings"
        holdings_response = fetch(base_url, path, allowed)
        if not isinstance(holdings_response, dict):
            continue
        enriched = enrich_holdings(holdings_response, bonds_by_id, issuers_by_id, indices_by_id)
        fi_holdings = [row for row in holdings_response.get("holdings", []) if row.get("instrument_id") in bonds_by_id]
        portfolio_facts[portfolio_id] = {
            "holdings_response": holdings_response,
            "enriched_holdings": enriched,
            "fixed_income_metrics": fixed_income_metrics(fi_holdings, bonds_by_id, issuers_by_id),
        }
        for row in enriched:
            if row.get("instrument_id", "").startswith("IDX_"):
                request["index_ids"] = unique_ordered(request["index_ids"] + [row["instrument_id"]])

    start = request["level_start_date"]
    end = request["level_end_date"]
    if request["index_ids"] and indices:
        meta_dates = [indices_by_id[idx] for idx in request["index_ids"] if idx in indices_by_id]
        if meta_dates:
            start = start or meta_dates[0].get("level_start_date")
            end = end or meta_dates[0].get("level_end_date")

    corr = {}
    if isinstance(env.get("index_levels"), dict) and request["index_ids"]:
        corr = correlations(env["index_levels"], request["index_ids"], start, end)

    alloc = allocation_rows(
        request["opportunity_sets"],
        request["quarters"],
        env.get("opportunity_sets") if isinstance(env.get("opportunity_sets"), list) else [],
        env.get("prior_views") if isinstance(env.get("prior_views"), list) else [],
        env.get("macro_signals") if isinstance(env.get("macro_signals"), list) else [],
    )

    output = {
        "request": request,
        "environment": {
            "base_url": base_url,
            "allowed_endpoints": sorted(allowed),
            "as_of_dates": {
                "energy": env.get("energy", {}).get("as_of_date") if isinstance(env.get("energy"), dict) else None,
            },
            "portfolio_summaries": env.get("portfolios"),
            "policies": env.get("policies"),
        },
        "portfolios": portfolio_facts,
        "candidate_bonds": candidate_bonds(bonds, issuers_by_id),
        "energy_signals": env.get("energy"),
        "correlations": corr,
        "allocation_views": alloc,
    }
    json.dump(output, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze_parser = subparsers.add_parser("analyze", help="print a task fact pack")
    analyze_parser.add_argument("path", nargs="?", default=".", help="task input directory, task directory, or cwd")
    analyze_parser.set_defaults(func=analyze)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
