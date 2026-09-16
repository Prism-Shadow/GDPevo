#!/usr/bin/env python3
"""Deterministic solver for Crescent Finance Ops reporting tasks."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP, getcontext
from pathlib import Path
from typing import Any


getcontext().prec = 28
MONEY_PLACES = Decimal("0.01")
RATIO_PLACES = Decimal("0.0001")
ZERO = Decimal("0")


def dec(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def qmoney_dec(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def qratio_dec(value: Decimal) -> Decimal:
    return value.quantize(RATIO_PLACES, rounding=ROUND_HALF_UP)


def money(value: Decimal) -> float:
    return float(qmoney_dec(value))


def ratio(value: Decimal) -> float:
    return float(qratio_dec(value))


def safe_div(numerator: Decimal, denominator: Decimal) -> Decimal:
    return ZERO if denominator == ZERO else numerator / denominator


def period_number(period: str) -> int:
    return int(period[1:])


def time_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def find_input_dir(path: Path) -> Path:
    path = path.resolve()
    if (path / "payloads").is_dir():
        return path
    if (path / "input" / "payloads").is_dir():
        return path / "input"
    if path.name == "payloads" and path.is_dir():
        return path.parent
    raise SystemExit(f"Cannot find payloads directory under {path}")


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get(self, endpoint: str) -> Any:
        url = f"{self.base_url}{endpoint}"
        with urllib.request.urlopen(url, timeout=20) as response:
            return json.load(response)


class FinanceOpsSolver:
    def __init__(self, input_dir: Path) -> None:
        self.input_dir = input_dir
        payloads = input_dir / "payloads"
        self.memo = self._read_json(payloads / "request_memo.json")
        self.template = self._read_json(payloads / "answer_template.json")
        env = self._read_json(payloads / "environment_access.json")
        self.api = ApiClient(self._resolve_base_url(env))

    @staticmethod
    def _read_json(path: Path) -> Any:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _resolve_base_url(env: dict[str, Any]) -> str:
        base_url = str(env.get("base_url", "")).strip()
        if not base_url or base_url.startswith("<"):
            base_url = (
                os.environ.get("TASK_ENV_BASE_URL")
                or os.environ.get("FINANCE_OPS_BASE_URL")
                or "http://task-env:9009/"
            )
        return base_url

    def solve(self) -> dict[str, Any]:
        if "production_id" in self.memo:
            return self.solve_payroll()
        if "scenario_id" in self.memo:
            return self.solve_compensation_forecast()
        if "ensemble_id" in self.memo:
            return self.solve_compensation_current()
        if "target_region_id" in self.memo:
            return self.solve_regional_finance()
        if "target_branch_id" in self.memo:
            return self.solve_branch_close()
        raise SystemExit("Unrecognized request memo shape")

    def finance_data(self) -> dict[str, Any]:
        if not hasattr(self, "_finance_data"):
            accounts = self.api.get("/api/finance/accounts")
            self._finance_data = {
                "branches": self.api.get("/api/finance/branches"),
                "period_map": self.api.get("/api/finance/period-map"),
                "accounts": accounts,
                "records": self.api.get("/api/finance/records"),
                "account_category": {row["account"]: row["category"] for row in accounts},
            }
        return self._finance_data

    def periods_for_year(self, fiscal_year: int) -> list[str]:
        data = self.finance_data()
        periods = [row["period"] for row in data["period_map"] if row["fiscal_year"] == fiscal_year]
        return sorted(periods, key=period_number)

    def fiscal_year_for_period(self, period: str) -> int:
        for row in self.finance_data()["period_map"]:
            if row["period"] == period:
                return int(row["fiscal_year"])
        raise SystemExit(f"Unknown period: {period}")

    def branch_ids_for_region(self, region_id: str) -> list[str]:
        branches = self.finance_data()["branches"]
        return sorted(row["branch_id"] for row in branches if row["region_id"] == region_id)

    def branch_by_id(self, branch_id: str) -> dict[str, Any]:
        for row in self.finance_data()["branches"]:
            if row["branch_id"] == branch_id:
                return row
        raise SystemExit(f"Unknown branch_id: {branch_id}")

    def finance_statement(self, branch_ids: str | list[str], periods: list[str]) -> dict[str, Any]:
        if isinstance(branch_ids, str):
            branch_set = {branch_ids}
        else:
            branch_set = set(branch_ids)
        data = self.finance_data()
        category_by_account = data["account_category"]
        category_totals: dict[str, Decimal] = defaultdict(Decimal)
        operating: dict[str, Decimal] = defaultdict(Decimal)

        for record in data["records"]:
            if record["branch_id"] not in branch_set:
                continue
            account = record["account"]
            amount = sum(dec(record["values"].get(period, 0)) for period in periods)
            category = category_by_account[account]
            if category == "operating":
                operating[account] += amount
            else:
                category_totals[category] += amount

        revenue = category_totals["revenue"]
        cogs = category_totals["cogs"]
        gross_margin = revenue - cogs
        sga = category_totals["sga"]
        allocations = category_totals["allocations"]
        ebitda = gross_margin - sga - allocations
        return {
            "revenue": revenue,
            "cogs": cogs,
            "gross_margin": gross_margin,
            "sga": sga,
            "allocations": allocations,
            "ebitda": ebitda,
            "operating": dict(operating),
        }

    def rounded_statement(self, statement: dict[str, Any], fields: list[str]) -> dict[str, Any]:
        return {field: money(statement[field]) for field in fields}

    def all_region_ids(self) -> list[str]:
        return sorted({row["region_id"] for row in self.finance_data()["branches"]})

    @staticmethod
    def rank_desc(items: list[tuple[str, Decimal]], target_id: str) -> int:
        ordered = sorted(items, key=lambda item: (-item[1], item[0]))
        return [item_id for item_id, _ in ordered].index(target_id) + 1

    def solve_branch_close(self) -> dict[str, Any]:
        memo = self.memo
        branch_id = memo["target_branch_id"]
        branch = self.branch_by_id(branch_id)
        current_period = memo["close_period"]
        prior_period = memo.get("prior_period") or f"M{period_number(current_period) - 1}"
        current_year = self.fiscal_year_for_period(current_period)
        prior_year = max(
            year
            for year in {row["fiscal_year"] for row in self.finance_data()["period_map"]}
            if year < current_year
        )
        current_year_periods = self.periods_for_year(current_year)
        prior_year_periods = self.periods_for_year(prior_year)

        current_month_statement = self.finance_statement(branch_id, [current_period])
        current_period_revenue = current_month_statement["revenue"]
        prior_period_revenue = self.finance_statement(branch_id, [prior_period])["revenue"]
        revenue_variance = current_period_revenue - prior_period_revenue

        fy_current = self.finance_statement(branch_id, current_year_periods)
        fy_prior = self.finance_statement(branch_id, prior_year_periods)
        fy_current_payload = self.rounded_statement(
            fy_current, ["revenue", "cogs", "gross_margin", "sga", "allocations", "ebitda"]
        )
        fy_current_payload["ebitda_margin"] = ratio(safe_div(fy_current["ebitda"], fy_current["revenue"]))
        fy_current_payload["arpu"] = money(
            safe_div(fy_current["revenue"], fy_current["operating"].get("active_customers", ZERO))
        )
        fy_current_payload["sales_per_labor_headcount"] = money(
            safe_div(fy_current["revenue"], fy_current["operating"].get("labor_headcount", ZERO))
        )

        region_id = branch["region_id"]
        region_branch_ids = self.branch_ids_for_region(region_id)
        region_ebitda = self.finance_statement(region_branch_ids, current_year_periods)["ebitda"]
        region_rank_items = [
            (
                candidate_region,
                self.finance_statement(self.branch_ids_for_region(candidate_region), current_year_periods)["ebitda"],
            )
            for candidate_region in self.all_region_ids()
        ]

        branch_growth_items = []
        branch_arpu_items = []
        for candidate in self.finance_data()["branches"]:
            candidate_id = candidate["branch_id"]
            candidate_current = self.finance_statement(candidate_id, current_year_periods)
            candidate_prior = self.finance_statement(candidate_id, prior_year_periods)
            branch_growth_items.append(
                (
                    candidate_id,
                    safe_div(
                        candidate_current["revenue"] - candidate_prior["revenue"],
                        candidate_prior["revenue"],
                    ),
                )
            )
            branch_arpu_items.append(
                (
                    candidate_id,
                    safe_div(
                        candidate_current["revenue"],
                        candidate_current["operating"].get("active_customers", ZERO),
                    ),
                )
            )

        period_convention: dict[str, Any] = {}
        periods_by_year: dict[int, list[str]] = defaultdict(list)
        for row in self.finance_data()["period_map"]:
            periods_by_year[int(row["fiscal_year"])].append(row["period"])
        for fiscal_year in sorted(periods_by_year):
            year_periods = sorted(periods_by_year[fiscal_year], key=period_number)
            period_convention[f"{year_periods[0]}_to_{year_periods[-1]}"] = f"FY{fiscal_year}"
        period_convention["current_month"] = current_period
        period_convention["prior_month"] = prior_period

        result = {
            "target_branch_id": branch_id,
            "target_branch_name": branch["branch_name"],
            "period_convention": period_convention,
            f"{current_period.lower()}_income_statement": self.rounded_statement(
                current_month_statement,
                ["revenue", "cogs", "gross_margin", "sga", "allocations", "ebitda"],
            ),
            "mom_revenue_variance": {
                "amount": money(revenue_variance),
                "pct": ratio(safe_div(revenue_variance, prior_period_revenue)),
            },
            f"fy{current_year}_vs_fy{prior_year}": {
                f"fy{current_year}": fy_current_payload,
                "revenue_growth_pct": ratio(
                    safe_div(fy_current["revenue"] - fy_prior["revenue"], fy_prior["revenue"])
                ),
                "ebitda_growth_pct": ratio(
                    safe_div(fy_current["ebitda"] - fy_prior["ebitda"], fy_prior["ebitda"])
                ),
            },
            "region_context": {
                "region_id": region_id,
                "branch_ids": region_branch_ids,
                "fy2025_ebitda" if current_year == 2025 else f"fy{current_year}_ebitda": money(region_ebitda),
                "ebitda_rank_desc": self.rank_desc(region_rank_items, region_id),
            },
            "branch_rankings": {
                "sales_growth_rank_desc": self.rank_desc(branch_growth_items, branch_id),
                "top_sales_growth_branch_id": sorted(branch_growth_items, key=lambda item: (-item[1], item[0]))[0][0],
                "top_arpu_branch_id": sorted(branch_arpu_items, key=lambda item: (-item[1], item[0]))[0][0],
            },
        }
        return self.filter_top_level(result)

    def solve_regional_finance(self) -> dict[str, Any]:
        memo = self.memo
        region_id = memo["target_region_id"]
        branch_ids = self.branch_ids_for_region(region_id)
        years = [int(year) for year in memo.get("requested_comparison_years", [])]
        if not years:
            years = sorted({row["fiscal_year"] for row in self.finance_data()["period_map"]})
        first_year, latest_year = min(years), max(years)
        first_statement = self.finance_statement(branch_ids, self.periods_for_year(first_year))
        latest_statement = self.finance_statement(branch_ids, self.periods_for_year(latest_year))

        result: dict[str, Any] = {"region_id": region_id, "branch_ids": branch_ids}
        field_types = self.template.get("field_types", {})
        for year in sorted(years):
            key = f"fy{year}"
            statement = self.finance_statement(branch_ids, self.periods_for_year(year))
            requested_fields = list(field_types.get(key, {}).keys())
            if not requested_fields:
                requested_fields = ["revenue", "sga", "allocations", "ebitda"]
            year_payload: dict[str, Any] = {}
            for field in requested_fields:
                if field == "ebitda_margin":
                    year_payload[field] = ratio(safe_div(statement["ebitda"], statement["revenue"]))
                elif field == "sales_per_labor_headcount":
                    year_payload[field] = money(
                        safe_div(statement["revenue"], statement["operating"].get("labor_headcount", ZERO))
                    )
                else:
                    year_payload[field] = money(statement[field])
            result[key] = year_payload

        branch_ebitda_items = [
            (branch_id, self.finance_statement(branch_id, self.periods_for_year(latest_year))["ebitda"])
            for branch_id in branch_ids
        ]
        result["revenue_growth_pct"] = ratio(
            safe_div(latest_statement["revenue"] - first_statement["revenue"], first_statement["revenue"])
        )
        result["top_ebitda_branch_id"] = sorted(branch_ebitda_items, key=lambda item: (-item[1], item[0]))[0][0]
        result["bottom_ebitda_branch_id"] = sorted(branch_ebitda_items, key=lambda item: (item[1], item[0]))[0][0]
        sum_branch_ebitda = sum((item[1] for item in branch_ebitda_items), ZERO)
        result["region_reconciliation_variance"] = money(latest_statement["ebitda"] - sum_branch_ebitda)
        return self.filter_top_level(result)

    def compensation_data(self) -> dict[str, Any]:
        if not hasattr(self, "_compensation_data"):
            self._compensation_data = {
                "rate_book": self.api.get("/api/compensation/rate-book"),
                "rosters": self.api.get("/api/compensation/rosters"),
            }
        return self._compensation_data

    def scenarios(self) -> dict[str, Any]:
        if not hasattr(self, "_scenarios"):
            self._scenarios = self.api.get("/api/compensation/scenarios")
        return self._scenarios

    def roster_rows(self, ensemble_id: str) -> list[dict[str, Any]]:
        return [row for row in self.compensation_data()["rosters"] if row["ensemble_id"] == ensemble_id]

    def seniority_weekly(self, years: int) -> Decimal:
        for band in self.compensation_data()["rate_book"]["seniority_weekly"]:
            if years >= band["min_years"] and (band["max_years"] is None or years <= band["max_years"]):
                return dec(band["weekly_amount"])
        raise SystemExit(f"No seniority band for {years} years")

    def compensation_counts(self, ensemble_id: str) -> dict[str, int]:
        rows = self.roster_rows(ensemble_id)
        default_weeks = self.compensation_data()["rate_book"]["quarter_weeks"]
        return {
            "combined_overscale_employee_count": sum(
                1 for row in rows if row.get("combined_overscale_includes_title")
            ),
            "partial_quarter_employee_count": sum(
                1 for row in rows if row.get("weeks_by_quarter", {}) != default_weeks
            ),
        }

    def compensation_totals(
        self,
        ensemble_id: str,
        scenario: dict[str, Any] | None = None,
        year_offset: int = 0,
    ) -> dict[str, Any]:
        rate_book = self.compensation_data()["rate_book"]
        pay_types = rate_book["pay_types"]
        mws_factor = Decimal("1")
        seniority_factor = Decimal("1")
        overscale_factor = Decimal("1")
        title_multiplier = Decimal("1")
        for offset in range(1, year_offset + 1):
            if scenario is None:
                break
            settings = scenario[f"year_plus_{offset}"]
            mws_factor *= Decimal("1") + dec(settings["mws_growth"])
            seniority_factor *= Decimal("1") + dec(settings["seniority_growth"])
            overscale_factor *= Decimal("1") + dec(settings["overscale_growth"])
            title_multiplier = dec(settings["title_pct_multiplier"])

        minimum_scale = dec(rate_book["minimum_weekly_scale"]) * mws_factor
        pay_type_totals = {pay_type: ZERO for pay_type in pay_types}
        quarter_totals = {quarter: ZERO for quarter in rate_book["quarter_weeks"].keys()}

        for row in self.roster_rows(ensemble_id):
            title_pct = dec(rate_book["title_premium_pct"].get(row.get("title"), 0)) * title_multiplier
            for quarter in quarter_totals.keys():
                weeks = dec(row.get("weeks_by_quarter", {}).get(quarter, 0))
                components = {
                    "Minimum Weekly Scale": minimum_scale * weeks,
                    "Titled Position Premium": (
                        ZERO
                        if row.get("combined_overscale_includes_title")
                        else minimum_scale * title_pct * weeks
                    ),
                    "Seniority": self.seniority_weekly(int(row["years_of_service"]) + year_offset)
                    * seniority_factor
                    * weeks,
                    "Overscale": dec(row.get("overscale_weekly", 0)) * overscale_factor * weeks,
                }
                for pay_type, amount in components.items():
                    pay_type_totals[pay_type] += amount
                    quarter_totals[quarter] += amount

        annual_from_quarters = sum((qmoney_dec(amount) for amount in quarter_totals.values()), ZERO)
        return {
            "pay_type_totals": pay_type_totals,
            "quarter_totals": quarter_totals,
            "annual_total": annual_from_quarters,
        }

    def solve_compensation_current(self) -> dict[str, Any]:
        ensemble_id = self.memo["ensemble_id"]
        rate_book = self.compensation_data()["rate_book"]
        totals = self.compensation_totals(ensemble_id)
        pay_types = rate_book["pay_types"]
        largest_pay_type = sorted(
            ((pay_type, totals["pay_type_totals"][pay_type]) for pay_type in pay_types),
            key=lambda item: (-item[1], pay_types.index(item[0])),
        )[0][0]
        result = {
            "ensemble_id": ensemble_id,
            "current_year": int(rate_book["current_year"]),
            "roster_count": len(self.roster_rows(ensemble_id)),
            "pay_types": pay_types,
            "quarter_totals": {quarter: money(amount) for quarter, amount in totals["quarter_totals"].items()},
            "annual_pay_type_totals": {
                pay_type: money(totals["pay_type_totals"][pay_type]) for pay_type in pay_types
            },
            "annual_total": float(totals["annual_total"]),
            "largest_pay_type": largest_pay_type,
            **self.compensation_counts(ensemble_id),
        }
        return self.filter_top_level(result)

    def solve_compensation_forecast(self) -> dict[str, Any]:
        ensemble_id = self.memo["ensemble_id"]
        scenario_id = self.memo["scenario_id"]
        scenario = self.scenarios()[scenario_id]
        pay_types = self.compensation_data()["rate_book"]["pay_types"]
        current = self.compensation_totals(ensemble_id)
        year_plus_1 = self.compensation_totals(ensemble_id, scenario, 1)
        year_plus_2 = self.compensation_totals(ensemble_id, scenario, 2)

        growth_items = []
        for pay_type in pay_types:
            current_amount = current["pay_type_totals"][pay_type]
            year_plus_2_amount = year_plus_2["pay_type_totals"][pay_type]
            growth_items.append((pay_type, safe_div(year_plus_2_amount - current_amount, current_amount)))
        largest_growth_pay_type = sorted(
            growth_items,
            key=lambda item: (-item[1], pay_types.index(item[0])),
        )[0][0]

        result = {
            "ensemble_id": ensemble_id,
            "scenario_id": scenario_id,
            "annual_totals": {
                "current": float(current["annual_total"]),
                "year_plus_1": float(year_plus_1["annual_total"]),
                "year_plus_2": float(year_plus_2["annual_total"]),
            },
            "growth_rates": {
                "year_plus_1_vs_current": ratio(
                    safe_div(year_plus_1["annual_total"] - current["annual_total"], current["annual_total"])
                ),
                "year_plus_2_vs_year_plus_1": ratio(
                    safe_div(
                        year_plus_2["annual_total"] - year_plus_1["annual_total"],
                        year_plus_1["annual_total"],
                    )
                ),
            },
            "year_plus_2_quarter_totals": {
                quarter: money(amount) for quarter, amount in year_plus_2["quarter_totals"].items()
            },
            "year_plus_2_pay_type_totals": {
                pay_type: money(year_plus_2["pay_type_totals"][pay_type]) for pay_type in pay_types
            },
            "largest_growth_pay_type": largest_growth_pay_type,
            **self.compensation_counts(ensemble_id),
        }
        return self.filter_top_level(result)

    def payroll_data(self) -> dict[str, Any]:
        if not hasattr(self, "_payroll_data"):
            self._payroll_data = {
                "rate_book": self.api.get("/api/payroll/rate-book"),
                "productions": self.api.get("/api/payroll/productions"),
            }
        return self._payroll_data

    def production(self, production_id: str) -> dict[str, Any]:
        for production in self.payroll_data()["productions"]:
            if production["production_id"] == production_id:
                return production
        raise SystemExit(f"Unknown production_id: {production_id}")

    def payroll_service_amount(self, service: dict[str, Any]) -> Decimal:
        rate_book = self.payroll_data()["rate_book"]
        service_type = service["service_type"]
        rate = dec(rate_book["service_rates"][service_type])
        if service_type == "Rehearsal":
            return rate * max(dec(service["duration_hours"]), Decimal("3"))
        return rate

    @staticmethod
    def payroll_category_for_service(service_type: str) -> str:
        if service_type == "Performance":
            return "performance"
        if service_type == "Audit":
            return "audit"
        if service_type == "Rehearsal":
            return "rehearsal"
        if "Sound Check" in service_type:
            return "sound_check"
        return service_type.lower().replace(" ", "_")

    def musician_payroll(
        self,
        musician: dict[str, Any],
        services_by_id: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, Decimal], Decimal]:
        rate_book = self.payroll_data()["rate_book"]
        premium_pct = rate_book["premium_pct"]
        categories: dict[str, Decimal] = defaultdict(Decimal)
        base_service_pay = ZERO

        for service_id in musician.get("assigned_service_ids", []):
            service = services_by_id[service_id]
            amount = self.payroll_service_amount(service)
            categories[self.payroll_category_for_service(service["service_type"])] += amount
            base_service_pay += amount

        if musician.get("substitute"):
            substitute_adjustment = dec(rate_book["service_rates"]["Performance"]) * Decimal("2")
            categories["performance"] += substitute_adjustment
            categories["substitute_adjustment"] += substitute_adjustment
            base_service_pay += substitute_adjustment

        premium_rate = ZERO
        if musician.get("principal") or musician.get("lead"):
            premium_rate += dec(premium_pct["principal_or_lead"])
        if musician.get("quartet"):
            premium_rate += dec(premium_pct["quartet"])
        if musician.get("electronic"):
            premium_rate += dec(premium_pct["electronic"])
        premium_amount = base_service_pay * premium_rate
        if premium_amount:
            categories["premium"] += premium_amount

        doubles_amount = ZERO
        doubles = int(musician.get("doubles", 0))
        if doubles > 0:
            doubles_rate = dec(premium_pct["first_double"]) + dec(premium_pct["additional_double"]) * (
                doubles - 1
            )
            doubles_amount = base_service_pay * doubles_rate
            categories["doubles"] += doubles_amount

        if not musician.get("substitute") and base_service_pay < dec(rate_book["weekly_guarantee"]):
            categories["guarantee_adjustment"] += dec(rate_book["weekly_guarantee"]) - base_service_pay

        if musician.get("vacation_eligible"):
            categories["vacation"] += (
                base_service_pay + premium_amount + doubles_amount
            ) * dec(premium_pct["vacation"])

        total = sum(categories.values(), ZERO)
        return dict(categories), total

    def payroll_conflict_flags(self, production: dict[str, Any]) -> list[str]:
        rate_book = self.payroll_data()["rate_book"]
        thresholds = rate_book["conflict_thresholds"]
        flags: set[str] = set()
        rehearsal_earliest = time_minutes(thresholds["rehearsal_earliest_start"])
        rehearsal_latest = time_minutes(thresholds["rehearsal_latest_end"])

        for service in production["schedule"]:
            service_type = service["service_type"]
            duration = dec(service["duration_hours"])
            limit = dec(rate_book["service_time_limits"][service_type])
            if duration > limit:
                flags.add("SERVICE_OVER_TIME_LIMIT")
            if "Sound Check" in service_type and duration != limit:
                flags.add("SOUND_CHECK_DURATION_MISMATCH")
            if service_type == "Rehearsal":
                if time_minutes(service["start_time"]) < rehearsal_earliest:
                    flags.add("REHEARSAL_EARLY_START")
                if time_minutes(service["end_time"]) > rehearsal_latest:
                    flags.add("REHEARSAL_LATE_END")
        return sorted(flags)

    def solve_payroll(self) -> dict[str, Any]:
        production_id = self.memo["production_id"]
        production = self.production(production_id)
        services_by_id = {service["service_id"]: service for service in production["schedule"]}
        service_counts = dict(sorted(Counter(service["service_type"] for service in production["schedule"]).items()))

        category_totals: dict[str, Decimal] = defaultdict(Decimal)
        per_musician = []
        top_paid: tuple[str, Decimal] | None = None
        for musician in sorted(production["roster"], key=lambda row: row["musician_id"]):
            categories, total = self.musician_payroll(musician, services_by_id)
            for category, amount in categories.items():
                category_totals[category] += amount
            if top_paid is None or total > top_paid[1] or (total == top_paid[1] and musician["musician_id"] < top_paid[0]):
                top_paid = (musician["musician_id"], total)
            per_musician.append(
                {
                    "musician_id": musician["musician_id"],
                    "name": musician["name"],
                    "total": money(total),
                    "categories": {
                        category: money(amount)
                        for category, amount in sorted(categories.items())
                        if qmoney_dec(amount) != ZERO
                    },
                }
            )

        category_template = self.template.get("field_types", {}).get("category_totals", {})
        if category_template:
            rounded_category_totals = {}
            for category, field_type in sorted(category_template.items()):
                amount = category_totals.get(category, ZERO)
                when_applicable = "when applicable" in str(field_type)
                if qmoney_dec(amount) != ZERO or not when_applicable:
                    rounded_category_totals[category] = money(amount)
        else:
            rounded_category_totals = {
                category: money(amount)
                for category, amount in sorted(category_totals.items())
                if qmoney_dec(amount) != ZERO
            }
        weekly_total = sum(category_totals.values(), ZERO)
        result = {
            "production_id": production_id,
            "service_counts": service_counts,
            "category_totals": rounded_category_totals,
            "weekly_total": money(weekly_total),
            "conflict_flags": self.payroll_conflict_flags(production),
            "per_musician": per_musician,
            "top_paid_musician_id": top_paid[0] if top_paid else None,
        }
        return self.filter_top_level(result)

    def filter_top_level(self, result: dict[str, Any]) -> dict[str, Any]:
        required = self.template.get("required_top_level_keys")
        if not required:
            return result
        filtered: dict[str, Any] = {}
        for key in required:
            if key in result:
                filtered[key] = result[key]
                continue
            replacement = self.find_compatible_key(key, result)
            if replacement is not None:
                filtered[key] = result[replacement]
                continue
            raise SystemExit(f"Could not produce required key: {key}")
        return filtered

    @staticmethod
    def find_compatible_key(required_key: str, result: dict[str, Any]) -> str | None:
        if required_key.endswith("_income_statement"):
            matches = [key for key in result if key.endswith("_income_statement")]
            return matches[0] if len(matches) == 1 else None
        if required_key.startswith("fy") and "_vs_fy" in required_key:
            matches = [key for key in result if key.startswith("fy") and "_vs_fy" in key]
            return matches[0] if len(matches) == 1 else None
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Solve Crescent Finance Ops reporting tasks.")
    parser.add_argument("input_dir", nargs="?", default=".", help="Task input directory or task root")
    args = parser.parse_args()
    solver = FinanceOpsSolver(find_input_dir(Path(args.input_dir)))
    result = solver.solve()
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
