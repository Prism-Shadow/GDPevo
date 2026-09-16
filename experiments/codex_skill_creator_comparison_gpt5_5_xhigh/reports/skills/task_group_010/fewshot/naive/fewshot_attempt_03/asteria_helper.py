#!/usr/bin/env python3
"""Reusable helper for Asteria Investment Office JSON tasks.

The script reads a task input directory, fetches the live read-only Asteria API,
and prints a best-effort JSON answer for the recurring task templates. It avoids
hard-coded task outputs: all values come from the local payload/template or the
current environment.
"""

from __future__ import annotations

import itertools
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


BASE_URL = os.environ.get("ASTERIA_BASE_URL", "http://task-env:9010").rstrip("/")


def fetch_json(path: str) -> Any:
    url = f"{BASE_URL}{path if path.startswith('/') else '/' + path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.load(response)
    except urllib.error.URLError as exc:
        raise RuntimeError(f"failed to fetch {url}: {exc}") from exc


class Env:
    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}

    def get(self, path: str) -> Any:
        if path not in self._cache:
            self._cache[path] = fetch_json(path)
        return self._cache[path]

    @property
    def policies(self) -> Dict[str, Any]:
        return self.get("/api/policies")

    @property
    def bonds(self) -> List[Dict[str, Any]]:
        return self.get("/api/instruments/bonds")

    @property
    def bonds_by_id(self) -> Dict[str, Dict[str, Any]]:
        return {row["instrument_id"]: row for row in self.bonds}

    @property
    def issuers_by_id(self) -> Dict[str, Dict[str, Any]]:
        return {row["issuer_id"]: row for row in self.get("/api/issuers")}

    @property
    def index_levels(self) -> Dict[str, List[Dict[str, Any]]]:
        return self.get("/api/index-levels")

    @property
    def indices_by_id(self) -> Dict[str, Dict[str, Any]]:
        return {row["index_id"]: row for row in self.get("/api/indices")}

    @property
    def opportunity_sets_by_name(self) -> Dict[str, Dict[str, Any]]:
        return {
            row["opportunity_set"]: row
            for row in self.get("/api/allocation/opportunity-sets")
        }

    @property
    def prior_views(self) -> List[Dict[str, Any]]:
        return self.get("/api/allocation/prior-views")

    @property
    def macro_signals(self) -> List[Dict[str, Any]]:
        return self.get("/api/macro-signals")

    @property
    def energy_market(self) -> Dict[str, Any]:
        return self.get("/api/market/energy")

    def portfolio(self, portfolio_id: str) -> Dict[str, Any]:
        return self.get(f"/api/portfolios/{portfolio_id}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_input_dir(path: Path) -> Path:
    if (path / "input").is_dir():
        return path / "input"
    return path


def read_task(input_path: str) -> Dict[str, Any]:
    input_dir = normalize_input_dir(Path(input_path).resolve())
    payload_dir = input_dir / "payloads"
    payloads: Dict[str, Any] = {}
    if payload_dir.is_dir():
        for path in sorted(payload_dir.glob("*.json")):
            payloads[path.name] = load_json(path)
    prompt_path = input_dir / "prompt.txt"
    prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    if "answer_template.json" not in payloads:
        raise RuntimeError(f"missing answer_template.json under {payload_dir}")
    return {
        "input_dir": str(input_dir),
        "prompt": prompt,
        "payloads": payloads,
        "template": payloads["answer_template.json"],
        "context_payloads": {
            key: value for key, value in payloads.items() if key != "answer_template.json"
        },
    }


def walk(obj: Any) -> Iterable[Any]:
    yield obj
    if isinstance(obj, dict):
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)


