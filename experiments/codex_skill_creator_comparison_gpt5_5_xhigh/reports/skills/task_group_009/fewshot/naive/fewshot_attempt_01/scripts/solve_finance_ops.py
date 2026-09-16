#!/usr/bin/env python3
"""Solve Crescent Finance Ops JSON tasks from payload files."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


MONEY_QUANT = Decimal("0.01")
RATIO_QUANT = Decimal("0.0001")


def D(value):
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def load_json_path(path: Path):
    return json.loads(path.read_text(), parse_float=Decimal)


def fetch_json(base_url: str, path: str):
    url = base_url.rstrip("/") + path
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"), parse_float=Decimal)


def money(value) -> float:
    return float(D(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def ratio4(value) -> float:
    return float(D(value).quantize(RATIO_QUANT, rounding=ROUND_HALF_UP))


def safe_ratio(numerator, denominator) -> Decimal:
    denominator = D(denominator)
    if denominator == 0:
        return Decimal("0")
    return D(numerator) / denominator


def json_ready(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_ready(v) for v in value]
    return value


def period_number(period: str) -> int:
    match = re.search(r"\d+", period)
    if not match:
        raise ValueError(f"Cannot parse period label: {period}")
    return int(match.group(0))


def finance_data(base_url: str):
    branches = fetch_json(base_url, "/api/finance/branches")
    period_map = fetch_json(base_url, "/api/finance/period-map")
    accounts = fetch_json(base_url, "/api/finance/accounts")
    records = fetch_json(base_url, "/api/finance/records")
    account_category = {row["account"]: row["category"] for row in accounts}
    periods_by_year = defaultdict(list)
    fiscal_year_by_period = {}
    for row in period_map:
        year = int(row["fiscal_year"])
        period = row["period"]
        periods_by_year[year].append(period)
        fiscal_year_by_period[period] = year
    for periods in periods_by_year.values():
        periods.sort(key=period_number)
    return {
        "branches": branches,
        "branch_by_id": {row["branch_id"]: row for row in branches},
        "period_map": period_map,
        "periods_by_year": dict(periods_by_year),
        "fiscal_year_by_period": fiscal_year_by_period,
        "account_category": account_category,
        "records": records,
    }


def finance_metrics(data, branch_ids, periods):
    branch_set = set(branch_ids)
    sums = {
        "revenue": Decimal("0"),
        "cogs": Decimal("0"),
        "sga": Decimal("0"),
        "allocations": Decimal("0"),
    }
    operating = defaultdict(Decimal)
    for record in data["records"]:
        if record["branch_id"] not in branch_set:
            continue
        account = record["account"]
        category = data["account_category"][account]
        value = sum(D(record["values"].get(period, 0)) for period in periods)
        if category in sums:
            sums[category] += value
        else:
            operating[account] += value
    revenue = sums["revenue"]
    cogs = sums["cogs"]
    gross_margin = revenue - cogs
    sga = sums["sga"]
    allocations = sums["allocations"]
    ebitda = gross_margin - sga - allocations
    return {
        "revenue": revenue,
        "cogs": cogs,
        "gross_margin": gross_margin,
        "sga": sga,
        "allocations": allocations,
        "ebitda": ebitda,
        "ebitda_margin": safe_ratio(ebitda, revenue),
        "arpu": safe_ratio(revenue, operating.get("active_customers", 0)),
        "sales_per_labor_headcount": safe_ratio(revenue, operating.get("labor_headcount", 0)),
        "operating": operating,
    }


def finance_field_object(metrics, field_names):
    result = {}
    for field in field_names:
        if field in {"revenue", "cogs", "gross_margin", "sga", "allocations", "ebitda", "arpu", "sales_per_labor_headcount"}:
            result[field] = money(metrics[field])
        elif field == "ebitda_margin":
            result[field] = ratio4(metrics[field])
    return result


def sorted_branch_ids_for_region(data, region_id):
    return sorted(row["branch_id"] for row in data["branches"] if row["region_id"] == region_id)


def prior_year_for(data, current_year):
    prior_years = [year for year in data["periods_by_year"] if year < current_year]
    if not prior_years:
        raise ValueError(f"No prior fiscal year for FY{current_year}")
    return max(prior_years)


def solve_branch_close(base_url, memo, template):
    data = finance_data(base_url)
    required = template.get("required_top_level_keys", [])
    field_types = template.get("field_types", {})
    branch_id = memo["target_branch_id"]
    close_period = memo["close_period"]
    prior_period = memo["prior_period"]
    current_year = data["fiscal_year_by_period"][close_period]
    prior_year = prior_year_for(data, current_year)
    current_periods = data["periods_by_year"][current_year]
    prior_periods = data["periods_by_year"][prior_year]

    branch = data["branch_by_id"][branch_id]
    current_month = finance_metrics(data, [branch_id], [close_period])
    previous_month = finance_metrics(data, [branch_id], [prior_period])
    current_year_metrics = finance_metrics(data, [branch_id], current_periods)
    prior_year_metrics = finance_metrics(data, [branch_id], prior_periods)

    region_id = branch["region_id"]
    region_branch_ids = sorted_branch_ids_for_region(data, region_id)
    region_metrics = finance_metrics(data, region_branch_ids, current_periods)
    region_rows = []
    for candidate_region in sorted({row["region_id"] for row in data["branches"]}):
        candidate_ids = sorted_branch_ids_for_region(data, candidate_region)
        candidate_metrics = finance_metrics(data, candidate_ids, current_periods)
        region_rows.append((candidate_region, candidate_metrics["ebitda"]))
    ranked_regions = sorted(region_rows, key=lambda item: (-item[1], item[0]))

    branch_rows = []
    for candidate in data["branches"]:
        candidate_id = candidate["branch_id"]
        candidate_current = finance_metrics(data, [candidate_id], current_periods)
        candidate_prior = finance_metrics(data, [candidate_id], prior_periods)
        branch_rows.append(
            {
                "branch_id": candidate_id,
                "sales_growth": safe_ratio(
                    candidate_current["revenue"] - candidate_prior["revenue"],
                    candidate_prior["revenue"],
                ),
                "arpu": candidate_current["arpu"],
            }
        )
    sales_rank = sorted(branch_rows, key=lambda row: (-row["sales_growth"], row["branch_id"]))
    arpu_rank = sorted(branch_rows, key=lambda row: (-row["arpu"], row["branch_id"]))

    income_key = next((key for key in required if key.endswith("_income_statement")), f"{close_period.lower()}_income_statement")
    comparison_key = next(
        (key for key in required if re.fullmatch(r"fy\d+_vs_fy\d+", key)),
        f"fy{current_year}_vs_fy{prior_year}",
    )
    current_year_key = f"fy{current_year}"
    comparison_fields = field_types.get(comparison_key, {})
    current_year_fields = comparison_fields.get(current_year_key, {})
    if not current_year_fields:
        current_year_fields = {
            "revenue": "currency",
            "cogs": "currency",
            "gross_margin": "currency",
            "sga": "currency",
            "allocations": "currency",
            "ebitda": "currency",
            "ebitda_margin": "decimal percent",
            "arpu": "currency",
            "sales_per_labor_headcount": "currency",
        }
    region_context_fields = field_types.get("region_context", {})
    region_ebitda_key = next(
        (key for key in region_context_fields if re.fullmatch(r"fy\d+_ebitda", key)),
        f"fy{current_year}_ebitda",
    )

    period_convention = {}
    for year in sorted(data["periods_by_year"]):
        periods = data["periods_by_year"][year]
        period_convention[f"{periods[0]}_to_{periods[-1]}"] = f"FY{year}"
    period_convention["current_month"] = close_period
    period_convention["prior_month"] = prior_period

    comparison = {
        current_year_key: finance_field_object(current_year_metrics, current_year_fields.keys()),
        "revenue_growth_pct": ratio4(
            safe_ratio(current_year_metrics["revenue"] - prior_year_metrics["revenue"], prior_year_metrics["revenue"])
        ),
        "ebitda_growth_pct": ratio4(
            safe_ratio(current_year_metrics["ebitda"] - prior_year_metrics["ebitda"], prior_year_metrics["ebitda"])
        ),
    }

    return {
        "target_branch_id": branch_id,
        "target_branch_name": branch["branch_name"],
        "period_convention": period_convention,
        income_key: finance_field_object(
            current_month,
            ["revenue", "cogs", "gross_margin", "sga", "allocations", "ebitda"],
        ),
        "mom_revenue_variance": {
            "amount": money(current_month["revenue"] - previous_month["revenue"]),
            "pct": ratio4(safe_ratio(current_month["revenue"] - previous_month["revenue"], previous_month["revenue"])),
        },
        comparison_key: comparison,
        "region_context": {
            "region_id": region_id,
            "branch_ids": region_branch_ids,
            region_ebitda_key: money(region_metrics["ebitda"]),
            "ebitda_rank_desc": next(index + 1 for index, row in enumerate(ranked_regions) if row[0] == region_id),
        },
        "branch_rankings": {
            "sales_growth_rank_desc": next(index + 1 for index, row in enumerate(sales_rank) if row["branch_id"] == branch_id),
            "top_sales_growth_branch_id": sales_rank[0]["branch_id"],
            "top_arpu_branch_id": arpu_rank[0]["branch_id"],
        },
    }


def solve_region(base_url, memo, template):
    data = finance_data(base_url)
    field_types = template.get("field_types", {})
    region_id = memo["target_region_id"]
    years = [int(year) for year in memo.get("requested_comparison_years", [])]
    if not years:
        years = sorted(data["periods_by_year"])
    years.sort()
    latest_year = years[-1]
    branch_ids = sorted_branch_ids_for_region(data, region_id)

    output = {"region_id": region_id, "branch_ids": branch_ids}
    metrics_by_year = {}
    for year in years:
        metrics = finance_metrics(data, branch_ids, data["periods_by_year"][year])
        metrics_by_year[year] = metrics
        key = f"fy{year}"
        fields = field_types.get(key, {}).keys()
        if not fields:
            fields = ["revenue", "sga", "allocations", "ebitda"]
            if year == latest_year:
                fields += ["ebitda_margin", "sales_per_labor_headcount"]
        output[key] = finance_field_object(metrics, fields)

    first_year = years[0]
    output["revenue_growth_pct"] = ratio4(
        safe_ratio(metrics_by_year[latest_year]["revenue"] - metrics_by_year[first_year]["revenue"], metrics_by_year[first_year]["revenue"])
    )
    branch_ebitda = []
    for branch_id in branch_ids:
        metrics = finance_metrics(data, [branch_id], data["periods_by_year"][latest_year])
        branch_ebitda.append((branch_id, metrics["ebitda"]))
    output["top_ebitda_branch_id"] = sorted(branch_ebitda, key=lambda row: (-row[1], row[0]))[0][0]
    output["bottom_ebitda_branch_id"] = sorted(branch_ebitda, key=lambda row: (row[1], row[0]))[0][0]
    branch_sum = sum((value for _, value in branch_ebitda), Decimal("0"))
    output["region_reconciliation_variance"] = money(metrics_by_year[latest_year]["ebitda"] - branch_sum)
    return output


def compensation_data(base_url: str, include_scenarios=False):
    data = {
        "rate_book": fetch_json(base_url, "/api/compensation/rate-book"),
        "rosters": fetch_json(base_url, "/api/compensation/rosters"),
    }
    if include_scenarios:
        data["scenarios"] = fetch_json(base_url, "/api/compensation/scenarios")
    return data


def seniority_weekly(rate_book, years_of_service: int) -> Decimal:
    for band in rate_book["seniority_weekly"]:
        min_years = int(band["min_years"])
        max_years = band["max_years"]
        if years_of_service >= min_years and (max_years is None or years_of_service <= int(max_years)):
            return D(band["weekly_amount"])
    raise ValueError(f"No seniority band for {years_of_service} years")


def compensation_factors(rate_book, scenarios, scenario_id, year_offset):
    minimum_weekly_scale = D(rate_book["minimum_weekly_scale"])
    overscale_factor = Decimal("1")
    seniority_factor = Decimal("1")
    title_multiplier = Decimal("1")
    if year_offset:
        scenario = scenarios[scenario_id]
        for offset in range(1, year_offset + 1):
            config = scenario[f"year_plus_{offset}"]
            minimum_weekly_scale *= Decimal("1") + D(config["mws_growth"])
            overscale_factor *= Decimal("1") + D(config["overscale_growth"])
            seniority_factor *= Decimal("1") + D(config["seniority_growth"])
        title_multiplier = D(scenario[f"year_plus_{year_offset}"]["title_pct_multiplier"])
    return minimum_weekly_scale, overscale_factor, seniority_factor, title_multiplier


def compensation_totals(data, ensemble_id, year_offset=0, scenario_id=None):
    rate_book = data["rate_book"]
    scenarios = data.get("scenarios", {})
    rows = [row for row in data["rosters"] if row["ensemble_id"] == ensemble_id]
    pay_types = list(rate_book["pay_types"])
    annual_by_type = {pay_type: Decimal("0") for pay_type in pay_types}
    quarter_totals = {quarter: Decimal("0") for quarter in rate_book["quarter_weeks"]}
    mws, overscale_factor, seniority_factor, title_multiplier = compensation_factors(
        rate_book, scenarios, scenario_id, year_offset
    )

    for row in rows:
        title = row.get("title")
        title_pct = D(rate_book["title_premium_pct"].get(title, 0)) if title else Decimal("0")
        title_weekly = Decimal("0")
        if not row.get("combined_overscale_includes_title"):
            title_weekly = mws * title_pct * title_multiplier
        weekly_by_type = {
            "Minimum Weekly Scale": mws,
            "Titled Position Premium": title_weekly,
            "Seniority": seniority_weekly(rate_book, int(row["years_of_service"]) + year_offset) * seniority_factor,
            "Overscale": D(row["overscale_weekly"]) * overscale_factor,
        }
        for quarter, weeks_value in row["weeks_by_quarter"].items():
            weeks = D(weeks_value)
            quarter_amount = Decimal("0")
            for pay_type in pay_types:
                amount = weekly_by_type[pay_type] * weeks
                annual_by_type[pay_type] += amount
                quarter_amount += amount
            quarter_totals[quarter] += quarter_amount

    return {
        "rows": rows,
        "pay_types": pay_types,
        "annual_by_type": annual_by_type,
        "quarter_totals": quarter_totals,
        "annual_total": sum(annual_by_type.values(), Decimal("0")),
    }


def roster_treatment_counts(rate_book, rows):
    combined = 0
    partial = 0
    for row in rows:
        if row.get("combined_overscale_includes_title"):
            combined += 1
        if any(int(row["weeks_by_quarter"].get(quarter, 0)) != int(weeks) for quarter, weeks in rate_book["quarter_weeks"].items()):
            partial += 1
    return combined, partial


def rounded_quarter_total(totals) -> Decimal:
    return sum(
        (amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP) for amount in totals["quarter_totals"].values()),
        Decimal("0"),
    )


def solve_compensation_current(base_url, memo, template):
    data = compensation_data(base_url)
    ensemble_id = memo["ensemble_id"]
    totals = compensation_totals(data, ensemble_id)
    rate_book = data["rate_book"]
    combined, partial = roster_treatment_counts(rate_book, totals["rows"])
    pay_types = totals["pay_types"]
    largest = max(pay_types, key=lambda pay_type: totals["annual_by_type"][pay_type])
    return {
        "ensemble_id": ensemble_id,
        "current_year": int(rate_book["current_year"]),
        "roster_count": len(totals["rows"]),
        "pay_types": pay_types,
        "quarter_totals": {quarter: money(totals["quarter_totals"][quarter]) for quarter in sorted(totals["quarter_totals"])},
        "annual_pay_type_totals": {pay_type: money(totals["annual_by_type"][pay_type]) for pay_type in pay_types},
        "annual_total": money(rounded_quarter_total(totals)),
        "largest_pay_type": largest,
        "combined_overscale_employee_count": combined,
        "partial_quarter_employee_count": partial,
    }


def solve_compensation_forecast(base_url, memo, template):
    data = compensation_data(base_url, include_scenarios=True)
    ensemble_id = memo["ensemble_id"]
    scenario_id = memo["scenario_id"]
    current = compensation_totals(data, ensemble_id, 0, scenario_id)
    year_plus_1 = compensation_totals(data, ensemble_id, 1, scenario_id)
    year_plus_2 = compensation_totals(data, ensemble_id, 2, scenario_id)
    pay_types = current["pay_types"]
    rate_book = data["rate_book"]
    combined, partial = roster_treatment_counts(rate_book, current["rows"])
    current_annual = rounded_quarter_total(current)
    year_plus_1_annual = rounded_quarter_total(year_plus_1)
    year_plus_2_annual = rounded_quarter_total(year_plus_2)

    def growth_metric(pay_type):
        base = current["annual_by_type"][pay_type]
        later = year_plus_2["annual_by_type"][pay_type]
        if base == 0:
            return Decimal("Infinity") if later > 0 else Decimal("0")
        return (later - base) / base

    largest_growth = max(pay_types, key=growth_metric)
    return {
        "ensemble_id": ensemble_id,
        "scenario_id": scenario_id,
        "annual_totals": {
            "current": money(current_annual),
            "year_plus_1": money(year_plus_1_annual),
            "year_plus_2": money(year_plus_2_annual),
        },
        "growth_rates": {
            "year_plus_1_vs_current": ratio4(
                safe_ratio(year_plus_1_annual - current_annual, current_annual)
            ),
            "year_plus_2_vs_year_plus_1": ratio4(
                safe_ratio(year_plus_2_annual - year_plus_1_annual, year_plus_1_annual)
            ),
        },
        "year_plus_2_quarter_totals": {
            quarter: money(year_plus_2["quarter_totals"][quarter]) for quarter in sorted(year_plus_2["quarter_totals"])
        },
        "year_plus_2_pay_type_totals": {pay_type: money(year_plus_2["annual_by_type"][pay_type]) for pay_type in pay_types},
        "largest_growth_pay_type": largest_growth,
        "combined_overscale_employee_count": combined,
        "partial_quarter_employee_count": partial,
    }


def payroll_data(base_url):
    return {
        "rate_book": fetch_json(base_url, "/api/payroll/rate-book"),
        "productions": fetch_json(base_url, "/api/payroll/productions"),
    }


def service_category(service_type: str) -> str:
    if service_type == "Performance":
        return "performance"
    if service_type == "Audit":
        return "audit"
    if service_type == "Rehearsal":
        return "rehearsal"
    if "Sound Check" in service_type:
        return "sound_check"
    return service_type.lower().replace(" ", "_")


def service_base_pay(rate_book, service):
    service_type = service["service_type"]
    if service_type == "Rehearsal":
        hours = max(D(service["duration_hours"]), Decimal("3"))
        return D(rate_book["service_rates"][service_type]) * hours
    return D(rate_book["service_rates"][service_type])


def minutes_since_midnight(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def payroll_conflict_flags(rate_book, schedule):
    flags = set()
    earliest_rehearsal = minutes_since_midnight(rate_book["conflict_thresholds"]["rehearsal_earliest_start"])
    latest_rehearsal = minutes_since_midnight(rate_book["conflict_thresholds"]["rehearsal_latest_end"])
    for service in schedule:
        service_type = service["service_type"]
        duration = D(service["duration_hours"])
        limit = D(rate_book["service_time_limits"].get(service_type, 0))
        if limit and duration > limit:
            flags.add("SERVICE_OVER_TIME_LIMIT")
        if service_type == "Rehearsal":
            if minutes_since_midnight(service["start_time"]) < earliest_rehearsal:
                flags.add("REHEARSAL_EARLY_START")
            if minutes_since_midnight(service["end_time"]) > latest_rehearsal:
                flags.add("REHEARSAL_LATE_END")
        if "Sound Check" in service_type and limit and duration != limit:
            flags.add("SOUND_CHECK_DURATION_MISMATCH")
    return sorted(flags)


def musician_pay(rate_book, services_by_id, musician):
    components = defaultdict(Decimal)
    base_service_pay = Decimal("0")
    for service_id in musician["assigned_service_ids"]:
        service = services_by_id[service_id]
        amount = service_base_pay(rate_book, service)
        components[service_category(service["service_type"])] += amount
        base_service_pay += amount

    substitute_adjustment = Decimal("0")
    premium_base = base_service_pay
    if musician.get("substitute"):
        substitute_adjustment = D(rate_book["service_rates"]["Performance"]) * Decimal("2")
        components["performance"] += substitute_adjustment
        components["substitute_adjustment"] += substitute_adjustment
        premium_base += substitute_adjustment

    premium_pct = Decimal("0")
    premium_rates = rate_book["premium_pct"]
    if musician.get("principal") or musician.get("lead"):
        premium_pct += D(premium_rates.get("principal_or_lead", 0))
    if musician.get("quartet"):
        premium_pct += D(premium_rates.get("quartet", 0))
    if musician.get("electronic"):
        premium_pct += D(premium_rates.get("electronic", 0))
    if musician.get("concertmaster"):
        premium_pct += D(premium_rates.get("concertmaster", 0))
    role_premium = premium_base * premium_pct
    if role_premium:
        components["premium"] += role_premium

    doubles_premium = Decimal("0")
    doubles = int(musician.get("doubles", 0))
    if doubles > 0:
        doubles_pct = D(premium_rates.get("first_double", 0))
        if doubles > 1:
            doubles_pct += D(premium_rates.get("additional_double", 0)) * Decimal(doubles - 1)
        doubles_premium = premium_base * doubles_pct
        components["doubles"] += doubles_premium

    if musician.get("vacation_eligible"):
        vacation = (base_service_pay + role_premium + doubles_premium) * D(premium_rates.get("vacation", 0))
        components["vacation"] += vacation

    if not musician.get("substitute"):
        guarantee = D(rate_book["weekly_guarantee"]) - base_service_pay
        if guarantee > 0:
            components["guarantee_adjustment"] += guarantee

    total = sum(components.values(), Decimal("0"))
    return components, total


def solve_payroll(base_url, memo, template):
    data = payroll_data(base_url)
    rate_book = data["rate_book"]
    production_id = memo["production_id"]
    production = next(row for row in data["productions"] if row["production_id"] == production_id)
    services_by_id = {service["service_id"]: service for service in production["schedule"]}
    service_counts = defaultdict(int)
    for service in production["schedule"]:
        service_counts[service["service_type"]] += 1

    category_totals = defaultdict(Decimal)
    musician_rows = []
    for musician in sorted(production["roster"], key=lambda row: row["musician_id"]):
        components, total = musician_pay(rate_book, services_by_id, musician)
        for category, amount in components.items():
            category_totals[category] += amount
        musician_rows.append(
            {
                "musician_id": musician["musician_id"],
                "name": musician["name"],
                "total_raw": total,
                "categories_raw": components,
            }
        )

    template_categories = template.get("field_types", {}).get("category_totals", {})
    category_keys = set(category for category, amount in category_totals.items() if amount != 0)
    for category in template_categories:
        if category != "substitute_adjustment" or category_totals.get(category, 0) != 0:
            category_keys.add(category)

    per_musician = []
    for row in musician_rows:
        categories = {
            category: money(row["categories_raw"][category])
            for category in sorted(row["categories_raw"])
            if row["categories_raw"][category] != 0
        }
        per_musician.append(
            {
                "musician_id": row["musician_id"],
                "name": row["name"],
                "total": money(row["total_raw"]),
                "categories": categories,
            }
        )

    top_paid = sorted(musician_rows, key=lambda row: (-row["total_raw"], row["musician_id"]))[0]["musician_id"]
    weekly_total = sum((row["total_raw"] for row in musician_rows), Decimal("0"))
    return {
        "production_id": production_id,
        "service_counts": {service_type: service_counts[service_type] for service_type in sorted(service_counts)},
        "category_totals": {category: money(category_totals.get(category, 0)) for category in sorted(category_keys)},
        "weekly_total": money(weekly_total),
        "conflict_flags": payroll_conflict_flags(rate_book, production["schedule"]),
        "per_musician": per_musician,
        "top_paid_musician_id": top_paid,
    }


def resolve_base_url(environment_payload):
    base_url = environment_payload.get("base_url") or ""
    if base_url == "<TASK_ENV_BASE_URL>" or not base_url:
        base_url = os.environ.get("TASK_ENV_BASE_URL") or os.environ.get("FINANCE_OPS_BASE_URL") or "http://task-env:9009/"
    return base_url.rstrip("/")


def solve(input_dir: Path):
    payload_dir = input_dir / "payloads" if (input_dir / "payloads").is_dir() else input_dir
    memo = load_json_path(payload_dir / "request_memo.json")
    template = load_json_path(payload_dir / "answer_template.json")
    environment_payload = load_json_path(payload_dir / "environment_access.json")
    base_url = resolve_base_url(environment_payload)

    if "target_branch_id" in memo:
        return solve_branch_close(base_url, memo, template)
    if "target_region_id" in memo:
        return solve_region(base_url, memo, template)
    if "production_id" in memo:
        return solve_payroll(base_url, memo, template)
    if "scenario_id" in memo:
        return solve_compensation_forecast(base_url, memo, template)
    if "ensemble_id" in memo:
        return solve_compensation_current(base_url, memo, template)
    raise ValueError("Unsupported Crescent Finance Ops request memo")


def main(argv):
    input_dir = Path(argv[1]).resolve() if len(argv) > 1 else Path.cwd()
    answer = solve(input_dir)
    print(json.dumps(json_ready(answer), indent=2, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv)
