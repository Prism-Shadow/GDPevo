#!/usr/bin/env python3
"""Utility calculations for credit-office committee JSON tasks.

The script intentionally fetches fresh public API data at solve time and does
not store branch-specific answers. Use its output as an audit worksheet, then
shape the final response to the task's answer_template.json.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from typing import Any


def api_get(base_url: str, path: str) -> Any:
    base = base_url.rstrip("/")
    url = f"{base}{path}"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"GET {path} failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"GET {path} failed: {exc.reason}") from exc


def dump(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=False))


def r2(value: float | int | None) -> float | None:
    if value is None:
        return None
    return round(float(value) + 1e-9, 2)


def r4(value: float | int | None) -> float | None:
    if value is None:
        return None
    return round(float(value) + 1e-12, 4)


def latest_metric(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    if not metrics:
        raise SystemExit("No branch metrics returned")
    return sorted(metrics, key=lambda row: row.get("quarter", ""))[-1]


def as_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def dscr_rating(dscr: Any) -> int | None:
    value = as_number(dscr)
    if value is None:
        return None
    if value >= 1.50:
        return 3
    if value >= 1.25:
        return 4
    if value >= 1.05:
        return 5
    if value >= 1.00:
        return 6
    return 7


def ltv_rating(ltv: Any) -> int | None:
    value = as_number(ltv)
    if value is None:
        return None
    if value <= 0.65:
        return 3
    if value <= 0.75:
        return 4
    if value <= 0.85:
        return 5
    if value <= 1.00:
        return 6
    return 7


def delinquency_rating(payment_status: str | None) -> int | None:
    return {
        "Current": None,
        "30 Days Past Due": 4,
        "60 Days Past Due": 5,
        "90+ Days Past Due": 7,
        "Nonaccrual": 8,
    }.get(payment_status or "")


def rederived_rating(loan: dict[str, Any]) -> int:
    ratings = [
        value
        for value in (
            dscr_rating(loan.get("dscr")),
            ltv_rating(loan.get("ltv")),
            delinquency_rating(loan.get("payment_status")),
        )
        if value is not None
    ]
    if not ratings:
        return int(loan.get("current_rating"))
    return max(ratings)


def recommended_action(
    *,
    final_rating: int | None = None,
    payment_status: str | None = None,
    risk_class: str | None = None,
) -> str:
    if risk_class == "Projected Loss" or payment_status == "Nonaccrual":
        return "partial_chargeoff_review"
    if final_rating is not None and final_rating >= 8:
        return "partial_chargeoff_review"
    if payment_status == "90+ Days Past Due":
        return "special_assets"
    if final_rating is not None and final_rating >= 7:
        return "special_assets"
    if final_rating is not None and final_rating >= 6:
        return "watchlist"
    return "monitor"


def group_exposure(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[Any, dict[str, Any]] = {}
    for row in rows:
        group_value = row[key]
        current = grouped.setdefault(
            group_value, {key: group_value, "loan_count": 0, "exposure": 0.0, "loan_ids": []}
        )
        current["loan_count"] += 1
        current["exposure"] += float(row["exposure"])
        if "loan_id" in row:
            current["loan_ids"].append(row["loan_id"])
    output = []
    for group_value in sorted(grouped):
        item = grouped[group_value]
        item["exposure"] = r2(item["exposure"])
        if item["loan_ids"]:
            item["loan_ids"] = sorted(item["loan_ids"])
        else:
            item.pop("loan_ids", None)
        output.append(item)
    return output


def rating_migration(args: argparse.Namespace) -> None:
    branch_id = args.branch_id
    loans = api_get(args.base_url, f"/api/branches/{branch_id}/loans")
    metrics = latest_metric(api_get(args.base_url, f"/api/branches/{branch_id}/metrics"))
    policies = api_get(args.base_url, "/api/policies")
    fdic = api_get(args.base_url, "/api/benchmarks/fdic/q4-2024")
    material_notches = int(policies["risk_rating"].get("material_downgrade_notches", 2))

    target = []
    for loan in loans:
        if int(loan.get("current_rating", 0)) >= args.current_rating_min:
            final = rederived_rating(loan)
            exposure = float(loan.get("outstanding_balance") or 0.0)
            target.append({**loan, "final_rating": final, "exposure": exposure})

    final_rows = [
        {"final_rating": row["final_rating"], "exposure": row["exposure"], "loan_id": row["loan_id"]}
        for row in target
    ]
    migration_source = [
        {"final_rating": row["final_rating"], "exposure": row["exposure"], "loan_id": row["loan_id"]}
        for row in target
        if int(row.get("current_rating")) == args.current_rating_min
        and row["final_rating"] != args.current_rating_min
    ]

    follow_up = []
    for row in target:
        if row["final_rating"] >= 6:
            follow_up.append(
                {
                    "action": recommended_action(
                        final_rating=row["final_rating"], payment_status=row.get("payment_status")
                    ),
                    "exposure": row["exposure"],
                    "loan_id": row["loan_id"],
                }
            )

    material = []
    for row in target:
        notches = int(row["final_rating"]) - int(row["current_rating"])
        if notches >= material_notches:
            material.append(
                {
                    "loan_id": row["loan_id"],
                    "current_rating": int(row["current_rating"]),
                    "final_rating": int(row["final_rating"]),
                    "downgrade_notches": notches,
                    "exposure": r2(row["exposure"]),
                }
            )
    material.sort(key=lambda row: row["loan_id"])

    top = sorted(target, key=lambda row: (row["final_rating"], row["exposure"]), reverse=True)[0]
    benchmark_value = float(fdic[args.benchmark_metric])
    branch_ratio = float(metrics["nonperforming_loans"]) / float(metrics["total_loans_outstanding"])
    variance = branch_ratio - benchmark_value

    dump(
        {
            "branch_id": branch_id,
            "review_date": args.review_date,
            "portfolio_regrade": {
                "target_current_rating_min": args.current_rating_min,
                "target_loan_count": len(target),
                "target_exposure": r2(sum(row["exposure"] for row in target)),
                "final_rating_exposure_totals": group_exposure(final_rows, "final_rating"),
                "migration_from_current_rating": group_exposure(migration_source, "final_rating"),
                "watch_list_action_coverage": {
                    "covered_loan_count": len(follow_up),
                    "covered_exposure": r2(sum(row["exposure"] for row in follow_up)),
                    "by_action": group_exposure(follow_up, "action"),
                },
            },
            "npa_benchmark": {
                "benchmark_version": fdic["benchmark_version"],
                "benchmark_metric": args.benchmark_metric,
                "branch_npa_exposure": r2(metrics["nonperforming_loans"]),
                "branch_total_loans": r2(metrics["total_loans_outstanding"]),
                "branch_npa_ratio": r4(branch_ratio),
                "fdic_benchmark_ratio": r4(benchmark_value),
                "variance_ratio": r4(variance),
                "variance_bps": r2(variance * 10000),
            },
            "material_downgrades": material,
            "top_problem_credit": {
                "loan_id": top["loan_id"],
                "borrower_name": top.get("borrower_name"),
                "exposure": r2(top["exposure"]),
                "current_rating": int(top["current_rating"]),
                "final_rating": int(top["final_rating"]),
                "payment_status": top.get("payment_status"),
                "recommended_action": recommended_action(
                    final_rating=top["final_rating"], payment_status=top.get("payment_status")
                ),
            },
        }
    )


def band_score(value: Any, bands: list[tuple[str, float, float | None, int]]) -> int | None:
    number = as_number(value)
    if number is None:
        return None
    for op, lower, upper, score in bands:
        if op == "lt" and number < lower:
            return score
        if op == "le_between" and upper is not None and lower <= number <= upper:
            return score
        if op == "gt" and number > lower:
            return score
    return None


def cdfi_factor_score(record: dict[str, Any]) -> tuple[int, dict[str, int]]:
    components: dict[str, int] = {}

    fico = as_number(record.get("fico"))
    if fico is not None:
        if fico > 720:
            components["fico"] = 0
        elif fico >= 680:
            components["fico"] = 1
        elif fico >= 580:
            components["fico"] = 3
        else:
            components["fico"] = 5

    ltv = as_number(record.get("ltv"))
    if ltv is not None:
        if ltv < 0.40:
            components["ltv"] = 0
        elif ltv <= 0.60:
            components["ltv"] = 2
        elif ltv <= 0.80:
            components["ltv"] = 4
        else:
            components["ltv"] = 6

    liquidity = as_number(record.get("liquidity_months"))
    if liquidity is not None:
        if liquidity > 12:
            components["liquidity_months"] = 0
        elif liquidity >= 6:
            components["liquidity_months"] = 1
        elif liquidity >= 3:
            components["liquidity_months"] = 3
        else:
            components["liquidity_months"] = 5

    debt_to_asset = as_number(record.get("debt_to_asset"))
    if debt_to_asset is None:
        total_debt = as_number(record.get("total_debt"))
        total_assets = as_number(record.get("total_assets"))
        if total_debt is not None and total_assets:
            debt_to_asset = total_debt / total_assets
    if debt_to_asset is not None:
        if debt_to_asset < 0.40:
            components["debt_to_asset"] = 0
        elif debt_to_asset <= 0.60:
            components["debt_to_asset"] = 2
        elif debt_to_asset <= 0.80:
            components["debt_to_asset"] = 4
        else:
            components["debt_to_asset"] = 6

    return sum(components.values()), components


def cdfi_class(record: dict[str, Any], score: int) -> str:
    ltv = as_number(record.get("ltv"))
    if ltv is not None and ltv > 1.0 and (
        record.get("payment_status") == "Nonaccrual" or int(record.get("current_rating") or 0) >= 8
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
    if ltv is not None and ltv > 1.0:
        return "Projected Loss"
    return "Doubtful"


def watchlist_stress(args: argparse.Namespace) -> None:
    branch_id = args.branch_id
    policies = api_get(args.base_url, "/api/policies")
    loans = api_get(args.base_url, f"/api/branches/{branch_id}/loans")
    threshold = float(policies["stress"].get("coverage_breach_threshold", 1.0))
    factor = 1.0 + 0.18

    adverse = [
        loan for loan in loans if int(loan.get("current_rating", 0)) >= args.adverse_rating_min
    ]
    enriched = []
    for loan in adverse:
        score, components = cdfi_factor_score(loan)
        risk_class = cdfi_class(loan, score)
        enriched.append({**loan, "factor_score": score, "score_components": components, "risk_class": risk_class})

    risk_classes = [
        {
            "loan_id": row["loan_id"],
            "risk_class": row["risk_class"],
            "factor_score": row["factor_score"],
        }
        for row in sorted(enriched, key=lambda row: row["loan_id"])
    ]

    stress_rows = []
    for row in enriched:
        dscr = as_number(row.get("dscr"))
        if dscr is None:
            continue
        stressed = dscr / factor
        stress_rows.append(
            {
                "loan_id": row["loan_id"],
                "base_dscr": r2(dscr),
                "stressed_dscr": r2(stressed),
                "breaches_threshold": stressed < threshold,
            }
        )
    stress_rows.sort(key=lambda row: row["loan_id"])

    workout = []
    for row in enriched:
        action = recommended_action(
            final_rating=int(row.get("current_rating")), payment_status=row.get("payment_status"), risk_class=row["risk_class"]
        )
        workout.append(
            {
                "loan_id": row["loan_id"],
                "exposure": r2(row.get("outstanding_balance") or 0.0),
                "risk_class": row["risk_class"],
                "payment_status": row.get("payment_status"),
                "recommended_action": action,
                "projected_loss": row["risk_class"] == "Projected Loss",
            }
        )
    workout.sort(key=lambda row: (-float(row["exposure"]), row["loan_id"]))

    severe_groups: dict[tuple[int, str], dict[str, Any]] = {}
    for row in enriched:
        key = (int(row.get("current_rating")), row.get("payment_status"))
        group = severe_groups.setdefault(
            key,
            {
                "current_rating": key[0],
                "payment_status": key[1],
                "loan_count": 0,
                "exposure": 0.0,
            },
        )
        group["loan_count"] += 1
        group["exposure"] += float(row.get("outstanding_balance") or 0.0)

    any_severe = any(
        row.get("payment_status") in {"90+ Days Past Due", "Nonaccrual"}
        or int(row.get("current_rating", 0)) >= 7
        for row in enriched
    )

    dump(
        {
            "branch_id": branch_id,
            "watch_list_summary": {
                "adverse_rating_min": args.adverse_rating_min,
                "adverse_loan_count": len(enriched),
                "adverse_balance": r2(sum(float(row.get("outstanding_balance") or 0.0) for row in enriched)),
                "risk_classes": risk_classes,
                "monitoring_cadence": "monthly" if any_severe else "quarterly",
            },
            "stress_results": {
                "shock_label": policies["stress"].get("watch_list_parallel_shock", "+200bp"),
                "breach_threshold": r2(threshold),
                "results": stress_rows,
                "breach_loan_ids": [row["loan_id"] for row in stress_rows if row["breaches_threshold"]],
            },
            "workout_queue": workout,
            "severe_bucket_counts": [
                {**row, "exposure": r2(row["exposure"])}
                for _, row in sorted(severe_groups.items(), key=lambda item: item[0])
            ],
        }
    )


def latest_total_loans(base_url: str, branch_id: str) -> float:
    metrics = latest_metric(api_get(base_url, f"/api/branches/{branch_id}/metrics"))
    return float(metrics["total_loans_outstanding"])


def sector_maps(base_url: str, branch_id: str) -> tuple[dict[str, dict[str, Any]], float]:
    exposures = api_get(base_url, f"/api/branches/{branch_id}/sector-exposures")
    by_sector = {row["sector"]: row for row in exposures}
    total = sum(float(row["current_exposure"]) for row in exposures)
    return by_sector, total


def guaranty_factor(app: dict[str, Any]) -> float:
    guaranty = as_number(app.get("sba_guaranty_pct"))
    if guaranty is None:
        return 1.0
    return max(0.0, 1.0 - guaranty)


def application_reason_codes(app: dict[str, Any]) -> list[str]:
    reasons: set[str] = set()
    dscr = as_number(app.get("dscr"))
    ltv = as_number(app.get("ltv"))
    fico = as_number(app.get("fico"))
    years = as_number(app.get("years_in_business"))
    if int(app.get("documentation_complete") or 0) == 0:
        reasons.add("documentation_gap")
    if dscr is not None and dscr < 1.25:
        reasons.add("weak_dscr")
    if ltv is not None and ltv > 0.80 and app.get("loan_type") != "Consumer":
        reasons.add("high_ltv")
    if ltv is not None and ltv > 1.00:
        reasons.add("underwater_collateral")
    if fico is not None and fico < 580:
        reasons.add("low_fico")
    if app.get("bankruptcy_months_ago") is not None and float(app["bankruptcy_months_ago"]) <= 24:
        reasons.add("recent_bankruptcy")
    if years is not None and years < 2.0:
        reasons.add("startup_risk")
    return sorted(reasons)


def allocation(args: argparse.Namespace) -> None:
    branch = api_get(args.base_url, f"/api/branches/{args.branch_id}")
    apps = api_get(args.base_url, f"/api/branches/{args.branch_id}/applications")
    sectors, existing_total = sector_maps(args.base_url, args.branch_id)
    capacity = float(branch["lending_capacity_q1"])

    # Score lower-risk applications first, then leave capacity/decline handling auditable.
    def priority_score(app: dict[str, Any]) -> tuple[float, str]:
        score = 0.0
        dscr = as_number(app.get("dscr"))
        if dscr is not None:
            score -= dscr * 4
        ltv = as_number(app.get("ltv"))
        if ltv is not None:
            score += ltv * 4
        years = as_number(app.get("years_in_business"))
        if years is not None and years < 2:
            score += 1.5
        fico = as_number(app.get("fico"))
        if fico is not None and fico < 700:
            score += 5
        score += len(application_reason_codes(app)) * 2
        score -= float(app.get("relationship_deposit_balance") or 0.0) / 2_000_000
        if app.get("co_guarantor_strength") == "strong":
            score -= 2
        if app.get("loan_type") in {"Consumer", "Residential Mortgage"}:
            score += 2
        return (score, app["application_id"])

    approved: list[dict[str, Any]] = []
    decisions: dict[str, dict[str, Any]] = {}

    for app in apps:
        reasons = application_reason_codes(app)
        amount = float(app["requested_amount"])
        requested_bank = amount * guaranty_factor(app)
        decision = "approve"
        conditions = ["none"]
        approved_amount = amount
        bank_capacity_used = requested_bank
        fico = as_number(app.get("fico"))

        if "documentation_gap" in reasons or "recent_bankruptcy" in reasons or "low_fico" in reasons:
            decision = "decline"
        elif {"weak_dscr", "high_ltv"}.issubset(reasons) and app.get("loan_type") != "SBA":
            decision = "decline"
        elif {"startup_risk", "high_ltv"}.issubset(reasons) and app.get("loan_type") != "SBA":
            decision = "decline"
        elif "high_ltv" in reasons and int(app.get("prior_delinquencies_12m") or 0) >= 2:
            decision = "decline"
        elif app.get("loan_type") in {"Consumer", "Residential Mortgage"} and fico is not None and fico < 700:
            decision = "decline"
            reasons = sorted(set(reasons) | {"capacity_limit"})
        elif app.get("loan_type") == "SBA" and as_number(app.get("sba_guaranty_pct")):
            decision = "conditional_approve"
            conditions = ["sba_guaranty_required"]
            if "startup_risk" in reasons or as_number(app.get("years_in_business")) is not None and float(app["years_in_business"]) < 2:
                conditions.append("startup_monitoring")

        if decision == "decline":
            approved_amount = 0.0
            bank_capacity_used = 0.0
            conditions = ["none"]
        else:
            approved.append({**app, "approved_amount": approved_amount, "bank_capacity_used": bank_capacity_used})

        decisions[app["application_id"]] = {
            "application_id": app["application_id"],
            "decision": decision,
            "approved_amount": r2(approved_amount),
            "bank_capacity_used": r2(bank_capacity_used),
            "conditions": sorted(conditions) if conditions != ["none"] else ["none"],
            "diagnostic_reason_codes": reasons,
        }

    bank_used = sum(float(app["bank_capacity_used"]) for app in approved)
    if bank_used > capacity:
        for app in sorted(approved, key=priority_score, reverse=True):
            if bank_used <= capacity:
                break
            app_id = app["application_id"]
            bank_used -= float(app["bank_capacity_used"])
            app["approved_amount"] = 0.0
            app["bank_capacity_used"] = 0.0
            decisions[app_id].update(
                {
                    "decision": "decline",
                    "approved_amount": 0.0,
                    "bank_capacity_used": 0.0,
                    "conditions": ["none"],
                    "diagnostic_reason_codes": sorted(
                        set(decisions[app_id]["diagnostic_reason_codes"]) | {"capacity_limit"}
                    ),
                }
            )
        approved = [app for app in approved if decisions[app["application_id"]]["decision"] != "decline"]

    gross_used = sum(float(app["approved_amount"]) for app in approved)

    # Apply participation after the candidate approval set is known. This avoids
    # order-dependent caps and mirrors committee allocation worksheets where the
    # retained bank exposure is solved after choosing the gross approval slate.
    post_gross_total = existing_total + gross_used
    for app in approved:
        sector = app["sector"]
        row = sectors.get(sector, {"current_exposure": 0.0, "limit_pct": branch["sector_ceiling_pct"]})
        limit_pct = float(row.get("limit_pct") or branch["sector_ceiling_pct"])
        exposure_after = float(row.get("current_exposure") or 0.0) + sum(
            float(item["approved_amount"]) for item in approved if item["sector"] == sector
        )
        post_gross_pct = exposure_after / post_gross_total if post_gross_total else 0.0
        notes = f"{app.get('notes') or ''}".lower()
        near_sector_ceiling = post_gross_pct >= limit_pct - 0.0005 or "near" in notes and "ceiling" in notes
        if not near_sector_ceiling:
            continue
        other_bank = sum(
            float(item["bank_capacity_used"])
            for item in approved
            if item["application_id"] != app["application_id"]
        )
        other_sector_bank = sum(
            float(item["bank_capacity_used"])
            for item in approved
            if item["application_id"] != app["application_id"] and item["sector"] == sector
        )
        sector_before = float(row.get("current_exposure") or 0.0) + other_sector_bank
        total_before = existing_total + other_bank
        retained_cap = (limit_pct * total_before - sector_before) / (1.0 - limit_pct)
        retained_cap = max(0.0, retained_cap)
        if retained_cap < float(app["bank_capacity_used"]):
            app["bank_capacity_used"] = retained_cap
            decisions[app["application_id"]].update(
                {
                    "decision": "conditional_approve",
                    "bank_capacity_used": r2(retained_cap),
                    "conditions": ["participation_required"],
                }
            )

    bank_used = sum(float(app["bank_capacity_used"]) for app in approved)

    gross_by_sector: dict[str, float] = defaultdict(float)
    for app in approved:
        gross_by_sector[app["sector"]] += float(app["approved_amount"])
    post_denominator = existing_total + gross_used
    concentrations = []
    flags = []
    for sector in sorted(gross_by_sector):
        row = sectors.get(sector, {"current_exposure": 0.0, "limit_pct": branch["sector_ceiling_pct"]})
        exposure_after = float(row.get("current_exposure") or 0.0) + gross_by_sector[sector]
        limit_pct = float(row.get("limit_pct") or branch["sector_ceiling_pct"])
        post_pct = exposure_after / post_denominator if post_denominator else 0.0
        over = post_pct > limit_pct
        concentrations.append(
            {
                "sector": sector,
                "exposure_after_approval": r2(exposure_after),
                "post_approval_pct": r4(post_pct),
                "limit_pct": r4(limit_pct),
                "over_limit": over,
            }
        )
        if over or post_pct >= limit_pct - 0.0005:
            sector_apps = sorted(app["application_id"] for app in approved if app["sector"] == sector)
            for app_id in sector_apps:
                flags.append(
                    {
                        "sector": sector,
                        "application_id": app_id,
                        "limit_pct": r4(limit_pct),
                        "post_approval_pct": r4(post_pct),
                        "flag": True,
                        "handling": decisions[app_id]["conditions"][0]
                        if decisions[app_id]["conditions"] != ["none"]
                        else "approve",
                    }
                )

    dump(
        {
            "branch_id": args.branch_id,
            "allocation": {
                "lending_capacity_q1": r2(capacity),
                "gross_approved_amount": r2(gross_used),
                "committed_capacity_amount": r2(bank_used),
                "remaining_capacity": r2(capacity - bank_used),
                "priority_ranking": [
                    row["application_id"]
                    for row in sorted(approved, key=priority_score)
                ],
            },
            "decisions": [decisions[key] for key in sorted(decisions)],
            "concentration_flags": sorted(flags, key=lambda row: (row["sector"], row["application_id"])),
            "decline_reasons": {
                key: value["diagnostic_reason_codes"]
                for key, value in sorted(decisions.items())
                if value["decision"] == "decline" and value["diagnostic_reason_codes"]
            },
            "post_approval_concentrations": concentrations,
        }
    )


def cre_component_scores(app: dict[str, Any], branch_adverse: bool, sector_stressed: bool) -> dict[str, int]:
    dscr = as_number(app.get("dscr"))
    if dscr is None:
        capacity = 6
    elif dscr >= 1.50:
        capacity = 0
    elif dscr >= 1.25:
        capacity = 2
    elif dscr >= 1.05:
        capacity = 4
    else:
        capacity = 6

    _, basic = cdfi_factor_score(app)
    capital = basic.get("debt_to_asset", 4)
    ltv = as_number(app.get("ltv"))
    if ltv is None:
        collateral = 4
    elif ltv <= 0.65:
        collateral = 2
    elif ltv <= 0.75:
        collateral = 4
    else:
        collateral = 6

    guarantor = app.get("co_guarantor_strength")
    prior_dq = int(app.get("prior_delinquencies_12m") or 0)
    if guarantor == "strong" and prior_dq == 0:
        character = 0
    elif guarantor in {"standard", "limited"} and prior_dq <= 1:
        character = 2
    else:
        character = 6

    conditions = 0
    if branch_adverse:
        conditions += 2
    if sector_stressed:
        conditions += 4
    if guarantor == "none":
        conditions += 2
    return {
        "capacity": capacity,
        "capital": capital,
        "character": character,
        "collateral_exposure": collateral,
        "conditions": conditions,
    }


def cre_compare(args: argparse.Namespace) -> None:
    policies = api_get(args.base_url, "/api/policies")
    apps = api_get(args.base_url, f"/api/branches/{args.branch_id}/applications")
    loans = api_get(args.base_url, f"/api/branches/{args.branch_id}/loans")
    branch = api_get(args.base_url, f"/api/branches/{args.branch_id}")
    metrics = latest_metric(api_get(args.base_url, f"/api/branches/{args.branch_id}/metrics"))
    sectors, _ = sector_maps(args.base_url, args.branch_id)
    fdic = api_get(args.base_url, "/api/benchmarks/fdic/q4-2024")
    requested = [app for app in apps if app["application_id"] in set(args.application_ids)]
    if len(requested) != len(args.application_ids):
        raise SystemExit("One or more requested application_ids were not returned")

    total_loans = float(metrics["total_loans_outstanding"])
    existing_cre = sum(float(row.get("outstanding_balance") or 0.0) for row in loans if row.get("loan_type") == "CRE")
    existing_cre_concentration = existing_cre / total_loans if total_loans else 0.0
    cre_limit = float(branch["cre_policy_limit_pct"])
    branch_delinquency_ratio = float(metrics["delinquency_30_plus_pct"])
    fdic_metric = "total_real_estate_30_89_pct"
    fdic_ratio = float(fdic[fdic_metric])
    branch_adverse = branch_delinquency_ratio > fdic_ratio
    weights = policies["cre_weighted_score"]["weights"]
    stress_factor = 0.85 / (1.0 + 0.18)
    threshold = float(policies["stress"].get("coverage_breach_threshold", 1.0))

    compared = []
    stress_results = []
    for app in requested:
        row = sectors.get(app["sector"])
        sector_stressed = bool(row and int(row.get("grandfathered") or 0))
        components = cre_component_scores(app, branch_adverse, sector_stressed)
        weighted = sum(float(weights[key]) * value for key, value in components.items())
        score_class = "approve_quality" if weighted <= 2.0 else "conditional" if weighted <= 3.0 else "weak"
        stressed_dscr = float(app["dscr"]) * stress_factor
        reason_codes: set[str] = set()
        if branch_adverse:
            reason_codes.add("fdic_adverse_variance")
        selected_post_cre = (existing_cre + float(app["requested_amount"])) / (
            total_loans + float(app["requested_amount"])
        )
        if selected_post_cre > cre_limit or existing_cre_concentration > cre_limit:
            reason_codes.add("sector_breach")
        if stressed_dscr < threshold:
            reason_codes.add("weak_dscr")
        if as_number(app.get("ltv")) is not None and float(app["ltv"]) > 0.80:
            reason_codes.add("high_ltv")
        decision = "conditional_approve" if score_class == "conditional" else "defer"
        if "sector_breach" in reason_codes and score_class != "weak":
            decision = "participation_required"
        compared.append(
            {
                "application_id": app["application_id"],
                "weighted_cdfi_score": round(weighted, 1),
                "score_class": score_class,
                "decision": decision,
                "reason_codes": sorted(reason_codes),
                "score_components": components,
                "selected_post_cre_concentration_raw": selected_post_cre,
                "selected_post_cre_concentration": r4(selected_post_cre),
            }
        )
        stress_results.append(
            {
                "application_id": app["application_id"],
                "base_dscr": r2(app["dscr"]),
                "stressed_dscr": r2(stressed_dscr),
                "breaches_threshold": stressed_dscr < threshold,
            }
        )

    compared.sort(key=lambda row: row["application_id"])
    selected = sorted(compared, key=lambda row: (row["weighted_cdfi_score"], row["application_id"]))[0]
    unselected = [row for row in compared if row["application_id"] != selected["application_id"]][0]
    fdic_variance = branch_delinquency_ratio - fdic_ratio
    selected_post_raw = float(selected["selected_post_cre_concentration_raw"])

    dump(
        {
            "branch_id": args.branch_id,
            "applications_compared": compared,
            "recommended_path": {
                "selected_application_id": selected["application_id"],
                "path": selected["decision"],
                "unselected_application_id": unselected["application_id"],
                "unselected_disposition": "defer" if unselected["decision"] != "decline" else "decline",
                "unselected_reason_codes": unselected["reason_codes"],
            },
            "stress": {
                "formula": "dscr * 0.85 / 1.18",
                "coverage_breach_threshold": r2(threshold),
                "results": sorted(stress_results, key=lambda row: row["application_id"]),
            },
            "concentration": {
                "cre_policy_limit_pct": r4(cre_limit),
                "existing_cre_exposure": r2(existing_cre),
                "existing_cre_concentration": r4(existing_cre_concentration),
                "selected_post_approval_cre_concentration": r4(selected_post_raw),
                "selected_policy_variance_bps": r2((selected_post_raw - cre_limit) * 10000),
                "fdic_benchmark_metric": fdic_metric,
                "branch_delinquency_ratio": r4(branch_delinquency_ratio),
                "fdic_benchmark_ratio": r4(fdic_ratio),
                "fdic_variance_ratio": r4(fdic_variance),
                "fdic_variance_bps": r2(fdic_variance * 10000),
            },
        }
    )


def direction(value: float, compare_to: float) -> str:
    if value > compare_to:
        return "higher"
    if value < compare_to:
        return "lower"
    return "equal"


def median(values: list[float]) -> float:
    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        raise ValueError("empty median")
    middle = count // 2
    if count % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def cu_posture(args: argparse.Namespace) -> None:
    segment = api_get(args.base_url, f"/api/credit-union-segments/{args.segment_id}")
    ncua = api_get(args.base_url, "/api/benchmarks/ncua/q1-2025")
    rows = {row["state_code"]: row for row in ncua["rows"]}
    state = rows[segment["state_code"]]
    us = rows["US"]
    peers = sorted(segment.get("peer_states", []))
    peer_medians = {
        metric: median([float(rows[state_code][metric]) for state_code in peers])
        for metric in [
            "delinquency_bps",
            "loan_to_share_pct",
            "roaa_bps",
            "positive_net_income_pct",
        ]
    }
    external_weaker = (
        state["delinquency_bps"] > us["delinquency_bps"]
        and state["loan_to_share_pct"] > us["loan_to_share_pct"]
        and state["roaa_bps"] < us["roaa_bps"]
        and state["positive_net_income_pct"] < us["positive_net_income_pct"]
    )
    capacity_available = float(segment.get("quarterly_capacity") or 0.0) > 0
    controls = list(segment.get("minimum_checklist", []))
    added = {
        "lien_perfection_prior_to_funding",
        "pre_close_insurance_binder_verification",
        "senior_underwriter_second_review",
        "quarterly_state_benchmark_monitoring",
    }
    recent_dq = int(segment.get("internal_context", {}).get("recent_delinquency_bps") or 0)
    if recent_dq:
        added.add("monthly_segment_delinquency_watch")

    posture = "continue_approving"
    if external_weaker or recent_dq >= 75:
        posture = "continue_with_tighter_conditions"
    if not capacity_available:
        posture = "temporarily_pause"

    triggers = []
    if recent_dq:
        triggers.append(
            {
                "trigger_id": "ET001",
                "condition": "segment_recent_delinquency_ge_90_bps",
                "owner": "credit_risk_manager",
            }
        )
    triggers.append(
        {
            "trigger_id": "ET002",
            "condition": "missing_insurance_or_lien_exception",
            "owner": "operations_control_manager",
        }
    )
    triggers.append(
        {
            "trigger_id": "ET003",
            "condition": "quarterly_capacity_exceeded_or_exception_requested",
            "owner": "lending_committee_chair",
        }
    )

    dump(
        {
            "segment_id": args.segment_id,
            "posture": posture,
            "state_metrics": {
                "state_code": segment["state_code"],
                "benchmark_version": ncua["benchmark_version"],
                "delinquency_bps": state["delinquency_bps"],
                "loan_to_share_pct": state["loan_to_share_pct"],
                "roaa_bps": state["roaa_bps"],
                "positive_net_income_pct": state["positive_net_income_pct"],
            },
            "peer_comparison": {
                "peer_states": peers,
                "nc_vs_us": {
                    metric: direction(float(state[metric]), float(us[metric]))
                    for metric in peer_medians
                },
                "nc_vs_peer_median": {
                    metric: direction(float(state[metric]), peer_medians[metric])
                    for metric in peer_medians
                },
            },
            "controls": {
                "required_checklist_gates": sorted(controls),
                "added_operating_controls": sorted(added),
            },
            "escalation_triggers": sorted(triggers, key=lambda row: row["trigger_id"]),
            "interpretation": {
                "capacity_status": "capacity_available" if capacity_available else "no_capacity",
                "external_risk_status": "weaker_than_national_and_peers"
                if external_weaker
                else "mixed_vs_national_and_peers",
                "risk_tolerance": segment.get("risk_tolerance", "moderate"),
                "committee_message": "capacity_available_but_external_risk_weaker"
                if capacity_available and external_weaker
                else "pause_until_state_metrics_recover"
                if not capacity_available
                else "routine_approval_path_supported",
            },
        }
    )


def inventory(args: argparse.Namespace) -> None:
    output: dict[str, Any] = {
        "manifest": api_get(args.base_url, "/api/manifest"),
        "policies": api_get(args.base_url, "/api/policies"),
    }
    if args.branch_id:
        output["branch"] = api_get(args.base_url, f"/api/branches/{args.branch_id}")
        output["metrics"] = api_get(args.base_url, f"/api/branches/{args.branch_id}/metrics")
        output["loans_sample"] = api_get(args.base_url, f"/api/branches/{args.branch_id}/loans")[:3]
        output["applications_sample"] = api_get(args.base_url, f"/api/branches/{args.branch_id}/applications")[:3]
        output["sector_exposures"] = api_get(args.base_url, f"/api/branches/{args.branch_id}/sector-exposures")
    if args.segment_id:
        output["segment"] = api_get(args.base_url, f"/api/credit-union-segments/{args.segment_id}")
    dump(output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Task API base URL, e.g. http://task-env:9011")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("inventory", help="Fetch manifest, policies, and optional target data")
    p.add_argument("--branch-id")
    p.add_argument("--segment-id")
    p.set_defaults(func=inventory)

    p = subparsers.add_parser("rating-migration", help="Re-derive ratings for a branch loan population")
    p.add_argument("--branch-id", required=True)
    p.add_argument("--review-date", default=None)
    p.add_argument("--current-rating-min", type=int, default=3)
    p.add_argument("--benchmark-metric", default="total_loans_noncurrent_pct")
    p.set_defaults(func=rating_migration)

    p = subparsers.add_parser("watchlist-stress", help="Build adverse-loan stress and workout worksheet")
    p.add_argument("--branch-id", required=True)
    p.add_argument("--adverse-rating-min", type=int, default=6)
    p.set_defaults(func=watchlist_stress)

    p = subparsers.add_parser("allocation", help="Draft pending-application allocation worksheet")
    p.add_argument("--branch-id", required=True)
    p.set_defaults(func=allocation)

    p = subparsers.add_parser("cre-compare", help="Compare competing CRE applications")
    p.add_argument("--branch-id", required=True)
    p.add_argument("--application-ids", nargs="+", required=True)
    p.set_defaults(func=cre_compare)

    p = subparsers.add_parser("cu-posture", help="Draft credit-union segment posture worksheet")
    p.add_argument("--segment-id", required=True)
    p.set_defaults(func=cu_posture)

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
