#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import OrderedDict, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import urlopen


ZERO = Decimal("0")
CURRENCY_Q = Decimal("0.01")
PERCENT_Q = Decimal("0.0001")


def d(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def money(value) -> float:
    return float(d(value).quantize(CURRENCY_Q, rounding=ROUND_HALF_UP))


def pct(value) -> float:
    return float(d(value).quantize(PERCENT_Q, rounding=ROUND_HALF_UP))


def sumd(values) -> Decimal:
    total = ZERO
    for value in values:
        total += d(value)
    return total


def load_json(path: Path):
    return json.loads(path.read_text())


def fetch_json(base_url: str, endpoint: str):
    with urlopen(urljoin(base_url.rstrip("/") + "/", endpoint.lstrip("/"))) as response:
        return json.load(response)


def find_input_root(start: Path) -> Path:
    path = start.resolve()
    if (path / "payloads").is_dir():
        return path
    if (path / "input" / "payloads").is_dir():
        return path / "input"
    raise FileNotFoundError(f"Could not find payloads/ under {start}")


def find_payload_file(input_root: Path, name: str) -> Path:
    path = input_root / "payloads" / name
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def resolve_base_url(input_root: Path) -> str:
    payload = load_json(find_payload_file(input_root, "environment_access.json"))
    base_url = str(payload.get("base_url", "")).strip()
    if base_url and "<" not in base_url:
        return base_url.rstrip("/")

    for env_name in ("TASK_ENV_BASE_URL", "CRESCENT_FINANCE_OPS_BASE_URL", "BASE_URL"):
        candidate = os.environ.get(env_name, "").strip()
        if candidate:
            return candidate.rstrip("/")

    for candidate_dir in [input_root, *input_root.parents]:
        md_path = candidate_dir / "environment_access.md"
        if md_path.exists():
            match = re.search(r"^base_url:\s*(\S+)\s*$", md_path.read_text(), re.MULTILINE)
            if match:
                return match.group(1).rstrip("/")

    return "http://task-env:9009"


def periods_by_year(period_map):
    year_periods = defaultdict(list)
    order = {}
    for row in period_map:
        year_periods[row["fiscal_year"]].append(row["period"])
        order[row["period"]] = row["month_number"]
    for year in year_periods:
        year_periods[year].sort(key=lambda period: order[period])
    return dict(sorted(year_periods.items()))


def build_finance_context(base_url: str):
    accounts = fetch_json(base_url, "/api/finance/accounts")
    records = fetch_json(base_url, "/api/finance/records")
    branches = fetch_json(base_url, "/api/finance/branches")
    period_map = fetch_json(base_url, "/api/finance/period-map")

    account_category = {row["account"]: row["category"] for row in accounts}
    category_accounts = defaultdict(list)
    for row in accounts:
        category_accounts[row["category"]].append(row["account"])
    record_index = {(row["branch_id"], row["account"]): row for row in records}
    branch_index = {row["branch_id"]: row for row in branches}
    region_branches = defaultdict(list)
    for row in branches:
        region_branches[row["region_id"]].append(row["branch_id"])
    for branch_ids in region_branches.values():
        branch_ids.sort()

    year_periods = periods_by_year(period_map)
    period_to_year = {row["period"]: row["fiscal_year"] for row in period_map}

    @lru_cache(maxsize=None)
    def account_total(branch_id: str, account: str, year: int) -> Decimal:
        record = record_index[(branch_id, account)]
        return sumd(record["values"][period] for period in year_periods[year])

    @lru_cache(maxsize=None)
    def branch_year_summary(branch_id: str, year: int):
        revenue = sum(account_total(branch_id, account, year) for account in category_accounts["revenue"])
        cogs = sum(account_total(branch_id, account, year) for account in category_accounts["cogs"])
        sga = sum(account_total(branch_id, account, year) for account in category_accounts["sga"])
        allocations = sum(account_total(branch_id, account, year) for account in category_accounts["allocations"])
        active_customers = account_total(branch_id, "active_customers", year)
        labor_headcount = account_total(branch_id, "labor_headcount", year)
        return {
            "revenue": revenue,
            "cogs": cogs,
            "gross_margin": revenue - cogs,
            "sga": sga,
            "allocations": allocations,
            "ebitda": revenue - cogs - sga - allocations,
            "active_customers": active_customers,
            "labor_headcount": labor_headcount,
        }

    def branch_period_summary(branch_id: str, period: str):
        revenue = sum(
            d(record_index[(branch_id, account)]["values"][period]) for account in category_accounts["revenue"]
        )
        cogs = sum(d(record_index[(branch_id, account)]["values"][period]) for account in category_accounts["cogs"])
        sga = sum(d(record_index[(branch_id, account)]["values"][period]) for account in category_accounts["sga"])
        allocations = sum(
            d(record_index[(branch_id, account)]["values"][period]) for account in category_accounts["allocations"]
        )
        return {
            "revenue": revenue,
            "cogs": cogs,
            "gross_margin": revenue - cogs,
            "sga": sga,
            "allocations": allocations,
            "ebitda": revenue - cogs - sga - allocations,
        }

    @lru_cache(maxsize=None)
    def region_year_summary(region_id: str, year: int):
        totals = defaultdict(Decimal)
        for branch_id in region_branches[region_id]:
            summary = branch_year_summary(branch_id, year)
            for key, value in summary.items():
                totals[key] += value
        return totals

    def branch_region(branch_id: str):
        row = branch_index[branch_id]
        return row["region_id"], row["region_name"]

    return {
        "accounts": accounts,
        "account_category": account_category,
        "branch_index": branch_index,
        "branch_region": branch_region,
        "branch_period_summary": branch_period_summary,
        "branch_year_summary": branch_year_summary,
        "region_branches": region_branches,
        "region_year_summary": region_year_summary,
        "year_periods": year_periods,
        "period_to_year": period_to_year,
    }


def solve_branch_close(memo, template, finance):
    branch_id = memo["target_branch_id"]
    close_period = memo["close_period"]
    prior_period = memo["prior_period"]
    close_year = finance["period_to_year"][close_period]
    prior_year = close_year - 1

    month_current = finance["branch_period_summary"](branch_id, close_period)
    month_prior = finance["branch_period_summary"](branch_id, prior_period)
    current = finance["branch_year_summary"](branch_id, close_year)
    prior = finance["branch_year_summary"](branch_id, prior_year)
    branch_row = finance["branch_index"][branch_id]
    region_id, _ = finance["branch_region"](branch_id)
    region_branch_ids = finance["region_branches"][region_id]

    year_key = f"fy{close_year}"
    compare_key = f"fy{close_year}_vs_fy{prior_year}"
    income_key = next(key for key in template["required_top_level_keys"] if key.endswith("_income_statement"))

    period_convention = OrderedDict(
        [
            ("M1_to_M12", f"FY{sorted(finance['year_periods'])[0]}"),
            ("M13_to_M24", f"FY{sorted(finance['year_periods'])[1]}"),
            ("current_month", close_period),
            ("prior_month", prior_period),
        ]
    )

    current_statement = OrderedDict(
        [
            ("revenue", money(current["revenue"])),
            ("cogs", money(current["cogs"])),
            ("gross_margin", money(current["gross_margin"])),
            ("sga", money(current["sga"])),
            ("allocations", money(current["allocations"])),
            ("ebitda", money(current["ebitda"])),
        ]
    )

    mom_amount = current["revenue"] - prior["revenue"]
    mom_pct = mom_amount / prior["revenue"] if prior["revenue"] else ZERO

    compare_block = OrderedDict(
        [
            (
                year_key,
                OrderedDict(
                    [
                        ("revenue", money(current["revenue"])),
                        ("cogs", money(current["cogs"])),
                        ("gross_margin", money(current["gross_margin"])),
                        ("sga", money(current["sga"])),
                        ("allocations", money(current["allocations"])),
                        ("ebitda", money(current["ebitda"])),
                        ("ebitda_margin", pct(current["ebitda"] / current["revenue"] if current["revenue"] else ZERO)),
                        ("arpu", money(current["revenue"] / current["active_customers"] if current["active_customers"] else ZERO)),
                        (
                            "sales_per_labor_headcount",
                            money(current["revenue"] / current["labor_headcount"] if current["labor_headcount"] else ZERO),
                        ),
                    ]
                ),
            ),
            ("revenue_growth_pct", pct((current["revenue"] - prior["revenue"]) / prior["revenue"] if prior["revenue"] else ZERO)),
            ("ebitda_growth_pct", pct((current["ebitda"] - prior["ebitda"]) / prior["ebitda"] if prior["ebitda"] else ZERO)),
        ]
    )

    region_totals = finance["region_year_summary"](region_id, close_year)
    region_rankings = []
    for candidate_region in finance["region_branches"]:
        total = finance["region_year_summary"](candidate_region, close_year)["ebitda"]
        region_rankings.append((candidate_region, total))
    region_rankings.sort(key=lambda item: (-item[1], item[0]))
    region_rank = {region: idx + 1 for idx, (region, _) in enumerate(region_rankings)}

    branch_growths = []
    branch_arpus = []
    for candidate_branch in finance["branch_index"]:
        current_summary = finance["branch_year_summary"](candidate_branch, close_year)
        prior_summary = finance["branch_year_summary"](candidate_branch, prior_year)
        growth = (
            (current_summary["revenue"] - prior_summary["revenue"]) / prior_summary["revenue"]
            if prior_summary["revenue"]
            else ZERO
        )
        arpu = (
            current_summary["revenue"] / current_summary["active_customers"]
            if current_summary["active_customers"]
            else ZERO
        )
        branch_growths.append((candidate_branch, growth))
        branch_arpus.append((candidate_branch, arpu))
    branch_growths.sort(key=lambda item: (-item[1], item[0]))
    branch_arpus.sort(key=lambda item: (-item[1], item[0]))
    growth_rank = {branch: idx + 1 for idx, (branch, _) in enumerate(branch_growths)}

    out = OrderedDict(
        [
            ("target_branch_id", branch_id),
            ("target_branch_name", branch_row["branch_name"]),
            ("period_convention", period_convention),
            (
                income_key,
                OrderedDict(
                    [
                        ("revenue", money(month_current["revenue"])),
                        ("cogs", money(month_current["cogs"])),
                        ("gross_margin", money(month_current["gross_margin"])),
                        ("sga", money(month_current["sga"])),
                        ("allocations", money(month_current["allocations"])),
                        ("ebitda", money(month_current["ebitda"])),
                    ]
                ),
            ),
            ("mom_revenue_variance", OrderedDict([("amount", money(month_current["revenue"] - month_prior["revenue"])), ("pct", pct((month_current["revenue"] - month_prior["revenue"]) / month_prior["revenue"] if month_prior["revenue"] else ZERO))])),
            (compare_key, compare_block),
            (
                "region_context",
                OrderedDict(
                    [
                        ("region_id", region_id),
                        ("branch_ids", list(region_branch_ids)),
                        (f"fy{close_year}_ebitda", money(region_totals["ebitda"])),
                        ("ebitda_rank_desc", region_rank[region_id]),
                    ]
                ),
            ),
            (
                "branch_rankings",
                OrderedDict(
                    [
                        ("sales_growth_rank_desc", growth_rank[branch_id]),
                        ("top_sales_growth_branch_id", branch_growths[0][0]),
                        ("top_arpu_branch_id", branch_arpus[0][0]),
                    ]
                ),
            ),
        ]
    )
    return out


def solve_regional_view(memo, finance):
    region_id = memo["target_region_id"]
    years = sorted(memo["requested_comparison_years"])
    prior_year, current_year = years[0], years[-1]
    branch_ids = finance["region_branches"][region_id]

    def year_block(year: int, include_ratios: bool):
        totals = finance["region_year_summary"](region_id, year)
        block = OrderedDict(
            [
                ("revenue", money(totals["revenue"])),
                ("sga", money(totals["sga"])),
                ("allocations", money(totals["allocations"])),
                ("ebitda", money(totals["ebitda"])),
            ]
        )
        if include_ratios:
            block["ebitda_margin"] = pct(totals["ebitda"] / totals["revenue"] if totals["revenue"] else ZERO)
            block["sales_per_labor_headcount"] = money(
                totals["revenue"] / totals["labor_headcount"] if totals["labor_headcount"] else ZERO
            )
        return block

    current_totals = finance["region_year_summary"](region_id, current_year)
    prior_totals = finance["region_year_summary"](region_id, prior_year)

    region_rankings = []
    for candidate_region in finance["region_branches"]:
        total = finance["region_year_summary"](candidate_region, current_year)["ebitda"]
        region_rankings.append((candidate_region, total))
    region_rankings.sort(key=lambda item: (-item[1], item[0]))

    branch_rankings = []
    for branch_id in branch_ids:
        summary = finance["branch_year_summary"](branch_id, current_year)
        branch_rankings.append((branch_id, summary["ebitda"]))
    branch_rankings.sort(key=lambda item: (-item[1], item[0]))

    out = OrderedDict(
        [
            ("region_id", region_id),
            ("branch_ids", list(branch_ids)),
            (f"fy{prior_year}", year_block(prior_year, include_ratios=False)),
            (f"fy{current_year}", year_block(current_year, include_ratios=True)),
            ("revenue_growth_pct", pct((current_totals["revenue"] - prior_totals["revenue"]) / prior_totals["revenue"] if prior_totals["revenue"] else ZERO)),
            ("top_ebitda_branch_id", branch_rankings[0][0]),
            ("bottom_ebitda_branch_id", branch_rankings[-1][0]),
            (
                "region_reconciliation_variance",
                money(
                    current_totals["ebitda"]
                    - sumd(finance["branch_year_summary"](branch_id, current_year)["ebitda"] for branch_id in branch_ids)
                ),
            ),
        ]
    )
    return out


def build_compensation_context(base_url: str):
    rate_book = fetch_json(base_url, "/api/compensation/rate-book")
    rosters = fetch_json(base_url, "/api/compensation/rosters")
    scenarios = fetch_json(base_url, "/api/compensation/scenarios")
    roster_by_ensemble = defaultdict(list)
    for row in rosters:
        roster_by_ensemble[row["ensemble_id"]].append(row)
    for rows in roster_by_ensemble.values():
        rows.sort(key=lambda row: row["employee_id"])
    return {
        "rate_book": rate_book,
        "rosters": rosters,
        "scenarios": scenarios,
        "roster_by_ensemble": roster_by_ensemble,
    }


def seniority_weekly(rate_book, years_of_service: int) -> Decimal:
    for band in rate_book["seniority_weekly"]:
        min_years = band["min_years"]
        max_years = band["max_years"]
        if years_of_service >= min_years and (max_years is None or years_of_service <= max_years):
            return d(band["weekly_amount"])
    raise ValueError(f"No seniority band for {years_of_service} years")


def compensation_year_totals(rate_book, rows, scenario, year_offset: int):
    quarter_order = list(rate_book["quarter_weeks"].keys())
    quarter_totals = OrderedDict((quarter, ZERO) for quarter in quarter_order)
    annual_pay_type_totals = OrderedDict((pay_type, ZERO) for pay_type in rate_book["pay_types"])
    total_weeks_by_row = {row["employee_id"]: sumd(row["weeks_by_quarter"][q] for q in quarter_order) for row in rows}
    total_weeks_all = sum(rate_book["quarter_weeks"].values())
    combined_overscale_count = sum(1 for row in rows if row.get("combined_overscale_includes_title"))
    partial_quarter_count = sum(
        1
        for row in rows
        if any(
            d(row["weeks_by_quarter"][quarter]) != d(rate_book["quarter_weeks"][quarter])
            for quarter in quarter_order
        )
    )

    mws_mult = Decimal("1")
    overscale_mult = Decimal("1")
    seniority_mult = Decimal("1")
    title_mult = Decimal("1")
    if year_offset:
        steps = [scenario["year_plus_1"]]
        if year_offset == 2:
            steps.append(scenario["year_plus_2"])
        for step in steps:
            mws_mult *= Decimal("1") + d(step["mws_growth"])
            overscale_mult *= Decimal("1") + d(step["overscale_growth"])
            seniority_mult *= Decimal("1") + d(step["seniority_growth"])
            title_mult *= d(step["title_pct_multiplier"])

    minimum_weekly_scale = d(rate_book["minimum_weekly_scale"]) * mws_mult
    title_pct = rate_book["title_premium_pct"]
    pay_types = rate_book["pay_types"]

    for row in rows:
        weeks_total = total_weeks_by_row[row["employee_id"]]
        title_weekly = ZERO
        if row.get("title") and not row.get("combined_overscale_includes_title"):
            title_weekly = minimum_weekly_scale * d(title_pct.get(row["title"], 0)) * title_mult
        seniority_weekly_amt = seniority_weekly(rate_book, int(row["years_of_service"]) + year_offset) * seniority_mult
        overscale_weekly_amt = d(row.get("overscale_weekly", 0)) * overscale_mult
        base_weekly = minimum_weekly_scale + title_weekly + seniority_weekly_amt + overscale_weekly_amt

        for quarter in quarter_order:
            quarter_totals[quarter] += base_weekly * d(row["weeks_by_quarter"][quarter])

        annual_pay_type_totals["Minimum Weekly Scale"] += minimum_weekly_scale * weeks_total
        annual_pay_type_totals["Titled Position Premium"] += title_weekly * weeks_total
        annual_pay_type_totals["Seniority"] += seniority_weekly_amt * weeks_total
        annual_pay_type_totals["Overscale"] += overscale_weekly_amt * weeks_total

    rounded_quarter_totals = OrderedDict((quarter, money(value)) for quarter, value in quarter_totals.items())
    annual_total = sumd(rounded_quarter_totals.values())
    return {
        "quarter_totals": rounded_quarter_totals,
        "annual_pay_type_totals": OrderedDict((pay_type, money(annual_pay_type_totals[pay_type])) for pay_type in pay_types),
        "annual_total": money(annual_total),
        "combined_overscale_employee_count": combined_overscale_count,
        "partial_quarter_employee_count": partial_quarter_count,
    }


def solve_compensation_current(memo, comp):
    rate_book = comp["rate_book"]
    ensemble_id = memo["ensemble_id"]
    rows = comp["roster_by_ensemble"][ensemble_id]
    result = compensation_year_totals(rate_book, rows, scenario=None, year_offset=0)
    pay_types = rate_book["pay_types"]
    largest_pay_type = max(pay_types, key=lambda pay_type: (d(result["annual_pay_type_totals"][pay_type]), -pay_types.index(pay_type)))
    return OrderedDict(
        [
            ("ensemble_id", ensemble_id),
            ("current_year", rate_book["current_year"]),
            ("roster_count", len(rows)),
            ("pay_types", pay_types),
            ("quarter_totals", result["quarter_totals"]),
            ("annual_pay_type_totals", result["annual_pay_type_totals"]),
            ("annual_total", result["annual_total"]),
            ("largest_pay_type", largest_pay_type),
            ("combined_overscale_employee_count", result["combined_overscale_employee_count"]),
            ("partial_quarter_employee_count", result["partial_quarter_employee_count"]),
        ]
    )


def solve_compensation_forecast(memo, comp):
    rate_book = comp["rate_book"]
    rows = comp["roster_by_ensemble"][memo["ensemble_id"]]
    scenario = comp["scenarios"][memo["scenario_id"]]
    current = compensation_year_totals(rate_book, rows, scenario, 0)
    year1 = compensation_year_totals(rate_book, rows, scenario, 1)
    year2 = compensation_year_totals(rate_book, rows, scenario, 2)
    pay_types = rate_book["pay_types"]

    def annual_total(data):
        return d(data["annual_total"])

    largest_growth_pay_type = max(
        pay_types,
        key=lambda pay_type: (
            (
                d(year2["annual_pay_type_totals"][pay_type]) - d(current["annual_pay_type_totals"][pay_type])
            )
            / d(current["annual_pay_type_totals"][pay_type])
            if d(current["annual_pay_type_totals"][pay_type])
            else Decimal("Infinity"),
            -pay_types.index(pay_type),
        ),
    )

    return OrderedDict(
        [
            ("ensemble_id", memo["ensemble_id"]),
            ("scenario_id", memo["scenario_id"]),
            (
                "annual_totals",
                OrderedDict(
                    [
                        ("current", current["annual_total"]),
                        ("year_plus_1", year1["annual_total"]),
                        ("year_plus_2", year2["annual_total"]),
                    ]
                ),
            ),
            (
                "growth_rates",
                OrderedDict(
                    [
                        (
                            "year_plus_1_vs_current",
                            pct((annual_total(year1) - annual_total(current)) / annual_total(current))
                            if annual_total(current)
                            else 0.0,
                        ),
                        (
                            "year_plus_2_vs_year_plus_1",
                            pct((annual_total(year2) - annual_total(year1)) / annual_total(year1))
                            if annual_total(year1)
                            else 0.0,
                        ),
                    ]
                ),
            ),
            ("year_plus_2_quarter_totals", year2["quarter_totals"]),
            ("year_plus_2_pay_type_totals", year2["annual_pay_type_totals"]),
            ("largest_growth_pay_type", largest_growth_pay_type),
            ("combined_overscale_employee_count", current["combined_overscale_employee_count"]),
            ("partial_quarter_employee_count", current["partial_quarter_employee_count"]),
        ]
    )


def build_payroll_context(base_url: str):
    rate_book = fetch_json(base_url, "/api/payroll/rate-book")
    productions = fetch_json(base_url, "/api/payroll/productions")
    production_by_id = {row["production_id"]: row for row in productions}
    return {"rate_book": rate_book, "productions": productions, "production_by_id": production_by_id}


def normalized_service_category(service_type: str) -> str:
    if service_type == "Rehearsal":
        return "rehearsal"
    if service_type == "Audit":
        return "audit"
    if service_type == "Performance":
        return "performance"
    if "Sound Check" in service_type:
        return "sound_check"
    raise ValueError(service_type)


def solve_payroll(memo, payroll):
    production = payroll["production_by_id"][memo["production_id"]]
    rate_book = payroll["rate_book"]
    schedule = production["schedule"]
    schedule_by_id = {row["service_id"]: row for row in schedule}
    service_order = list(rate_book["service_rates"].keys())

    service_counts = OrderedDict()
    for service_type in service_order:
        count = sum(1 for row in schedule if row["service_type"] == service_type)
        if count:
            service_counts[service_type] = count

    category_totals = defaultdict(Decimal)
    conflict_flags = set()
    per_musician = []
    weekly_total = ZERO
    top_paid_total = None
    top_paid_id = ""

    for row in sorted(production["roster"], key=lambda item: item["musician_id"]):
        row_categories = defaultdict(Decimal)

        for service_id in row["assigned_service_ids"]:
            service = schedule_by_id[service_id]
            service_type = service["service_type"]
            duration = d(service["duration_hours"])
            if service_type == "Rehearsal":
                pay = d(rate_book["service_rates"][service_type]) * max(duration, Decimal("3"))
            else:
                pay = d(rate_book["service_rates"][service_type])

            category = normalized_service_category(service_type)
            row_categories[category] += pay
            category_totals[category] += pay

            if service_type == "Rehearsal":
                if service["start_time"] < rate_book["conflict_thresholds"]["rehearsal_earliest_start"]:
                    conflict_flags.add("REHEARSAL_EARLY_START")
                if service["end_time"] > rate_book["conflict_thresholds"]["rehearsal_latest_end"]:
                    conflict_flags.add("REHEARSAL_LATE_END")
            if duration > d(rate_book["service_time_limits"][service_type]):
                conflict_flags.add("SERVICE_OVER_TIME_LIMIT")
            if "Sound Check" in service_type:
                nominal = Decimal("1") if service_type.startswith("1hr") else Decimal("2")
                if abs(duration - nominal) > Decimal("0.0001"):
                    conflict_flags.add("SOUND_CHECK_DURATION_MISMATCH")

        if row.get("substitute"):
            substitute_adjustment = d(rate_book["service_rates"]["Performance"]) * Decimal("2")
            row_categories["performance"] += substitute_adjustment
            row_categories["substitute_adjustment"] += substitute_adjustment
            category_totals["performance"] += substitute_adjustment
            category_totals["substitute_adjustment"] += substitute_adjustment

        base_service = row_categories["audit"] + row_categories["performance"] + row_categories["rehearsal"] + row_categories["sound_check"]
        premium_total = ZERO
        if row.get("principal") or row.get("lead"):
            premium_total += base_service * d(rate_book["premium_pct"]["principal_or_lead"])
        if row.get("quartet"):
            premium_total += base_service * d(rate_book["premium_pct"]["quartet"])
        if row.get("electronic"):
            premium_total += base_service * d(rate_book["premium_pct"]["electronic"])
        if row.get("concertmaster"):
            premium_total += base_service * d(rate_book["premium_pct"]["concertmaster"])
        if row.get("assistant_principal") or row.get("title") == "Assistant Principal":
            premium_total += base_service * d(rate_book["premium_pct"].get("assistant_principal", rate_book["premium_pct"]["principal_or_lead"]))
        if row.get("associate_principal") or row.get("title") == "Associate Principal":
            premium_total += base_service * d(rate_book["premium_pct"].get("assistant_principal", rate_book["premium_pct"]["principal_or_lead"]))

        doubles = int(row.get("doubles", 0) or 0)
        doubles_total = ZERO
        if doubles >= 1:
            doubles_total += base_service * d(rate_book["premium_pct"]["first_double"])
        if doubles >= 2:
            doubles_total += base_service * d(rate_book["premium_pct"]["additional_double"]) * Decimal(doubles - 1)

        if premium_total:
            row_categories["premium"] += premium_total
            category_totals["premium"] += premium_total
        if doubles_total:
            row_categories["doubles"] += doubles_total
            category_totals["doubles"] += doubles_total

        vacation_total = ZERO
        if row.get("vacation_eligible"):
            vacation_total = (base_service + premium_total + doubles_total) * d(rate_book["premium_pct"]["vacation"])
            row_categories["vacation"] += vacation_total
            category_totals["vacation"] += vacation_total

        guarantee_total = ZERO
        if not row.get("substitute") and base_service < d(rate_book["weekly_guarantee"]):
            guarantee_total = d(rate_book["weekly_guarantee"]) - base_service
            row_categories["guarantee_adjustment"] += guarantee_total
            category_totals["guarantee_adjustment"] += guarantee_total

        row_total = base_service + premium_total + doubles_total + vacation_total + guarantee_total
        if row.get("substitute"):
            row_total += row_categories["substitute_adjustment"]
        weekly_total += row_total

        categories = OrderedDict((key, money(value)) for key, value in sorted(row_categories.items()) if value != ZERO)
        per_musician.append(
            OrderedDict(
                [
                    ("categories", categories),
                    ("musician_id", row["musician_id"]),
                    ("name", row["name"]),
                    ("total", money(row_total)),
                ]
            )
        )

        if top_paid_total is None or row_total > top_paid_total or (
            row_total == top_paid_total and row["musician_id"] < top_paid_id
        ):
            top_paid_total = row_total
            top_paid_id = row["musician_id"]

    category_order = [
        "audit",
        "doubles",
        "guarantee_adjustment",
        "performance",
        "premium",
        "rehearsal",
        "sound_check",
        "substitute_adjustment",
        "vacation",
    ]
    category_output = OrderedDict((key, money(category_totals.get(key, ZERO))) for key in category_order if category_totals.get(key, ZERO) != ZERO or key != "substitute_adjustment")
    conflict_flags = sorted(conflict_flags)

    return OrderedDict(
        [
            ("production_id", production["production_id"]),
            ("service_counts", service_counts),
            ("category_totals", category_output),
            ("weekly_total", money(weekly_total)),
            ("conflict_flags", conflict_flags),
            ("per_musician", per_musician),
            ("top_paid_musician_id", top_paid_id),
        ]
    )


def dispatch(task_input_root: Path):
    base_url = resolve_base_url(task_input_root)
    memo = load_json(find_payload_file(task_input_root, "request_memo.json"))
    template = load_json(find_payload_file(task_input_root, "answer_template.json"))
    required = template["required_top_level_keys"]

    if "production_id" in required and "weekly_total" in required:
        payroll = build_payroll_context(base_url)
        return solve_payroll(memo, payroll)
    if "scenario_id" in required and "annual_totals" in required:
        comp = build_compensation_context(base_url)
        return solve_compensation_forecast(memo, comp)
    if "current_year" in required and "annual_pay_type_totals" in required:
        comp = build_compensation_context(base_url)
        return solve_compensation_current(memo, comp)
    if "region_reconciliation_variance" in required and "fy2024" in required:
        finance = build_finance_context(base_url)
        return solve_regional_view(memo, finance)
    if any(key.endswith("_income_statement") for key in required):
        finance = build_finance_context(base_url)
        return solve_branch_close(memo, template, finance)
    raise ValueError(f"Unrecognized answer template: {required}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Solve Crescent Finance Ops JSON reports.")
    parser.add_argument("task_input_dir", nargs="?", default=".", help="Task input directory or its parent.")
    parser.add_argument("--out", help="Optional output path.")
    args = parser.parse_args(argv)

    task_input_root = find_input_root(Path(args.task_input_dir))
    output = dispatch(task_input_root)
    text = json.dumps(output, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n")
    else:
        sys.stdout.write(text + "\n")


if __name__ == "__main__":
    main()
