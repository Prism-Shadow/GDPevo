#!/usr/bin/env python3
"""Utility calculations for shared credit office API tasks.

The script fetches public API records and prints derivation JSON. It is designed
to support, not replace, careful conformance to each task's answer_template.json.
It uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from typing import Any


PAYMENT_SEVERITY = {
    "Current": 0,
    "30 Days Past Due": 1,
    "60 Days Past Due": 2,
    "90+ Days Past Due": 3,
    "Nonaccrual": 4,
}


def money(value: float | int | None) -> float | None:
    return None if value is None else round(float(value) + 0.0, 2)


def ratio(value: float | int | None) -> float | None:
    return None if value is None else round(float(value) + 0.0, 4)


def dscr_value(value: float | int | None) -> float | None:
    return None if value is None else round(float(value) + 0.0, 2)


def score_value(value: float | int | None) -> float | None:
    return None if value is None else round(float(value) + 0.0, 1)


def bps(value: float | int | None) -> float | None:
    return None if value is None else round(float(value) * 10000.0, 2)


def fetch_json(base_url: str, path: str) -> Any:
    base = base_url.rstrip("/") + "/"
    url = urllib.parse.urljoin(base, path.lstrip("/"))
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(f"failed to fetch {url}: {exc}") from exc


def print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=False))


def latest_metric(metrics: list[dict[str, Any]], as_of: str | None = None) -> dict[str, Any]:
    if not metrics:
        return {}
    if as_of and len(as_of) >= 7:
        year = as_of[:4]
        month = int(as_of[5:7])
        quarter = (month - 1) // 3 + 1
        label = f"{year}Q{quarter}"
        for row in metrics:
            if row.get("quarter") == label:
                return row
    return sorted(metrics, key=lambda row: str(row.get("quarter", "")))[-1]


def dscr_rating(dscr: float | int | None) -> int | None:
    if dscr is None:
        return None
    x = float(dscr)
    if x >= 1.50:
        return 3
    if x >= 1.25:
        return 4
    if x >= 1.05:
        return 5
    if x >= 1.00:
        return 6
    return 7


def ltv_rating(ltv: float | int | None) -> int | None:
    if ltv is None:
        return None
    x = float(ltv)
    if x <= 0.65:
        return 3
    if x <= 0.75:
        return 4
    if x <= 0.85:
        return 5
    if x <= 1.00:
        return 6
    return 7


def delinquency_rating(payment_status: str | None, policies: dict[str, Any] | None = None) -> int | None:
    default = {
        "30 Days Past Due": 4,
        "60 Days Past Due": 5,
        "90+ Days Past Due": 7,
        "Nonaccrual": 8,
        "Current": None,
    }
    table = (
        policies
        or {}
    ).get("risk_rating", {}).get("delinquency_minimums", default)
    return table.get(payment_status)


def regrade_loan(loan: dict[str, Any], policies: dict[str, Any] | None = None) -> dict[str, Any]:
    factors = {
        "dscr": dscr_rating(loan.get("dscr")),
        "ltv": ltv_rating(loan.get("ltv")),
        "delinquency": delinquency_rating(loan.get("payment_status"), policies),
    }
    available = [value for value in factors.values() if value is not None]
    final_rating = max(available) if available else loan.get("current_rating")
    current_rating = loan.get("current_rating")
    return {
        "loan_id": loan.get("loan_id"),
        "borrower_name": loan.get("borrower_name"),
        "current_rating": current_rating,
        "final_rating": final_rating,
        "downgrade_notches": (
            None if current_rating is None or final_rating is None else final_rating - current_rating
        ),
        "exposure": money(loan.get("outstanding_balance")),
        "payment_status": loan.get("payment_status"),
        "factors": factors,
        "recommended_action": recommend_action(final_rating, loan.get("payment_status")),
    }


def recommend_action(final_rating: int | None, payment_status: str | None = None, projected_loss: bool = False) -> str:
    if projected_loss or payment_status == "Nonaccrual" or (final_rating is not None and final_rating >= 8):
        return "partial_chargeoff_review"
    if payment_status == "90+ Days Past Due" or (final_rating is not None and final_rating >= 7):
        return "special_assets"
    if final_rating is not None and final_rating >= 6:
        return "watchlist"
    return "monitor"


def score_ltv(value: float | int | None) -> int | None:
    if value is None:
        return None
    x = float(value)
    if x < 0.40:
        return 0
    if x <= 0.60:
        return 2
    if x <= 0.80:
        return 4
    return 6


def score_debt_to_asset(value: float | int | None) -> int | None:
    if value is None:
        return None
    x = float(value)
    if x < 0.40:
        return 0
    if x <= 0.60:
        return 2
    if x <= 0.80:
        return 4
    return 6


def score_liquidity(value: float | int | None) -> int | None:
    if value is None:
        return None
    x = float(value)
    if x > 12:
        return 0
    if x >= 6:
        return 1
    if x >= 3:
        return 3
    return 5


def score_fico(value: float | int | None) -> int | None:
    if value is None:
        return None
    x = float(value)
    if x > 720:
        return 0
    if x >= 680:
        return 1
    if x >= 580:
        return 3
    return 5


def debt_to_asset(record: dict[str, Any]) -> float | None:
    if record.get("debt_to_asset") is not None:
        return float(record["debt_to_asset"])
    if record.get("total_debt") is not None and record.get("total_assets"):
        return float(record["total_debt"]) / float(record["total_assets"])
    return None


def cdfi_score(record: dict[str, Any]) -> dict[str, Any]:
    parts = {
        "ltv": score_ltv(record.get("ltv")),
        "debt_to_asset": score_debt_to_asset(debt_to_asset(record)),
        "liquidity_months": score_liquidity(record.get("liquidity_months")),
        "fico": score_fico(record.get("fico")),
    }
    total = sum(value for value in parts.values() if value is not None)
    risk_class = cdfi_class(total, record)
    return {
        "id": record.get("loan_id") or record.get("application_id"),
        "factor_score": total,
        "risk_class": risk_class,
        "parts": parts,
    }


def cdfi_class(score: int, record: dict[str, Any]) -> str:
    notes = str(record.get("notes", "")).lower()
    underwater = record.get("ltv") is not None and float(record["ltv"]) > 1.0
    loss_signal = (
        record.get("payment_status") == "Nonaccrual"
        or "projected loss" in notes
        or "underwater" in notes
    )
    if underwater and (loss_signal or score >= 19):
        return "Projected Loss"
    if score >= 19:
        return "Doubtful"
    if score >= 14:
        return "Watch"
    if score >= 10:
        return "Satisfactory"
    if score >= 6:
        return "Desirable"
    return "Prime"


def watchlist_stress(dscr: float | int | None) -> float | None:
    if dscr is None:
        return None
    return dscr_value(float(dscr) / 1.18)


def cre_dual_stress(dscr: float | int | None) -> float | None:
    if dscr is None:
        return None
    return dscr_value(float(dscr) * 0.85 / 1.18)


def sector_total(rows: list[dict[str, Any]]) -> float:
    return sum(float(row.get("current_exposure") or 0.0) for row in rows)


def sector_lookup(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["sector"]: row for row in rows}


def current_sector_exposure(rows: list[dict[str, Any]], sector: str) -> float:
    return float(sector_lookup(rows).get(sector, {}).get("current_exposure") or 0.0)


def sector_limit(rows: list[dict[str, Any]], branch: dict[str, Any], sector: str) -> float:
    row = sector_lookup(rows).get(sector, {})
    if row.get("limit_pct") is not None:
        return float(row["limit_pct"])
    return float(branch.get("sector_ceiling_pct") or 0.0)


def retained_for_sba(app: dict[str, Any], amount: float | None = None) -> float:
    approved = float(amount if amount is not None else app.get("requested_amount") or 0.0)
    guarantee = app.get("sba_guaranty_pct")
    if guarantee is None:
        return approved
    return approved * (1.0 - float(guarantee))


def participation_cap(
    current_total: float,
    prior_committed: float,
    current_sector: float,
    limit_pct: float,
    requested: float,
) -> float:
    if limit_pct >= 1:
        return requested
    cap = (limit_pct * (current_total + prior_committed) - current_sector) / (1.0 - limit_pct)
    return max(0.0, min(float(requested), cap))


def severe_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("current_rating"),
        PAYMENT_SEVERITY.get(row.get("payment_status"), 99),
    )


def command_snapshot(args: argparse.Namespace) -> None:
    payload: dict[str, Any] = {
        "manifest": fetch_json(args.base_url, "/api/manifest"),
        "policies": fetch_json(args.base_url, "/api/policies"),
    }
    if args.branch_id:
        bid = args.branch_id
        payload["branch"] = fetch_json(args.base_url, f"/api/branches/{bid}")
        payload["metrics"] = fetch_json(args.base_url, f"/api/branches/{bid}/metrics")
        payload["loans_count"] = len(fetch_json(args.base_url, f"/api/branches/{bid}/loans"))
        payload["sector_exposures"] = fetch_json(args.base_url, f"/api/branches/{bid}/sector-exposures")
        payload["applications_count"] = len(fetch_json(args.base_url, f"/api/branches/{bid}/applications"))
        payload["selected_metric"] = latest_metric(payload["metrics"], args.as_of)
    if args.segment_id:
        payload["segment"] = fetch_json(args.base_url, f"/api/credit-union-segments/{args.segment_id}")
    print_json(payload)


def command_regrade(args: argparse.Namespace) -> None:
    policies = fetch_json(args.base_url, "/api/policies")
    loans = fetch_json(args.base_url, f"/api/branches/{args.branch_id}/loans")
    target = [loan for loan in loans if int(loan.get("current_rating") or 0) >= args.min_rating]
    rows = [regrade_loan(loan, policies) for loan in target]
    rows.sort(key=lambda row: row["loan_id"])

    grouped: dict[int, dict[str, Any]] = {}
    for row in rows:
        rating = int(row["final_rating"])
        entry = grouped.setdefault(rating, {"final_rating": rating, "loan_count": 0, "exposure": 0.0})
        entry["loan_count"] += 1
        entry["exposure"] += row["exposure"] or 0.0
    final_totals = [
        {"final_rating": key, "loan_count": value["loan_count"], "exposure": money(value["exposure"])}
        for key, value in sorted(grouped.items())
    ]

    material_notches = int(policies.get("risk_rating", {}).get("material_downgrade_notches", 2))
    material = [
        {
            "loan_id": row["loan_id"],
            "current_rating": row["current_rating"],
            "final_rating": row["final_rating"],
            "downgrade_notches": row["downgrade_notches"],
            "exposure": row["exposure"],
        }
        for row in rows
        if row["downgrade_notches"] is not None and row["downgrade_notches"] >= material_notches
    ]

    follow_up = [row for row in rows if row["recommended_action"] != "monitor"]
    action_groups: dict[str, dict[str, Any]] = {}
    for row in follow_up:
        action = row["recommended_action"]
        entry = action_groups.setdefault(action, {"action": action, "loan_count": 0, "exposure": 0.0, "loan_ids": []})
        entry["loan_count"] += 1
        entry["exposure"] += row["exposure"] or 0.0
        entry["loan_ids"].append(row["loan_id"])

    output = {
        "target_current_rating_min": args.min_rating,
        "target_loan_count": len(rows),
        "target_exposure": money(sum(row["exposure"] or 0.0 for row in rows)),
        "rows": rows,
        "final_rating_exposure_totals": final_totals,
        "material_downgrades": material,
        "watch_list_action_coverage": {
            "covered_loan_count": len(follow_up),
            "covered_exposure": money(sum(row["exposure"] or 0.0 for row in follow_up)),
            "by_action": [
                {
                    "action": action,
                    "loan_count": value["loan_count"],
                    "exposure": money(value["exposure"]),
                    "loan_ids": sorted(value["loan_ids"]),
                }
                for action, value in sorted(action_groups.items())
            ],
        },
        "top_problem_credit_candidate": sorted(
            rows,
            key=lambda row: (
                -(row["final_rating"] or 0),
                -PAYMENT_SEVERITY.get(row.get("payment_status"), 0),
                -(row["exposure"] or 0.0),
                row["loan_id"],
            ),
        )[0] if rows else None,
    }
    print_json(output)


def command_watchlist(args: argparse.Namespace) -> None:
    loans = fetch_json(args.base_url, f"/api/branches/{args.branch_id}/loans")
    target = [loan for loan in loans if int(loan.get("current_rating") or 0) >= args.min_rating]
    target.sort(key=lambda row: row["loan_id"])
    classes = []
    stress_rows = []
    workout_rows = []
    bucket: dict[tuple[int, str], dict[str, Any]] = {}

    for loan in target:
        cdfi = cdfi_score(loan)
        projected_loss = cdfi["risk_class"] == "Projected Loss"
        classes.append({
            "loan_id": loan["loan_id"],
            "risk_class": cdfi["risk_class"],
            "factor_score": cdfi["factor_score"],
            "parts": cdfi["parts"],
        })
        if loan.get("dscr") is not None:
            stressed = watchlist_stress(loan["dscr"])
            stress_rows.append({
                "loan_id": loan["loan_id"],
                "base_dscr": dscr_value(loan["dscr"]),
                "stressed_dscr": stressed,
                "breaches_threshold": bool(stressed is not None and stressed < args.threshold),
            })
        workout_rows.append({
            "loan_id": loan["loan_id"],
            "exposure": money(loan.get("outstanding_balance")),
            "risk_class": cdfi["risk_class"],
            "payment_status": loan.get("payment_status"),
            "recommended_action": recommend_action(loan.get("current_rating"), loan.get("payment_status"), projected_loss),
            "projected_loss": projected_loss,
        })
        key = (int(loan.get("current_rating")), loan.get("payment_status"))
        entry = bucket.setdefault(key, {
            "current_rating": key[0],
            "payment_status": key[1],
            "loan_count": 0,
            "exposure": 0.0,
        })
        entry["loan_count"] += 1
        entry["exposure"] += float(loan.get("outstanding_balance") or 0.0)

    print_json({
        "adverse_rating_min": args.min_rating,
        "adverse_loan_count": len(target),
        "adverse_balance": money(sum(float(row.get("outstanding_balance") or 0.0) for row in target)),
        "risk_classes": classes,
        "stress_results": {
            "shock_label": "+200bp",
            "breach_threshold": args.threshold,
            "results": sorted(stress_rows, key=lambda row: row["loan_id"]),
            "breach_loan_ids": [row["loan_id"] for row in sorted(stress_rows, key=lambda row: row["loan_id"]) if row["breaches_threshold"]],
        },
        "workout_queue": sorted(workout_rows, key=lambda row: (-(row["exposure"] or 0.0), row["loan_id"])),
        "severe_bucket_counts": [
            {
                "current_rating": value["current_rating"],
                "payment_status": value["payment_status"],
                "loan_count": value["loan_count"],
                "exposure": money(value["exposure"]),
            }
            for _, value in sorted(bucket.items(), key=lambda item: severe_sort_key(item[1]))
        ],
    })


def median(values: list[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        return math.nan
    middle = n // 2
    if n % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def direction(left: float, right: float) -> str:
    if left > right:
        return "higher"
    if left < right:
        return "lower"
    return "equal"


def command_segment(args: argparse.Namespace) -> None:
    segment = fetch_json(args.base_url, f"/api/credit-union-segments/{args.segment_id}")
    ncua = fetch_json(args.base_url, "/api/benchmarks/ncua/q1-2025")
    rows = {row["state_code"]: row for row in ncua["rows"]}
    state = segment["state_code"]
    peers = sorted(segment.get("peer_states", []))
    metrics = ["delinquency_bps", "loan_to_share_pct", "roaa_bps", "positive_net_income_pct"]
    state_row = rows[state]
    us_row = rows["US"]
    peer_medians = {
        metric: median([float(rows[peer][metric]) for peer in peers])
        for metric in metrics
    }
    print_json({
        "segment": segment,
        "state_metrics": {
            "state_code": state,
            "benchmark_version": ncua["benchmark_version"],
            **{metric: state_row[metric] for metric in metrics},
        },
        "peer_states": peers,
        "nc_vs_us": {
            metric: direction(float(state_row[metric]), float(us_row[metric]))
            for metric in metrics
        },
        "nc_vs_peer_median": {
            metric: direction(float(state_row[metric]), float(peer_medians[metric]))
            for metric in metrics
        },
        "peer_medians": peer_medians,
    })


def cre_component_scores(app: dict[str, Any], branch_adverse: bool = False, concentration_breach: bool = False) -> dict[str, int]:
    stressed = cre_dual_stress(app.get("dscr"))
    if stressed is not None and stressed < 1.0:
        capacity = 5
    else:
        rating = dscr_rating(app.get("dscr"))
        capacity = {3: 1, 4: 2, 5: 3, 6: 4, 7: 5}.get(rating, 3)

    dta = debt_to_asset(app)
    if dta is None:
        capital = 3
    elif dta <= 0.40:
        capital = 1
    elif dta <= 0.60:
        capital = 2
    elif dta <= 0.80:
        capital = 3
    elif dta <= 1.00:
        capital = 4
    else:
        capital = 5

    prior = int(app.get("prior_delinquencies_12m") or 0)
    years = app.get("years_in_business")
    relationship = float(app.get("existing_relationship_years") or 0.0)
    guarantor = app.get("co_guarantor_strength")
    if app.get("bankruptcy_months_ago") is not None or prior >= 3:
        character = 5
    elif years is not None and float(years) < 2:
        character = 4
    elif guarantor == "strong" and prior == 0 and relationship >= 5:
        character = 1
    elif guarantor in {"strong", "standard"} and prior <= 1:
        character = 2
    elif guarantor == "limited" and prior <= 1:
        character = 3
    else:
        character = 4

    ltv = app.get("ltv")
    if ltv is None:
        collateral = 3
    elif float(ltv) <= 0.65:
        collateral = 2
    elif float(ltv) <= 0.75:
        collateral = 3
    elif float(ltv) <= 0.85:
        collateral = 4
    else:
        collateral = 5

    notes = str(app.get("notes", "")).lower()
    conditions = 3
    if "branch cre exposure" in notes or "elevated" in notes or "concentration" in notes:
        conditions = 5
    elif "seasonal" in notes or "sponsor support" in notes or "strong guarantor" in notes:
        conditions = 3
    if app.get("documentation_complete") == 0:
        conditions = max(conditions, 5)

    return {
        "capacity": capacity,
        "capital": capital,
        "character": character,
        "collateral_exposure": collateral,
        "conditions": conditions,
    }


def weighted_cre_score(app: dict[str, Any], weights: dict[str, float], **flags: bool) -> dict[str, Any]:
    components = cre_component_scores(app, **flags)
    value = sum(float(weights[key]) * components[key] for key in weights)
    if app.get("documentation_complete") == 0:
        value = max(value, 4.0)
    if app.get("bankruptcy_months_ago") is not None:
        value = max(value, 4.0)
    score = score_value(value)
    if score is not None and score <= 2.0:
        score_class = "approve_quality"
    elif score is not None and score <= 3.0:
        score_class = "conditional"
    else:
        score_class = "weak"
    return {
        "application_id": app.get("application_id"),
        "weighted_cdfi_score": score,
        "score_class": score_class,
        "components": components,
    }


def command_cre_compare(args: argparse.Namespace) -> None:
    policies = fetch_json(args.base_url, "/api/policies")
    branch = fetch_json(args.base_url, f"/api/branches/{args.branch_id}")
    metrics = fetch_json(args.base_url, f"/api/branches/{args.branch_id}/metrics")
    sector_rows = fetch_json(args.base_url, f"/api/branches/{args.branch_id}/sector-exposures")
    applications = fetch_json(args.base_url, f"/api/branches/{args.branch_id}/applications")
    fdic = fetch_json(args.base_url, "/api/benchmarks/fdic/q4-2024")
    selected_ids = {item.strip() for item in args.applications.split(",") if item.strip()}
    apps = [app for app in applications if app.get("application_id") in selected_ids]
    metric = latest_metric(metrics, args.as_of)
    current_total = sector_total(sector_rows)
    existing_cre = sum(
        float(row.get("current_exposure") or 0.0)
        for row in sector_rows
        if "CRE" in row.get("sector", "") or row.get("sector") in {"Hospitality", "Office", "Multifamily", "Construction"}
    )
    cre_limit = float(branch.get("cre_policy_limit_pct") or 0.0)
    existing_cre_concentration = existing_cre / current_total if current_total else 0.0
    fdic_metric = fdic.get("total_real_estate_30_89_pct")
    branch_delinquency = float(metric.get("delinquency_30_plus_pct") or 0.0)
    branch_adverse = fdic_metric is not None and branch_delinquency > float(fdic_metric)

    rows = []
    for app in apps:
        requested = float(app.get("requested_amount") or 0.0)
        post_cre = (existing_cre + requested) / (current_total + requested) if current_total + requested else 0.0
        concentration_breach = post_cre > cre_limit or existing_cre_concentration > cre_limit
        score = weighted_cre_score(
            app,
            policies.get("cre_weighted_score", {}).get("weights", {}),
            branch_adverse=branch_adverse,
            concentration_breach=concentration_breach,
        )
        stressed = cre_dual_stress(app.get("dscr"))
        reason_codes = []
        if stressed is not None and stressed < 1.0:
            reason_codes.append("weak_dscr")
        if app.get("ltv") is not None and float(app["ltv"]) > 0.75:
            reason_codes.append("high_ltv")
        if concentration_breach:
            reason_codes.append("sector_breach")
        if branch_adverse:
            reason_codes.append("fdic_adverse_variance")
        rows.append({
            **score,
            "requested_amount": money(requested),
            "base_dscr": dscr_value(app.get("dscr")),
            "stressed_dscr": stressed,
            "stress_breach": bool(stressed is not None and stressed < 1.0),
            "post_cre_concentration": ratio(post_cre),
            "reason_codes": sorted(set(reason_codes)),
        })
    rows.sort(key=lambda row: row["application_id"])
    print_json({
        "branch_id": args.branch_id,
        "existing_cre_exposure": money(existing_cre),
        "existing_cre_concentration": ratio(existing_cre_concentration),
        "cre_policy_limit_pct": ratio(cre_limit),
        "branch_delinquency_ratio": ratio(branch_delinquency),
        "fdic_benchmark_ratio": ratio(fdic_metric),
        "fdic_variance_ratio": ratio(branch_delinquency - float(fdic_metric or 0.0)),
        "fdic_variance_bps": bps(branch_delinquency - float(fdic_metric or 0.0)),
        "applications": rows,
    })


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_base(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--base-url", required=True)
        sub.add_argument("--as-of", default=None)

    snapshot = subparsers.add_parser("snapshot")
    add_base(snapshot)
    snapshot.add_argument("--branch-id")
    snapshot.add_argument("--segment-id")
    snapshot.set_defaults(func=command_snapshot)

    regrade = subparsers.add_parser("regrade")
    add_base(regrade)
    regrade.add_argument("--branch-id", required=True)
    regrade.add_argument("--min-rating", type=int, default=3)
    regrade.set_defaults(func=command_regrade)

    watchlist = subparsers.add_parser("watchlist")
    add_base(watchlist)
    watchlist.add_argument("--branch-id", required=True)
    watchlist.add_argument("--min-rating", type=int, default=6)
    watchlist.add_argument("--threshold", type=float, default=1.0)
    watchlist.set_defaults(func=command_watchlist)

    segment = subparsers.add_parser("segment")
    add_base(segment)
    segment.add_argument("--segment-id", required=True)
    segment.set_defaults(func=command_segment)

    compare = subparsers.add_parser("cre-compare")
    add_base(compare)
    compare.add_argument("--branch-id", required=True)
    compare.add_argument("--applications", required=True)
    compare.set_defaults(func=command_cre_compare)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
