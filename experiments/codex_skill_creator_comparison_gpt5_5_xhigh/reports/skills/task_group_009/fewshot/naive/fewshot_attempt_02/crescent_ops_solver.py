#!/usr/bin/env python3
"""Generic Crescent Finance Ops calculator for skill users."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


def money(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def ratio(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def fetch_json(base_url: str, endpoint: str) -> Any:
    url = base_url.rstrip("/") + endpoint
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return json.load(response)
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed to fetch {url}: {exc}") from exc


def discover_base_url(input_dir: Path, override: str | None) -> str:
    if override:
        return override
    env_url = os.environ.get("TASK_ENV_BASE_URL")
    if env_url:
        return env_url

    payload_env = input_dir / "payloads" / "environment_access.json"
    if payload_env.exists():
        candidate = read_json(payload_env).get("base_url")
        if candidate and not str(candidate).startswith("<"):
            return str(candidate)

    for start in [input_dir, Path.cwd(), Path(__file__).resolve().parent]:
        for parent in [start, *start.parents]:
            path = parent / "environment_access.md"
            if path.exists():
                match = re.search(r"Base URL:\s*(\S+)", path.read_text(encoding="utf-8"))
                if match:
                    return match.group(1)

    raise SystemExit("Base URL not found; pass --base-url or set TASK_ENV_BASE_URL.")


def ordered_output(required_keys: list[str], values: dict[str, Any]) -> dict[str, Any]:
    if required_keys:
        return {key: values[key] for key in required_keys if key in values}
    return values


def sort_dict(data: dict[str, Any]) -> dict[str, Any]:
    return {key: data[key] for key in sorted(data)}


def finance_context(base_url: str) -> dict[str, Any]:
    branches = fetch_json(base_url, "/api/finance/branches")
    period_map = fetch_json(base_url, "/api/finance/period-map")
    accounts = fetch_json(base_url, "/api/finance/accounts")
    records = fetch_json(base_url, "/api/finance/records")

    periods_by_year: dict[int, list[str]] = defaultdict(list)
    period_year: dict[str, int] = {}
    for row in sorted(period_map, key=lambda r: (r["fiscal_year"], r["month_number"])):
        periods_by_year[row["fiscal_year"]].append(row["period"])
        period_year[row["period"]] = row["fiscal_year"]

    return {
        "branches": branches,
        "branch_by_id": {b["branch_id"]: b for b in branches},
        "accounts": accounts,
        "account_category": {a["account"]: a["category"] for a in accounts},
        "records": records,
        "periods_by_year": dict(periods_by_year),
        "period_year": period_year,
    }


def finance_sum(ctx: dict[str, Any], branch_ids: list[str], accounts: list[str], periods: list[str]) -> float:
    branch_set = set(branch_ids)
    account_set = set(accounts)
    total = 0.0
    for record in ctx["records"]:
        if record["branch_id"] in branch_set and record["account"] in account_set:
            total += sum(float(record["values"].get(period, 0.0)) for period in periods)
    return total


def accounts_in_category(ctx: dict[str, Any], category: str) -> list[str]:
    return [account for account, cat in ctx["account_category"].items() if cat == category]


def finance_metrics(ctx: dict[str, Any], branch_ids: list[str], periods: list[str]) -> dict[str, float]:
    revenue = finance_sum(ctx, branch_ids, accounts_in_category(ctx, "revenue"), periods)
    cogs = finance_sum(ctx, branch_ids, accounts_in_category(ctx, "cogs"), periods)
    sga = finance_sum(ctx, branch_ids, accounts_in_category(ctx, "sga"), periods)
    allocations = finance_sum(ctx, branch_ids, accounts_in_category(ctx, "allocations"), periods)
    gross_margin = revenue - cogs
    ebitda = gross_margin - sga - allocations
    active_customers = finance_sum(ctx, branch_ids, ["active_customers"], periods)
    labor_headcount = finance_sum(ctx, branch_ids, ["labor_headcount"], periods)
    return {
        "revenue": revenue,
        "cogs": cogs,
        "gross_margin": gross_margin,
        "sga": sga,
        "allocations": allocations,
        "ebitda": ebitda,
        "active_customers": active_customers,
        "labor_headcount": labor_headcount,
    }


def rounded_income(metrics: dict[str, float]) -> dict[str, float]:
    return {
        "revenue": money(metrics["revenue"]),
        "cogs": money(metrics["cogs"]),
        "gross_margin": money(metrics["gross_margin"]),
        "sga": money(metrics["sga"]),
        "allocations": money(metrics["allocations"]),
        "ebitda": money(metrics["ebitda"]),
    }


def fiscal_year_key(required: list[str], marker: str, default_key: str) -> str:
    for key in required:
        if marker in key:
            return key
    return default_key


def solve_branch_close(base_url: str, request: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    ctx = finance_context(base_url)
    required = template.get("required_top_level_keys", [])
    branch_id = request["target_branch_id"]
    close_period = request["close_period"]
    prior_period = request["prior_period"]
    branch = ctx["branch_by_id"][branch_id]
    current_year = ctx["period_year"][close_period]
    prior_years = [year for year in sorted(ctx["periods_by_year"]) if year < current_year]
    prior_year = prior_years[-1]
    current_periods = ctx["periods_by_year"][current_year]
    prior_periods = ctx["periods_by_year"][prior_year]

    close_metrics = finance_metrics(ctx, [branch_id], [close_period])
    current_metrics = finance_metrics(ctx, [branch_id], current_periods)
    prior_metrics = finance_metrics(ctx, [branch_id], prior_periods)
    prior_month_metrics = finance_metrics(ctx, [branch_id], [prior_period])

    current_fy = rounded_income(current_metrics)
    current_fy["ebitda_margin"] = ratio(safe_div(current_metrics["ebitda"], current_metrics["revenue"]))
    current_fy["arpu"] = money(safe_div(current_metrics["revenue"], current_metrics["active_customers"]))
    current_fy["sales_per_labor_headcount"] = money(
        safe_div(current_metrics["revenue"], current_metrics["labor_headcount"])
    )

    region_branches = sorted(
        b["branch_id"] for b in ctx["branches"] if b["region_id"] == branch["region_id"]
    )
    region_metrics = finance_metrics(ctx, region_branches, current_periods)
    region_ids = sorted({b["region_id"] for b in ctx["branches"]})
    region_ebitda = []
    for rid in region_ids:
        bids = [b["branch_id"] for b in ctx["branches"] if b["region_id"] == rid]
        region_ebitda.append((rid, finance_metrics(ctx, bids, current_periods)["ebitda"]))
    region_ranked = sorted(region_ebitda, key=lambda item: (-item[1], item[0]))

    all_branch_growth = []
    all_branch_arpu = []
    for b in ctx["branches"]:
        bid = b["branch_id"]
        cm = finance_metrics(ctx, [bid], current_periods)
        pm = finance_metrics(ctx, [bid], prior_periods)
        all_branch_growth.append((bid, safe_div(cm["revenue"] - pm["revenue"], pm["revenue"])))
        all_branch_arpu.append((bid, safe_div(cm["revenue"], cm["active_customers"])))
    growth_ranked = sorted(all_branch_growth, key=lambda item: (-item[1], item[0]))
    arpu_ranked = sorted(all_branch_arpu, key=lambda item: (-item[1], item[0]))

    income_key = fiscal_year_key(required, "_income_statement", f"{close_period.lower()}_income_statement")
    comparison_key = fiscal_year_key(required, "_vs_", f"fy{current_year}_vs_fy{prior_year}")

    period_convention = {}
    for year, periods in sorted(ctx["periods_by_year"].items()):
        nums = [int(period[1:]) for period in periods]
        period_convention[f"M{min(nums)}_to_M{max(nums)}"] = f"FY{year}"
    period_convention["current_month"] = close_period
    period_convention["prior_month"] = prior_period

    values = {
        "target_branch_id": branch_id,
        "target_branch_name": branch["branch_name"],
        "period_convention": period_convention,
        income_key: rounded_income(close_metrics),
        "mom_revenue_variance": {
            "amount": money(close_metrics["revenue"] - prior_month_metrics["revenue"]),
            "pct": ratio(safe_div(close_metrics["revenue"] - prior_month_metrics["revenue"], prior_month_metrics["revenue"])),
        },
        comparison_key: {
            f"fy{current_year}": current_fy,
            "revenue_growth_pct": ratio(
                safe_div(current_metrics["revenue"] - prior_metrics["revenue"], prior_metrics["revenue"])
            ),
            "ebitda_growth_pct": ratio(
                safe_div(current_metrics["ebitda"] - prior_metrics["ebitda"], prior_metrics["ebitda"])
            ),
        },
        "region_context": {
            "region_id": branch["region_id"],
            "branch_ids": region_branches,
            "fy%s_ebitda" % current_year: money(region_metrics["ebitda"]),
            "ebitda_rank_desc": [rid for rid, _ in region_ranked].index(branch["region_id"]) + 1,
        },
        "branch_rankings": {
            "sales_growth_rank_desc": [bid for bid, _ in growth_ranked].index(branch_id) + 1,
            "top_sales_growth_branch_id": growth_ranked[0][0],
            "top_arpu_branch_id": arpu_ranked[0][0],
        },
    }
    return ordered_output(required, values)


def solve_region(base_url: str, request: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    ctx = finance_context(base_url)
    required = template.get("required_top_level_keys", [])
    region_id = request["target_region_id"]
    years = sorted(int(year) for year in request["requested_comparison_years"])
    prior_year, current_year = years[0], years[-1]
    branch_ids = sorted(b["branch_id"] for b in ctx["branches"] if b["region_id"] == region_id)

    metrics_by_year = {
        year: finance_metrics(ctx, branch_ids, ctx["periods_by_year"][year]) for year in years
    }
    prior = metrics_by_year[prior_year]
    current = metrics_by_year[current_year]

    branch_ebitda = [
        (bid, finance_metrics(ctx, [bid], ctx["periods_by_year"][current_year])["ebitda"])
        for bid in branch_ids
    ]
    desc = sorted(branch_ebitda, key=lambda item: (-item[1], item[0]))
    asc = sorted(branch_ebitda, key=lambda item: (item[1], item[0]))

    values = {
        "region_id": region_id,
        "branch_ids": branch_ids,
        f"fy{prior_year}": {
            "revenue": money(prior["revenue"]),
            "sga": money(prior["sga"]),
            "allocations": money(prior["allocations"]),
            "ebitda": money(prior["ebitda"]),
        },
        f"fy{current_year}": {
            "revenue": money(current["revenue"]),
            "sga": money(current["sga"]),
            "allocations": money(current["allocations"]),
            "ebitda": money(current["ebitda"]),
            "ebitda_margin": ratio(safe_div(current["ebitda"], current["revenue"])),
            "sales_per_labor_headcount": money(
                safe_div(current["revenue"], current["labor_headcount"])
            ),
        },
        "revenue_growth_pct": ratio(safe_div(current["revenue"] - prior["revenue"], prior["revenue"])),
        "top_ebitda_branch_id": desc[0][0],
        "bottom_ebitda_branch_id": asc[0][0],
        "region_reconciliation_variance": money(current["ebitda"] - sum(v for _, v in branch_ebitda)),
    }
    return ordered_output(required, values)


def compensation_context(base_url: str) -> dict[str, Any]:
    return {
        "rate_book": fetch_json(base_url, "/api/compensation/rate-book"),
        "rosters": fetch_json(base_url, "/api/compensation/rosters"),
        "scenarios": fetch_json(base_url, "/api/compensation/scenarios"),
    }


def seniority_weekly(rate_book: dict[str, Any], years: int) -> float:
    for band in rate_book["seniority_weekly"]:
        max_years = band["max_years"]
        if years >= band["min_years"] and (max_years is None or years <= max_years):
            return float(band["weekly_amount"])
    return 0.0


def forecast_factors(rate_book: dict[str, Any], scenario: dict[str, Any] | None, year_label: str) -> dict[str, float]:
    if year_label == "current":
        return {
            "years_add": 0,
            "mws": float(rate_book["minimum_weekly_scale"]),
            "overscale_factor": 1.0,
            "seniority_factor": 1.0,
            "title_multiplier": 1.0,
        }

    if scenario is None:
        raise ValueError("scenario is required for forecast years")

    first = scenario["year_plus_1"]
    if year_label == "year_plus_1":
        return {
            "years_add": 1,
            "mws": float(rate_book["minimum_weekly_scale"]) * (1 + first["mws_growth"]),
            "overscale_factor": 1 + first["overscale_growth"],
            "seniority_factor": 1 + first["seniority_growth"],
            "title_multiplier": first["title_pct_multiplier"],
        }

    second = scenario["year_plus_2"]
    return {
        "years_add": 2,
        "mws": float(rate_book["minimum_weekly_scale"]) * (1 + first["mws_growth"]) * (1 + second["mws_growth"]),
        "overscale_factor": (1 + first["overscale_growth"]) * (1 + second["overscale_growth"]),
        "seniority_factor": (1 + first["seniority_growth"]) * (1 + second["seniority_growth"]),
        "title_multiplier": second["title_pct_multiplier"],
    }


def compensation_totals(
    rate_book: dict[str, Any],
    rosters: list[dict[str, Any]],
    ensemble_id: str,
    scenario: dict[str, Any] | None = None,
    year_label: str = "current",
) -> tuple[dict[str, float], dict[str, float], float]:
    rows = [row for row in rosters if row["ensemble_id"] == ensemble_id]
    pay_types = rate_book["pay_types"]
    pay_totals = {pay_type: 0.0 for pay_type in pay_types}
    quarter_totals = {quarter: 0.0 for quarter in rate_book["quarter_weeks"]}
    factors = forecast_factors(rate_book, scenario, year_label)

    for row in rows:
        title = row.get("title")
        for quarter, weeks in row["weeks_by_quarter"].items():
            components = {
                "Minimum Weekly Scale": factors["mws"] * weeks,
                "Titled Position Premium": 0.0,
                "Seniority": seniority_weekly(rate_book, row["years_of_service"] + int(factors["years_add"]))
                * factors["seniority_factor"]
                * weeks,
                "Overscale": float(row["overscale_weekly"]) * factors["overscale_factor"] * weeks,
            }
            if title and not row.get("combined_overscale_includes_title", False):
                pct = rate_book["title_premium_pct"][title] * factors["title_multiplier"]
                components["Titled Position Premium"] = factors["mws"] * pct * weeks
            for pay_type in pay_types:
                pay_totals[pay_type] += components[pay_type]
                quarter_totals[quarter] += components[pay_type]

    annual_total = sum(pay_totals.values())
    return pay_totals, quarter_totals, annual_total


def roster_counts(rate_book: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, int]:
    standard = rate_book["quarter_weeks"]
    return {
        "combined_overscale_employee_count": sum(
            1 for row in rows if row.get("combined_overscale_includes_title", False)
        ),
        "partial_quarter_employee_count": sum(
            1
            for row in rows
            if any(row["weeks_by_quarter"].get(q) != weeks for q, weeks in standard.items())
        ),
    }


def solve_comp_current(base_url: str, request: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    ctx = compensation_context(base_url)
    rb = ctx["rate_book"]
    rows = [row for row in ctx["rosters"] if row["ensemble_id"] == request["ensemble_id"]]
    pay_totals, quarter_totals, annual_total = compensation_totals(rb, ctx["rosters"], request["ensemble_id"])
    counts = roster_counts(rb, rows)
    pay_order = rb["pay_types"]
    rounded_pay_totals = {pt: money(pay_totals[pt]) for pt in pay_order}
    rounded_quarters = {q: money(quarter_totals[q]) for q in sorted(quarter_totals)}
    largest = max(pay_order, key=lambda pay_type: (pay_totals[pay_type], -pay_order.index(pay_type)))
    values = {
        "ensemble_id": request["ensemble_id"],
        "current_year": rb["current_year"],
        "roster_count": len(rows),
        "pay_types": pay_order,
        "quarter_totals": rounded_quarters,
        "annual_pay_type_totals": rounded_pay_totals,
        "annual_total": money(sum(rounded_quarters.values())),
        "largest_pay_type": largest,
        **counts,
    }
    return ordered_output(template.get("required_top_level_keys", []), values)


def solve_comp_forecast(base_url: str, request: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    ctx = compensation_context(base_url)
    rb = ctx["rate_book"]
    ensemble_id = request["ensemble_id"]
    scenario = ctx["scenarios"][request["scenario_id"]]
    rows = [row for row in ctx["rosters"] if row["ensemble_id"] == ensemble_id]
    current_pay, current_quarters, current_annual = compensation_totals(rb, ctx["rosters"], ensemble_id)
    y1_pay, y1_quarters, y1_annual = compensation_totals(rb, ctx["rosters"], ensemble_id, scenario, "year_plus_1")
    y2_pay, y2_quarters, y2_annual = compensation_totals(rb, ctx["rosters"], ensemble_id, scenario, "year_plus_2")
    pay_order = rb["pay_types"]
    current_annual = money(sum(money(v) for v in current_quarters.values()))
    y1_annual = money(sum(money(v) for v in y1_quarters.values()))
    y2_annual = money(sum(money(v) for v in y2_quarters.values()))
    largest_growth = max(
        pay_order,
        key=lambda pay_type: (
            safe_div(y2_pay[pay_type] - current_pay[pay_type], current_pay[pay_type]),
            -pay_order.index(pay_type),
        ),
    )
    values = {
        "ensemble_id": ensemble_id,
        "scenario_id": request["scenario_id"],
        "annual_totals": {
            "current": money(current_annual),
            "year_plus_1": money(y1_annual),
            "year_plus_2": money(y2_annual),
        },
        "growth_rates": {
            "year_plus_1_vs_current": ratio(safe_div(y1_annual - current_annual, current_annual)),
            "year_plus_2_vs_year_plus_1": ratio(safe_div(y2_annual - y1_annual, y1_annual)),
        },
        "year_plus_2_quarter_totals": {q: money(y2_quarters[q]) for q in sorted(y2_quarters)},
        "year_plus_2_pay_type_totals": {pt: money(y2_pay[pt]) for pt in pay_order},
        "largest_growth_pay_type": largest_growth,
        **roster_counts(rb, rows),
    }
    return ordered_output(template.get("required_top_level_keys", []), values)


def payroll_context(base_url: str) -> dict[str, Any]:
    return {
        "rate_book": fetch_json(base_url, "/api/payroll/rate-book"),
        "productions": fetch_json(base_url, "/api/payroll/productions"),
    }


def category_for_service(service_type: str) -> str:
    if "Sound Check" in service_type:
        return "sound_check"
    return service_type.lower()


def time_value(value: str) -> tuple[int, int]:
    hour, minute = value.split(":")
    return int(hour), int(minute)


def payroll_conflicts(rate_book: dict[str, Any], schedule: list[dict[str, Any]]) -> list[str]:
    flags = set()
    earliest = time_value(rate_book["conflict_thresholds"]["rehearsal_earliest_start"])
    latest = time_value(rate_book["conflict_thresholds"]["rehearsal_latest_end"])
    for service in schedule:
        service_type = service["service_type"]
        duration = float(service["duration_hours"])
        limit = rate_book["service_time_limits"].get(service_type)
        if service_type == "Rehearsal":
            if time_value(service["start_time"]) < earliest:
                flags.add("REHEARSAL_EARLY_START")
            if time_value(service["end_time"]) > latest:
                flags.add("REHEARSAL_LATE_END")
        if limit is not None and duration > float(limit):
            flags.add("SERVICE_OVER_TIME_LIMIT")
        if "Sound Check" in service_type and limit is not None and abs(duration - float(limit)) > 1e-9:
            flags.add("SOUND_CHECK_DURATION_MISMATCH")
    return sorted(flags)


def musician_pay(rate_book: dict[str, Any], musician: dict[str, Any], services: dict[str, dict[str, Any]]) -> dict[str, float]:
    rates = rate_book["service_rates"]
    categories: dict[str, float] = defaultdict(float)

    for service_id in musician["assigned_service_ids"]:
        service = services[service_id]
        service_type = service["service_type"]
        if service_type == "Rehearsal":
            amount = rates[service_type] * max(float(service["duration_hours"]), 3.0)
        else:
            amount = rates[service_type]
        categories[category_for_service(service_type)] += amount

    if musician.get("substitute", False):
        adjustment = 2 * rates["Performance"]
        categories["performance"] += adjustment
        categories["substitute_adjustment"] += adjustment

    base_service_pay = sum(categories.get(key, 0.0) for key in ["performance", "audit", "rehearsal", "sound_check"])

    premium_pct = 0.0
    premiums = rate_book["premium_pct"]
    if musician.get("principal", False) or musician.get("lead", False):
        premium_pct += premiums.get("principal_or_lead", 0.0)
    if musician.get("quartet", False):
        premium_pct += premiums.get("quartet", 0.0)
    if musician.get("electronic", False):
        premium_pct += premiums.get("electronic", 0.0)
    if musician.get("concertmaster", False):
        premium_pct += premiums.get("concertmaster", 0.0)
    if premium_pct:
        categories["premium"] += base_service_pay * premium_pct

    doubles = int(musician.get("doubles", 0) or 0)
    if doubles:
        double_pct = premiums["first_double"] + max(0, doubles - 1) * premiums["additional_double"]
        categories["doubles"] += base_service_pay * double_pct

    if musician.get("vacation_eligible", False):
        vacation_base = base_service_pay + categories.get("premium", 0.0) + categories.get("doubles", 0.0)
        categories["vacation"] += vacation_base * premiums["vacation"]

    if not musician.get("substitute", False) and base_service_pay < rate_book["weekly_guarantee"]:
        categories["guarantee_adjustment"] += rate_book["weekly_guarantee"] - base_service_pay

    return {key: amount for key, amount in categories.items() if abs(amount) > 1e-9}


def solve_payroll(base_url: str, request: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    ctx = payroll_context(base_url)
    rb = ctx["rate_book"]
    production_id = request["production_id"]
    production = next(p for p in ctx["productions"] if p["production_id"] == production_id)
    services = {service["service_id"]: service for service in production["schedule"]}
    service_counts = Counter(service["service_type"] for service in production["schedule"])
    category_totals: dict[str, float] = defaultdict(float)
    per_musician = []

    for musician in sorted(production["roster"], key=lambda row: row["musician_id"]):
        categories = musician_pay(rb, musician, services)
        total = sum(categories.values())
        for key, value in categories.items():
            category_totals[key] += value
        per_musician.append(
            {
                "musician_id": musician["musician_id"],
                "name": musician["name"],
                "total": money(total),
                "categories": {key: money(categories[key]) for key in sorted(categories)},
            }
        )

    top = min(per_musician, key=lambda row: (-row["total"], row["musician_id"]))
    values = {
        "production_id": production_id,
        "service_counts": {key: service_counts[key] for key in sorted(service_counts)},
        "category_totals": {key: money(category_totals[key]) for key in sorted(category_totals)},
        "weekly_total": money(sum(category_totals.values())),
        "conflict_flags": payroll_conflicts(rb, production["schedule"]),
        "per_musician": per_musician,
        "top_paid_musician_id": top["musician_id"],
    }
    return ordered_output(template.get("required_top_level_keys", []), values)


def solve(input_dir: Path, base_url: str) -> dict[str, Any]:
    payloads = input_dir / "payloads"
    request = read_json(payloads / "request_memo.json")
    template = read_json(payloads / "answer_template.json")
    required = template.get("required_top_level_keys", [])

    if "production_id" in request:
        return solve_payroll(base_url, request, template)
    if "scenario_id" in request:
        return solve_comp_forecast(base_url, request, template)
    if "ensemble_id" in request:
        return solve_comp_current(base_url, request, template)
    if "target_region_id" in request:
        return solve_region(base_url, request, template)
    if "target_branch_id" in request or any(key.endswith("_income_statement") for key in required):
        return solve_branch_close(base_url, request, template)
    raise SystemExit("Could not determine Crescent task type from request/template.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, help="Task input directory containing payloads/")
    parser.add_argument("--base-url", default=None, help="Finance Ops base URL")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    base_url = discover_base_url(input_dir, args.base_url)
    answer = solve(input_dir, base_url)
    print(json.dumps(answer, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