def find_key(obj: Any, key: str) -> Optional[Any]:
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for value in obj.values():
            found = find_key(value, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_key(value, key)
            if found is not None:
                return found
    return None


def top_keys(template: Dict[str, Any]) -> List[str]:
    if isinstance(template.get("required"), list):
        return list(template["required"])
    if isinstance(template.get("required_top_level_keys"), list):
        return list(template["required_top_level_keys"])
    return [
        key
        for key, value in template.items()
        if isinstance(value, dict) and ("type" in value or "required_value" in value)
    ]


def field_def(template: Dict[str, Any], key: str) -> Dict[str, Any]:
    for container in ("properties", "fields", "field_definitions"):
        value = template.get(container, {})
        if isinstance(value, dict) and isinstance(value.get(key), dict):
            return value[key]
    if isinstance(template.get(key), dict):
        return template[key]
    return {}


def required_value(template: Dict[str, Any], key: str) -> Optional[Any]:
    field = field_def(template, key)
    if "required_value" in field:
        return field["required_value"]
    return find_key(field, "required_value")


def allowed_values_for(template: Dict[str, Any], path_key: str) -> List[Any]:
    field = field_def(template, path_key)
    values = find_key(field, "allowed_values")
    return list(values) if isinstance(values, list) else []


def prompt_portfolio_id(prompt: str) -> Optional[str]:
    match = re.search(r"\bPF-[A-Z]+-[A-Z]+\b", prompt)
    return match.group(0) if match else None


def find_portfolio_id(task: Dict[str, Any]) -> str:
    rv = required_value(task["template"], "portfolio_id")
    if isinstance(rv, str):
        return rv
    for payload in task["context_payloads"].values():
        value = find_key(payload, "portfolio_id")
        if isinstance(value, str):
            return value
    found = prompt_portfolio_id(task["prompt"])
    if found:
        return found
    raise RuntimeError("could not determine portfolio_id")


def first_context_payload(task: Dict[str, Any]) -> Dict[str, Any]:
    for value in task["context_payloads"].values():
        if isinstance(value, dict):
            return value
    return {}


def as_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def round_to(value: float, precision: int) -> float:
    return round(float(value) + 0.0, precision)


def simple_returns(level_rows: Sequence[Dict[str, Any]]) -> List[float]:
    ordered = sorted(level_rows, key=lambda row: row["date"])
    return [
        as_number(ordered[idx]["level"]) / as_number(ordered[idx - 1]["level"]) - 1.0
        for idx in range(1, len(ordered))
    ]


def pearson(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("correlation requires equal series with at least two observations")
    mean_l = sum(left) / len(left)
    mean_r = sum(right) / len(right)
    numerator = sum((a - mean_l) * (b - mean_r) for a, b in zip(left, right))
    denom_l = sum((a - mean_l) ** 2 for a in left)
    denom_r = sum((b - mean_r) ** 2 for b in right)
    if denom_l <= 0 or denom_r <= 0:
        return 0.0
    return numerator / math.sqrt(denom_l * denom_r)


def windowed_levels(
    env: Env,
    index_id: str,
    start_date: Optional[str],
    end_date: Optional[str],
) -> List[Dict[str, Any]]:
    rows = list(env.index_levels[index_id])
    if start_date:
        rows = [row for row in rows if row["date"] >= start_date]
    if end_date:
        rows = [row for row in rows if row["date"] <= end_date]
    return sorted(rows, key=lambda row: row["date"])


def requested_window(task: Dict[str, Any], env: Env) -> Tuple[Optional[str], Optional[str]]:
    for payload in task["context_payloads"].values():
        for node in walk(payload):
            if isinstance(node, dict):
                start = node.get("level_start_date")
                end = node.get("level_end_date")
                if isinstance(start, str) and isinstance(end, str):
                    return start, end
    policy = env.policies.get("correlation", {})
    return policy.get("review_window_start"), policy.get("review_window_end")


def requested_index_ids(task: Dict[str, Any], env: Env, portfolio: Optional[Dict[str, Any]] = None) -> List[str]:
    for payload in task["context_payloads"].values():
        for key in ("index_universe", "index_ids"):
            value = find_key(payload, key)
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                return list(value)
    allowed = allowed_values_for(task["template"], "index_set")
    if allowed:
        return list(allowed)
    if portfolio:
        ids = [
            row["instrument_id"]
            for row in portfolio.get("holdings", [])
            if str(row.get("instrument_id", "")).startswith("IDX_")
        ]
        if ids:
            return ids
    return sorted(env.index_levels)


def correlation_pairs(
    env: Env,
    index_ids: Sequence[str],
    start_date: Optional[str],
    end_date: Optional[str],
) -> List[Dict[str, Any]]:
    returns = {
        index_id: simple_returns(windowed_levels(env, index_id, start_date, end_date))
        for index_id in index_ids
    }
    pairs: List[Dict[str, Any]] = []
    for left, right in itertools.combinations(sorted(index_ids), 2):
        pairs.append(
            {
                "pair": [left, right],
                "correlation": pearson(returns[left], returns[right]),
            }
        )
    return pairs


def pair_lookup(pairs: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], float]:
    return {tuple(row["pair"]): row["correlation"] for row in pairs}


def corr_between(pairs: Sequence[Dict[str, Any]], left: str, right: str) -> Optional[float]:
    a, b = sorted([left, right])
    return pair_lookup(pairs).get((a, b))


def highest_pair(pairs: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return max(pairs, key=lambda row: (row["correlation"], row["pair"]))


def lowest_pair(pairs: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return min(pairs, key=lambda row: (row["correlation"], row["pair"]))


def correlation_policy(env: Env) -> Dict[str, Any]:
    return env.policies.get("correlation", {})


def concentration_code(
    env: Env,
    index_ids: Sequence[str],
    pairs: Sequence[Dict[str, Any]],
) -> Tuple[bool, str, bool]:
    high_threshold = as_number(correlation_policy(env).get("correlation_high_threshold"), 0.8)
    high_breached = any(row["correlation"] >= high_threshold for row in pairs)
    ids = set(index_ids)
    china_pairs = [("IDX_CHINA", "IDX_EM"), ("IDX_CHINA", "IDX_AC_ASIA_PAC_EX_JP")]
    china_flag = any(
        left in ids
        and right in ids
        and (corr_between(pairs, left, right) or -1.0) >= high_threshold
        for left, right in china_pairs
    )
    if china_flag:
        return True, "CHINA_ASIA_DEPENDENCE", high_breached
    developed_ids = {"IDX_ACWI_IMI", "IDX_WORLD", "IDX_EAFE"}
    if high_breached and len(ids & developed_ids) >= 2:
        return False, "GLOBAL_DEVELOPED_OVERLAP", True
    return False, "NO_MATERIAL_CONCENTRATION", high_breached


def diversification_candidates(
    task: Dict[str, Any],
    pairs: Sequence[Dict[str, Any]],
    primary_code: str,
) -> List[str]:
    allowed = allowed_values_for(task["template"], "diversification_candidates")
    if not allowed:
        return []
    chosen: List[str] = []
    if primary_code == "CHINA_ASIA_DEPENDENCE" and "IDX_EM_EX_CHINA" in allowed:
        chosen.append("IDX_EM_EX_CHINA")
    best = None
    best_corr = float("inf")
    concentration_refs = ["IDX_CHINA", "IDX_EM", "IDX_AC_ASIA_PAC_EX_JP"]
    for candidate in allowed:
        if candidate in chosen:
            continue
        corr_values = [
            corr_between(pairs, candidate, ref)
            for ref in concentration_refs
            if ref != candidate and corr_between(pairs, candidate, ref) is not None
        ]
        if not corr_values:
            continue
        candidate_score = min(corr_values)
        if candidate_score < best_corr:
            best = candidate
            best_corr = candidate_score
    if best is not None:
        chosen.append(best)
    return sorted(dict.fromkeys(chosen))


def sleeve_for_index(portfolio: Dict[str, Any], env: Env, index_id: str) -> str:
    for holding in portfolio.get("holdings", []):
        if holding.get("instrument_id") == index_id and holding.get("sleeve"):
            return str(holding["sleeve"])
    index = env.indices_by_id.get(index_id, {})
    return str(index.get("region") or index.get("display_name") or index_id)


def correlation_sleeve_actions(
    task: Dict[str, Any],
    env: Env,
    portfolio: Dict[str, Any],
    pairs: Sequence[Dict[str, Any]],
    primary_code: str,
) -> List[Dict[str, Any]]:
    target_allowed = []
    field = field_def(task["template"], "sleeve_actions")
    found = find_key(field, "target_index_allowed_values")
    if isinstance(found, list):
        target_allowed = list(found)
    allowed_set = set(target_allowed)
    actions: List[Dict[str, Any]] = []
    if primary_code == "CHINA_ASIA_DEPENDENCE" and (not allowed_set or "IDX_CHINA" in allowed_set):
        actions.append(
            {
                "sleeve": sleeve_for_index(portfolio, env, "IDX_CHINA"),
                "action": "trim",
                "target_index_id": "IDX_CHINA",
            }
        )
    low = lowest_pair(pairs)
    diversifier = None
    already_targeted = {row["target_index_id"] for row in actions}
    for idx in low["pair"]:
        if idx not in already_targeted and (not allowed_set or idx in allowed_set):
            diversifier = idx
            break
    if diversifier is None:
        cands = diversification_candidates(task, pairs, primary_code)
        if cands:
            diversifier = cands[-1]
    if diversifier:
        actions.append(
            {
                "sleeve": sleeve_for_index(portfolio, env, diversifier),
                "action": "add",
                "target_index_id": diversifier,
            }
        )
    deduped = {row["target_index_id"]: row for row in actions}
    return sorted(deduped.values(), key=lambda row: row["sleeve"])[:2]


def solve_correlation_review(task: Dict[str, Any], env: Env) -> Dict[str, Any]:
    portfolio_id = find_portfolio_id(task)
    portfolio = env.portfolio(portfolio_id)
    start, end = requested_window(task, env)
    index_ids = requested_index_ids(task, env, portfolio)
    pairs = correlation_pairs(env, index_ids, start, end)
    high = highest_pair(pairs)
    low = lowest_pair(pairs)
    china_flag, primary_code, high_breached = concentration_code(env, index_ids, pairs)
    levels = windowed_levels(env, index_ids[0], start, end)
    return {
        "portfolio_id": portfolio_id,
        "review_window": {
            "level_start_date": start,
            "level_end_date": end,
            "return_observations": max(0, len(levels) - 1),
        },
        "index_set": sorted(index_ids),
        "extreme_pairs": {
            "highest_positive": {
                "pair_id": high["pair"],
                "correlation": round_to(high["correlation"], 3),
            },
            "lowest": {
                "pair_id": low["pair"],
                "correlation": round_to(low["correlation"], 3),
            },
        },
        "concentration": {
            "china_asia_dependence_flag": china_flag,
            "primary_code": primary_code,
            "high_threshold_breached": high_breached,
        },
        "diversification_candidates": diversification_candidates(task, pairs, primary_code),
        "sleeve_actions": correlation_sleeve_actions(task, env, portfolio, pairs, primary_code),
    }


VIEW_RANK = {"UW": -1, "N": 0, "OW": 1}


def requested_quarter(task: Dict[str, Any]) -> Optional[str]:
    for key in ("target_quarter", "review_quarter"):
        rv = required_value(task["template"], key)
        if isinstance(rv, str):
            return rv
    for payload in task["context_payloads"].values():
        for key in ("target_quarter", "review_quarter", "quarter"):
            value = find_key(payload, key)
            if isinstance(value, str) and re.match(r"Q[1-4]_\d{4}", value):
                return value
    return None


def prior_quarter(task: Dict[str, Any], target_quarter: Optional[str], env: Env) -> Optional[str]:
    rv = required_value(task["template"], "prior_quarter")
    if isinstance(rv, str):
        return rv
    for payload in task["context_payloads"].values():
        value = find_key(payload, "prior_quarter")
        if isinstance(value, str):
            return value
    if target_quarter:
        for row in env.prior_views:
            if row.get("quarter") == target_quarter:
                return row.get("previous_quarter")
    return None


def requested_opportunity_sets(task: Dict[str, Any]) -> List[str]:
    for payload in task["context_payloads"].values():
        for key in ("focus_opportunity_sets", "opportunity_sets"):
            value = find_key(payload, key)
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                return list(value)
    values = allowed_values_for(task["template"], "allocation_views")
    return list(values)


def macro_for(env: Env, opportunity_set: str, quarter: Optional[str]) -> Dict[str, Any]:
    rows = [
        row
        for row in env.macro_signals
        if row.get("opportunity_set") == opportunity_set
        and (quarter is None or row.get("quarter") == quarter)
    ]
    if rows:
        return rows[0]
    raise RuntimeError(f"missing macro signal for {opportunity_set} {quarter or ''}".strip())


def prior_for(env: Env, opportunity_set: str, quarter: Optional[str]) -> Dict[str, Any]:
    rows = [
        row
        for row in env.prior_views
        if row.get("opportunity_set") == opportunity_set
        and (quarter is None or row.get("quarter") == quarter)
    ]
    if rows:
        return rows[0]
    return {"view": "N", "conviction": "LOW", "previous_quarter": None}


def view_from_score(env: Env, score: float) -> str:
    thresholds = env.policies.get("allocation_mapping", {}).get("view_score_thresholds", {})
    if score >= as_number(thresholds.get("OW_min"), 0.35):
        return "OW"
    if score <= as_number(thresholds.get("UW_max"), -0.35):
        return "UW"
    return "N"


def conviction_from_score(env: Env, score: float) -> str:
    thresholds = env.policies.get("allocation_mapping", {}).get("conviction_thresholds", {})
    abs_score = abs(score)
    if abs_score >= as_number(thresholds.get("HIGH_abs_min"), 0.7):
        return "HIGH"
    if abs_score >= as_number(thresholds.get("MEDIUM_abs_min"), 0.35):
        return "MEDIUM"
    return "LOW"


def view_change(prior_view: str, view: str) -> str:
    delta = VIEW_RANK.get(view, 0) - VIEW_RANK.get(prior_view, 0)
    if delta > 0:
        return "UP"
    if delta < 0:
        return "DOWN"
    return "UNCHANGED"


def allocation_rows(task: Dict[str, Any], env: Env, include_prior: bool = False, include_score: bool = False) -> List[Dict[str, Any]]:
    quarter = requested_quarter(task)
    rows: List[Dict[str, Any]] = []
    for opportunity_set in requested_opportunity_sets(task):
        signal = macro_for(env, opportunity_set, quarter)
        prior = prior_for(env, opportunity_set, quarter)
        score = as_number(signal.get("score"))
        view = view_from_score(env, score)
        row: Dict[str, Any] = {
            "opportunity_set": opportunity_set,
        }
        taxonomy = env.opportunity_sets_by_name.get(opportunity_set, {})
        if not include_prior:
            row["asset_class"] = taxonomy.get("asset_class")
        if include_prior:
            row["prior_view"] = prior.get("view", "N")
        if include_score:
            row["signal_score"] = round_to(score, 3)
        row.update(
            {
                "view": view,
                "change": view_change(str(prior.get("view", "N")), view),
                "conviction": conviction_from_score(env, score),
                "rationale_code": signal.get("rationale_code"),
            }
        )
        rows.append(row)
    return rows


def risk_overlay(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    rationale_by_set = {row["opportunity_set"]: row.get("rationale_code") for row in rows}
    views_by_set = {row["opportunity_set"]: row.get("view") for row in rows}
    rationale_priority: List[str] = []

    def add_reason(code: Optional[str]) -> None:
        if code and code not in rationale_priority:
            rationale_priority.append(code)

    if views_by_set.get("U.S. Treasuries") == "OW":
        add_reason(rationale_by_set.get("U.S. Treasuries"))
    if views_by_set.get("Corporate High Yield") == "UW":
        add_reason(rationale_by_set.get("Corporate High Yield"))
    if views_by_set.get("Emerging Markets") == "UW":
        add_reason(rationale_by_set.get("Emerging Markets"))
    for row in rows:
        if row.get("view") != "N":
            add_reason(row.get("rationale_code"))

    has_duration_support = any(
        row.get("opportunity_set") in {"U.S. Treasuries", "German Bunds", "U.K. Gilts", "Canada Bonds"}
        and row.get("view") == "OW"
        for row in rows
    )
    has_hy_risk = views_by_set.get("Corporate High Yield") == "UW"
    has_currency_defense = any(
        row.get("asset_class") == "Currency"
        and row.get("rationale_code") == "DOLLAR_DEFENSIVE"
        for row in rows
    )
    has_equity_extension = any(
        row.get("asset_class") == "Equities" and row.get("view") == "OW"
        for row in rows
    )

    if has_duration_support and has_hy_risk:
        code = "DURATION_QUALITY_TILT"
        action = "tilt_to_duration_quality"
    elif has_hy_risk:
        code = "CREDIT_RISK_REDUCTION"
        action = "trim_credit_beta"
    elif has_currency_defense:
        code = "CURRENCY_DEFENSIVE_HEDGE"
        action = "add_currency_hedge"
    elif has_equity_extension:
        code = "EQUITY_BETA_EXTENSION"
        action = "add_cyclical_equity_beta"
    else:
        code = "NO_OVERLAY"
        action = "hold_policy_weights"

    return {
        "overlay_code": code,
        "primary_action": action,
        "rationale_codes": rationale_priority[:3],
    }


def solve_allocation(task: Dict[str, Any], env: Env) -> Dict[str, Any]:
    quarter = requested_quarter(task)
    rows = allocation_rows(task, env)
    answer: Dict[str, Any] = {}
    task_id = required_value(task["template"], "task_id")
    if isinstance(task_id, str):
        answer["task_id"] = task_id
    answer.update(
        {
            "as_of_date": env.policies.get("as_of_date"),
            "target_quarter": quarter,
            "prior_quarter": prior_quarter(task, quarter, env),
            "policy_id": env.policies.get("policy_id"),
            "allocation_views": rows,
            "risk_overlay": risk_overlay(rows),
        }
    )
    return answer


def holding_quantities(portfolio: Dict[str, Any]) -> Dict[str, float]:
    return {
        row["instrument_id"]: as_number(row.get("quantity_usd_m"))
        for row in portfolio.get("holdings", [])
    }


def apply_trade_quantities(quantities: Dict[str, float], trades: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    post = dict(quantities)
    for trade in trades:
        instrument_id = trade["instrument_id"]
        qty = as_number(trade.get("quantity_usd_m", trade.get("notional_usd_m")))
        if trade["action"] == "SELL":
            qty = -qty
        elif trade["action"] not in {"BUY", "HOLD", "NO_TRADE"}:
            continue
        post[instrument_id] = round_to(post.get(instrument_id, 0.0) + qty, 10)
        if abs(post[instrument_id]) < 1e-9:
            del post[instrument_id]
    return post


def issuer_watchlist(env: Env, instrument_id: str) -> bool:
    bond = env.bonds_by_id.get(instrument_id)
    if not bond:
        return False
    issuer = env.issuers_by_id.get(bond.get("issuer_id"), {})
    return bool(issuer.get("watchlist"))


def credit_metrics(env: Env, quantities: Dict[str, float]) -> Dict[str, float]:
    total = sum(qty for qty in quantities.values() if qty > 0)
    bond_total = sum(qty for iid, qty in quantities.items() if qty > 0 and iid in env.bonds_by_id)
    metric_denominator = bond_total or total or 1.0
    hy = 0.0
    duration = 0.0
    ytm = 0.0
    watchlist = 0.0
    for instrument_id, qty in quantities.items():
        if qty <= 0:
            continue
        bond = env.bonds_by_id.get(instrument_id)
        if not bond:
            continue
        if bond.get("rating_bucket") == "HY":
            hy += qty
        if issuer_watchlist(env, instrument_id):
            watchlist += qty
        duration += qty * as_number(bond.get("modified_duration_years"))
        ytm += qty * as_number(bond.get("yield_to_maturity_pct"))
    return {
        "total_market_value_usd_m": total,
        "hy_allocation_pct": 100.0 * hy / (total or 1.0),
        "weighted_modified_duration_years": duration / metric_denominator,
        "weighted_yield_to_maturity_pct": ytm / metric_denominator,
        "watchlist_exposure_usd_m": watchlist,
    }


def current_constraints(portfolio: Dict[str, Any], env: Env) -> Dict[str, Any]:
    constraints = dict(portfolio.get("constraints") or {})
    policy_id = constraints.get("policy_id")
    if policy_id:
        for value in env.policies.values():
            if isinstance(value, dict) and value.get("policy_id") == policy_id:
                merged = dict(value)
                merged.update(constraints)
                return merged
    return constraints


def selected_issuer_exposure_pass(
    env: Env,
    quantities: Dict[str, float],
    selected_ids: Sequence[str],
    limit_pct: float,
) -> bool:
    if not selected_ids or limit_pct <= 0:
        return True
    total = sum(qty for qty in quantities.values() if qty > 0) or 1.0
    selected_issuers = {
        env.bonds_by_id[iid].get("issuer_id")
        for iid in selected_ids
        if iid in env.bonds_by_id
    }
    exposure: Dict[str, float] = {issuer_id: 0.0 for issuer_id in selected_issuers}
    for instrument_id, qty in quantities.items():
        bond = env.bonds_by_id.get(instrument_id)
        if bond and bond.get("issuer_id") in exposure:
            exposure[bond["issuer_id"]] += max(0.0, qty)
    return all(100.0 * value / total <= limit_pct + 1e-9 for value in exposure.values())


def credit_constraint_flags(
    env: Env,
    quantities: Dict[str, float],
    constraints: Dict[str, Any],
    selected_ids: Sequence[str] = (),
    current_hy_pct: Optional[float] = None,
) -> Dict[str, bool]:
    metrics = credit_metrics(env, quantities)
    low, high = constraints.get("duration_band_years", [float("-inf"), float("inf")])
    max_hy = as_number(constraints.get("max_hy_allocation_pct"), float("inf"))
    target_reduction = as_number(constraints.get("target_hy_reduction_pct"), 0.0)
    selected_subsectors = {
        env.bonds_by_id[iid].get("subsector")
        for iid in selected_ids
        if iid in env.bonds_by_id
    }
    min_subsectors = int(as_number(constraints.get("subsector_min_count_for_diversified"), 0))
    issuer_limit = as_number(constraints.get("issuer_concentration_limit_pct"), 0.0)
    reduction = (current_hy_pct if current_hy_pct is not None else metrics["hy_allocation_pct"]) - metrics["hy_allocation_pct"]
    return {
        "hy_cap_pass": metrics["hy_allocation_pct"] <= max_hy + 1e-9,
        "duration_band_pass": low <= metrics["weighted_modified_duration_years"] <= high,
        "selected_issuer_diversification_pass": selected_issuer_exposure_pass(
            env, quantities, selected_ids, issuer_limit
        ),
        "selected_subsector_diversification_pass": (
            len(selected_subsectors) >= min_subsectors if selected_ids and min_subsectors else True
        ),
        "watchlist_avoidance_pass": all(not issuer_watchlist(env, iid) for iid in selected_ids),
        "target_hy_reduction_met": reduction + 1e-9 >= target_reduction,
        "watchlist_exposure_cleared": metrics["watchlist_exposure_usd_m"] <= 1e-9,
    }


def payload_text(task: Dict[str, Any]) -> str:
    return json.dumps(task["context_payloads"], sort_keys=True).lower() + "\n" + task["prompt"].lower()


def data_precedence(task: Dict[str, Any], env_as_of: str) -> str:
    text = payload_text(task)
    if "stale" in text or "current environment" in text:
        return "current_environment_over_stale_payload"
    dates = re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", text)
    if any(date < env_as_of for date in dates):
        return "current_environment_over_stale_payload"
    return "no_conflict_found"


def requested_trade_count(task: Dict[str, Any]) -> int:
    for payload in task["context_payloads"].values():
        value = find_key(payload, "ticket_count")
        if value is not None:
            return int(value)
    length = find_key(field_def(task["template"], "trade_package"), "length")
    return int(length) if length else 2


def requested_buy_notional(task: Dict[str, Any]) -> float:
    for payload in task["context_payloads"].values():
        value = find_key(payload, "total_notional_usd_m")
        if value is not None:
            return as_number(value)
    match = re.search(r"USD\s+([0-9]+(?:\.[0-9]+)?)\s+million", task["prompt"], re.I)
    if match:
        return float(match.group(1))
    return 0.0


def theme_bonus(task: Dict[str, Any], env: Env, bond: Dict[str, Any]) -> float:
    text = payload_text(task)
    tags = " ".join(str(tag).lower() for tag in bond.get("recommended_theme_tags", []))
    issuer = env.issuers_by_id.get(bond.get("issuer_id"), {})
    score = 0.0
    if ("lng" in text or "gas" in text) and ("lng" in tags or "gas" in tags or "Natural Gas/LNG".lower() in str(bond.get("subsector", "")).lower()):
        score += 2.0
    if "midstream" in text and ("midstream" in tags or "midstream" in str(bond.get("subsector", "")).lower()):
        score += 0.8
    if "renewable" in text and "renewable" in (tags + str(bond.get("subsector", "")).lower()):
        score += 0.4
    if bond.get("rating_bucket") == "IG" and ("client" in text or "pitch" in text):
        score += 0.6
    if issuer.get("credit_outlook") == "positive":
        score += 0.3
    if bond.get("rating_bucket") == "HY":
        score -= 0.8
    if "DURATION_LONG" in bond.get("recommended_theme_tags", []):
        score -= 1.5
    return score


def solve_energy_trade(task: Dict[str, Any], env: Env) -> Dict[str, Any]:
    portfolio_id = find_portfolio_id(task)
    portfolio = env.portfolio(portfolio_id)
    constraints = current_constraints(portfolio, env)
    quantities = holding_quantities(portfolio)
    count = requested_trade_count(task)
    total_notional = requested_buy_notional(task)
    per_ticket = total_notional / count if count else 0.0
    text = payload_text(task)
    candidates = [
        bond
        for bond in env.bonds
        if bond.get("candidate")
        and (not ("energy" in text or "lng" in text or "gas" in text) or bond.get("energy_linked"))
        and not issuer_watchlist(env, bond["instrument_id"])
    ]
    best: Optional[Tuple[float, List[Dict[str, Any]], Dict[str, float]]] = None
    for combo in itertools.combinations(candidates, count):
        trades = [
            {
                "action": "BUY",
                "instrument_id": bond["instrument_id"],
                "notional_usd_m": round_to(per_ticket, 1),
            }
            for bond in combo
        ]
        post = apply_trade_quantities(quantities, trades)
        flags = credit_constraint_flags(
            env, post, constraints, [bond["instrument_id"] for bond in combo]
        )
        if not (
            flags["hy_cap_pass"]
            and flags["duration_band_pass"]
            and flags["selected_issuer_diversification_pass"]
            and flags["selected_subsector_diversification_pass"]
            and flags["watchlist_avoidance_pass"]
        ):
            continue
        metrics = credit_metrics(env, post)
        score = sum(as_number(bond.get("yield_to_maturity_pct")) + theme_bonus(task, env, bond) for bond in combo)
        duration_band = constraints.get("duration_band_years", [0.0, float("inf")])
        instrument_high = as_number(duration_band[1], float("inf"))
        score -= sum(
            max(0.0, as_number(bond.get("modified_duration_years")) - instrument_high) * 2.0
            for bond in combo
        )
        score -= max(0.0, metrics["hy_allocation_pct"] - 0.8 * as_number(constraints.get("max_hy_allocation_pct"), 20.0)) * 0.15
        score += len({bond.get("subsector") for bond in combo}) * 0.15
        if best is None or score > best[0]:
            best = (score, trades, post)
    if best is None:
        raise RuntimeError("no valid energy trade package found")
    trades = sorted(best[1], key=lambda row: row["instrument_id"])
    post_metrics = credit_metrics(env, best[2])
    flags = credit_constraint_flags(env, best[2], constraints, [row["instrument_id"] for row in trades])
    selected_bonds = [env.bonds_by_id[row["instrument_id"]] for row in trades]
    theme = "midstream_stability"
    if any("LNG" in " ".join(bond.get("recommended_theme_tags", [])) or bond.get("subsector") == "Natural Gas/LNG" for bond in selected_bonds):
        theme = "lng_export_tailwind"
    elif any(issuer_watchlist(env, row["instrument_id"]) for row in trades):
        theme = "avoid_watchlist_yield_trap"
    elif any("Renewables" == bond.get("subsector") for bond in selected_bonds):
        theme = "transition_bond_selectivity"
    target_segment = "multi_asset_income"
    text = payload_text(task)
    if "insurance" in text:
        target_segment = "insurance_general_account"
    elif "pension" in text:
        target_segment = "pension_liability_matching"
    elif "private bank" in text or "private_bank" in text:
        target_segment = "private_bank_income"
    elif "endowment" in text:
        target_segment = "endowment_opportunistic"
    return {
        "portfolio_id": portfolio_id,
        "as_of_date": portfolio.get("as_of_date"),
        "trade_package": trades,
        "post_trade_metrics": {
            "total_market_value_usd_m": round_to(post_metrics["total_market_value_usd_m"], 2),
            "hy_allocation_pct": round_to(post_metrics["hy_allocation_pct"], 2),
            "weighted_modified_duration_years": round_to(post_metrics["weighted_modified_duration_years"], 2),
            "weighted_yield_to_maturity_pct": round_to(post_metrics["weighted_yield_to_maturity_pct"], 2),
        },
        "constraint_checks": {
            "hy_cap_pass": flags["hy_cap_pass"],
            "duration_band_pass": flags["duration_band_pass"],
            "selected_issuer_diversification_pass": flags["selected_issuer_diversification_pass"],
            "selected_subsector_diversification_pass": flags["selected_subsector_diversification_pass"],
            "watchlist_avoidance_pass": flags["watchlist_avoidance_pass"],
        },
        "sales_positioning": {
            "target_segment": target_segment,
            "theme": theme,
        },
        "data_precedence": data_precedence(task, str(portfolio.get("as_of_date", ""))),
    }


def ordered_candidate_ids(task: Dict[str, Any]) -> List[str]:
    for payload in task["context_payloads"].values():
        for key, value in walk_key_values(payload):
            if "candidate" in key.lower() and isinstance(value, list):
                ids = [
                    row.get("instrument_id")
                    for row in value
                    if isinstance(row, dict) and isinstance(row.get("instrument_id"), str)
                ]
                if ids:
                    return ids
    return []


def walk_key_values(obj: Any) -> Iterable[Tuple[str, Any]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key, value
            yield from walk_key_values(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk_key_values(value)


def allocate_proceeds(total: float, selected_ids: Sequence[str]) -> Dict[str, float]:
    if not selected_ids:
        return {}
    n = len(selected_ids)
    if n == 1:
        return {selected_ids[0]: round_to(total, 1)}
    if n == 2:
        weights = [0.5, 0.5]
    elif n == 3:
        weights = [0.4, 0.35, 0.25]
    else:
        raw = list(range(n, 0, -1))
        denom = sum(raw)
        weights = [value / denom for value in raw]
    allocations = [round_to(total * weight, 1) for weight in weights]
    residual = round_to(total - sum(allocations), 1)
    allocations[0] = round_to(allocations[0] + residual, 1)
    return {instrument_id: qty for instrument_id, qty in zip(selected_ids, allocations)}


def solve_credit_rotation(task: Dict[str, Any], env: Env) -> Dict[str, Any]:
    portfolio_id = find_portfolio_id(task)
    portfolio = env.portfolio(portfolio_id)
    constraints = current_constraints(portfolio, env)
    quantities = holding_quantities(portfolio)
    current = credit_metrics(env, quantities)
    sells: List[Dict[str, Any]] = []

    for instrument_id, qty in sorted(quantities.items()):
        if instrument_id in env.bonds_by_id and issuer_watchlist(env, instrument_id):
            sells.append(
                {
                    "action": "SELL",
                    "instrument_id": instrument_id,
                    "quantity_usd_m": round_to(qty, 1),
                }
            )

    def post_after_sells(extra_sells: Sequence[Dict[str, Any]]) -> Dict[str, float]:
        return apply_trade_quantities(quantities, [*sells, *extra_sells])

    extra: List[Dict[str, Any]] = []
    hy_holdings = [
        (instrument_id, qty)
        for instrument_id, qty in quantities.items()
        if instrument_id in env.bonds_by_id
        and env.bonds_by_id[instrument_id].get("rating_bucket") == "HY"
        and not issuer_watchlist(env, instrument_id)
    ]
    hy_holdings.sort(key=lambda item: (item[1], env.bonds_by_id[item[0]].get("yield_to_maturity_pct", 0), item[0]))
    for instrument_id, qty in hy_holdings:
        post = post_after_sells(extra)
        flags = credit_constraint_flags(env, post, constraints, current_hy_pct=current["hy_allocation_pct"])
        if flags["hy_cap_pass"] and flags["target_hy_reduction_met"]:
            break
        extra.append(
            {
                "action": "SELL",
                "instrument_id": instrument_id,
                "quantity_usd_m": round_to(qty, 1),
            }
        )
    sells.extend(extra)

    proceeds = sum(row["quantity_usd_m"] for row in sells)
    local_candidates = ordered_candidate_ids(task)
    if local_candidates:
        candidate_pool = [env.bonds_by_id[iid] for iid in local_candidates if iid in env.bonds_by_id]
    else:
        candidate_pool = list(env.bonds)
    candidate_pool = [
        bond
        for bond in candidate_pool
        if bond.get("candidate")
        and bond.get("rating_bucket") == "IG"
        and not issuer_watchlist(env, bond["instrument_id"])
        and bond["instrument_id"] not in quantities
    ]
    if not candidate_pool:
        candidate_pool = [
            bond
            for bond in env.bonds
            if bond.get("candidate")
            and bond.get("rating_bucket") == "IG"
            and not issuer_watchlist(env, bond["instrument_id"])
            and bond["instrument_id"] not in quantities
        ]
    selected = candidate_pool[:3] if local_candidates else sorted(
        candidate_pool,
        key=lambda bond: (
            -as_number(bond.get("yield_to_maturity_pct")),
            abs(as_number(bond.get("modified_duration_years")) - 4.25),
            bond["instrument_id"],
        ),
    )[:3]
    allocations = allocate_proceeds(proceeds, [bond["instrument_id"] for bond in selected])
    buys = [
        {
            "action": "BUY",
            "instrument_id": instrument_id,
            "quantity_usd_m": qty,
        }
        for instrument_id, qty in allocations.items()
        if qty > 0
    ]
    trades = sorted(sells, key=lambda row: row["instrument_id"]) + sorted(buys, key=lambda row: row["instrument_id"])
    post_quantities = apply_trade_quantities(quantities, trades)
    post = credit_metrics(env, post_quantities)
    flags = credit_constraint_flags(
        env,
        post_quantities,
        constraints,
        [row["instrument_id"] for row in buys],
        current["hy_allocation_pct"],
    )
    watchlist_sells = sorted(
        row["instrument_id"]
        for row in sells
        if issuer_watchlist(env, row["instrument_id"])
    )
    if watchlist_sells:
        note = "watchlist_concentration"
    elif current["hy_allocation_pct"] > as_number(constraints.get("max_hy_allocation_pct"), 100.0):
        note = "hy_cap_pressure"
    elif not flags["duration_band_pass"]:
        note = "duration_preservation"
    elif trades:
        note = "carry_tradeoff"
    else:
        note = "no_action"
    answer: Dict[str, Any] = {}
    task_id = required_value(task["template"], "task_id")
    if isinstance(task_id, str):
        answer["task_id"] = task_id
    answer.update(
        {
            "portfolio_id": portfolio_id,
            "as_of_date": portfolio.get("as_of_date"),
            "rotation": {"trades": trades},
            "risk_metrics": {
                "post_trade_hy_allocation_pct": round_to(post["hy_allocation_pct"], 2),
                "post_trade_duration_years": round_to(post["weighted_modified_duration_years"], 2),
                "hy_reduction_pct_points": round_to(current["hy_allocation_pct"] - post["hy_allocation_pct"], 2),
                "post_trade_watchlist_exposure_usd_m": round_to(post["watchlist_exposure_usd_m"], 1),
            },
            "exception_flags": {
                "hy_cap_pass": flags["hy_cap_pass"],
                "duration_band_pass": flags["duration_band_pass"],
                "target_hy_reduction_met": flags["target_hy_reduction_met"],
                "watchlist_exposure_cleared": flags["watchlist_exposure_cleared"],
            },
            "watchlist_handling": {
                "watchlist_sell_ids": watchlist_sells,
                "buys_avoid_watchlist": all(not issuer_watchlist(env, row["instrument_id"]) for row in buys),
            },
            "risk_note_code": note,
        }
    )
    return answer


OPPORTUNITY_TO_INDEX = {
    "Emerging Markets": "IDX_EM",
    "India": "IDX_INDIA",
    "Latin America": "IDX_LATAM",
    "China": "IDX_CHINA",
    "Europe": "IDX_EUROPE",
    "Japan": "IDX_JAPAN",
}


def committee_actions(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    for row in rows:
        opp = row["opportunity_set"]
        view = row.get("view")
        change = row.get("change")
        if opp in {"USD", "EUR", "JPY", "CHF"}:
            action = "hedge" if change == "DOWN" or view != "OW" else "hold"
        elif view == "OW":
            action = "add"
        elif view == "UW":
            action = "trim"
        elif row.get("rationale_code") in {"CHINA_DEPENDENCE", "HY_VALUATION_RISK"}:
            action = "monitor"
        else:
            action = "hold"
        actions.append({"opportunity_set": opp, "action": action})
    return actions


def solve_committee(task: Dict[str, Any], env: Env) -> Dict[str, Any]:
    portfolio_id = find_portfolio_id(task)
    portfolio = env.portfolio(portfolio_id)
    start, end = requested_window(task, env)
    index_ids = requested_index_ids(task, env, portfolio)
    pairs = correlation_pairs(env, index_ids, start, end)
    high = highest_pair(pairs)
    low = lowest_pair(pairs)
    high_threshold = as_number(correlation_policy(env).get("correlation_high_threshold"), 0.8)
    high_breached = high["correlation"] >= high_threshold
    rows = allocation_rows(task, env, include_prior=True, include_score=True)
    return {
        "portfolio_id": portfolio_id,
        "as_of_date": portfolio.get("as_of_date"),
        "review_quarter": requested_quarter(task),
        "correlation_summary": [
            {
                "pair_role": "highest_concentration",
                "pair": high["pair"],
                "correlation": round_to(high["correlation"], 3),
            },
            {
                "pair_role": "best_diversifier",
                "pair": low["pair"],
                "correlation": round_to(low["correlation"], 3),
            },
        ],
        "target_sleeve_actions": committee_actions(rows),
        "allocation_views": rows,
        "rebalance_trigger": "correlation_cap_breach" if high_breached else "committee_review",
        "portfolio_risk_concentration_flag": high_breached,
        "next_step": "approve_with_monitoring" if high_breached else "approve_rotation",
    }


def solve(task: Dict[str, Any], env: Env) -> Dict[str, Any]:
    keys = set(top_keys(task["template"]))
    if "trade_package" in keys:
        return solve_energy_trade(task, env)
    if "rotation" in keys:
        return solve_credit_rotation(task, env)
    if "correlation_summary" in keys and "target_sleeve_actions" in keys:
        return solve_committee(task, env)
    if "extreme_pairs" in keys:
        return solve_correlation_review(task, env)
    if "allocation_views" in keys and "risk_overlay" in keys:
        return solve_allocation(task, env)
    raise RuntimeError(f"unrecognized Asteria template keys: {sorted(keys)}")


def main(argv: Sequence[str]) -> int:
    if len(argv) != 2:
        print("usage: python3 skill/asteria_helper.py /path/to/task/input", file=sys.stderr)
        return 2
    task = read_task(argv[1])
    env = Env()
    answer = solve(task, env)
    print(json.dumps(answer, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
