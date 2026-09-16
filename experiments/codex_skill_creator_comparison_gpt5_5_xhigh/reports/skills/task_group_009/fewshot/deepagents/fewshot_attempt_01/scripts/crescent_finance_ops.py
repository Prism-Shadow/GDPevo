#!/usr/bin/env python3
"""Solve Crescent Finance Ops JSON tasks from API payloads."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ZERO = Decimal("0")
CENT = Decimal("0.01")
BPS = Decimal("0.0001")


def dec(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return ZERO
    return Decimal(str(value))


def out_decimal(value: Decimal, quantum: Decimal) -> float:
    return float(dec(value).quantize(quantum, rounding=ROUND_HALF_UP))


def quant_money(value: Decimal) -> Decimal:
    return dec(value).quantize(CENT, rounding=ROUND_HALF_UP)


def money(value: Decimal) -> float:
    return float(quant_money(value))


def ratio(value: Decimal) -> float:
    return out_decimal(value, BPS)


def div(numerator: Decimal, denominator: Decimal) -> Decimal:
    denominator = dec(denominator)
    if denominator == 0:
        return ZERO
    return dec(numerator) / denominator


def load_json(path: str | None):
    if not path:
        return {}
    return json.loads(Path(path).read_text())


def resolve_base_url(args) -> str:
    candidates = [
        args.base_url,
        os.environ.get("TASK_ENV_BASE_URL"),
        os.environ.get("FINANCE_OPS_BASE_URL"),
        os.environ.get("BASE_URL"),
    ]
    if args.env_file:
        env_data = load_json(args.env_file)
        candidates.append(env_data.get("base_url"))
    if args.memo:
        sibling_env = Path(args.memo).parent / "environment_access.json"
        if sibling_env.exists():
            candidates.append(load_json(str(sibling_env)).get("base_url"))
    for candidate in candidates:
        if candidate and not str(candidate).startswith("<"):
            return str(candidate).rstrip("/")
    raise SystemExit(
        "No concrete base URL found. Pass --base-url or set TASK_ENV_BASE_URL."
    )


def fetch(base_url: str, path: str):
    with urllib.request.urlopen(base_url + path) as response:
        return json.load(response)


def period_number(period: str) -> int:
    return int(period.removeprefix("M"))


def sorted_periods(periods):
    return sorted(periods, key=period_number)


def sorted_ids(ids):
    return sorted(ids)


def rank_desc(items, target_id):
    ordered = sorted(items, key=lambda item: (-item[1], item[0]))
    for index, item in enumerate(ordered, start=1):
        if item[0] == target_id:
            return index
    return None


class Finance:
    def __init__(self, base_url: str):
        self.branches = fetch(base_url, "/api/finance/branches")
        self.period_map = fetch(base_url, "/api/finance/period-map")
        self.accounts = fetch(base_url, "/api/finance/accounts")
        self.records = fetch(base_url, "/api/finance/records")
        self.account_category = {a["account"]: a["category"] for a in self.accounts}
        self.period_to_fy = {p["period"]: p["fiscal_year"] for p in self.period_map}
        self.fy_to_periods = {}
        for item in self.period_map:
            self.fy_to_periods.setdefault(item["fiscal_year"], []).append(item["period"])
        self.fy_to_periods = {
            fy: sorted_periods(periods) for fy, periods in self.fy_to_periods.items()
        }

    def rows(self, branch_id=None, region_id=None):
        return [
            row
            for row in self.records
            if (branch_id is None or row["branch_id"] == branch_id)
            and (region_id is None or row["region_id"] == region_id)
        ]

    def category_sum(self, rows, category: str, periods) -> Decimal:
        total = ZERO
        for row in rows:
            if self.account_category[row["account"]] != category:
                continue
            for period in periods:
                total += dec(row["values"].get(period, 0))
        return total

    def account_sum(self, rows, account: str, periods) -> Decimal:
        total = ZERO
        for row in rows:
            if row["account"] != account:
                continue
            for period in periods:
                total += dec(row["values"].get(period, 0))
        return total

    def metrics(self, rows, periods):
        revenue = self.category_sum(rows, "revenue", periods)
        cogs = self.category_sum(rows, "cogs", periods)
        gross_margin = revenue - cogs
        sga = self.category_sum(rows, "sga", periods)
        allocations = self.category_sum(rows, "allocations", periods)
        ebitda = gross_margin - sga - allocations
        active_customers = self.account_sum(rows, "active_customers", periods)
        labor_headcount = self.account_sum(rows, "labor_headcount", periods)
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

    def branch(self, branch_id: str):
        for branch in self.branches:
            if branch["branch_id"] == branch_id:
                return branch
        raise KeyError(f"Unknown branch_id: {branch_id}")

    def region_ids(self):
        return sorted_ids({branch["region_id"] for branch in self.branches})

    def branch_ids_for_region(self, region_id: str):
        return sorted_ids(
            branch["branch_id"] for branch in self.branches if branch["region_id"] == region_id
        )

    def fiscal_year_for_period(self, period: str) -> int:
        return self.period_to_fy[period]


def finance_output_metrics(metrics, include_operating=False):
    result = {
        "revenue": money(metrics["revenue"]),
        "cogs": money(metrics["cogs"]),
        "gross_margin": money(metrics["gross_margin"]),
        "sga": money(metrics["sga"]),
        "allocations": money(metrics["allocations"]),
        "ebitda": money(metrics["ebitda"]),
    }
    if include_operating:
        result["ebitda_margin"] = ratio(div(metrics["ebitda"], metrics["revenue"]))
        result["arpu"] = money(div(metrics["revenue"], metrics["active_customers"]))
        result["sales_per_labor_headcount"] = money(
            div(metrics["revenue"], metrics["labor_headcount"])
        )
    return result


def solve_branch_close(base_url: str, memo, template):
    finance = Finance(base_url)
    branch_id = memo["target_branch_id"]
    close_period = memo["close_period"]
    prior_period = memo["prior_period"]
    branch = finance.branch(branch_id)
    region_id = branch["region_id"]
    current_fy = finance.fiscal_year_for_period(close_period)
    prior_fy = max(fy for fy in finance.fy_to_periods if fy < current_fy)
    current_periods = finance.fy_to_periods[current_fy]
    prior_periods = finance.fy_to_periods[prior_fy]
    rows = finance.rows(branch_id=branch_id)

    monthly_metrics = finance.metrics(rows, [close_period])
    current_metrics = finance.metrics(rows, current_periods)
    prior_metrics = finance.metrics(rows, prior_periods)
    current_revenue = finance.metrics(rows, [close_period])["revenue"]
    prior_revenue = finance.metrics(rows, [prior_period])["revenue"]

    required = template.get("required_top_level_keys", [])
    income_key = next(
        (key for key in required if key.endswith("_income_statement")),
        f"{close_period.lower()}_income_statement",
    )
    fy_key = next(
        (key for key in required if key.startswith("fy") and "_vs_" in key),
        f"fy{current_fy}_vs_fy{prior_fy}",
    )

    branch_growth_items = []
    branch_arpu_items = []
    branch_ebitda_items = []
    for item in finance.branches:
        b_rows = finance.rows(branch_id=item["branch_id"])
        b_current = finance.metrics(b_rows, current_periods)
        b_prior = finance.metrics(b_rows, prior_periods)
        growth = div(
            b_current["revenue"] - b_prior["revenue"], b_prior["revenue"]
        )
        arpu = div(b_current["revenue"], b_current["active_customers"])
        branch_growth_items.append((item["branch_id"], growth))
        branch_arpu_items.append((item["branch_id"], arpu))
        branch_ebitda_items.append((item["branch_id"], b_current["ebitda"]))

    region_ebitda_items = []
    for rid in finance.region_ids():
        r_current = finance.metrics(finance.rows(region_id=rid), current_periods)
        region_ebitda_items.append((rid, r_current["ebitda"]))

    region_metrics = finance.metrics(finance.rows(region_id=region_id), current_periods)
    period_convention = {}
    for fy, periods in sorted(finance.fy_to_periods.items()):
        label = f"{periods[0]}_to_{periods[-1]}"
        period_convention[label] = f"FY{fy}"
    period_convention["current_month"] = close_period
    period_convention["prior_month"] = prior_period

    result = {
        "target_branch_id": branch_id,
        "target_branch_name": branch["branch_name"],
        "period_convention": period_convention,
        income_key: finance_output_metrics(monthly_metrics),
        "mom_revenue_variance": {
            "amount": money(current_revenue - prior_revenue),
            "pct": ratio(div(current_revenue - prior_revenue, prior_revenue)),
        },
        fy_key: {
            f"fy{current_fy}": finance_output_metrics(
                current_metrics, include_operating=True
            ),
            "revenue_growth_pct": ratio(
                div(
                    current_metrics["revenue"] - prior_metrics["revenue"],
                    prior_metrics["revenue"],
                )
            ),
            "ebitda_growth_pct": ratio(
                div(
                    current_metrics["ebitda"] - prior_metrics["ebitda"],
                    prior_metrics["ebitda"],
                )
            ),
        },
        "region_context": {
            "region_id": region_id,
            "branch_ids": finance.branch_ids_for_region(region_id),
            f"fy{current_fy}_ebitda": money(region_metrics["ebitda"]),
            "ebitda_rank_desc": rank_desc(region_ebitda_items, region_id),
        },
        "branch_rankings": {
            "sales_growth_rank_desc": rank_desc(branch_growth_items, branch_id),
            "top_sales_growth_branch_id": sorted(
                branch_growth_items, key=lambda item: (-item[1], item[0])
            )[0][0],
            "top_arpu_branch_id": sorted(
                branch_arpu_items, key=lambda item: (-item[1], item[0])
            )[0][0],
        },
    }
    return result


def solve_region_view(base_url: str, memo, template):
    finance = Finance(base_url)
    region_id = memo["target_region_id"]
    years = sorted(memo.get("requested_comparison_years") or finance.fy_to_periods)
    prior_fy = years[0]
    current_fy = years[-1]
    branch_ids = finance.branch_ids_for_region(region_id)
    region_rows = finance.rows(region_id=region_id)

    prior_metrics = finance.metrics(region_rows, finance.fy_to_periods[prior_fy])
    current_metrics = finance.metrics(region_rows, finance.fy_to_periods[current_fy])

    branch_ebitda_items = []
    branch_ebitda_sum = ZERO
    for branch_id in branch_ids:
        metrics = finance.metrics(
            finance.rows(branch_id=branch_id), finance.fy_to_periods[current_fy]
        )
        branch_ebitda_items.append((branch_id, metrics["ebitda"]))
        branch_ebitda_sum += metrics["ebitda"]

    result = {
        "region_id": region_id,
        "branch_ids": branch_ids,
        f"fy{prior_fy}": {
            "revenue": money(prior_metrics["revenue"]),
            "sga": money(prior_metrics["sga"]),
            "allocations": money(prior_metrics["allocations"]),
            "ebitda": money(prior_metrics["ebitda"]),
        },
        f"fy{current_fy}": {
            "revenue": money(current_metrics["revenue"]),
            "sga": money(current_metrics["sga"]),
            "allocations": money(current_metrics["allocations"]),
            "ebitda": money(current_metrics["ebitda"]),
            "ebitda_margin": ratio(
                div(current_metrics["ebitda"], current_metrics["revenue"])
            ),
            "sales_per_labor_headcount": money(
                div(current_metrics["revenue"], current_metrics["labor_headcount"])
            ),
        },
        "revenue_growth_pct": ratio(
            div(
                current_metrics["revenue"] - prior_metrics["revenue"],
                prior_metrics["revenue"],
            )
        ),
        "top_ebitda_branch_id": sorted(
            branch_ebitda_items, key=lambda item: (-item[1], item[0])
        )[0][0],
        "bottom_ebitda_branch_id": sorted(
            branch_ebitda_items, key=lambda item: (item[1], item[0])
        )[0][0],
        "region_reconciliation_variance": money(
            current_metrics["ebitda"] - branch_ebitda_sum
        ),
    }
    return result


class Compensation:
    def __init__(self, base_url: str):
        self.rate_book = fetch(base_url, "/api/compensation/rate-book")
        self.rosters = fetch(base_url, "/api/compensation/rosters")
        self.scenarios = fetch(base_url, "/api/compensation/scenarios")
        self.pay_types = self.rate_book["pay_types"]

    def roster(self, ensemble_id: str):
        rows = [row for row in self.rosters if row["ensemble_id"] == ensemble_id]
        if not rows:
            raise KeyError(f"Unknown ensemble_id: {ensemble_id}")
        return rows

    def seniority_weekly(self, years: int) -> Decimal:
        for band in self.rate_book["seniority_weekly"]:
            max_years = band["max_years"]
            if years >= band["min_years"] and (
                max_years is None or years <= max_years
            ):
                return dec(band["weekly_amount"])
        raise ValueError(f"No seniority band for {years} years")

    def aggregate(self, ensemble_id: str, forecast_label="current", scenario_id=None):
        scenario = self.scenarios.get(scenario_id, {}) if scenario_id else {}
        mws_factor, overscale_factor, seniority_factor, title_multiplier, year_add = (
            self.forecast_factors(forecast_label, scenario)
        )
        quarter_totals = {quarter: ZERO for quarter in self.rate_book["quarter_weeks"]}
        pay_type_totals = {pay_type: ZERO for pay_type in self.pay_types}
        base_mws = dec(self.rate_book["minimum_weekly_scale"]) * mws_factor

        for row in self.roster(ensemble_id):
            years = int(row["years_of_service"]) + year_add
            seniority = self.seniority_weekly(years) * seniority_factor
            for quarter, weeks_value in row["weeks_by_quarter"].items():
                weeks = dec(weeks_value)
                amounts = {
                    "Minimum Weekly Scale": base_mws * weeks,
                    "Titled Position Premium": ZERO,
                    "Seniority": seniority * weeks,
                    "Overscale": dec(row["overscale_weekly"]) * overscale_factor * weeks,
                }
                title = row.get("title")
                if title and not row.get("combined_overscale_includes_title"):
                    pct = dec(self.rate_book["title_premium_pct"].get(title, 0))
                    amounts["Titled Position Premium"] = (
                        base_mws * pct * title_multiplier * weeks
                    )
                for pay_type, amount in amounts.items():
                    pay_type_totals[pay_type] += amount
                    quarter_totals[quarter] += amount

        annual_total = sum(quarter_totals.values(), ZERO)
        return quarter_totals, pay_type_totals, annual_total

    def forecast_factors(self, label: str, scenario):
        if label == "current" or not scenario:
            return Decimal("1"), Decimal("1"), Decimal("1"), Decimal("1"), 0
        y1 = scenario["year_plus_1"]
        if label == "year_plus_1":
            return (
                Decimal("1") + dec(y1["mws_growth"]),
                Decimal("1") + dec(y1["overscale_growth"]),
                Decimal("1") + dec(y1["seniority_growth"]),
                dec(y1["title_pct_multiplier"]),
                1,
            )
        y2 = scenario["year_plus_2"]
        return (
            (Decimal("1") + dec(y1["mws_growth"]))
            * (Decimal("1") + dec(y2["mws_growth"])),
            (Decimal("1") + dec(y1["overscale_growth"]))
            * (Decimal("1") + dec(y2["overscale_growth"])),
            (Decimal("1") + dec(y1["seniority_growth"]))
            * (Decimal("1") + dec(y2["seniority_growth"])),
            dec(y2["title_pct_multiplier"]),
            2,
        )

    def treatment_counts(self, ensemble_id: str):
        standard_weeks = self.rate_book["quarter_weeks"]
        rows = self.roster(ensemble_id)
        combined = sum(1 for row in rows if row.get("combined_overscale_includes_title"))
        partial = 0
        for row in rows:
            if any(
                dec(row["weeks_by_quarter"].get(q, 0)) != dec(weeks)
                for q, weeks in standard_weeks.items()
            ):
                partial += 1
        return combined, partial


def rounded_money_map(mapping):
    return {key: money(value) for key, value in mapping.items()}


def solve_compensation_current(base_url: str, memo, template):
    comp = Compensation(base_url)
    ensemble_id = memo["ensemble_id"]
    quarters, pay_types, _annual_total = comp.aggregate(ensemble_id)
    combined, partial = comp.treatment_counts(ensemble_id)
    largest = sorted(pay_types.items(), key=lambda item: (-item[1], comp.pay_types.index(item[0])))[0][0]
    return {
        "ensemble_id": ensemble_id,
        "current_year": int(comp.rate_book["current_year"]),
        "roster_count": len(comp.roster(ensemble_id)),
        "pay_types": comp.pay_types,
        "quarter_totals": rounded_money_map(quarters),
        "annual_pay_type_totals": rounded_money_map(pay_types),
        "annual_total": money(sum((quant_money(v) for v in quarters.values()), ZERO)),
        "largest_pay_type": largest,
        "combined_overscale_employee_count": combined,
        "partial_quarter_employee_count": partial,
    }


def solve_compensation_forecast(base_url: str, memo, template):
    comp = Compensation(base_url)
    ensemble_id = memo["ensemble_id"]
    scenario_id = memo["scenario_id"]
    labels = ["current", "year_plus_1", "year_plus_2"]
    display_annual_totals = {}
    pay_type_totals = {}
    quarter_totals = {}
    for label in labels:
        quarters, pay_types, _total = comp.aggregate(ensemble_id, label, scenario_id)
        display_annual_totals[label] = sum(
            (quant_money(v) for v in quarters.values()), ZERO
        )
        pay_type_totals[label] = pay_types
        quarter_totals[label] = quarters
    combined, partial = comp.treatment_counts(ensemble_id)

    growth_scores = []
    for index, pay_type in enumerate(comp.pay_types):
        current = pay_type_totals["current"][pay_type]
        future = pay_type_totals["year_plus_2"][pay_type]
        score = div(future - current, current) if current != 0 else future
        growth_scores.append((pay_type, score, index))
    largest_growth = sorted(growth_scores, key=lambda item: (-item[1], item[2]))[0][0]

    return {
        "ensemble_id": ensemble_id,
        "scenario_id": scenario_id,
        "annual_totals": {label: money(display_annual_totals[label]) for label in labels},
        "growth_rates": {
            "year_plus_1_vs_current": ratio(
                div(
                    display_annual_totals["year_plus_1"]
                    - display_annual_totals["current"],
                    display_annual_totals["current"],
                )
            ),
            "year_plus_2_vs_year_plus_1": ratio(
                div(
                    display_annual_totals["year_plus_2"]
                    - display_annual_totals["year_plus_1"],
                    display_annual_totals["year_plus_1"],
                )
            ),
        },
        "year_plus_2_quarter_totals": rounded_money_map(
            quarter_totals["year_plus_2"]
        ),
        "year_plus_2_pay_type_totals": rounded_money_map(
            pay_type_totals["year_plus_2"]
        ),
        "largest_growth_pay_type": largest_growth,
        "combined_overscale_employee_count": combined,
        "partial_quarter_employee_count": partial,
    }


class Payroll:
    def __init__(self, base_url: str):
        self.rate_book = fetch(base_url, "/api/payroll/rate-book")
        self.productions = fetch(base_url, "/api/payroll/productions")

    def production(self, production_id: str):
        for production in self.productions:
            if production["production_id"] == production_id:
                return production
        raise KeyError(f"Unknown production_id: {production_id}")

    def service_amount(self, service) -> tuple[str, Decimal]:
        service_type = service["service_type"]
        rates = self.rate_book["service_rates"]
        if service_type == "Rehearsal":
            return "rehearsal", dec(rates[service_type]) * max(
                dec(service["duration_hours"]), Decimal("3")
            )
        if service_type == "Performance":
            return "performance", dec(rates[service_type])
        if service_type == "Audit":
            return "audit", dec(rates[service_type])
        if "Sound Check" in service_type:
            return "sound_check", dec(rates[service_type])
        raise ValueError(f"Unsupported service type: {service_type}")

    def conflict_flags(self, production):
        flags = set()
        thresholds = self.rate_book["conflict_thresholds"]
        limits = self.rate_book["service_time_limits"]
        for service in production["schedule"]:
            service_type = service["service_type"]
            duration = dec(service["duration_hours"])
            limit = dec(limits[service_type])
            if duration > limit:
                flags.add("SERVICE_OVER_TIME_LIMIT")
            if "Sound Check" in service_type and duration != limit:
                flags.add("SOUND_CHECK_DURATION_MISMATCH")
            if service_type == "Rehearsal":
                if service["start_time"] < thresholds["rehearsal_earliest_start"]:
                    flags.add("REHEARSAL_EARLY_START")
                if service["end_time"] > thresholds["rehearsal_latest_end"]:
                    flags.add("REHEARSAL_LATE_END")
        return sorted(flags)

    def musician_pay(self, musician, services_by_id):
        categories = {
            "performance": ZERO,
            "audit": ZERO,
            "rehearsal": ZERO,
            "sound_check": ZERO,
            "premium": ZERO,
            "doubles": ZERO,
            "vacation": ZERO,
            "guarantee_adjustment": ZERO,
            "substitute_adjustment": ZERO,
        }
        for service_id in musician["assigned_service_ids"]:
            category, amount = self.service_amount(services_by_id[service_id])
            categories[category] += amount

        if musician.get("substitute"):
            substitute_adjustment = (
                Decimal("2") * dec(self.rate_book["service_rates"]["Performance"])
            )
            categories["performance"] += substitute_adjustment
            categories["substitute_adjustment"] = substitute_adjustment

        base_service_pay = (
            categories["performance"]
            + categories["audit"]
            + categories["rehearsal"]
            + categories["sound_check"]
        )

        premium_pct = ZERO
        premium_book = self.rate_book["premium_pct"]
        if musician.get("concertmaster"):
            premium_pct += dec(premium_book.get("concertmaster", 0))
        if musician.get("principal") or musician.get("lead"):
            premium_pct += dec(premium_book.get("principal_or_lead", 0))
        if musician.get("quartet"):
            premium_pct += dec(premium_book.get("quartet", 0))
        if musician.get("electronic"):
            premium_pct += dec(premium_book.get("electronic", 0))
        categories["premium"] = base_service_pay * premium_pct

        doubles = int(musician.get("doubles") or 0)
        if doubles > 0:
            double_pct = dec(premium_book["first_double"]) + dec(
                premium_book["additional_double"]
            ) * max(0, doubles - 1)
            categories["doubles"] = base_service_pay * double_pct

        if musician.get("vacation_eligible"):
            categories["vacation"] = (
                base_service_pay + categories["premium"] + categories["doubles"]
            ) * dec(premium_book["vacation"])

        if not musician.get("substitute"):
            guarantee = dec(self.rate_book["weekly_guarantee"]) - base_service_pay
            if guarantee > 0:
                categories["guarantee_adjustment"] = guarantee

        total = sum(categories.values(), ZERO)
        rounded_categories = {
            key: money(value)
            for key, value in categories.items()
            if value != 0
        }
        return {
            "musician_id": musician["musician_id"],
            "name": musician["name"],
            "total_raw": total,
            "total": money(total),
            "categories": rounded_categories,
        }, categories


def solve_payroll(base_url: str, memo, template):
    payroll = Payroll(base_url)
    production = payroll.production(memo["production_id"])
    services_by_id = {service["service_id"]: service for service in production["schedule"]}
    service_counts = dict(Counter(service["service_type"] for service in production["schedule"]))
    musicians = []
    category_totals = {
        "performance": ZERO,
        "audit": ZERO,
        "rehearsal": ZERO,
        "sound_check": ZERO,
        "premium": ZERO,
        "doubles": ZERO,
        "vacation": ZERO,
        "guarantee_adjustment": ZERO,
        "substitute_adjustment": ZERO,
    }
    for musician in production["roster"]:
        result, categories = payroll.musician_pay(musician, services_by_id)
        musicians.append(result)
        for key, value in categories.items():
            category_totals[key] += value

    musicians.sort(key=lambda item: item["musician_id"])
    top = sorted(musicians, key=lambda item: (-item["total_raw"], item["musician_id"]))[0]
    for musician in musicians:
        musician.pop("total_raw")

    template_categories = (
        template.get("field_types", {})
        .get("category_totals", {})
        .keys()
    )
    category_keys = list(template_categories) or list(category_totals.keys())
    rounded_category_totals = {
        key: money(category_totals[key])
        for key in category_keys
        if key in category_totals and (category_totals[key] != 0 or key != "substitute_adjustment")
    }
    weekly_total = sum(category_totals.values(), ZERO)

    return {
        "production_id": production["production_id"],
        "service_counts": service_counts,
        "category_totals": rounded_category_totals,
        "weekly_total": money(weekly_total),
        "conflict_flags": payroll.conflict_flags(production),
        "per_musician": musicians,
        "top_paid_musician_id": top["musician_id"],
    }


def solve(base_url: str, memo, template):
    if "production_id" in memo:
        return solve_payroll(base_url, memo, template)
    if "target_region_id" in memo:
        return solve_region_view(base_url, memo, template)
    if "target_branch_id" in memo:
        return solve_branch_close(base_url, memo, template)
    if "ensemble_id" in memo and "scenario_id" in memo:
        return solve_compensation_forecast(base_url, memo, template)
    if "ensemble_id" in memo:
        return solve_compensation_current(base_url, memo, template)
    raise SystemExit("Unsupported request_memo.json shape.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--env-file")
    parser.add_argument("--memo", required=True)
    parser.add_argument("--template")
    args = parser.parse_args()

    base_url = resolve_base_url(args)
    memo = load_json(args.memo)
    template = load_json(args.template)
    result = solve(base_url, memo, template)
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
