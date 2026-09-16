#!/usr/bin/env python3
"""Calculator for Crescent Finance Ops JSON reporting tasks."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


MONEY = Decimal("0.01")
RATIO = Decimal("0.0001")
ZERO = Decimal("0")


def dec(value: Any) -> Decimal:
    return Decimal(str(value))


def money(value: Decimal) -> float:
    return float(value.quantize(MONEY, rounding=ROUND_HALF_UP))


def ratio(value: Decimal) -> float:
    return float(value.quantize(RATIO, rounding=ROUND_HALF_UP))


def pct(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return ZERO
    return numerator / denominator


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def find_input_dir(path: Path) -> Path:
    if (path / "payloads").is_dir():
        return path
    if (path / "input" / "payloads").is_dir():
        return path / "input"
    raise SystemExit(f"Cannot find payloads/ under {path}")


def usable_base_url(payload_base: str | None, override: str | None) -> str:
    base = override or os.environ.get("TASK_ENV_BASE_URL")
    if not base and payload_base and "<" not in payload_base and ">" not in payload_base:
        base = payload_base
    if not base:
        base = "http://task-env:9009/"
    return base.rstrip("/")


def fetch_json(base_url: str, endpoint: str) -> Any:
    url = f"{base_url}{endpoint}"
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def period_number(period: str) -> int:
    return int(period.upper().lstrip("M"))


def sorted_periods(periods: list[str]) -> list[str]:
    return sorted(periods, key=period_number)


def time_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


class FinanceData:
    def __init__(self, base_url: str):
        self.branches = fetch_json(base_url, "/api/finance/branches")
        self.period_map = fetch_json(base_url, "/api/finance/period-map")
        self.accounts = fetch_json(base_url, "/api/finance/accounts")
        self.records = fetch_json(base_url, "/api/finance/records")
        self.account_category = {row["account"]: row["category"] for row in self.accounts}
        self.record_index = {
            (row["branch_id"], row["account"]): row["values"] for row in self.records
        }
        self.branch_by_id = {row["branch_id"]: row for row in self.branches}
        self.period_to_year = {
            row["period"]: int(row["fiscal_year"]) for row in self.period_map
        }

    def periods_for_year(self, fiscal_year: int) -> list[str]:
        return sorted_periods(
            [row["period"] for row in self.period_map if int(row["fiscal_year"]) == fiscal_year]
        )

    def year_for_period(self, period: str) -> int:
        return self.period_to_year[period]

    def sum_account(self, branch_ids: list[str], account: str, periods: list[str]) -> Decimal:
        total = ZERO
        for branch_id in branch_ids:
            values = self.record_index.get((branch_id, account), {})
            total += sum((dec(values.get(period, 0)) for period in periods), ZERO)
        return total

    def category_sum(
        self, branch_ids: list[str], category: str, periods: list[str]
    ) -> Decimal:
        total = ZERO
        for account, account_category in self.account_category.items():
            if account_category == category:
                total += self.sum_account(branch_ids, account, periods)
        return total

    def statement(self, branch_ids: list[str], periods: list[str]) -> dict[str, Decimal]:
        revenue = self.category_sum(branch_ids, "revenue", periods)
        cogs = self.category_sum(branch_ids, "cogs", periods)
        gross_margin = revenue - cogs
        sga = self.category_sum(branch_ids, "sga", periods)
        allocations = self.category_sum(branch_ids, "allocations", periods)
        ebitda = gross_margin - sga - allocations
        return {
            "revenue": revenue,
            "cogs": cogs,
            "gross_margin": gross_margin,
            "sga": sga,
            "allocations": allocations,
            "ebitda": ebitda,
        }

    def fiscal_metrics(self, branch_ids: list[str], fiscal_year: int) -> dict[str, Decimal]:
        periods = self.periods_for_year(fiscal_year)
        values = self.statement(branch_ids, periods)
        values["ebitda_margin"] = pct(values["ebitda"], values["revenue"])
        active_customers = self.sum_account(branch_ids, "active_customers", periods)
        labor_headcount = self.sum_account(branch_ids, "labor_headcount", periods)
        values["arpu"] = pct(values["revenue"], active_customers)
        values["sales_per_labor_headcount"] = pct(values["revenue"], labor_headcount)
        return values

    def branch_ids_for_region(self, region_id: str) -> list[str]:
        return sorted(
            [row["branch_id"] for row in self.branches if row["region_id"] == region_id]
        )


def rounded_statement(values: dict[str, Decimal], include_cogs: bool = True) -> dict[str, float]:
    keys = ["revenue", "cogs", "gross_margin", "sga", "allocations", "ebitda"]
    if not include_cogs:
        keys = ["revenue", "sga", "allocations", "ebitda"]
    return {key: money(values[key]) for key in keys}


def rounded_fiscal_metrics(values: dict[str, Decimal]) -> dict[str, float]:
    output = rounded_statement(values)
    output["ebitda_margin"] = ratio(values["ebitda_margin"])
    output["arpu"] = money(values["arpu"])
    output["sales_per_labor_headcount"] = money(values["sales_per_labor_headcount"])
    return output


def rank_desc(items: dict[str, Decimal], target_id: str) -> int:
    ordered = sorted(items.items(), key=lambda item: (-item[1], item[0]))
    return [item[0] for item in ordered].index(target_id) + 1


def top_id_desc(items: dict[str, Decimal]) -> str:
    return sorted(items.items(), key=lambda item: (-item[1], item[0]))[0][0]


def bottom_id_asc(items: dict[str, Decimal]) -> str:
    return sorted(items.items(), key=lambda item: (item[1], item[0]))[0][0]


def period_convention(finance: FinanceData, current: str, prior: str) -> dict[str, str]:
    grouped: dict[int, list[str]] = defaultdict(list)
    for row in finance.period_map:
        grouped[int(row["fiscal_year"])].append(row["period"])
    output: dict[str, str] = {}
    for fiscal_year in sorted(grouped):
        periods = sorted_periods(grouped[fiscal_year])
        output[f"{periods[0]}_to_{periods[-1]}"] = f"FY{fiscal_year}"
    output["current_month"] = current
    output["prior_month"] = prior
    return output


def find_required_key(template: dict[str, Any], pattern: str, default: str) -> str:
    for key in template.get("required_top_level_keys", []):
        if re.fullmatch(pattern, key):
            return key
    return default


def solve_branch_close(base_url: str, memo: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    finance = FinanceData(base_url)
    branch_id = memo["target_branch_id"]
    close_period = memo.get("close_period") or memo.get("current_period")
    prior_period = memo.get("prior_period")
    current_year = finance.year_for_period(close_period)
    previous_year = max(year for year in {row["fiscal_year"] for row in finance.period_map} if year < current_year)

    month_key = find_required_key(
        template, r"m\d+_income_statement", f"{close_period.lower()}_income_statement"
    )
    fy_key = find_required_key(
        template, r"fy\d+_vs_fy\d+", f"fy{current_year}_vs_fy{previous_year}"
    )

    branch_row = finance.branch_by_id[branch_id]
    current_statement = finance.statement([branch_id], [close_period])
    prior_statement = finance.statement([branch_id], [prior_period])
    current_fy = finance.fiscal_metrics([branch_id], current_year)
    prior_fy = finance.fiscal_metrics([branch_id], previous_year)

    all_growth: dict[str, Decimal] = {}
    all_arpu: dict[str, Decimal] = {}
    for branch in finance.branches:
        bid = branch["branch_id"]
        cur = finance.fiscal_metrics([bid], current_year)
        prev = finance.fiscal_metrics([bid], previous_year)
        all_growth[bid] = pct(cur["revenue"] - prev["revenue"], prev["revenue"])
        all_arpu[bid] = cur["arpu"]

    region_id = branch_row["region_id"]
    region_branch_ids = finance.branch_ids_for_region(region_id)
    region_ebitda_by_region = {
        rid: finance.fiscal_metrics(finance.branch_ids_for_region(rid), current_year)["ebitda"]
        for rid in sorted({row["region_id"] for row in finance.branches})
    }
    region_ebitda = region_ebitda_by_region[region_id]

    return {
        "target_branch_id": branch_id,
        "target_branch_name": branch_row["branch_name"],
        "period_convention": period_convention(finance, close_period, prior_period),
        month_key: rounded_statement(current_statement),
        "mom_revenue_variance": {
            "amount": money(current_statement["revenue"] - prior_statement["revenue"]),
            "pct": ratio(pct(current_statement["revenue"] - prior_statement["revenue"], prior_statement["revenue"])),
        },
        fy_key: {
            f"fy{current_year}": rounded_fiscal_metrics(current_fy),
            "revenue_growth_pct": ratio(pct(current_fy["revenue"] - prior_fy["revenue"], prior_fy["revenue"])),
            "ebitda_growth_pct": ratio(pct(current_fy["ebitda"] - prior_fy["ebitda"], prior_fy["ebitda"])),
        },
        "region_context": {
            "region_id": region_id,
            "branch_ids": region_branch_ids,
            f"fy{current_year}_ebitda": money(region_ebitda),
            "ebitda_rank_desc": rank_desc(region_ebitda_by_region, region_id),
        },
        "branch_rankings": {
            "sales_growth_rank_desc": rank_desc(all_growth, branch_id),
            "top_sales_growth_branch_id": top_id_desc(all_growth),
            "top_arpu_branch_id": top_id_desc(all_arpu),
        },
    }


def solve_regional(base_url: str, memo: dict[str, Any]) -> dict[str, Any]:
    finance = FinanceData(base_url)
    region_id = memo["target_region_id"]
    years = sorted(int(year) for year in memo.get("requested_comparison_years", []))
    if len(years) < 2:
        years = sorted({int(row["fiscal_year"]) for row in finance.period_map})[-2:]
    previous_year, current_year = years[0], years[-1]
    branch_ids = finance.branch_ids_for_region(region_id)

    previous = finance.fiscal_metrics(branch_ids, previous_year)
    current = finance.fiscal_metrics(branch_ids, current_year)
    branch_ebitda = {
        bid: finance.fiscal_metrics([bid], current_year)["ebitda"] for bid in branch_ids
    }
    sum_branch_ebitda = sum(branch_ebitda.values(), ZERO)

    return {
        "region_id": region_id,
        "branch_ids": branch_ids,
        f"fy{previous_year}": rounded_statement(previous, include_cogs=False),
        f"fy{current_year}": {
            **rounded_statement(current, include_cogs=False),
            "ebitda_margin": ratio(current["ebitda_margin"]),
            "sales_per_labor_headcount": money(current["sales_per_labor_headcount"]),
        },
        "revenue_growth_pct": ratio(pct(current["revenue"] - previous["revenue"], previous["revenue"])),
        "top_ebitda_branch_id": top_id_desc(branch_ebitda),
        "bottom_ebitda_branch_id": bottom_id_asc(branch_ebitda),
        "region_reconciliation_variance": money(sum_branch_ebitda - current["ebitda"]),
    }


class CompensationData:
    def __init__(self, base_url: str, include_scenarios: bool = False):
        self.rate = fetch_json(base_url, "/api/compensation/rate-book")
        self.rosters = fetch_json(base_url, "/api/compensation/rosters")
        self.scenarios = (
            fetch_json(base_url, "/api/compensation/scenarios") if include_scenarios else {}
        )

    def roster(self, ensemble_id: str) -> list[dict[str, Any]]:
        return [row for row in self.rosters if row["ensemble_id"] == ensemble_id]

    def seniority_weekly(self, years: int) -> Decimal:
        for band in self.rate["seniority_weekly"]:
            if years >= int(band["min_years"]) and (
                band["max_years"] is None or years <= int(band["max_years"])
            ):
                return dec(band["weekly_amount"])
        return ZERO

    def scenario_factors(self, scenario_id: str | None, offset: int) -> dict[str, Decimal]:
        factors = {
            "mws": Decimal("1"),
            "seniority": Decimal("1"),
            "overscale": Decimal("1"),
            "title": Decimal("1"),
        }
        if not scenario_id or offset == 0:
            return factors
        scenario = self.scenarios[scenario_id]
        for label in ["year_plus_1", "year_plus_2"][:offset]:
            step = scenario[label]
            factors["mws"] *= Decimal("1") + dec(step["mws_growth"])
            factors["seniority"] *= Decimal("1") + dec(step["seniority_growth"])
            factors["overscale"] *= Decimal("1") + dec(step["overscale_growth"])
            factors["title"] *= dec(step["title_pct_multiplier"])
        return factors

    def calculate(
        self, ensemble_id: str, offset: int = 0, scenario_id: str | None = None
    ) -> tuple[dict[str, Decimal], dict[str, Decimal], Decimal]:
        rows = self.roster(ensemble_id)
        pay_types = self.rate["pay_types"]
        pay_totals = {pay_type: ZERO for pay_type in pay_types}
        quarter_totals = {quarter: ZERO for quarter in self.rate["quarter_weeks"]}
        factors = self.scenario_factors(scenario_id, offset)
        minimum_weekly = dec(self.rate["minimum_weekly_scale"]) * factors["mws"]
        title_pct = {
            title: dec(value) for title, value in self.rate["title_premium_pct"].items()
        }

        for row in rows:
            for quarter, weeks_value in row["weeks_by_quarter"].items():
                weeks = dec(weeks_value)
                mws = minimum_weekly * weeks
                if row.get("combined_overscale_includes_title"):
                    title = ZERO
                else:
                    title = (
                        minimum_weekly
                        * title_pct.get(row.get("title"), ZERO)
                        * factors["title"]
                        * weeks
                    )
                seniority = (
                    self.seniority_weekly(int(row["years_of_service"]) + offset)
                    * factors["seniority"]
                    * weeks
                )
                overscale = dec(row["overscale_weekly"]) * factors["overscale"] * weeks
                values = {
                    "Minimum Weekly Scale": mws,
                    "Titled Position Premium": title,
                    "Seniority": seniority,
                    "Overscale": overscale,
                }
                for pay_type, amount in values.items():
                    pay_totals[pay_type] += amount
                    quarter_totals[quarter] += amount

        return pay_totals, quarter_totals, sum(pay_totals.values(), ZERO)

    def treatment_counts(self, ensemble_id: str) -> dict[str, int]:
        rows = self.roster(ensemble_id)
        standard_weeks = self.rate["quarter_weeks"]
        return {
            "combined_overscale_employee_count": sum(
                1 for row in rows if row.get("combined_overscale_includes_title")
            ),
            "partial_quarter_employee_count": sum(
                1 for row in rows if row["weeks_by_quarter"] != standard_weeks
            ),
        }


def rounded_pay_totals(pay_types: list[str], totals: dict[str, Decimal]) -> dict[str, float]:
    return {pay_type: money(totals[pay_type]) for pay_type in pay_types}


def rounded_quarters(totals: dict[str, Decimal]) -> dict[str, float]:
    return {quarter: money(totals[quarter]) for quarter in sorted(totals)}


def annual_from_rounded_quarters(totals: dict[str, Decimal]) -> Decimal:
    return sum((dec(money(totals[quarter])) for quarter in sorted(totals)), ZERO)


def solve_comp_current(base_url: str, memo: dict[str, Any]) -> dict[str, Any]:
    comp = CompensationData(base_url)
    ensemble_id = memo["ensemble_id"]
    pay_types = comp.rate["pay_types"]
    pay_totals, quarter_totals, _annual_total = comp.calculate(ensemble_id)
    counts = comp.treatment_counts(ensemble_id)

    return {
        "ensemble_id": ensemble_id,
        "current_year": int(comp.rate["current_year"]),
        "roster_count": len(comp.roster(ensemble_id)),
        "pay_types": pay_types,
        "quarter_totals": rounded_quarters(quarter_totals),
        "annual_pay_type_totals": rounded_pay_totals(pay_types, pay_totals),
        "annual_total": money(annual_from_rounded_quarters(quarter_totals)),
        "largest_pay_type": max(pay_types, key=lambda pay_type: (pay_totals[pay_type], -pay_types.index(pay_type))),
        **counts,
    }


def solve_comp_forecast(base_url: str, memo: dict[str, Any]) -> dict[str, Any]:
    comp = CompensationData(base_url, include_scenarios=True)
    ensemble_id = memo["ensemble_id"]
    scenario_id = memo["scenario_id"]
    pay_types = comp.rate["pay_types"]
    current_pay, current_quarters, _current_total = comp.calculate(ensemble_id, 0, scenario_id)
    y1_pay, y1_quarters, _y1_total = comp.calculate(ensemble_id, 1, scenario_id)
    y2_pay, y2_quarters, y2_total = comp.calculate(ensemble_id, 2, scenario_id)
    counts = comp.treatment_counts(ensemble_id)
    current_total = annual_from_rounded_quarters(current_quarters)
    y1_total = annual_from_rounded_quarters(y1_quarters)
    y2_total = annual_from_rounded_quarters(y2_quarters)

    def growth_for_pay_type(pay_type: str) -> Decimal:
        start = current_pay[pay_type]
        if start == 0:
            return Decimal("Infinity") if y2_pay[pay_type] > 0 else ZERO
        return (y2_pay[pay_type] - start) / start

    largest_growth_pay_type = max(
        pay_types, key=lambda pay_type: (growth_for_pay_type(pay_type), -pay_types.index(pay_type))
    )

    return {
        "ensemble_id": ensemble_id,
        "scenario_id": scenario_id,
        "annual_totals": {
            "current": money(current_total),
            "year_plus_1": money(y1_total),
            "year_plus_2": money(y2_total),
        },
        "growth_rates": {
            "year_plus_1_vs_current": ratio(pct(y1_total - current_total, current_total)),
            "year_plus_2_vs_year_plus_1": ratio(pct(y2_total - y1_total, y1_total)),
        },
        "year_plus_2_quarter_totals": rounded_quarters(y2_quarters),
        "year_plus_2_pay_type_totals": rounded_pay_totals(pay_types, y2_pay),
        "largest_growth_pay_type": largest_growth_pay_type,
        **counts,
    }


def payroll_service_amount(service: dict[str, Any], rates: dict[str, Any]) -> tuple[str, Decimal]:
    service_type = service["service_type"]
    service_rates = rates["service_rates"]
    if service_type == "Rehearsal":
        amount = dec(service_rates[service_type]) * max(dec(service["duration_hours"]), Decimal("3"))
        return "rehearsal", amount
    if service_type == "Performance":
        return "performance", dec(service_rates[service_type])
    if service_type == "Audit":
        return "audit", dec(service_rates[service_type])
    if "Sound Check" in service_type:
        return "sound_check", dec(service_rates[service_type])
    raise ValueError(f"Unhandled service type: {service_type}")


def payroll_conflict_flags(production: dict[str, Any], rates: dict[str, Any]) -> list[str]:
    flags: set[str] = set()
    thresholds = rates["conflict_thresholds"]
    earliest_rehearsal = time_minutes(thresholds["rehearsal_earliest_start"])
    latest_rehearsal = time_minutes(thresholds["rehearsal_latest_end"])
    limits = {key: dec(value) for key, value in rates["service_time_limits"].items()}

    for service in production["schedule"]:
        service_type = service["service_type"]
        duration = dec(service["duration_hours"])
        if service_type == "Rehearsal":
            if time_minutes(service["start_time"]) < earliest_rehearsal:
                flags.add("REHEARSAL_EARLY_START")
            if time_minutes(service["end_time"]) > latest_rehearsal:
                flags.add("REHEARSAL_LATE_END")
        if service_type in limits and duration > limits[service_type]:
            flags.add("SERVICE_OVER_TIME_LIMIT")
        if "Sound Check" in service_type and service_type in limits and duration != limits[service_type]:
            flags.add("SOUND_CHECK_DURATION_MISMATCH")

    return sorted(flags)


def solve_payroll(base_url: str, memo: dict[str, Any]) -> dict[str, Any]:
    rates = fetch_json(base_url, "/api/payroll/rate-book")
    productions = fetch_json(base_url, "/api/payroll/productions")
    production_id = memo["production_id"]
    production = next(row for row in productions if row["production_id"] == production_id)
    service_by_id = {row["service_id"]: row for row in production["schedule"]}
    service_counts = dict(sorted(Counter(row["service_type"] for row in production["schedule"]).items()))
    premium_pct = {key: dec(value) for key, value in rates["premium_pct"].items()}
    performance_rate = dec(rates["service_rates"]["Performance"])

    per_musician = []
    category_totals: defaultdict[str, Decimal] = defaultdict(Decimal)

    for musician in sorted(production["roster"], key=lambda row: row["musician_id"]):
        categories: defaultdict[str, Decimal] = defaultdict(Decimal)
        base_pay = ZERO
        performance_count = 0
        for service_id in musician["assigned_service_ids"]:
            service = service_by_id[service_id]
            category, amount = payroll_service_amount(service, rates)
            categories[category] += amount
            base_pay += amount
            if service["service_type"] == "Performance":
                performance_count += 1

        adjusted_base = base_pay
        if musician.get("substitute"):
            substitute_adjustment = max(0, 6 - performance_count) * performance_rate
            if substitute_adjustment:
                categories["performance"] += substitute_adjustment
                categories["substitute_adjustment"] += substitute_adjustment
                adjusted_base += substitute_adjustment

        total_premium_pct = ZERO
        if musician.get("principal") or musician.get("lead"):
            total_premium_pct += premium_pct["principal_or_lead"]
        if musician.get("quartet"):
            total_premium_pct += premium_pct["quartet"]
        if musician.get("electronic"):
            total_premium_pct += premium_pct["electronic"]
        premium = adjusted_base * total_premium_pct
        if premium:
            categories["premium"] += premium

        doubles = int(musician.get("doubles") or 0)
        if doubles > 0:
            double_pct = premium_pct["first_double"] + premium_pct["additional_double"] * (doubles - 1)
            categories["doubles"] += adjusted_base * double_pct

        if musician.get("vacation_eligible"):
            categories["vacation"] += (
                adjusted_base + categories["premium"] + categories["doubles"]
            ) * premium_pct["vacation"]

        if not musician.get("substitute"):
            guarantee = dec(rates["weekly_guarantee"]) - base_pay
            if guarantee > 0:
                categories["guarantee_adjustment"] += guarantee

        musician_total = sum(categories.values(), ZERO)
        for category, amount in categories.items():
            category_totals[category] += amount

        per_musician.append(
            {
                "musician_id": musician["musician_id"],
                "name": musician["name"],
                "total": money(musician_total),
                "categories": {
                    key: money(categories[key]) for key in sorted(categories) if categories[key] != 0
                },
            }
        )

    standard_categories = [
        "performance",
        "audit",
        "rehearsal",
        "sound_check",
        "premium",
        "doubles",
        "vacation",
        "guarantee_adjustment",
    ]
    output_category_keys = sorted(
        set(standard_categories)
        | {key for key, value in category_totals.items() if value != 0}
    )
    weekly_total = sum((category_totals[key] for key in output_category_keys), ZERO)
    top_paid = sorted(
        per_musician, key=lambda row: (-dec(row["total"]), row["musician_id"])
    )[0]["musician_id"]

    return {
        "production_id": production_id,
        "service_counts": service_counts,
        "category_totals": {
            key: money(category_totals[key]) for key in output_category_keys
        },
        "weekly_total": money(weekly_total),
        "conflict_flags": payroll_conflict_flags(production, rates),
        "per_musician": per_musician,
        "top_paid_musician_id": top_paid,
    }


def solve(input_dir: Path, base_url: str) -> dict[str, Any]:
    memo = load_json(input_dir / "payloads" / "request_memo.json")
    template_path = input_dir / "payloads" / "answer_template.json"
    template = load_json(template_path) if template_path.exists() else {}

    if "production_id" in memo:
        return solve_payroll(base_url, memo)
    if "target_region_id" in memo:
        return solve_regional(base_url, memo)
    if "target_branch_id" in memo:
        return solve_branch_close(base_url, memo, template)
    if "ensemble_id" in memo and "scenario_id" in memo:
        return solve_comp_forecast(base_url, memo)
    if "ensemble_id" in memo:
        return solve_comp_current(base_url, memo)
    raise SystemExit("Unsupported Crescent Finance Ops request memo shape")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_path", help="Task input directory, or its parent task directory")
    parser.add_argument("--base-url", help="Override the Finance Ops environment base URL")
    args = parser.parse_args()

    input_dir = find_input_dir(Path(args.input_path).resolve())
    env_payload = load_json(input_dir / "payloads" / "environment_access.json")
    base_url = usable_base_url(env_payload.get("base_url"), args.base_url)
    result = solve(input_dir, base_url)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
