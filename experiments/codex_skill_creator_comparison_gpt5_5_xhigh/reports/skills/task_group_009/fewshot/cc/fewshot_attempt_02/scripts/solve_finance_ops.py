#!/usr/bin/env python3
"""Solve Crescent Finance Ops JSON reporting tasks from staged payloads."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


EPSILON = 1e-9
CATEGORY_ORDER = [
    "performance",
    "audit",
    "rehearsal",
    "sound_check",
    "premium",
    "doubles",
    "vacation",
    "guarantee_adjustment",
    "substitute_adjustment",
]


def round_decimal(value: float, places: int) -> float:
    quant = Decimal("1").scaleb(-places)
    return float(Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP))


def money(value: float) -> float:
    return round_decimal(value, 2)


def pct(value: float) -> float:
    return round_decimal(value, 4)


def safe_div(numerator: float, denominator: float) -> float:
    if abs(denominator) <= EPSILON:
        return 0.0
    return numerator / denominator


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_input_dir(path: Path) -> Path:
    path = path.resolve()
    candidates = [path, path / "input"]
    if path.name != "input":
        candidates.append(path.parent / "input")
    for candidate in candidates:
        if (candidate / "payloads" / "request_memo.json").exists():
            return candidate
    raise SystemExit(f"Could not find input/payloads under {path}")


def parse_base_url_from_md(path: Path) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("base_url:"):
            value = line.split(":", 1)[1].strip()
            if value:
                return value
    return None


def resolve_base_url(input_dir: Path, env_payload: dict, override: str | None) -> str:
    if override:
        return override.rstrip("/")

    payload_url = str(env_payload.get("base_url", "")).strip()
    if payload_url and not payload_url.startswith("<"):
        return payload_url.rstrip("/")

    env_url = os.environ.get("TASK_ENV_BASE_URL", "").strip()
    if env_url:
        return env_url.rstrip("/")

    for start in [input_dir, Path.cwd()]:
        for candidate in [start, *start.parents]:
            parsed = parse_base_url_from_md(candidate / "environment_access.md")
            if parsed:
                return parsed.rstrip("/")

    raise SystemExit(
        "No usable base URL found. Pass --base-url or set TASK_ENV_BASE_URL."
    )


def fetch_json(base_url: str, endpoint: str):
    url = base_url.rstrip("/") + endpoint
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.load(response)


def period_num(period: str) -> int:
    return int(period.lstrip("M"))


def periods_for_year(period_map: list[dict], fiscal_year: int) -> list[str]:
    periods = [row["period"] for row in period_map if row["fiscal_year"] == fiscal_year]
    return sorted(periods, key=period_num)


def fiscal_year_for_period(period_map: list[dict], period: str) -> int:
    for row in period_map:
        if row["period"] == period:
            return int(row["fiscal_year"])
    raise KeyError(f"Unknown period {period}")


def period_convention(period_map: list[dict], current_period: str, prior_period: str) -> dict:
    result = {}
    for fiscal_year in sorted({int(row["fiscal_year"]) for row in period_map}):
        periods = periods_for_year(period_map, fiscal_year)
        if periods:
            result[f"{periods[0]}_to_{periods[-1]}"] = f"FY{fiscal_year}"
    result["current_month"] = current_period
    result["prior_month"] = prior_period
    return result


def finance_metrics(
    records: list[dict],
    account_categories: dict[str, str],
    branch_ids: list[str] | set[str],
    periods: list[str],
) -> dict[str, float]:
    branch_set = set(branch_ids)
    account_totals = defaultdict(float)
    category_totals = defaultdict(float)

    for record in records:
        if record["branch_id"] not in branch_set:
            continue
        amount = sum(float(record["values"].get(period, 0.0)) for period in periods)
        account = record["account"]
        account_totals[account] += amount
        category_totals[account_categories.get(account, "unknown")] += amount

    revenue = category_totals["revenue"]
    cogs = category_totals["cogs"]
    sga = category_totals["sga"]
    allocations = category_totals["allocations"]
    gross_margin = revenue - cogs
    ebitda = gross_margin - sga - allocations

    return {
        "revenue": revenue,
        "cogs": cogs,
        "gross_margin": gross_margin,
        "sga": sga,
        "allocations": allocations,
        "ebitda": ebitda,
        "ebitda_margin": safe_div(ebitda, revenue),
        "arpu": safe_div(revenue, account_totals["active_customers"]),
        "sales_per_labor_headcount": safe_div(revenue, account_totals["labor_headcount"]),
    }


def rounded_metric_object(metrics: dict[str, float], fields: list[str]) -> dict:
    result = {}
    for field in fields:
        if field in {"ebitda_margin", "revenue_growth_pct", "ebitda_growth_pct"}:
            result[field] = pct(metrics[field])
        elif field in metrics:
            result[field] = money(metrics[field])
    return result


def growth(current: float, prior: float) -> float:
    return safe_div(current - prior, prior)


def rank_desc(items: list[tuple[str, float]], target_id: str) -> int:
    ordered = sorted(items, key=lambda item: (-item[1], item[0]))
    for index, (item_id, _) in enumerate(ordered, start=1):
        if item_id == target_id:
            return index
    raise KeyError(target_id)


def solve_branch_close(base_url: str, request: dict, template: dict) -> dict:
    branches = fetch_json(base_url, "/api/finance/branches")
    period_map = fetch_json(base_url, "/api/finance/period-map")
    accounts = fetch_json(base_url, "/api/finance/accounts")
    records = fetch_json(base_url, "/api/finance/records")

    account_categories = {row["account"]: row["category"] for row in accounts}
    branch_by_id = {row["branch_id"]: row for row in branches}
    target_branch_id = request["target_branch_id"]
    target_branch = branch_by_id[target_branch_id]
    current_period = request["close_period"]
    prior_period = request["prior_period"]
    current_year = fiscal_year_for_period(period_map, current_period)
    prior_year = current_year - 1
    current_periods = periods_for_year(period_map, current_year)
    prior_periods = periods_for_year(period_map, prior_year)

    current_month = finance_metrics(records, account_categories, [target_branch_id], [current_period])
    prior_month = finance_metrics(records, account_categories, [target_branch_id], [prior_period])
    current_fy = finance_metrics(records, account_categories, [target_branch_id], current_periods)
    prior_fy = finance_metrics(records, account_categories, [target_branch_id], prior_periods)

    required = template.get("required_top_level_keys", [])
    statement_key = next(
        (key for key in required if key.endswith("_income_statement")),
        f"{current_period.lower()}_income_statement",
    )
    comparison_key = next(
        (key for key in required if key.startswith("fy") and "_vs_" in key),
        f"fy{current_year}_vs_fy{prior_year}",
    )
    comparison_template = template.get("field_types", {}).get(comparison_key, {})
    current_fy_key = next(
        (key for key in comparison_template if key.startswith("fy") and key[2:].isdigit()),
        f"fy{current_year}",
    )
    current_fy_fields = list(
        comparison_template.get(
            current_fy_key,
            {
                "revenue": None,
                "cogs": None,
                "gross_margin": None,
                "sga": None,
                "allocations": None,
                "ebitda": None,
                "ebitda_margin": None,
                "arpu": None,
                "sales_per_labor_headcount": None,
            },
        ).keys()
    )

    branch_growth = []
    branch_arpu = []
    branch_ebitda = []
    region_ebitda = []
    for branch in branches:
        branch_id = branch["branch_id"]
        branch_current = finance_metrics(records, account_categories, [branch_id], current_periods)
        branch_prior = finance_metrics(records, account_categories, [branch_id], prior_periods)
        branch_growth.append((branch_id, growth(branch_current["revenue"], branch_prior["revenue"])))
        branch_arpu.append((branch_id, branch_current["arpu"]))
        branch_ebitda.append((branch_id, branch_current["ebitda"]))

    for region in sorted({row["region_id"] for row in branches}):
        region_branch_ids = [row["branch_id"] for row in branches if row["region_id"] == region]
        region_current = finance_metrics(records, account_categories, region_branch_ids, current_periods)
        region_ebitda.append((region, region_current["ebitda"]))

    region_branch_ids = sorted(
        [row["branch_id"] for row in branches if row["region_id"] == target_branch["region_id"]]
    )
    region_fy = finance_metrics(records, account_categories, region_branch_ids, current_periods)

    return {
        "target_branch_id": target_branch_id,
        "target_branch_name": target_branch["branch_name"],
        "period_convention": period_convention(period_map, current_period, prior_period),
        statement_key: rounded_metric_object(
            current_month,
            ["revenue", "cogs", "gross_margin", "sga", "allocations", "ebitda"],
        ),
        "mom_revenue_variance": {
            "amount": money(current_month["revenue"] - prior_month["revenue"]),
            "pct": pct(growth(current_month["revenue"], prior_month["revenue"])),
        },
        comparison_key: {
            current_fy_key: rounded_metric_object(current_fy, current_fy_fields),
            "revenue_growth_pct": pct(growth(current_fy["revenue"], prior_fy["revenue"])),
            "ebitda_growth_pct": pct(growth(current_fy["ebitda"], prior_fy["ebitda"])),
        },
        "region_context": {
            "region_id": target_branch["region_id"],
            "branch_ids": region_branch_ids,
            f"fy{current_year}_ebitda": money(region_fy["ebitda"]),
            "ebitda_rank_desc": rank_desc(region_ebitda, target_branch["region_id"]),
        },
        "branch_rankings": {
            "sales_growth_rank_desc": rank_desc(branch_growth, target_branch_id),
            "top_sales_growth_branch_id": sorted(branch_growth, key=lambda item: (-item[1], item[0]))[0][0],
            "top_arpu_branch_id": sorted(branch_arpu, key=lambda item: (-item[1], item[0]))[0][0],
        },
    }


def solve_regional_view(base_url: str, request: dict, template: dict) -> dict:
    branches = fetch_json(base_url, "/api/finance/branches")
    period_map = fetch_json(base_url, "/api/finance/period-map")
    accounts = fetch_json(base_url, "/api/finance/accounts")
    records = fetch_json(base_url, "/api/finance/records")

    account_categories = {row["account"]: row["category"] for row in accounts}
    region_id = request["target_region_id"]
    branch_ids = sorted([row["branch_id"] for row in branches if row["region_id"] == region_id])
    years = sorted(int(year) for year in request.get("requested_comparison_years", []))
    if not years:
        years = sorted({int(row["fiscal_year"]) for row in period_map})
    earlier_year, later_year = years[0], years[-1]

    year_metrics = {
        year: finance_metrics(
            records,
            account_categories,
            branch_ids,
            periods_for_year(period_map, year),
        )
        for year in years
    }

    field_types = template.get("field_types", {})
    output = {"region_id": region_id, "branch_ids": branch_ids}
    for year in years:
        key = f"fy{year}"
        fields = list(
            field_types.get(
                key,
                {
                    "revenue": None,
                    "sga": None,
                    "allocations": None,
                    "ebitda": None,
                    "ebitda_margin": None,
                    "sales_per_labor_headcount": None,
                },
            ).keys()
        )
        output[key] = rounded_metric_object(year_metrics[year], fields)

    branch_ebitda = []
    for branch_id in branch_ids:
        metrics = finance_metrics(
            records,
            account_categories,
            [branch_id],
            periods_for_year(period_map, later_year),
        )
        branch_ebitda.append((branch_id, metrics["ebitda"]))

    aggregate_from_branches = sum(value for _, value in branch_ebitda)
    output.update(
        {
            "revenue_growth_pct": pct(
                growth(year_metrics[later_year]["revenue"], year_metrics[earlier_year]["revenue"])
            ),
            "top_ebitda_branch_id": sorted(branch_ebitda, key=lambda item: (-item[1], item[0]))[0][0],
            "bottom_ebitda_branch_id": sorted(branch_ebitda, key=lambda item: (item[1], item[0]))[0][0],
            "region_reconciliation_variance": money(
                year_metrics[later_year]["ebitda"] - aggregate_from_branches
            ),
        }
    )
    return output


def seniority_weekly(rate_book: dict, years: int) -> float:
    for band in rate_book["seniority_weekly"]:
        if years >= int(band["min_years"]) and (
            band["max_years"] is None or years <= int(band["max_years"])
        ):
            return float(band["weekly_amount"])
    return 0.0


def roster_rows(rosters: list[dict], ensemble_id: str) -> list[dict]:
    return sorted(
        [row for row in rosters if row["ensemble_id"] == ensemble_id],
        key=lambda row: row["employee_id"],
    )


def compensation_totals(
    rows: list[dict],
    rate_book: dict,
    minimum_weekly_scale: float,
    seniority_multiplier: float,
    overscale_multiplier: float,
    title_pct_multiplier: float,
    service_year_add: int,
) -> tuple[dict[str, float], dict[str, float], float]:
    pay_types = rate_book["pay_types"]
    pay_type_totals = {pay_type: 0.0 for pay_type in pay_types}
    quarter_totals = {quarter: 0.0 for quarter in rate_book["quarter_weeks"]}

    for row in rows:
        title_pct = float(rate_book["title_premium_pct"].get(row.get("title", ""), 0.0))
        if row.get("combined_overscale_includes_title"):
            title_pct = 0.0
        title_pct *= title_pct_multiplier
        seniority = seniority_weekly(rate_book, int(row["years_of_service"]) + service_year_add)

        for quarter in quarter_totals:
            weeks = float(row.get("weeks_by_quarter", {}).get(quarter, 0.0))
            amounts = {
                "Minimum Weekly Scale": minimum_weekly_scale * weeks,
                "Titled Position Premium": minimum_weekly_scale * title_pct * weeks,
                "Seniority": seniority * seniority_multiplier * weeks,
                "Overscale": float(row.get("overscale_weekly", 0.0)) * overscale_multiplier * weeks,
            }
            for pay_type in pay_types:
                amount = amounts.get(pay_type, 0.0)
                pay_type_totals[pay_type] += amount
                quarter_totals[quarter] += amount

    return pay_type_totals, quarter_totals, sum(pay_type_totals.values())


def rounded_money_map(values: dict[str, float]) -> dict[str, float]:
    return {key: money(value) for key, value in values.items()}


def rounded_sum(values: dict[str, float]) -> float:
    return money(sum(money(value) for value in values.values()))


def partial_quarter_count(rows: list[dict], rate_book: dict) -> int:
    expected = rate_book["quarter_weeks"]
    count = 0
    for row in rows:
        weeks = row.get("weeks_by_quarter", {})
        if any(float(weeks.get(q, 0.0)) != float(expected.get(q, 0.0)) for q in expected):
            count += 1
    return count


def solve_compensation_current(base_url: str, request: dict) -> dict:
    rate_book = fetch_json(base_url, "/api/compensation/rate-book")
    rosters = fetch_json(base_url, "/api/compensation/rosters")
    ensemble_id = request["ensemble_id"]
    rows = roster_rows(rosters, ensemble_id)
    pay_type_totals, quarter_totals, annual_total = compensation_totals(
        rows,
        rate_book,
        float(rate_book["minimum_weekly_scale"]),
        1.0,
        1.0,
        1.0,
        0,
    )
    pay_types = rate_book["pay_types"]

    return {
        "ensemble_id": ensemble_id,
        "current_year": int(rate_book["current_year"]),
        "roster_count": len(rows),
        "pay_types": pay_types,
        "quarter_totals": rounded_money_map(quarter_totals),
        "annual_pay_type_totals": rounded_money_map(pay_type_totals),
        "annual_total": rounded_sum(quarter_totals),
        "largest_pay_type": max(pay_types, key=lambda pay_type: (pay_type_totals[pay_type], -pay_types.index(pay_type))),
        "combined_overscale_employee_count": sum(
            1 for row in rows if row.get("combined_overscale_includes_title")
        ),
        "partial_quarter_employee_count": partial_quarter_count(rows, rate_book),
    }


def forecast_params(rate_book: dict, scenario: dict, year_key: str) -> tuple[float, float, float, float]:
    minimum_scale = float(rate_book["minimum_weekly_scale"])
    overscale_multiplier = 1.0
    seniority_multiplier = 1.0
    for key in ["year_plus_1", "year_plus_2"]:
        params = scenario[key]
        minimum_scale *= 1.0 + float(params["mws_growth"])
        overscale_multiplier *= 1.0 + float(params["overscale_growth"])
        seniority_multiplier *= 1.0 + float(params["seniority_growth"])
        if key == year_key:
            return (
                minimum_scale,
                seniority_multiplier,
                overscale_multiplier,
                float(params.get("title_pct_multiplier", 1.0)),
            )
    raise KeyError(year_key)


def solve_compensation_forecast(base_url: str, request: dict) -> dict:
    rate_book = fetch_json(base_url, "/api/compensation/rate-book")
    rosters = fetch_json(base_url, "/api/compensation/rosters")
    scenarios = fetch_json(base_url, "/api/compensation/scenarios")

    ensemble_id = request["ensemble_id"]
    scenario_id = request["scenario_id"]
    scenario = scenarios[scenario_id]
    rows = roster_rows(rosters, ensemble_id)

    current_pay_types, current_quarters, current_total = compensation_totals(
        rows,
        rate_book,
        float(rate_book["minimum_weekly_scale"]),
        1.0,
        1.0,
        1.0,
        0,
    )

    year_results = {"current": (current_pay_types, current_quarters, current_total)}
    for year_key, service_add in [("year_plus_1", 1), ("year_plus_2", 2)]:
        min_scale, seniority_mult, overscale_mult, title_mult = forecast_params(
            rate_book, scenario, year_key
        )
        pay_types, quarter_totals, annual_total = compensation_totals(
            rows,
            rate_book,
            min_scale,
            seniority_mult,
            overscale_mult,
            title_mult,
            service_add,
        )
        year_results[year_key] = (pay_types, quarter_totals, annual_total)

    pay_type_order = rate_book["pay_types"]
    y2_pay_types, y2_quarters, y2_total = year_results["year_plus_2"]

    def pay_type_growth_rate(pay_type: str) -> float:
        current = current_pay_types[pay_type]
        later = y2_pay_types[pay_type]
        if abs(current) <= EPSILON:
            return float("inf") if later > 0 else 0.0
        return (later - current) / current

    return {
        "ensemble_id": ensemble_id,
        "scenario_id": scenario_id,
        "annual_totals": {
            "current": rounded_sum(year_results["current"][1] or {}),
            "year_plus_1": rounded_sum(year_results["year_plus_1"][1] or {}),
            "year_plus_2": rounded_sum(y2_quarters or {}),
        },
        "growth_rates": {
            "year_plus_1_vs_current": pct(
                growth(
                    rounded_sum(year_results["year_plus_1"][1] or {}),
                    rounded_sum(year_results["current"][1] or {}),
                )
            ),
            "year_plus_2_vs_year_plus_1": pct(
                growth(
                    rounded_sum(y2_quarters or {}),
                    rounded_sum(year_results["year_plus_1"][1] or {}),
                )
            ),
        },
        "year_plus_2_quarter_totals": rounded_money_map(y2_quarters or {}),
        "year_plus_2_pay_type_totals": rounded_money_map(y2_pay_types),
        "largest_growth_pay_type": max(
            pay_type_order,
            key=lambda pay_type: (pay_type_growth_rate(pay_type), -pay_type_order.index(pay_type)),
        ),
        "combined_overscale_employee_count": sum(
            1 for row in rows if row.get("combined_overscale_includes_title")
        ),
        "partial_quarter_employee_count": partial_quarter_count(rows, rate_book),
    }


def minutes(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def payroll_base_categories(rate_book: dict, services: list[dict]) -> dict[str, float]:
    service_rates = rate_book["service_rates"]
    categories = defaultdict(float)
    for service in services:
        service_type = service["service_type"]
        if service_type == "Rehearsal":
            amount = float(service_rates[service_type]) * max(float(service["duration_hours"]), 3.0)
            categories["rehearsal"] += amount
        elif "Sound Check" in service_type:
            categories["sound_check"] += float(service_rates[service_type])
        elif service_type == "Performance":
            categories["performance"] += float(service_rates[service_type])
        elif service_type == "Audit":
            categories["audit"] += float(service_rates[service_type])
    return dict(categories)


def doubles_pct(rate_book: dict, doubles: int) -> float:
    if doubles <= 0:
        return 0.0
    premium_pct = rate_book["premium_pct"]
    return float(premium_pct["first_double"]) + (doubles - 1) * float(
        premium_pct["additional_double"]
    )


def musician_premium_pct(rate_book: dict, row: dict) -> float:
    premium_pct = rate_book["premium_pct"]
    total = 0.0
    if row.get("principal") or row.get("lead"):
        total += float(premium_pct["principal_or_lead"])
    if row.get("quartet"):
        total += float(premium_pct["quartet"])
    if row.get("electronic"):
        total += float(premium_pct["electronic"])
    if str(row.get("instrument", "")).lower() == "concertmaster":
        total += float(premium_pct.get("concertmaster", 0.0))
    return total


def sorted_nonzero_categories(categories: dict[str, float]) -> dict[str, float]:
    ordered_keys = [key for key in CATEGORY_ORDER if abs(categories.get(key, 0.0)) > EPSILON]
    ordered_keys.extend(
        sorted(key for key in categories if key not in CATEGORY_ORDER and abs(categories[key]) > EPSILON)
    )
    return {key: money(categories[key]) for key in ordered_keys}


def conflict_flags(rate_book: dict, schedule: list[dict]) -> list[str]:
    flags = set()
    earliest = minutes(rate_book["conflict_thresholds"]["rehearsal_earliest_start"])
    latest = minutes(rate_book["conflict_thresholds"]["rehearsal_latest_end"])
    limits = rate_book["service_time_limits"]
    for service in schedule:
        service_type = service["service_type"]
        duration = float(service["duration_hours"])
        if service_type == "Rehearsal":
            if minutes(service["start_time"]) < earliest:
                flags.add("REHEARSAL_EARLY_START")
            if minutes(service["end_time"]) > latest:
                flags.add("REHEARSAL_LATE_END")
        if service_type in limits and duration - float(limits[service_type]) > EPSILON:
            flags.add("SERVICE_OVER_TIME_LIMIT")
        if "Sound Check" in service_type and abs(duration - float(limits[service_type])) > EPSILON:
            flags.add("SOUND_CHECK_DURATION_MISMATCH")
    return sorted(flags)


def solve_payroll_review(base_url: str, request: dict) -> dict:
    rate_book = fetch_json(base_url, "/api/payroll/rate-book")
    productions = fetch_json(base_url, "/api/payroll/productions")
    production_id = request["production_id"]
    production = next(row for row in productions if row["production_id"] == production_id)
    schedule_by_id = {row["service_id"]: row for row in production["schedule"]}
    service_counts = dict(sorted(Counter(row["service_type"] for row in production["schedule"]).items()))

    per_musician = []
    category_totals = defaultdict(float)
    performance_rate = float(rate_book["service_rates"]["Performance"])

    for row in sorted(production["roster"], key=lambda item: item["musician_id"]):
        assigned_services = [schedule_by_id[service_id] for service_id in row["assigned_service_ids"]]
        categories = defaultdict(float)
        for key, value in payroll_base_categories(rate_book, assigned_services).items():
            categories[key] += value

        base_service_pay = sum(categories.values())
        substitute_adjustment = 2 * performance_rate if row.get("substitute") else 0.0
        if substitute_adjustment:
            categories["performance"] += substitute_adjustment
            categories["substitute_adjustment"] += substitute_adjustment

        premium_base = base_service_pay + substitute_adjustment
        premium = premium_base * musician_premium_pct(rate_book, row)
        if premium:
            categories["premium"] += premium

        doubles = premium_base * doubles_pct(rate_book, int(row.get("doubles", 0) or 0))
        if doubles:
            categories["doubles"] += doubles

        if row.get("vacation_eligible"):
            vacation = (premium_base + premium + doubles) * float(
                rate_book["premium_pct"]["vacation"]
            )
            if vacation:
                categories["vacation"] += vacation

        if not row.get("substitute") and base_service_pay + EPSILON < float(
            rate_book["weekly_guarantee"]
        ):
            categories["guarantee_adjustment"] += float(rate_book["weekly_guarantee"]) - base_service_pay

        total = sum(categories.values())
        for key, value in categories.items():
            category_totals[key] += value
        per_musician.append(
            {
                "musician_id": row["musician_id"],
                "name": row["name"],
                "total": money(total),
                "categories": sorted_nonzero_categories(categories),
                "_raw_total": total,
            }
        )

    top_paid = sorted(per_musician, key=lambda row: (-row["_raw_total"], row["musician_id"]))[0][
        "musician_id"
    ]
    for row in per_musician:
        row.pop("_raw_total", None)

    return {
        "production_id": production_id,
        "service_counts": service_counts,
        "category_totals": sorted_nonzero_categories(category_totals),
        "weekly_total": money(sum(category_totals.values())),
        "conflict_flags": conflict_flags(rate_book, production["schedule"]),
        "per_musician": per_musician,
        "top_paid_musician_id": top_paid,
    }


def solve(base_url: str, request: dict, template: dict) -> dict:
    if "target_branch_id" in request:
        return solve_branch_close(base_url, request, template)
    if "target_region_id" in request:
        return solve_regional_view(base_url, request, template)
    if "production_id" in request:
        return solve_payroll_review(base_url, request)
    if "ensemble_id" in request and "scenario_id" in request:
        return solve_compensation_forecast(base_url, request)
    if "ensemble_id" in request:
        return solve_compensation_current(base_url, request)
    raise SystemExit(f"Unsupported request_memo shape: {sorted(request)}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Task directory, input directory, or payloads parent")
    parser.add_argument("--base-url", help="Finance Ops API base URL")
    args = parser.parse_args(argv)

    input_dir = find_input_dir(Path(args.path))
    payloads = input_dir / "payloads"
    request = read_json(payloads / "request_memo.json")
    template = read_json(payloads / "answer_template.json")
    env_payload = read_json(payloads / "environment_access.json")
    base_url = resolve_base_url(input_dir, env_payload, args.base_url)
    result = solve(base_url, request, template)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
