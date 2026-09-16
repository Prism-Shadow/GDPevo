#!/usr/bin/env python3
"""Compute Asteria Investment Office JSON drafts from task inputs and live APIs."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, Iterable, List, Optional, Tuple


Json = Dict[str, Any]


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def resolve_input_dir(task_dir: str) -> str:
    if os.path.isfile(os.path.join(task_dir, "prompt.txt")):
        return task_dir
    nested = os.path.join(task_dir, "input")
    if os.path.isfile(os.path.join(nested, "prompt.txt")):
        return nested
    raise SystemExit(f"cannot find prompt.txt under {task_dir!r}")


def load_task(task_dir: str) -> Json:
    input_dir = resolve_input_dir(task_dir)
    payload_dir = os.path.join(input_dir, "payloads")
    payloads: Json = {}
    if os.path.isdir(payload_dir):
        for name in sorted(os.listdir(payload_dir)):
            if name.endswith(".json"):
                payloads[os.path.splitext(name)[0]] = load_json(os.path.join(payload_dir, name))
    return {
        "input_dir": input_dir,
        "prompt": read_text(os.path.join(input_dir, "prompt.txt")),
        "payloads": payloads,
        "template": payloads.get("answer_template", {}),
    }


def parse_env(env_path: str) -> Json:
    text = read_text(env_path)
    base = None
    endpoints: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("base_url:"):
            base = stripped.split(":", 1)[1].strip().rstrip("/")
        elif stripped.startswith("- "):
            endpoints.append(stripped[2:].strip())
    if not base:
        raise SystemExit(f"cannot find base_url in {env_path}")
    return {"base_url": base, "endpoints": endpoints}


def fetch_json(base_url: str, path: str, required: bool = True) -> Any:
    url = base_url.rstrip("/") + path
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        if required:
            raise SystemExit(f"failed to fetch {path}: {exc}") from exc
        return None


def walk(obj: Any) -> Iterable[Any]:
    yield obj
    if isinstance(obj, dict):
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)


def first_key(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for value in obj.values():
            found = first_key(value, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = first_key(value, key)
            if found is not None:
                return found
    return None


def all_values_for_key(obj: Any, key: str) -> List[Any]:
    values = []
    for node in walk(obj):
        if isinstance(node, dict) and key in node:
            values.append(node[key])
    return values


def required_value(template: Any, field: str) -> Any:
    if isinstance(template, dict):
        node = template.get(field)
        if isinstance(node, dict) and "required_value" in node:
            return node["required_value"]
        for value in template.values():
            found = required_value(value, field)
            if found is not None:
                return found
    elif isinstance(template, list):
        for value in template:
            found = required_value(value, field)
            if found is not None:
                return found
    return None


def template_text(task: Json) -> str:
    return json.dumps(task.get("template", {}), sort_keys=True)


def required_keys(task: Json) -> List[str]:
    tmpl = task.get("template", {})
    keys = tmpl.get("required_top_level_keys") or tmpl.get("required")
    if isinstance(keys, list):
        return list(keys)
    if isinstance(tmpl, dict):
        return [k for k, v in tmpl.items() if isinstance(v, dict) and "type" in v]
    return []


def find_portfolio_id(task: Json) -> str:
    payloads = task.get("payloads", {})
    for value in all_values_for_key(payloads, "portfolio_id"):
        if isinstance(value, str) and value.startswith("PF-"):
            return value
    value = required_value(task.get("template", {}), "portfolio_id")
    if isinstance(value, str):
        return value
    match = re.search(r"PF-[A-Z0-9-]+", task.get("prompt", ""))
    if match:
        return match.group(0)
    raise SystemExit("cannot determine portfolio_id")


def load_environment(env_path: str, task: Json) -> Json:
    env = parse_env(env_path)
    base = env["base_url"]
    data: Json = {
        "base_url": base,
        "portfolios": fetch_json(base, "/api/portfolios"),
        "bonds": fetch_json(base, "/api/instruments/bonds", required=False) or [],
        "issuers": fetch_json(base, "/api/issuers", required=False) or [],
        "energy": fetch_json(base, "/api/market/energy", required=False) or {},
        "indices": fetch_json(base, "/api/indices", required=False) or [],
        "index_levels": fetch_json(base, "/api/index-levels", required=False) or {},
        "opportunity_sets": fetch_json(base, "/api/allocation/opportunity-sets", required=False) or [],
        "prior_views": fetch_json(base, "/api/allocation/prior-views", required=False) or [],
        "macro_signals": fetch_json(base, "/api/macro-signals", required=False) or [],
    }
    if "/api/policies" in task.get("prompt", "") or any("/api/policies" in ep for ep in env["endpoints"]):
        data["policies"] = fetch_json(base, "/api/policies", required=False) or {}
    else:
        data["policies"] = fetch_json(base, "/api/policies", required=False) or {}
    data["holdings"] = {}
    for portfolio in data["portfolios"]:
        pid = portfolio.get("portfolio_id")
        if pid:
            holding = fetch_json(base, f"/api/portfolios/{pid}/holdings", required=False)
            if holding:
                data["holdings"][pid] = holding
    return data


def by_key(rows: Iterable[Json], key: str) -> Dict[str, Json]:
    return {row[key]: row for row in rows if key in row}


def policies(data: Json) -> Json:
    return data.get("policies") or {}


def policy_section(data: Json, section: str, defaults: Json) -> Json:
    result = dict(defaults)
    found = policies(data).get(section)
    if isinstance(found, dict):
        result.update(found)
    return result


def portfolio_record(data: Json, portfolio_id: str) -> Json:
    for row in data.get("portfolios", []):
        if row.get("portfolio_id") == portfolio_id:
            return row
    return {}


def bond_positions(data: Json, portfolio_id: str) -> List[Json]:
    bonds = by_key(data.get("bonds", []), "instrument_id")
    issuers = by_key(data.get("issuers", []), "issuer_id")
    rows = []
    for holding in data.get("holdings", {}).get(portfolio_id, {}).get("holdings", []):
        inst = bonds.get(holding.get("instrument_id"))
        if not inst:
            continue
        issuer = issuers.get(inst.get("issuer_id"), {})
        row = dict(inst)
        row.update({
            "quantity_usd_m": float(holding.get("quantity_usd_m", 0.0)),
            "holding_notes": holding.get("notes"),
            "sleeve": holding.get("sleeve"),
            "watchlist": bool(issuer.get("watchlist")),
            "issuer_credit_outlook": issuer.get("credit_outlook"),
        })
        rows.append(row)
    return rows


def apply_trades(data: Json, portfolio_id: str, trades: List[Json]) -> List[Json]:
    bonds = by_key(data.get("bonds", []), "instrument_id")
    issuers = by_key(data.get("issuers", []), "issuer_id")
    pos = {row["instrument_id"]: dict(row) for row in bond_positions(data, portfolio_id)}
    for trade in trades:
        inst_id = trade["instrument_id"]
        qty = float(trade.get("notional_usd_m", trade.get("quantity_usd_m", 0.0)))
        if inst_id not in pos:
            inst = dict(bonds.get(inst_id, {"instrument_id": inst_id}))
            issuer = issuers.get(inst.get("issuer_id"), {})
            inst.update({
                "quantity_usd_m": 0.0,
                "watchlist": bool(issuer.get("watchlist")),
                "issuer_credit_outlook": issuer.get("credit_outlook"),
            })
            pos[inst_id] = inst
        if trade["action"] == "BUY":
            pos[inst_id]["quantity_usd_m"] = pos[inst_id].get("quantity_usd_m", 0.0) + qty
        elif trade["action"] == "SELL":
            pos[inst_id]["quantity_usd_m"] = max(0.0, pos[inst_id].get("quantity_usd_m", 0.0) - qty)
    return [row for row in pos.values() if row.get("quantity_usd_m", 0.0) > 1e-9]


def credit_metrics(positions: List[Json]) -> Json:
    total = sum(float(row.get("quantity_usd_m", 0.0)) for row in positions)
    if total <= 0:
        return {
            "total_market_value_usd_m": 0.0,
            "hy_allocation_pct": 0.0,
            "weighted_modified_duration_years": 0.0,
            "weighted_yield_to_maturity_pct": 0.0,
            "watchlist_exposure_usd_m": 0.0,
        }
    hy = sum(float(row.get("quantity_usd_m", 0.0)) for row in positions if row.get("rating_bucket") == "HY")
    dur = sum(float(row.get("quantity_usd_m", 0.0)) * float(row.get("modified_duration_years", 0.0)) for row in positions) / total
    ytm = sum(float(row.get("quantity_usd_m", 0.0)) * float(row.get("yield_to_maturity_pct", 0.0)) for row in positions) / total
    watch = sum(float(row.get("quantity_usd_m", 0.0)) for row in positions if row.get("watchlist"))
    return {
        "total_market_value_usd_m": total,
        "hy_allocation_pct": hy / total * 100.0,
        "weighted_modified_duration_years": dur,
        "weighted_yield_to_maturity_pct": ytm,
        "watchlist_exposure_usd_m": watch,
    }


def round_num(value: float, digits: int) -> float:
    return round(float(value) + 0.0, digits)


def change_from_prior(prior: str, current: str, rank: Json) -> str:
    delta = int(rank.get(current, 0)) - int(rank.get(prior, 0))
    if delta > 0:
        return "UP"
    if delta < 0:
        return "DOWN"
    return "UNCHANGED"


def allocation_policy(data: Json) -> Json:
    return policy_section(data, "allocation_mapping", {
        "policy_id": "POL_ALLOCATION_MAPPING",
        "view_rank": {"UW": -1, "N": 0, "OW": 1},
        "view_score_thresholds": {"OW_min": 0.35, "UW_max": -0.35},
        "conviction_thresholds": {"HIGH_abs_min": 0.7, "MEDIUM_abs_min": 0.35, "LOW_abs_below": 0.35},
    })


def view_for_score(score: float, policy: Json) -> str:
    thresholds = policy.get("view_score_thresholds", {})
    if score >= float(thresholds.get("OW_min", 0.35)):
        return "OW"
    if score <= float(thresholds.get("UW_max", -0.35)):
        return "UW"
    return "N"


def conviction_for_score(score: float, policy: Json) -> str:
    thresholds = policy.get("conviction_thresholds", {})
    abs_score = abs(score)
    if abs_score >= float(thresholds.get("HIGH_abs_min", 0.7)):
        return "HIGH"
    if abs_score >= float(thresholds.get("MEDIUM_abs_min", 0.35)):
        return "MEDIUM"
    return "LOW"


def requested_sets(task: Json) -> List[str]:
    payloads = task["payloads"]
    for key in ("focus_opportunity_sets", "opportunity_sets"):
        value = first_key(payloads, key)
        if isinstance(value, list):
            return [str(v) for v in value]
    value = first_key(payloads, "allocation_review")
    if isinstance(value, dict) and isinstance(value.get("opportunity_sets"), list):
        return [str(v) for v in value["opportunity_sets"]]
    value = first_key(task["template"], "item_order")
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


def requested_quarter(task: Json) -> str:
    for key in ("target_quarter", "review_quarter", "quarter"):
        value = first_key(task["payloads"], key)
        if isinstance(value, str):
            return value
        value = required_value(task["template"], key)
        if isinstance(value, str):
            return value
    return "Q2_2026"


def prior_quarter(task: Json) -> str:
    value = first_key(task["payloads"], "prior_quarter")
    if isinstance(value, str):
        return value
    value = required_value(task["template"], "prior_quarter")
    if isinstance(value, str):
        return value
    target = requested_quarter(task)
    match = re.match(r"Q([1-4])_(\d{4})", target)
    if match:
        q = int(match.group(1))
        year = int(match.group(2))
        if q == 1:
            return f"Q4_{year - 1}"
        return f"Q{q - 1}_{year}"
    return ""


def build_allocation_rows(task: Json, data: Json, sets: List[str]) -> List[Json]:
    quarter = requested_quarter(task)
    prior_q = prior_quarter(task)
    policy = allocation_policy(data)
    rank = policy.get("view_rank", {"UW": -1, "N": 0, "OW": 1})
    macro = {(row.get("quarter"), row.get("opportunity_set")): row for row in data.get("macro_signals", [])}
    prior = {
        (row.get("quarter"), row.get("previous_quarter"), row.get("opportunity_set")): row
        for row in data.get("prior_views", [])
    }
    taxonomy = by_key(data.get("opportunity_sets", []), "opportunity_set")
    ttext = template_text(task)
    rows = []
    for opp in sets:
        sig = macro.get((quarter, opp), {})
        old = prior.get((quarter, prior_q, opp)) or prior.get((quarter, None, opp)) or {}
        score = float(sig.get("score", 0.0))
        view = view_for_score(score, policy)
        prior_view = old.get("view", "N")
        row: Json = {"opportunity_set": opp}
        if '"asset_class"' in ttext:
            row["asset_class"] = taxonomy.get(opp, {}).get("asset_class", "")
        if '"prior_view"' in ttext:
            row["prior_view"] = prior_view
        if '"signal_score"' in ttext:
            row["signal_score"] = round_num(score, 3)
        row.update({
            "view": view,
            "change": change_from_prior(prior_view, view, rank),
            "conviction": conviction_for_score(score, policy),
            "rationale_code": sig.get("rationale_code", "NEUTRAL_BALANCE"),
        })
        rows.append(row)
    return rows


def solve_allocation(task: Json, data: Json) -> Json:
    sets = requested_sets(task)
    rows = build_allocation_rows(task, data, sets)
    policy_id = policies(data).get("policy_id") or allocation_policy(data).get("policy_id")
    out: Json = {}
    task_id = required_value(task["template"], "task_id")
    if task_id is not None:
        out["task_id"] = task_id
    out["as_of_date"] = policies(data).get("as_of_date") or max((p.get("as_of_date", "") for p in data.get("portfolios", [])), default="")
    out["target_quarter"] = requested_quarter(task)
    prior_q = prior_quarter(task)
    if prior_q:
        out["prior_quarter"] = prior_q
    if "policy_id" in template_text(task):
        out["policy_id"] = policy_id
    out["allocation_views"] = rows
    if "risk_overlay" in required_keys(task) or '"risk_overlay"' in template_text(task):
        out["risk_overlay"] = build_risk_overlay(rows)
    return out


def build_risk_overlay(rows: List[Json]) -> Json:
    by_set = {row["opportunity_set"]: row for row in rows}
    codes = {row.get("rationale_code") for row in rows}
    if by_set.get("U.S. Treasuries", {}).get("view") == "OW" and by_set.get("Corporate High Yield", {}).get("view") == "UW":
        overlay = "DURATION_QUALITY_TILT"
        action = "tilt_to_duration_quality"
    elif by_set.get("Corporate High Yield", {}).get("view") == "UW" or "HY_VALUATION_RISK" in codes:
        overlay = "CREDIT_RISK_REDUCTION"
        action = "trim_credit_beta"
    elif "DOLLAR_DEFENSIVE" in codes:
        overlay = "CURRENCY_DEFENSIVE_HEDGE"
        action = "add_currency_hedge"
    elif any(row.get("view") == "OW" and row.get("asset_class") == "Equities" for row in rows):
        overlay = "EQUITY_BETA_EXTENSION"
        action = "add_cyclical_equity_beta"
    else:
        overlay = "NO_OVERLAY"
        action = "hold_policy_weights"
    priority = [
        "DURATION_SUPPORT",
        "HY_VALUATION_RISK",
        "CHINA_DEPENDENCE",
        "CREDIT_SPREAD_RISK",
        "DOLLAR_DEFENSIVE",
        "RATE_CUT_SUPPORT",
        "EUROPE_RECOVERY",
        "JAPAN_POLICY_RISK",
        "LATAM_DIVERSIFIER",
        "INDIA_OFFSET",
        "GROWTH_IMPROVES",
        "NEUTRAL_BALANCE",
    ]
    selected = [code for code in priority if code in codes and code != "NEUTRAL_BALANCE"]
    if not selected:
        selected = ["NEUTRAL_BALANCE"]
    return {"overlay_code": overlay, "primary_action": action, "rationale_codes": selected[:3]}


def level_window(task: Json, data: Json) -> Tuple[Optional[str], Optional[str]]:
    review = first_key(task["payloads"], "review_window")
    if isinstance(review, dict):
        start = review.get("level_start_date")
        end = review.get("level_end_date")
        if start or end:
            return start, end
    corr = policies(data).get("correlation", {})
    return corr.get("review_window_start"), corr.get("review_window_end")


def requested_indices(task: Json, data: Json, portfolio_id: Optional[str] = None) -> List[str]:
    payloads = task["payloads"]
    for key in ("index_universe", "index_ids"):
        value = first_key(payloads, key)
        if isinstance(value, list):
            return [str(v) for v in value]
    allowed = extract_allowed_values(task["template"], "index_set")
    if allowed:
        return allowed
    if portfolio_id:
        rows = data.get("holdings", {}).get(portfolio_id, {}).get("holdings", [])
        ids = [row["instrument_id"] for row in rows if str(row.get("instrument_id", "")).startswith("IDX_")]
        if ids:
            return ids
    return [row["index_id"] for row in data.get("indices", []) if "index_id" in row]


def returns_for_index(levels: List[Json], start: Optional[str], end: Optional[str]) -> List[float]:
    rows = sorted(levels, key=lambda row: row.get("date", ""))
    if start:
        rows = [row for row in rows if row.get("date", "") >= start]
    if end:
        rows = [row for row in rows if row.get("date", "") <= end]
    values = [float(row["level"]) for row in rows]
    return [values[i] / values[i - 1] - 1.0 for i in range(1, len(values))]


def pearson(xs: List[float], ys: List[float]) -> float:
    n = min(len(xs), len(ys))
    xs = xs[:n]
    ys = ys[:n]
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = sum((x - mx) ** 2 for x in xs)
    den_y = sum((y - my) ** 2 for y in ys)
    if den_x <= 0 or den_y <= 0:
        return 0.0
    return num / math.sqrt(den_x * den_y)


def correlations(task: Json, data: Json, index_ids: List[str]) -> Json:
    start, end = level_window(task, data)
    levels_by_id = data.get("index_levels", {})
    returns = {idx: returns_for_index(levels_by_id.get(idx, []), start, end) for idx in index_ids}
    pair_rows = []
    for a, b in itertools.combinations(sorted(index_ids), 2):
        pair_rows.append({"pair": [a, b], "correlation": pearson(returns[a], returns[b])})
    observations = min((len(v) for v in returns.values()), default=0)
    return {"start": start, "end": end, "observations": observations, "pairs": pair_rows}


def extract_allowed_values(template: Any, field: str) -> List[str]:
    if isinstance(template, dict):
        node = template.get(field)
        if isinstance(node, dict) and isinstance(node.get("allowed_values"), list):
            return [str(v) for v in node["allowed_values"]]
        if isinstance(node, dict):
            found = first_key(node, "allowed_values")
            if isinstance(found, list):
                return [str(v) for v in found]
        for value in template.values():
            found = extract_allowed_values(value, field)
            if found:
                return found
    elif isinstance(template, list):
        for value in template:
            found = extract_allowed_values(value, field)
            if found:
                return found
    return []


def concentration_details(corr: Json, threshold: float) -> Json:
    pairs = corr["pairs"]
    highest = max(pairs, key=lambda row: (row["correlation"], row["pair"])) if pairs else {"pair": [], "correlation": 0.0}
    lowest = min(pairs, key=lambda row: (row["correlation"], row["pair"])) if pairs else {"pair": [], "correlation": 0.0}
    high_pairs = [row for row in pairs if row["correlation"] >= threshold]
    china_flag = any(
        "IDX_CHINA" in row["pair"] and any(idx in row["pair"] for idx in ("IDX_EM", "IDX_AC_ASIA_PAC_EX_JP", "IDX_ACWI_IMI", "IDX_WORLD"))
        for row in high_pairs
    )
    if china_flag:
        code = "CHINA_ASIA_DEPENDENCE"
    elif high_pairs:
        code = "GLOBAL_DEVELOPED_OVERLAP"
    else:
        code = "NO_MATERIAL_CONCENTRATION"
    return {"highest": highest, "lowest": lowest, "high_pairs": high_pairs, "china_flag": china_flag, "primary_code": code}


def solve_correlation_review(task: Json, data: Json) -> Json:
    portfolio_id = find_portfolio_id(task)
    index_ids = requested_indices(task, data, portfolio_id)
    corr = correlations(task, data, index_ids)
    threshold = float(policy_section(data, "correlation", {"correlation_high_threshold": 0.8}).get("correlation_high_threshold", 0.8))
    details = concentration_details(corr, threshold)
    allowed_candidates = extract_allowed_values(task["template"], "diversification_candidates")
    candidates = diversification_candidates(details, corr, allowed_candidates)
    out: Json = {
        "portfolio_id": portfolio_id,
        "review_window": {
            "level_start_date": corr["start"],
            "level_end_date": corr["end"],
            "return_observations": corr["observations"],
        },
        "index_set": sorted(index_ids),
        "extreme_pairs": {
            "highest_positive": {
                "pair_id": details["highest"]["pair"],
                "correlation": round_num(details["highest"]["correlation"], 3),
            },
            "lowest": {
                "pair_id": details["lowest"]["pair"],
                "correlation": round_num(details["lowest"]["correlation"], 3),
            },
        },
        "concentration": {
            "china_asia_dependence_flag": bool(details["china_flag"]),
            "primary_code": details["primary_code"],
            "high_threshold_breached": bool(details["high_pairs"]),
        },
        "diversification_candidates": sorted(candidates),
        "sleeve_actions": sleeve_actions_for_correlation(data, portfolio_id, details, candidates),
    }
    return out


def diversification_candidates(details: Json, corr: Json, allowed: List[str]) -> List[str]:
    allowed_set = set(allowed)
    candidates: List[str] = []
    if details["china_flag"] and (not allowed_set or "IDX_EM_EX_CHINA" in allowed_set):
        candidates.append("IDX_EM_EX_CHINA")
    low_pair = details["lowest"]["pair"]
    for idx in low_pair:
        if idx != "IDX_CHINA" and (not allowed_set or idx in allowed_set):
            candidates.append(idx)
    if allowed:
        anchor = "IDX_CHINA" if details["china_flag"] else (details["highest"]["pair"][0] if details["highest"]["pair"] else "")
        ranked = []
        for idx in allowed:
            if idx in candidates:
                continue
            pair = sorted([anchor, idx])
            match = next((row for row in corr["pairs"] if row["pair"] == pair), None)
            ranked.append((match["correlation"] if match else 1.0, idx))
        for _, idx in sorted(ranked):
            candidates.append(idx)
            if len(candidates) >= 2:
                break
    seen = []
    for idx in candidates:
        if idx in allowed_set or not allowed:
            if idx not in seen:
                seen.append(idx)
    return seen[:2]


def sleeve_for_index(data: Json, portfolio_id: str, index_id: str) -> str:
    rows = data.get("holdings", {}).get(portfolio_id, {}).get("holdings", [])
    for row in rows:
        if row.get("instrument_id") == index_id:
            return row.get("sleeve") or index_id
    meta = by_key(data.get("indices", []), "index_id").get(index_id, {})
    return meta.get("region") or meta.get("display_name") or index_id


def sleeve_actions_for_correlation(data: Json, portfolio_id: str, details: Json, candidates: List[str]) -> List[Json]:
    target = "IDX_CHINA" if details["china_flag"] else (details["highest"]["pair"][0] if details["highest"]["pair"] else "")
    diversifier = "IDX_LATAM" if "IDX_LATAM" in candidates else (candidates[0] if candidates else "")
    actions = []
    if target:
        actions.append({"sleeve": sleeve_for_index(data, portfolio_id, target), "action": "trim", "target_index_id": target})
    if diversifier:
        actions.append({"sleeve": sleeve_for_index(data, portfolio_id, diversifier), "action": "add", "target_index_id": diversifier})
    return sorted(actions[:2], key=lambda row: row["sleeve"])


def energy_score(bond: Json, issuer: Json) -> float:
    text = " ".join(str(x) for x in [
        bond.get("instrument_id", ""),
        bond.get("issuer_name", ""),
        bond.get("subsector", ""),
        " ".join(bond.get("recommended_theme_tags", [])),
    ]).upper()
    score = float(bond.get("yield_to_maturity_pct", 0.0))
    if bond.get("rating_bucket") == "HY":
        score -= 0.8
    if bond.get("modified_duration_years", 0.0) > 5.0 or "DURATION_LONG" in text:
        score -= 0.7
    if "LNG" in text:
        score += 1.5
    if "GAS" in text:
        score += 0.5
    if "MIDSTREAM" in text:
        score += 0.35
    if issuer.get("credit_outlook") == "positive":
        score += 0.2
    if issuer.get("watchlist"):
        score -= 100.0
    return score


def solve_energy_trade(task: Json, data: Json) -> Json:
    portfolio_id = find_portfolio_id(task)
    payloads = task["payloads"]
    ticket_count = int(first_key(payloads, "ticket_count") or 2)
    total_notional = float(first_key(payloads, "total_notional_usd_m") or first_key(payloads, "total_notional") or 0.0)
    if total_notional <= 0:
        total_notional = float(first_key(payloads, "notional_usd_m") or 0.0)
    per_ticket = total_notional / ticket_count if ticket_count else 0.0
    current_positions = bond_positions(data, portfolio_id)
    held_ids = {row["instrument_id"] for row in current_positions}
    held_issuers = {row.get("issuer_id") for row in current_positions}
    issuers = by_key(data.get("issuers", []), "issuer_id")
    policy = policy_section(data, "credit_default", {
        "max_hy_allocation_pct": 20.0,
        "duration_band_years": [3.0, 5.0],
        "subsector_min_count_for_diversified": 2,
    })
    candidates = []
    for bond in data.get("bonds", []):
        issuer = issuers.get(bond.get("issuer_id"), {})
        if not bond.get("candidate"):
            continue
        if not bond.get("energy_linked"):
            continue
        if bond.get("instrument_id") in held_ids:
            continue
        if bond.get("issuer_id") in held_issuers:
            continue
        if issuer.get("watchlist"):
            continue
        row = dict(bond)
        row["_score"] = energy_score(bond, issuer)
        candidates.append(row)
    best_combo = None
    best_score = -10**9
    for combo in itertools.combinations(candidates, ticket_count):
        if len({row.get("issuer_id") for row in combo}) < len(combo):
            continue
        if len({row.get("subsector") for row in combo}) < min(len(combo), int(policy.get("subsector_min_count_for_diversified", 2))):
            continue
        trades = [{"action": "BUY", "instrument_id": row["instrument_id"], "notional_usd_m": per_ticket} for row in combo]
        metrics = credit_metrics(apply_trades(data, portfolio_id, trades))
        low, high = policy.get("duration_band_years", [3.0, 5.0])
        if metrics["hy_allocation_pct"] > float(policy.get("max_hy_allocation_pct", 20.0)):
            continue
        if not (float(low) <= metrics["weighted_modified_duration_years"] <= float(high)):
            continue
        combo_score = sum(row["_score"] for row in combo) + metrics["weighted_yield_to_maturity_pct"] * 0.2
        if combo_score > best_score:
            best_score = combo_score
            best_combo = trades
    trades = best_combo or []
    post = credit_metrics(apply_trades(data, portfolio_id, trades))
    selected = [by_key(data.get("bonds", []), "instrument_id").get(t["instrument_id"], {}) for t in trades]
    low, high = policy.get("duration_band_years", [3.0, 5.0])
    out = {
        "portfolio_id": portfolio_id,
        "as_of_date": portfolio_record(data, portfolio_id).get("as_of_date") or data.get("energy", {}).get("as_of_date"),
        "trade_package": sorted([
            {"action": t["action"], "instrument_id": t["instrument_id"], "notional_usd_m": round_num(t["notional_usd_m"], 1)}
            for t in trades
        ], key=lambda row: row["instrument_id"]),
        "post_trade_metrics": {
            "total_market_value_usd_m": round_num(post["total_market_value_usd_m"], 2),
            "hy_allocation_pct": round_num(post["hy_allocation_pct"], 2),
            "weighted_modified_duration_years": round_num(post["weighted_modified_duration_years"], 2),
            "weighted_yield_to_maturity_pct": round_num(post["weighted_yield_to_maturity_pct"], 2),
        },
        "constraint_checks": {
            "hy_cap_pass": post["hy_allocation_pct"] <= float(policy.get("max_hy_allocation_pct", 20.0)),
            "duration_band_pass": float(low) <= post["weighted_modified_duration_years"] <= float(high),
            "selected_issuer_diversification_pass": len({row.get("issuer_id") for row in selected}) == len(selected),
            "selected_subsector_diversification_pass": len({row.get("subsector") for row in selected}) >= min(len(selected), int(policy.get("subsector_min_count_for_diversified", 2))),
            "watchlist_avoidance_pass": all(not issuers.get(row.get("issuer_id"), {}).get("watchlist") for row in selected),
        },
        "sales_positioning": sales_positioning(task, selected),
        "data_precedence": "current_environment_over_stale_payload" if "stale" in json.dumps(payloads).lower() else "no_conflict_found",
    }
    return out


def sales_positioning(task: Json, selected: List[Json]) -> Json:
    context_payloads = {k: v for k, v in task.get("payloads", {}).items() if k != "answer_template"}
    context = json.dumps(context_payloads).lower()
    target = "multi_asset_income"
    if "private bank" in context or "private_bank" in context:
        target = "private_bank_income"
    elif "insurance" in context:
        target = "insurance_general_account"
    elif "pension" in context or "liability" in context:
        target = "pension_liability_matching"
    elif "endowment" in context:
        target = "endowment_opportunistic"
    text = " ".join(
        " ".join(row.get("recommended_theme_tags", [])) + " " + str(row.get("subsector", ""))
        for row in selected
    ).upper()
    if "LNG" in text or "GAS" in text:
        theme = "lng_export_tailwind"
    elif "MIDSTREAM" in text:
        theme = "midstream_stability"
    elif "REFIN" in text or "WATCHLIST" in context:
        theme = "avoid_watchlist_yield_trap"
    elif "OIL" in text:
        theme = "oil_oversupply_caution"
    else:
        theme = "transition_bond_selectivity"
    return {"target_segment": target, "theme": theme}


def solve_credit_rebalance(task: Json, data: Json) -> Json:
    portfolio_id = find_portfolio_id(task)
    policy = policy_section(data, "credit_risk_reduction", {
        "max_hy_allocation_pct": 20.0,
        "duration_band_years": [3.0, 5.0],
        "target_hy_reduction_pct": 4.0,
    })
    current = bond_positions(data, portfolio_id)
    pre = credit_metrics(current)
    sells = [row for row in current if row.get("watchlist")]
    non_watch_hy = sorted(
        [row for row in current if row.get("rating_bucket") == "HY" and not row.get("watchlist")],
        key=lambda row: (float(row.get("yield_to_maturity_pct", 0.0)), row.get("instrument_id", "")),
    )
    target_reduction = float(policy.get("target_hy_reduction_pct", 4.0))
    def post_after_sells(rows: List[Json]) -> Json:
        trades = [{"action": "SELL", "instrument_id": row["instrument_id"], "quantity_usd_m": row["quantity_usd_m"]} for row in rows]
        return credit_metrics(apply_trades(data, portfolio_id, trades))
    for row in non_watch_hy:
        post = post_after_sells(sells)
        if pre["hy_allocation_pct"] - post["hy_allocation_pct"] >= target_reduction and sells:
            break
        sells.append(row)
    if sells and non_watch_hy and all(row not in sells for row in non_watch_hy):
        sells.append(non_watch_hy[0])
    sell_total = sum(float(row.get("quantity_usd_m", 0.0)) for row in sells)
    buy_candidates = replacement_candidates(task, data, portfolio_id)
    buy_candidates = buy_candidates[: min(3, len(buy_candidates))]
    quantities = allocate_duration_biased(sell_total, buy_candidates)
    trades: List[Json] = []
    for row in sells:
        trades.append({"action": "SELL", "instrument_id": row["instrument_id"], "quantity_usd_m": round_num(row["quantity_usd_m"], 1)})
    for row, qty in zip(buy_candidates, quantities):
        if qty > 0:
            trades.append({"action": "BUY", "instrument_id": row["instrument_id"], "quantity_usd_m": round_num(qty, 1)})
    trades = sorted(trades, key=lambda row: (0 if row["action"] == "SELL" else 1, row["instrument_id"]))
    post = credit_metrics(apply_trades(data, portfolio_id, trades))
    low, high = policy.get("duration_band_years", [3.0, 5.0])
    out = {
        "task_id": required_value(task["template"], "task_id"),
        "portfolio_id": portfolio_id,
        "as_of_date": portfolio_record(data, portfolio_id).get("as_of_date"),
        "rotation": {"trades": trades},
        "risk_metrics": {
            "post_trade_hy_allocation_pct": round_num(post["hy_allocation_pct"], 2),
            "post_trade_duration_years": round_num(post["weighted_modified_duration_years"], 2),
            "hy_reduction_pct_points": round_num(pre["hy_allocation_pct"] - post["hy_allocation_pct"], 2),
            "post_trade_watchlist_exposure_usd_m": round_num(post["watchlist_exposure_usd_m"], 1),
        },
        "exception_flags": {
            "hy_cap_pass": post["hy_allocation_pct"] <= float(policy.get("max_hy_allocation_pct", 20.0)),
            "duration_band_pass": float(low) <= post["weighted_modified_duration_years"] <= float(high),
            "target_hy_reduction_met": pre["hy_allocation_pct"] - post["hy_allocation_pct"] >= target_reduction,
            "watchlist_exposure_cleared": post["watchlist_exposure_usd_m"] <= 1e-9,
        },
        "watchlist_handling": {
            "watchlist_sell_ids": sorted([row["instrument_id"] for row in sells if row.get("watchlist")]),
            "buys_avoid_watchlist": all(not row.get("watchlist") for row in buy_candidates),
        },
        "risk_note_code": "watchlist_concentration" if any(row.get("watchlist") for row in sells) else "hy_cap_pressure",
    }
    return out


def replacement_candidates(task: Json, data: Json, portfolio_id: str) -> List[Json]:
    shortlist = first_key(task["payloads"], "candidate_shortlist_from_prior_week") or []
    shortlist_ids = [row.get("instrument_id") for row in shortlist if isinstance(row, dict)]
    held_ids = {row["instrument_id"] for row in bond_positions(data, portfolio_id)}
    issuers = by_key(data.get("issuers", []), "issuer_id")
    candidates = []
    for bond in data.get("bonds", []):
        if shortlist_ids and bond.get("instrument_id") not in shortlist_ids:
            continue
        if not shortlist_ids and bond.get("instrument_id") in held_ids:
            continue
        issuer = issuers.get(bond.get("issuer_id"), {})
        if not bond.get("candidate") or issuer.get("watchlist") or bond.get("rating_bucket") != "IG":
            continue
        row = dict(bond)
        row["watchlist"] = False
        candidates.append(row)
    return sorted(candidates, key=lambda row: (-float(row.get("modified_duration_years", 0.0)), -float(row.get("yield_to_maturity_pct", 0.0)), row.get("instrument_id", "")))


def allocate_duration_biased(total: float, candidates: List[Json]) -> List[float]:
    if total <= 0 or not candidates:
        return []
    n = len(candidates)
    if n == 1:
        return [round_num(total, 1)]
    weights = [1.0 + 0.25 * ((n - 1) / 2.0 - i) for i in range(n)]
    weight_sum = sum(weights)
    raw = [total * weight / weight_sum for weight in weights]
    if abs(total - round(total)) < 1e-9:
        rounded = [float(round(x)) for x in raw]
        diff = int(round(total - sum(rounded)))
        rounded[0] += diff
        return rounded
    rounded = [round_num(x, 1) for x in raw]
    rounded[-1] = round_num(total - sum(rounded[:-1]), 1)
    return rounded


def solve_committee(task: Json, data: Json) -> Json:
    portfolio_id = find_portfolio_id(task)
    ids = requested_indices(task, data, portfolio_id)
    corr = correlations(task, data, ids)
    threshold = float(policy_section(data, "correlation", {"correlation_high_threshold": 0.8}).get("correlation_high_threshold", 0.8))
    details = concentration_details(corr, threshold)
    sets = requested_sets(task)
    alloc = build_allocation_rows(task, data, sets)
    corr_summary = [
        {"pair_role": "highest_concentration", "pair": details["highest"]["pair"], "correlation": round_num(details["highest"]["correlation"], 3)},
        {"pair_role": "best_diversifier", "pair": details["lowest"]["pair"], "correlation": round_num(details["lowest"]["correlation"], 3)},
    ]
    actions = []
    lowest_pair = set(details["lowest"]["pair"])
    for row in alloc:
        opp = row["opportunity_set"]
        view = row["view"]
        if opp == "USD" and (row.get("prior_view") == "OW" or "hedge" in task["prompt"].lower() or "hedge" in json.dumps(task["payloads"]).lower()):
            action = "hedge"
        elif opp == "Emerging Markets" and details["china_flag"]:
            action = "trim"
        elif opp == "Latin America" and "IDX_LATAM" in lowest_pair:
            action = "add"
        elif view == "OW":
            action = "add"
        elif view == "UW":
            action = "trim"
        else:
            action = "hold"
        actions.append({"opportunity_set": opp, "action": action})
    risk_flag = bool(details["high_pairs"])
    return {
        "portfolio_id": portfolio_id,
        "as_of_date": portfolio_record(data, portfolio_id).get("as_of_date") or policies(data).get("as_of_date"),
        "review_quarter": requested_quarter(task),
        "correlation_summary": corr_summary,
        "target_sleeve_actions": actions,
        "allocation_views": alloc,
        "rebalance_trigger": "correlation_cap_breach" if risk_flag else "committee_review",
        "portfolio_risk_concentration_flag": risk_flag,
        "next_step": "approve_with_monitoring" if risk_flag else "approve_rotation",
    }


def solve(task: Json, data: Json) -> Json:
    keys = set(required_keys(task))
    ttext = template_text(task)
    if "trade_package" in keys or '"trade_package"' in ttext:
        return solve_energy_trade(task, data)
    if "rotation" in keys or '"rotation"' in ttext:
        return solve_credit_rebalance(task, data)
    if "correlation_summary" in keys or '"correlation_summary"' in ttext:
        return solve_committee(task, data)
    if "extreme_pairs" in keys or '"extreme_pairs"' in ttext:
        return solve_correlation_review(task, data)
    if "allocation_views" in keys or '"allocation_views"' in ttext:
        return solve_allocation(task, data)
    raise SystemExit("template does not match a supported Asteria workflow")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    solve_p = sub.add_parser("solve", help="draft JSON answer for a supported task")
    solve_p.add_argument("--task-dir", required=True, help="task input directory or task root")
    solve_p.add_argument("--env", required=True, help="environment_access.md")
    args = parser.parse_args(argv)
    task = load_task(args.task_dir)
    data = load_environment(args.env, task)
    if args.command == "solve":
        print(json.dumps(solve(task, data), indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
