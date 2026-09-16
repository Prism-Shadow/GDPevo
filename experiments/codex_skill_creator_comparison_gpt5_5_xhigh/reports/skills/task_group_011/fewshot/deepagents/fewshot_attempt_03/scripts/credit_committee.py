#!/usr/bin/env python3
"""Draft committee JSON answers from the public credit-office task API."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Any


def rounded(value: float | int | None, digits: int) -> float | None:
    if value is None:
        return None
    return float(f"{float(value):.{digits}f}")


def money(value: float | int) -> float:
    return float(f"{float(value):.2f}")


def ratio(value: float | int) -> float:
    return float(f"{float(value):.4f}")


def bps(value: float | int) -> float:
    return float(f"{float(value) * 10000:.2f}")


class ApiClient:
    def __init__(self, base_url: str):
        if not base_url:
            raise SystemExit("Set TASK_ENV_BASE_URL or pass --base-url")
        self.base_url = base_url.rstrip("/") + "/"

    def get(self, path: str) -> Any:
        url = urllib.parse.urljoin(self.base_url, path.lstrip("/"))
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"GET {path} failed: HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise SystemExit(f"GET {path} failed: {exc}") from exc

    def branch(self, branch_id: str) -> dict[str, Any]:
        return self.get(f"/api/branches/{branch_id}")

    def metrics(self, branch_id: str) -> list[dict[str, Any]]:
        return self.get(f"/api/branches/{branch_id}/metrics")

    def loans(self, branch_id: str) -> list[dict[str, Any]]:
        return self.get(f"/api/branches/{branch_id}/loans")

    def sectors(self, branch_id: str) -> list[dict[str, Any]]:
        return self.get(f"/api/branches/{branch_id}/sector-exposures")

    def applications(self, branch_id: str) -> list[dict[str, Any]]:
        return self.get(f"/api/branches/{branch_id}/applications")


def latest_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise SystemExit("No branch metrics returned")
    return max(rows, key=lambda row: str(row.get("quarter", "")))


def sorted_ids(items: list[dict[str, Any]], key: str) -> list[str]:
    return sorted(str(item[key]) for item in items)


def group_sum(rows: list[dict[str, Any]], key: str) -> dict[Any, dict[str, Any]]:
    grouped: dict[Any, dict[str, Any]] = {}
    for row in rows:
        group_key = row[key]
        bucket = grouped.setdefault(group_key, {"loan_count": 0, "exposure": 0.0, "items": []})
        bucket["loan_count"] += 1
        bucket["exposure"] += float(row.get("outstanding_balance", row.get("exposure", 0.0)))
        bucket["items"].append(row)
    return grouped


def dscr_rating(dscr: float | None, policy: dict[str, Any]) -> int | None:
    if dscr is None:
        return None
    thresholds = policy["risk_rating"]["dscr_thresholds"]
    for threshold in sorted((t for t in thresholds if "min" in t), key=lambda t: t["min"], reverse=True):
        if dscr >= threshold["min"]:
            return int(threshold["rating"])
    for threshold in thresholds:
        if "max_below" in threshold and dscr < threshold["max_below"]:
            return int(threshold["rating"])
    return None


def ltv_rating(ltv: float | None, policy: dict[str, Any]) -> int | None:
    if ltv is None:
        return None
    thresholds = policy["risk_rating"]["ltv_thresholds"]
    for threshold in sorted((t for t in thresholds if "max" in t), key=lambda t: t["max"]):
        if ltv <= threshold["max"]:
            return int(threshold["rating"])
    for threshold in thresholds:
        if "min_above" in threshold and ltv > threshold["min_above"]:
            return int(threshold["rating"])
    return None


def delinquency_rating(payment_status: str | None, policy: dict[str, Any]) -> int | None:
    if payment_status is None:
        return None
    value = policy["risk_rating"]["delinquency_minimums"].get(payment_status)
    return None if value is None else int(value)


def rederived_rating(loan: dict[str, Any], policy: dict[str, Any]) -> int:
    factors = [
        dscr_rating(loan.get("dscr"), policy),
        ltv_rating(loan.get("ltv"), policy),
        delinquency_rating(loan.get("payment_status"), policy),
    ]
    available = [rating for rating in factors if rating is not None]
    if available:
        return max(available)
    return int(loan["current_rating"])


def action_for_rating(rating_value: int, payment_status: str | None = None, risk_class: str | None = None) -> str:
    if risk_class == "Projected Loss" or payment_status == "Nonaccrual" or rating_value >= 8:
        return "partial_chargeoff_review"
    if payment_status == "90+ Days Past Due" or rating_value >= 7:
        return "special_assets"
    if rating_value >= 6:
        return "watchlist"
    return "monitor"


def rating_migration(client: ApiClient, args: argparse.Namespace) -> dict[str, Any]:
    policy = client.get("/api/policies")
    fdic = client.get("/api/benchmarks/fdic/q4-2024")
    metrics = latest_metrics(client.metrics(args.branch))
    loans = client.loans(args.branch)
    target = [loan for loan in loans if int(loan["current_rating"]) >= args.current_rating_min]
    for loan in target:
        loan["final_rating"] = rederived_rating(loan, policy)
        loan["exposure"] = float(loan["outstanding_balance"])
        loan["recommended_action"] = action_for_rating(loan["final_rating"], loan.get("payment_status"))

    final_totals = []
    for final_rating, bucket in sorted(group_sum(target, "final_rating").items()):
        final_totals.append(
            {
                "final_rating": int(final_rating),
                "loan_count": bucket["loan_count"],
                "exposure": money(bucket["exposure"]),
            }
        )

    migration = []
    from_current = [loan for loan in target if int(loan["current_rating"]) == args.current_rating_min]
    for final_rating, bucket in sorted(group_sum(from_current, "final_rating").items()):
        migration.append(
            {
                "final_rating": int(final_rating),
                "loan_count": bucket["loan_count"],
                "exposure": money(bucket["exposure"]),
                "loan_ids": sorted_ids(bucket["items"], "loan_id"),
            }
        )

    covered = [loan for loan in target if int(loan["final_rating"]) >= 6]
    by_action = []
    action_groups = defaultdict(list)
    for loan in covered:
        action_groups[loan["recommended_action"]].append(loan)
    for action in sorted(action_groups):
        rows = action_groups[action]
        by_action.append(
            {
                "action": action,
                "loan_count": len(rows),
                "exposure": money(sum(float(row["outstanding_balance"]) for row in rows)),
                "loan_ids": sorted_ids(rows, "loan_id"),
            }
        )

    material_threshold = int(policy["risk_rating"]["material_downgrade_notches"])
    material = []
    for loan in sorted(target, key=lambda row: row["loan_id"]):
        downgrade = int(loan["final_rating"]) - int(loan["current_rating"])
        if downgrade >= material_threshold:
            material.append(
                {
                    "loan_id": loan["loan_id"],
                    "current_rating": int(loan["current_rating"]),
                    "final_rating": int(loan["final_rating"]),
                    "downgrade_notches": downgrade,
                    "exposure": money(loan["outstanding_balance"]),
                }
            )

    top = max(covered or target, key=lambda row: (int(row["final_rating"]), float(row["outstanding_balance"])))
    branch_npa_ratio = float(metrics["nonperforming_loans"]) / float(metrics["total_loans_outstanding"])
    benchmark_value = float(fdic[args.benchmark_metric])
    variance = branch_npa_ratio - benchmark_value
    return {
        "branch_id": args.branch,
        "review_date": args.review_date,
        "portfolio_regrade": {
            "target_current_rating_min": args.current_rating_min,
            "target_loan_count": len(target),
            "target_exposure": money(sum(float(loan["outstanding_balance"]) for loan in target)),
            "final_rating_exposure_totals": final_totals,
            f"migration_from_current_rating_{args.current_rating_min}": migration,
            "watch_list_action_coverage": {
                "covered_loan_count": len(covered),
                "covered_exposure": money(sum(float(loan["outstanding_balance"]) for loan in covered)),
                "by_action": by_action,
            },
        },
        "npa_benchmark": {
            "benchmark_version": fdic["benchmark_version"],
            "benchmark_metric": args.benchmark_metric,
            "branch_npa_exposure": money(metrics["nonperforming_loans"]),
            "branch_total_loans": money(metrics["total_loans_outstanding"]),
            "branch_npa_ratio": ratio(branch_npa_ratio),
            "fdic_benchmark_ratio": ratio(benchmark_value),
            "variance_ratio": ratio(variance),
            "variance_bps": bps(variance),
        },
        "material_downgrades": material,
        "top_problem_credit": {
            "loan_id": top["loan_id"],
            "borrower_name": top["borrower_name"],
            "exposure": money(top["outstanding_balance"]),
            "current_rating": int(top["current_rating"]),
            "final_rating": int(top["final_rating"]),
            "payment_status": top["payment_status"],
            "recommended_action": top["recommended_action"],
        },
    }


def score_range(value: float | int | None, ranges: list[dict[str, Any]]) -> int:
    if value is None:
        return 0
    numeric = float(value)
    for entry in ranges:
        text = entry["range"]
        if text.startswith("<"):
            if numeric < float(text[1:]):
                return int(entry["score"])
        elif text.startswith(">"):
            if numeric > float(text[1:]):
                return int(entry["score"])
        elif "-" in text:
            lower, upper = text.split("-", 1)
            if float(lower) <= numeric <= float(upper):
                return int(entry["score"])
    return 0


def cdfi_factor_score(row: dict[str, Any], policy: dict[str, Any]) -> int:
    table = policy["cdfi_factor_scores"]
    return sum(
        [
            score_range(row.get("ltv"), table["ltv"]),
            score_range(row.get("debt_to_asset"), table["debt_to_asset"]),
            score_range(row.get("fico"), table["fico"]),
            score_range(row.get("liquidity_months"), table["liquidity_months"]),
        ]
    )


def cdfi_class(score: int, row: dict[str, Any]) -> str:
    ltv = row.get("ltv")
    if ltv is not None and float(ltv) > 1.0 and (
        row.get("payment_status") == "Nonaccrual" or int(row.get("current_rating", 0)) >= 8
    ):
        return "Projected Loss"
    if score <= 5:
        return "Prime"
    if score <= 9:
        return "Desirable"
    if score <= 13:
        return "Satisfactory"
    if score <= 18:
        return "Watch"
    if ltv is not None and float(ltv) > 1.0:
        return "Projected Loss"
    return "Doubtful"


def watchlist_stress(client: ApiClient, args: argparse.Namespace) -> dict[str, Any]:
    policy = client.get("/api/policies")
    loans = [loan for loan in client.loans(args.branch) if int(loan["current_rating"]) >= args.adverse_rating_min]
    for loan in loans:
        loan["factor_score"] = cdfi_factor_score(loan, policy)
        loan["risk_class"] = cdfi_class(loan["factor_score"], loan)

    stress_results = []
    breach_ids = []
    threshold = float(policy["stress"]["coverage_breach_threshold"])
    for loan in sorted((loan for loan in loans if loan.get("dscr") is not None), key=lambda row: row["loan_id"]):
        stressed = float(loan["dscr"]) / 1.18
        breaches = stressed < threshold
        if breaches:
            breach_ids.append(loan["loan_id"])
        stress_results.append(
            {
                "loan_id": loan["loan_id"],
                "base_dscr": rounded(loan["dscr"], 2),
                "stressed_dscr": rounded(stressed, 2),
                "breaches_threshold": breaches,
            }
        )

    workout = []
    for loan in sorted(loans, key=lambda row: (-float(row["outstanding_balance"]), row["loan_id"])):
        action = action_for_rating(int(loan["current_rating"]), loan.get("payment_status"), loan["risk_class"])
        workout.append(
            {
                "loan_id": loan["loan_id"],
                "exposure": money(loan["outstanding_balance"]),
                "risk_class": loan["risk_class"],
                "payment_status": loan["payment_status"],
                "recommended_action": action,
                "projected_loss": loan["risk_class"] == "Projected Loss",
            }
        )

    severe_groups: dict[tuple[int, str], float] = defaultdict(float)
    severe_counts: dict[tuple[int, str], int] = defaultdict(int)
    for loan in loans:
        key = (int(loan["current_rating"]), str(loan["payment_status"]))
        severe_groups[key] += float(loan["outstanding_balance"])
        severe_counts[key] += 1
    severe = [
        {
            "current_rating": rating_value,
            "payment_status": status,
            "loan_count": severe_counts[(rating_value, status)],
            "exposure": money(exposure),
        }
        for (rating_value, status), exposure in sorted(severe_groups.items(), key=lambda item: (item[0][0], item[0][1]))
    ]

    return {
        "branch_id": args.branch,
        "watch_list_summary": {
            "adverse_rating_min": args.adverse_rating_min,
            "adverse_loan_count": len(loans),
            "adverse_balance": money(sum(float(loan["outstanding_balance"]) for loan in loans)),
            "risk_classes": [
                {"loan_id": loan["loan_id"], "risk_class": loan["risk_class"], "factor_score": loan["factor_score"]}
                for loan in sorted(loans, key=lambda row: row["loan_id"])
            ],
            "monitoring_cadence": "monthly" if loans else "quarterly",
        },
        "stress_results": {
            "shock_label": policy["stress"]["watch_list_parallel_shock"],
            "breach_threshold": rounded(threshold, 2),
            "results": stress_results,
            "breach_loan_ids": sorted(breach_ids),
        },
        "workout_queue": workout,
        "severe_bucket_counts": severe,
    }


def median_for(rows: list[dict[str, Any]], field: str) -> float:
    return statistics.median(float(row[field]) for row in rows)


def direction(value: float, compare_to: float) -> str:
    if value > compare_to:
        return "higher"
    if value < compare_to:
        return "lower"
    return "equal"


def external_status(state: dict[str, Any], us: dict[str, Any], peers: list[dict[str, Any]]) -> str:
    weak_metrics = 0
    strong_metrics = 0
    peer_medians = {field: median_for(peers, field) for field in STATE_METRIC_FIELDS}
    for field in ("delinquency_bps", "loan_to_share_pct"):
        if float(state[field]) > float(us[field]) and float(state[field]) > peer_medians[field]:
            weak_metrics += 1
        elif float(state[field]) < float(us[field]) and float(state[field]) < peer_medians[field]:
            strong_metrics += 1
    for field in ("roaa_bps", "positive_net_income_pct"):
        if float(state[field]) < float(us[field]) and float(state[field]) < peer_medians[field]:
            weak_metrics += 1
        elif float(state[field]) > float(us[field]) and float(state[field]) > peer_medians[field]:
            strong_metrics += 1
    if weak_metrics == 4:
        return "weaker_than_national_and_peers"
    if strong_metrics == 4:
        return "stronger_than_national_and_peers"
    return "mixed_vs_national_and_peers"


STATE_METRIC_FIELDS = ("delinquency_bps", "loan_to_share_pct", "roaa_bps", "positive_net_income_pct")


def segment_posture(client: ApiClient, args: argparse.Namespace) -> dict[str, Any]:
    segment = client.get(f"/api/credit-union-segments/{args.segment}")
    ncua = client.get("/api/benchmarks/ncua/q1-2025")
    rows = {row["state_code"]: row for row in ncua["rows"]}
    state = rows[segment["state_code"]]
    us = rows["US"]
    peer_codes = sorted(segment.get("peer_states", []))
    peers = [rows[code] for code in peer_codes]
    peer_medians = {field: median_for(peers, field) for field in STATE_METRIC_FIELDS}
    status = external_status(state, us, peers)

    quarterly_capacity = float(segment.get("quarterly_capacity") or 0.0)
    current_outstanding = float(segment.get("current_outstanding") or 0.0)
    if quarterly_capacity <= 0:
        capacity_status = "no_capacity"
    elif current_outstanding and quarterly_capacity / current_outstanding < 0.10:
        capacity_status = "capacity_constrained"
    else:
        capacity_status = "capacity_available"

    context_text = " ".join(str(value).lower() for value in segment.get("internal_context", {}).values())
    controls = set()
    if "insurance" in context_text or "proof_of_insurance" in segment.get("minimum_checklist", []):
        controls.add("pre_close_insurance_binder_verification")
    if "lien" in context_text or "ucc_or_title_lien" in segment.get("minimum_checklist", []):
        controls.add("lien_perfection_prior_to_funding")
    if "staff" in context_text or segment.get("risk_tolerance") in {"moderate", "restrained"}:
        controls.add("senior_underwriter_second_review")
    if status != "stronger_than_national_and_peers":
        controls.add("quarterly_state_benchmark_monitoring")
    if int(segment.get("internal_context", {}).get("recent_delinquency_bps", 0)) >= 75:
        controls.add("monthly_segment_delinquency_watch")
    if capacity_status != "capacity_available":
        controls.add("committee_exception_for_capacity_overrun")

    triggers = [
        {
            "trigger_id": "ET001",
            "condition": "segment_recent_delinquency_ge_90_bps",
            "owner": "credit_risk_manager",
        },
        {
            "trigger_id": "ET002",
            "condition": "missing_insurance_or_lien_exception",
            "owner": "operations_control_manager",
        },
        {
            "trigger_id": "ET003",
            "condition": "quarterly_capacity_exceeded_or_exception_requested",
            "owner": "lending_committee_chair",
        },
    ]
    delinquency_gap = max(
        float(state["delinquency_bps"]) - float(us["delinquency_bps"]),
        float(state["delinquency_bps"]) - peer_medians["delinquency_bps"],
    )
    if delinquency_gap >= 25:
        triggers.append(
            {
                "trigger_id": "ET004",
                "condition": "state_delinquency_gap_widens_25_bps",
                "owner": "credit_risk_manager",
            }
        )

    if capacity_status == "no_capacity" or (
        status == "weaker_than_national_and_peers"
        and segment.get("risk_tolerance") == "restrained"
        and int(segment.get("internal_context", {}).get("recent_delinquency_bps", 0)) >= 90
    ):
        posture = "temporarily_pause"
    elif status != "stronger_than_national_and_peers" or controls:
        posture = "continue_with_tighter_conditions"
    else:
        posture = "continue_approving"

    if posture == "temporarily_pause":
        committee_message = "pause_until_state_metrics_recover"
    elif status == "stronger_than_national_and_peers" and capacity_status == "capacity_available":
        committee_message = "routine_approval_path_supported"
    else:
        committee_message = "capacity_available_but_external_risk_weaker"

    return {
        "segment_id": args.segment,
        "posture": posture,
        "state_metrics": {
            "state_code": state["state_code"],
            "benchmark_version": ncua["benchmark_version"],
            **{field: int(state[field]) for field in STATE_METRIC_FIELDS},
        },
        "peer_comparison": {
            "peer_states": peer_codes,
            "nc_vs_us": {field: direction(float(state[field]), float(us[field])) for field in STATE_METRIC_FIELDS},
            "nc_vs_peer_median": {
                field: direction(float(state[field]), peer_medians[field]) for field in STATE_METRIC_FIELDS
            },
        },
        "controls": {
            "required_checklist_gates": segment.get("minimum_checklist", []),
            "added_operating_controls": sorted(controls),
        },
        "escalation_triggers": sorted(triggers, key=lambda row: row["trigger_id"]),
        "interpretation": {
            "capacity_status": capacity_status,
            "external_risk_status": status,
            "risk_tolerance": segment.get("risk_tolerance", "moderate"),
            "committee_message": committee_message,
        },
    }


def sector_map(sectors: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["sector"]: row for row in sectors}


def sector_row(branch: dict[str, Any], sectors_by_name: dict[str, dict[str, Any]], sector: str) -> dict[str, Any]:
    return sectors_by_name.get(
        sector,
        {
            "sector": sector,
            "current_exposure": 0.0,
            "limit_pct": branch.get("sector_ceiling_pct", 0.0),
            "grandfathered": 0,
        },
    )


def solve_retained_amount(current_exposure: float, limit_pct: float, total_loans: float, other_committed: float) -> float:
    if limit_pct >= 1:
        return 0.0
    return max(0.0, (limit_pct * (total_loans + other_committed) - current_exposure) / (1.0 - limit_pct))


def weak_dscr(app: dict[str, Any]) -> bool:
    dscr = app.get("dscr")
    return dscr is not None and float(dscr) < 1.20 and float(app.get("sba_guaranty_pct") or 0.0) < 0.50


def high_ltv(app: dict[str, Any]) -> bool:
    ltv = app.get("ltv")
    if ltv is None:
        return False
    if app.get("loan_type") in {"Consumer", "Residential Mortgage"}:
        return False
    return float(ltv) > 0.80


def startup_risk(app: dict[str, Any]) -> bool:
    years = app.get("years_in_business")
    return years is not None and float(years) < 2.0


def application_decline_reasons(app: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if app.get("fico") is not None and int(app["fico"]) < 580:
        reasons.append("low_fico")
    if app.get("bankruptcy_months_ago") is not None and int(app["bankruptcy_months_ago"]) <= 24:
        reasons.append("recent_bankruptcy")
    if app.get("documentation_complete") == 0:
        reasons.append("documentation_gap")
    if high_ltv(app):
        reasons.append("high_ltv")
    if weak_dscr(app):
        reasons.append("weak_dscr")
    if startup_risk(app) and float(app.get("sba_guaranty_pct") or 0.0) < 0.50:
        reasons.append("startup_risk")
    if app.get("ltv") is not None and float(app["ltv"]) > 1.0:
        reasons.append("underwater_collateral")
    return sorted(set(reasons))


def app_priority(app: dict[str, Any]) -> tuple[float, str]:
    score = 0.0
    if app.get("loan_type") not in {"Consumer", "Residential Mortgage"}:
        score += 50.0
    if app.get("co_guarantor_strength") == "strong":
        score += 10.0
    elif app.get("co_guarantor_strength") == "standard":
        score += 5.0
    score += min(float(app.get("existing_relationship_years") or 0.0), 15.0)
    if app.get("dscr") is not None:
        score += float(app["dscr"]) * 10.0
    if app.get("ltv") is not None:
        score += max(0.0, 1.0 - float(app["ltv"])) * 10.0
    score += float(app.get("sba_guaranty_pct") or 0.0) * 5.0
    if startup_risk(app):
        score -= 25.0
    if app.get("dscr") is not None and float(app["dscr"]) < 1.25:
        score -= 10.0
    return (-score, app["application_id"])


def allocation(client: ApiClient, args: argparse.Namespace) -> dict[str, Any]:
    branch = client.branch(args.branch)
    metrics = latest_metrics(client.metrics(args.branch))
    total_loans = float(metrics["total_loans_outstanding"])
    sectors_by_name = sector_map(client.sectors(args.branch))
    applications = sorted(client.applications(args.branch), key=lambda app: app["application_id"])

    declined: dict[str, list[str]] = {}
    candidates: list[dict[str, Any]] = []
    for app in applications:
        reasons = application_decline_reasons(app)
        high_dti_capacity = app.get("dti") is not None and float(app["dti"]) > 0.50
        if reasons:
            declined[app["application_id"]] = reasons
        elif high_dti_capacity:
            declined[app["application_id"]] = ["capacity_limit"]
        else:
            candidates.append(app)

    approved = sorted(candidates, key=app_priority)
    gross_approved = sum(float(app["requested_amount"]) for app in approved)
    initial_capacity: dict[str, float] = {}
    for app in approved:
        guaranty = float(app.get("sba_guaranty_pct") or 0.0)
        initial_capacity[app["application_id"]] = float(app["requested_amount"]) * (1.0 - guaranty)

    decisions_by_id: dict[str, dict[str, Any]] = {}
    concentration_flags = []
    for app in approved:
        app_id = app["application_id"]
        sector_info = sector_row(branch, sectors_by_name, app["sector"])
        post_gross = float(sector_info["current_exposure"]) + float(app["requested_amount"])
        gross_denominator = total_loans + gross_approved
        post_pct = post_gross / gross_denominator if gross_denominator else 0.0
        limit_pct = float(sector_info["limit_pct"])
        near_limit = post_pct >= limit_pct - 0.0005
        bank_capacity = initial_capacity[app_id]
        conditions: list[str] = []
        decision = "approve"
        if float(app.get("sba_guaranty_pct") or 0.0) >= 0.50 and startup_risk(app):
            decision = "conditional_approve"
            conditions.extend(["sba_guaranty_required", "startup_monitoring"])
        if near_limit:
            other_committed = sum(initial_capacity[other["application_id"]] for other in approved if other["application_id"] != app_id)
            retained = solve_retained_amount(float(sector_info["current_exposure"]), limit_pct, total_loans, other_committed)
            bank_capacity = min(bank_capacity, float(f"{retained:.2f}"))
            if bank_capacity < float(app["requested_amount"]):
                decision = "conditional_approve"
                conditions = ["participation_required"]
                concentration_flags.append(
                    {
                        "sector": app["sector"],
                        "application_id": app_id,
                        "limit_pct": ratio(limit_pct),
                        "post_approval_pct": ratio(post_pct),
                        "flag": True,
                        "handling": "participation_required",
                    }
                )
        decisions_by_id[app_id] = {
            "application_id": app_id,
            "decision": decision,
            "approved_amount": money(app["requested_amount"]),
            "bank_capacity_used": money(bank_capacity),
            "conditions": sorted(conditions) if conditions else ["none"],
        }

    for app_id, reasons in declined.items():
        decisions_by_id[app_id] = {
            "application_id": app_id,
            "decision": "decline",
            "approved_amount": 0.0,
            "bank_capacity_used": 0.0,
            "conditions": ["none"],
        }

    committed = sum(float(row["bank_capacity_used"]) for row in decisions_by_id.values())
    approved_by_sector: dict[str, float] = defaultdict(float)
    for app in approved:
        approved_by_sector[app["sector"]] += float(app["requested_amount"])
    denominator = total_loans + gross_approved
    post_concentrations = []
    for sector in sorted(approved_by_sector):
        info = sector_row(branch, sectors_by_name, sector)
        exposure = float(info["current_exposure"]) + approved_by_sector[sector]
        pct = exposure / denominator if denominator else 0.0
        post_concentrations.append(
            {
                "sector": sector,
                "exposure_after_approval": money(exposure),
                "post_approval_pct": ratio(pct),
                "limit_pct": ratio(float(info["limit_pct"])),
                "over_limit": pct > float(info["limit_pct"]),
            }
        )

    return {
        "branch_id": args.branch,
        "allocation": {
            "lending_capacity_q1": money(branch["lending_capacity_q1"]),
            "gross_approved_amount": money(gross_approved),
            "committed_capacity_amount": money(committed),
            "remaining_capacity": money(float(branch["lending_capacity_q1"]) - committed),
            "priority_ranking": [app["application_id"] for app in approved],
        },
        "decisions": [decisions_by_id[app["application_id"]] for app in applications],
        "concentration_flags": sorted(concentration_flags, key=lambda row: (row["sector"], row["application_id"])),
        "decline_reasons": {app_id: declined[app_id] for app_id in sorted(declined)},
        "post_approval_concentrations": post_concentrations,
    }


def cre_stressed_dscr(app: dict[str, Any]) -> float:
    return float(app["dscr"]) * 0.85 / 1.18


def cre_capacity_score(app: dict[str, Any]) -> int:
    stressed = cre_stressed_dscr(app)
    if stressed >= 1.25:
        return 1
    if stressed >= 1.05:
        return 2
    if stressed >= 1.00:
        return 3
    return 4


def cre_capital_score(app: dict[str, Any]) -> int:
    assets = app.get("total_assets")
    debt = app.get("total_debt")
    if not assets or float(assets) == 0.0 or debt is None:
        return 3
    dta = float(debt) / float(assets)
    if dta < 0.40:
        return 1
    if dta < 0.60:
        return 2
    if dta < 0.80:
        return 3
    if dta < 1.00:
        return 4
    return 5


def cre_character_score(app: dict[str, Any]) -> int:
    if app.get("bankruptcy_months_ago") is not None or (app.get("fico") is not None and int(app["fico"]) < 580):
        return 5
    strength = app.get("co_guarantor_strength")
    years = float(app.get("existing_relationship_years") or 0.0)
    if strength == "strong" and years >= 8 and int(app.get("prior_delinquencies_12m") or 0) == 0:
        return 2
    if strength == "none" or years < 4 or int(app.get("prior_delinquencies_12m") or 0) >= 2:
        return 4
    return 3


def cre_collateral_score(app: dict[str, Any], branch: dict[str, Any], sectors_by_name: dict[str, dict[str, Any]], total_loans: float) -> int:
    ltv = float(app.get("ltv") or 1.0)
    if ltv <= 0.65:
        score = 2
    elif ltv <= 0.75:
        score = 3
    elif ltv <= 0.85:
        score = 4
    else:
        score = 5
    sector_info = sector_row(branch, sectors_by_name, app["sector"])
    post_sector_pct = (float(sector_info["current_exposure"]) + float(app["requested_amount"])) / (
        total_loans + float(app["requested_amount"])
    )
    if int(sector_info.get("grandfathered") or 0) == 1 or post_sector_pct > float(sector_info["limit_pct"]):
        score = min(5, score + 1)
    return score


def cre_conditions_score(app: dict[str, Any], fdic_adverse: bool) -> int:
    if app.get("documentation_complete") == 0:
        return 5
    if fdic_adverse:
        return 4
    return 2


def weighted_cre_score(app: dict[str, Any], branch: dict[str, Any], sectors_by_name: dict[str, dict[str, Any]], total_loans: float, fdic_adverse: bool, policy: dict[str, Any]) -> float:
    weights = policy["cre_weighted_score"]["weights"]
    scores = {
        "capacity": cre_capacity_score(app),
        "capital": cre_capital_score(app),
        "character": cre_character_score(app),
        "collateral_exposure": cre_collateral_score(app, branch, sectors_by_name, total_loans),
        "conditions": cre_conditions_score(app, fdic_adverse),
    }
    return rounded(sum(float(weights[name]) * score for name, score in scores.items()), 1)


def cre_score_class(score: float) -> str:
    if score <= 2.0:
        return "approve_quality"
    if score <= 3.0:
        return "conditional"
    return "weak"


def competing_cre(client: ApiClient, args: argparse.Namespace) -> dict[str, Any]:
    policy = client.get("/api/policies")
    fdic = client.get("/api/benchmarks/fdic/q4-2024")
    branch = client.branch(args.branch)
    metrics = latest_metrics(client.metrics(args.branch))
    total_loans = float(metrics["total_loans_outstanding"])
    sectors_by_name = sector_map(client.sectors(args.branch))
    apps_by_id = {app["application_id"]: app for app in client.applications(args.branch)}
    selected_apps = [apps_by_id[app_id] for app_id in args.applications]
    existing_cre = sum(float(loan["outstanding_balance"]) for loan in client.loans(args.branch) if loan.get("loan_type") == "CRE")
    fdic_metric = "total_real_estate_30_89_pct"
    branch_ratio = float(metrics["delinquency_30_plus_pct"])
    fdic_ratio = float(fdic[fdic_metric])
    fdic_adverse = branch_ratio > fdic_ratio

    compared = []
    stress_results = []
    for app in sorted(selected_apps, key=lambda row: row["application_id"]):
        score = weighted_cre_score(app, branch, sectors_by_name, total_loans, fdic_adverse, policy)
        stressed = cre_stressed_dscr(app)
        reasons = []
        if fdic_adverse:
            reasons.append("fdic_adverse_variance")
        post_cre = (existing_cre + float(app["requested_amount"])) / (total_loans + float(app["requested_amount"]))
        if post_cre > float(branch["cre_policy_limit_pct"]):
            reasons.append("sector_breach")
        if stressed < float(policy["stress"]["coverage_breach_threshold"]):
            reasons.append("weak_dscr")
        if app.get("ltv") is not None and float(app["ltv"]) > 0.80:
            reasons.append("high_ltv")
        score_class = cre_score_class(score)
        decision = "defer" if score_class == "weak" else "participation_required" if "sector_breach" in reasons else "conditional_approve"
        compared.append(
            {
                "application_id": app["application_id"],
                "weighted_cdfi_score": score,
                "score_class": score_class,
                "decision": decision,
                "reason_codes": sorted(set(reasons)),
            }
        )
        stress_results.append(
            {
                "application_id": app["application_id"],
                "base_dscr": rounded(app["dscr"], 2),
                "stressed_dscr": rounded(stressed, 2),
                "breaches_threshold": stressed < float(policy["stress"]["coverage_breach_threshold"]),
            }
        )

    winner = min(compared, key=lambda row: (row["weighted_cdfi_score"], row["application_id"]))
    loser = max(compared, key=lambda row: (row["weighted_cdfi_score"], row["application_id"]))
    winner_app = apps_by_id[winner["application_id"]]
    selected_post = (existing_cre + float(winner_app["requested_amount"])) / (total_loans + float(winner_app["requested_amount"]))
    variance_ratio = branch_ratio - fdic_ratio
    return {
        "branch_id": args.branch,
        "applications_compared": compared,
        "recommended_path": {
            "selected_application_id": winner["application_id"],
            "path": winner["decision"],
            "unselected_application_id": loser["application_id"],
            "unselected_disposition": "defer" if loser["decision"] == "defer" else "decline",
            "unselected_reason_codes": sorted(code for code in loser["reason_codes"] if code in {"sector_breach", "weak_dscr", "high_ltv", "fdic_adverse_variance"}),
        },
        "stress": {
            "formula": "dscr * 0.85 / 1.18",
            "coverage_breach_threshold": rounded(policy["stress"]["coverage_breach_threshold"], 2),
            "results": stress_results,
        },
        "concentration": {
            "cre_policy_limit_pct": ratio(branch["cre_policy_limit_pct"]),
            "existing_cre_exposure": money(existing_cre),
            "existing_cre_concentration": ratio(existing_cre / total_loans),
            "selected_post_approval_cre_concentration": ratio(selected_post),
            "selected_policy_variance_bps": bps(selected_post - float(branch["cre_policy_limit_pct"])),
            "fdic_benchmark_metric": fdic_metric,
            "branch_delinquency_ratio": ratio(branch_ratio),
            "fdic_benchmark_ratio": ratio(fdic_ratio),
            "fdic_variance_ratio": ratio(variance_ratio),
            "fdic_variance_bps": bps(variance_ratio),
        },
        "conditions": sorted(
            [
                "bank_retained_exposure_cap",
                "committee_cre_exception",
                "updated_appraisal_before_close",
                "tenant_roll_and_lease_review",
                "minimum_dscr_covenant_1_25",
                "quarterly_financial_reporting",
                "no_additional_cre_without_committee_review",
            ]
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("TASK_ENV_BASE_URL", ""))
    subparsers = parser.add_subparsers(dest="task", required=True)

    rating_parser = subparsers.add_parser("rating-migration")
    rating_parser.add_argument("--branch", required=True)
    rating_parser.add_argument("--review-date", required=True)
    rating_parser.add_argument("--current-rating-min", type=int, default=3)
    rating_parser.add_argument("--benchmark-metric", default="total_loans_noncurrent_pct")
    rating_parser.set_defaults(func=rating_migration)

    allocation_parser = subparsers.add_parser("allocation")
    allocation_parser.add_argument("--branch", required=True)
    allocation_parser.set_defaults(func=allocation)

    segment_parser = subparsers.add_parser("segment-posture")
    segment_parser.add_argument("--segment", required=True)
    segment_parser.set_defaults(func=segment_posture)

    watch_parser = subparsers.add_parser("watchlist-stress")
    watch_parser.add_argument("--branch", required=True)
    watch_parser.add_argument("--adverse-rating-min", type=int, default=6)
    watch_parser.set_defaults(func=watchlist_stress)

    cre_parser = subparsers.add_parser("competing-cre")
    cre_parser.add_argument("--branch", required=True)
    cre_parser.add_argument("--applications", nargs="+", required=True)
    cre_parser.set_defaults(func=competing_cre)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    client = ApiClient(args.base_url)
    result = args.func(client, args)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
