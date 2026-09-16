#!/usr/bin/env python3
"""Compute Crescent Finance Ops JSON reports from task payloads."""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


PLACEHOLDER_BASES = {"", "<TASK_ENV_BASE_URL>", "TASK_ENV_BASE_URL"}


def money(value):
    return quantize(value, 2)


def ratio(value):
    return quantize(value, 4)


def quantize(value, places):
    epsilon = 10 ** (-(places + 6))
    adjusted = float(value) + (epsilon if value >= 0 else -epsilon)
    quantum = Decimal("1").scaleb(-places)
    return float(Decimal(str(adjusted)).quantize(quantum, rounding=ROUND_HALF_UP))


def safe_div(numerator, denominator):
    return 0.0 if not denominator else numerator / denominator


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_payloads(input_path):
    root = Path(input_path).resolve()
    candidates = [root, root / "payloads", root / "input" / "payloads"]
    for candidate in candidates:
        if (candidate / "request_memo.json").exists():
            return candidate
    raise SystemExit(f"Could not find payloads under {root}")


def parse_environment_md(path):
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("base_url:"):
            return line.split(":", 1)[1].strip()
    return ""


def clean_base_url(raw):
    value = (raw or "").strip().rstrip("/")
    if value in PLACEHOLDER_BASES or value.startswith("<"):
        return ""
    return value


def resolve_base_url(payloads, override):
    if override:
        return clean_base_url(override)

    env_payload = payloads / "environment_access.json"
    if env_payload.exists():
        from_payload = clean_base_url(load_json(env_payload).get("base_url", ""))
        if from_payload:
            return from_payload

    from_env = clean_base_url(os.environ.get("TASK_ENV_BASE_URL", ""))
    if from_env:
        return from_env

    from_md = clean_base_url(parse_environment_md(Path("/work/environment_access.md")))
    if from_md:
        return from_md

    return "http://task-env:9009"


class Api:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.cache = {}

    def get(self, endpoint):
        if endpoint not in self.cache:
            url = f"{self.base_url}{endpoint}"
            try:
                with urllib.request.urlopen(url, timeout=20) as response:
                    self.cache[endpoint] = json.load(response)
            except urllib.error.URLError as exc:
                raise SystemExit(f"Failed to fetch {url}: {exc}") from exc
        return self.cache[endpoint]


def ordered_top_level(answer, template):
    keys = template.get("required_top_level_keys") or []
    if not keys:
        return answer
    ordered = {key: answer[key] for key in keys if key in answer}
    for key, value in answer.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def sorted_ids(values):
    return sorted(values, key=str)


def rank_desc(rows, target_id):
    ordered = sorted(rows, key=lambda item: (-item["value"], item["id"]))
    for index, item in enumerate(ordered, start=1):
        if item["id"] == target_id:
            return index
    return None


def first_desc(rows):
    return sorted(rows, key=lambda item: (-item["value"], item["id"]))[0]["id"]


def first_asc(rows):
    return sorted(rows, key=lambda item: (item["value"], item["id"]))[0]["id"]


def period_sort_key(period):
    match = re.match(r"^M(\d+)$", str(period))
    return int(match.group(1)) if match else str(period)


class FinanceData:
    def __init__(self, api):
        self.branches = api.get("/api/finance/branches")
        self.period_map = api.get("/api/finance/period-map")
        self.accounts = api.get("/api/finance/accounts")
        self.records = api.get("/api/finance/records")
        self.branch_by_id = {row["branch_id"]: row for row in self.branches}
        self.period_by_label = {row["period"]: row for row in self.period_map}
        self.periods_by_year = defaultdict(list)
        for row in self.period_map:
            self.periods_by_year[row["fiscal_year"]].append(row["period"])
        for periods in self.periods_by_year.values():
            periods.sort(key=period_sort_key)
        self.account_category = {row["account"]: row["category"] for row in self.accounts}

    def category_total(self, branch_ids, category, periods):
        branch_set = set(branch_ids)
        period_list = list(periods)
        total = 0.0
        for row in self.records:
            if row["branch_id"] in branch_set and self.account_category.get(row["account"]) == category:
                total += sum(float(row["values"].get(period, 0.0)) for period in period_list)
        return total

    def account_total(self, branch_ids, account, periods):
        branch_set = set(branch_ids)
        period_list = list(periods)
        total = 0.0
        for row in self.records:
            if row["branch_id"] in branch_set and row["account"] == account:
                total += sum(float(row["values"].get(period, 0.0)) for period in period_list)
        return total

    def statement_raw(self, branch_ids, periods):
        revenue = self.category_total(branch_ids, "revenue", periods)
        cogs = self.category_total(branch_ids, "cogs", periods)
        sga = self.category_total(branch_ids, "sga", periods)
        allocations = self.category_total(branch_ids, "allocations", periods)
        gross_margin = revenue - cogs
        ebitda = gross_margin - sga - allocations
        return {
            "revenue": revenue,
            "cogs": cogs,
            "gross_margin": gross_margin,
            "sga": sga,
            "allocations": allocations,
            "ebitda": ebitda,
        }

    def statement_money(self, branch_ids, periods, include_cogs=True):
        raw = self.statement_raw(branch_ids, periods)
        keys = ["revenue", "cogs", "gross_margin", "sga", "allocations", "ebitda"]
        if not include_cogs:
            keys = ["revenue", "sga", "allocations", "ebitda"]
        return {key: money(raw[key]) for key in keys}

    def enrich_operating(self, statement, branch_ids, periods, include_arpu=False):
        raw = self.statement_raw(branch_ids, periods)
        statement["ebitda_margin"] = ratio(safe_div(raw["ebitda"], raw["revenue"]))
        if include_arpu:
            customers = self.account_total(branch_ids, "active_customers", periods)
            statement["arpu"] = money(safe_div(raw["revenue"], customers))
        labor = self.account_total(branch_ids, "labor_headcount", periods)
        statement["sales_per_labor_headcount"] = money(safe_div(raw["revenue"], labor))
        return statement

    def branch_ids_for_region(self, region_id):
        return sorted_ids([row["branch_id"] for row in self.branches if row["region_id"] == region_id])


def fiscal_compare_key(template, current_year, prior_year):
    for key in template.get("required_top_level_keys", []):
        if re.match(r"^fy\d+_vs_fy\d+$", key):
            return key
    return f"fy{current_year}_vs_fy{prior_year}"


def income_statement_key(template, period):
    for key in template.get("required_top_level_keys", []):
        if key.endswith("_income_statement"):
            return key
    return f"{period.lower()}_income_statement"


def branch_close(api, memo, template):
    data = FinanceData(api)
    branch_id = memo["target_branch_id"]
    close_period = memo["close_period"]
    prior_period = memo["prior_period"]
    branch = data.branch_by_id[branch_id]
    current_year = data.period_by_label[close_period]["fiscal_year"]
    prior_year = current_year - 1
    current_periods = data.periods_by_year[current_year]
    prior_periods = data.periods_by_year[prior_year]

    close_revenue = data.statement_raw([branch_id], [close_period])["revenue"]
    prior_revenue = data.statement_raw([branch_id], [prior_period])["revenue"]
    current_fy_raw = data.statement_raw([branch_id], current_periods)
    prior_fy_raw = data.statement_raw([branch_id], prior_periods)
    current_fy = data.statement_money([branch_id], current_periods)
    data.enrich_operating(current_fy, [branch_id], current_periods, include_arpu=True)

    region_ids = data.branch_ids_for_region(branch["region_id"])
    all_region_ids = sorted_ids({row["region_id"] for row in data.branches})
    region_rank_rows = [
        {
            "id": candidate_region,
            "value": data.statement_raw(data.branch_ids_for_region(candidate_region), current_periods)["ebitda"],
        }
        for candidate_region in all_region_ids
    ]
    all_branch_rows = []
    arpu_rows = []
    for candidate in sorted_ids(data.branch_by_id):
        candidate_current = data.statement_raw([candidate], current_periods)
        candidate_prior = data.statement_raw([candidate], prior_periods)
        growth = safe_div(candidate_current["revenue"] - candidate_prior["revenue"], candidate_prior["revenue"])
        customers = data.account_total([candidate], "active_customers", current_periods)
        all_branch_rows.append({"id": candidate, "value": growth})
        arpu_rows.append({"id": candidate, "value": safe_div(candidate_current["revenue"], customers)})

    compare = {
        f"fy{current_year}": current_fy,
        "revenue_growth_pct": ratio(safe_div(current_fy_raw["revenue"] - prior_fy_raw["revenue"], prior_fy_raw["revenue"])),
        "ebitda_growth_pct": ratio(safe_div(current_fy_raw["ebitda"] - prior_fy_raw["ebitda"], prior_fy_raw["ebitda"])),
    }

    first_year = min(data.periods_by_year)
    second_year = max(data.periods_by_year)
    answer = {
        "target_branch_id": branch_id,
        "target_branch_name": branch["branch_name"],
        "period_convention": {
            "M1_to_M12": f"FY{first_year}",
            "M13_to_M24": f"FY{second_year}",
            "current_month": close_period,
            "prior_month": prior_period,
        },
        income_statement_key(template, close_period): data.statement_money([branch_id], [close_period]),
        "mom_revenue_variance": {
            "amount": money(close_revenue - prior_revenue),
            "pct": ratio(safe_div(close_revenue - prior_revenue, prior_revenue)),
        },
        fiscal_compare_key(template, current_year, prior_year): compare,
        "region_context": {
            "region_id": branch["region_id"],
            "branch_ids": region_ids,
            f"fy{current_year}_ebitda": money(data.statement_raw(region_ids, current_periods)["ebitda"]),
            "ebitda_rank_desc": rank_desc(region_rank_rows, branch["region_id"]),
        },
        "branch_rankings": {
            "sales_growth_rank_desc": rank_desc(all_branch_rows, branch_id),
            "top_sales_growth_branch_id": first_desc(all_branch_rows),
            "top_arpu_branch_id": first_desc(arpu_rows),
        },
    }
    return ordered_top_level(answer, template)


def regional_report(api, memo, template):
    data = FinanceData(api)
    region_id = memo["target_region_id"]
    years = sorted(memo.get("requested_comparison_years") or data.periods_by_year)
    prior_year, current_year = years[0], years[-1]
    branch_ids = data.branch_ids_for_region(region_id)
    prior_periods = data.periods_by_year[prior_year]
    current_periods = data.periods_by_year[current_year]
    prior_raw = data.statement_raw(branch_ids, prior_periods)
    current_raw = data.statement_raw(branch_ids, current_periods)
    current_statement = data.statement_money(branch_ids, current_periods, include_cogs=False)
    data.enrich_operating(current_statement, branch_ids, current_periods, include_arpu=False)
    branch_ebitda = [
        {"id": bid, "value": data.statement_raw([bid], current_periods)["ebitda"]}
        for bid in branch_ids
    ]
    answer = {
        "region_id": region_id,
        "branch_ids": branch_ids,
        f"fy{prior_year}": data.statement_money(branch_ids, prior_periods, include_cogs=False),
        f"fy{current_year}": current_statement,
        "revenue_growth_pct": ratio(safe_div(current_raw["revenue"] - prior_raw["revenue"], prior_raw["revenue"])),
        "top_ebitda_branch_id": first_desc(branch_ebitda),
        "bottom_ebitda_branch_id": first_asc(branch_ebitda),
        "region_reconciliation_variance": money(current_raw["ebitda"] - sum(row["value"] for row in branch_ebitda)),
    }
    return ordered_top_level(answer, template)


def seniority_weekly(rate_book, years):
    for band in rate_book["seniority_weekly"]:
        max_years = band.get("max_years")
        if years >= band["min_years"] and (max_years is None or years <= max_years):
            return float(band["weekly_amount"])
    return 0.0


def compensation_rows(api, ensemble_id):
    return [row for row in api.get("/api/compensation/rosters") if row["ensemble_id"] == ensemble_id]


def compensation_totals(rate_book, rows, factors=None, years_add=0):
    factors = factors or {}
    mws_factor = factors.get("mws", 1.0)
    overscale_factor = factors.get("overscale", 1.0)
    seniority_factor = factors.get("seniority", 1.0)
    title_multiplier = factors.get("title_multiplier", 1.0)
    pay_types = list(rate_book["pay_types"])
    by_pay_type = {pay_type: 0.0 for pay_type in pay_types}
    by_quarter = {quarter: 0.0 for quarter in rate_book["quarter_weeks"]}

    for row in rows:
        for quarter, default_weeks in rate_book["quarter_weeks"].items():
            weeks = float(row.get("weeks_by_quarter", {}).get(quarter, default_weeks))
            title_pct = float(rate_book["title_premium_pct"].get(row.get("title", ""), 0.0))
            mws = float(rate_book["minimum_weekly_scale"]) * mws_factor * weeks
            title = 0.0
            if not row.get("combined_overscale_includes_title", False):
                title = float(rate_book["minimum_weekly_scale"]) * mws_factor * title_pct * title_multiplier * weeks
            seniority = seniority_weekly(rate_book, int(row["years_of_service"]) + years_add) * seniority_factor * weeks
            overscale = float(row.get("overscale_weekly", 0.0)) * overscale_factor * weeks
            values = {
                "Minimum Weekly Scale": mws,
                "Titled Position Premium": title,
                "Seniority": seniority,
                "Overscale": overscale,
            }
            for pay_type, value in values.items():
                by_pay_type[pay_type] += value
                by_quarter[quarter] += value

    total = sum(by_pay_type.values())
    return {"pay_type": by_pay_type, "quarter": by_quarter, "total": total}


def roster_counts(rate_book, rows):
    combined = sum(1 for row in rows if row.get("combined_overscale_includes_title", False))
    partial = 0
    for row in rows:
        weeks = row.get("weeks_by_quarter", {})
        if any(float(weeks.get(q, default)) != float(default) for q, default in rate_book["quarter_weeks"].items()):
            partial += 1
    return combined, partial


def rounded_pay_type_totals(raw_totals, pay_types):
    return {pay_type: money(raw_totals["pay_type"].get(pay_type, 0.0)) for pay_type in pay_types}


def rounded_quarter_totals(raw_totals, quarters):
    return {quarter: money(raw_totals["quarter"].get(quarter, 0.0)) for quarter in quarters}


def annual_from_rounded_quarters(raw_totals, quarters):
    return money(sum(rounded_quarter_totals(raw_totals, quarters).values()))


def largest_by_value(values, order):
    return sorted(order, key=lambda key: (-values.get(key, 0.0), order.index(key)))[0]


def compensation_current(api, memo, template):
    rate_book = api.get("/api/compensation/rate-book")
    rows = compensation_rows(api, memo["ensemble_id"])
    pay_types = list(rate_book["pay_types"])
    raw = compensation_totals(rate_book, rows)
    combined, partial = roster_counts(rate_book, rows)
    annual_pay_types = rounded_pay_type_totals(raw, pay_types)
    answer = {
        "ensemble_id": memo["ensemble_id"],
        "current_year": int(rate_book["current_year"]),
        "roster_count": len(rows),
        "pay_types": pay_types,
        "quarter_totals": rounded_quarter_totals(raw, rate_book["quarter_weeks"].keys()),
        "annual_pay_type_totals": annual_pay_types,
        "annual_total": annual_from_rounded_quarters(raw, rate_book["quarter_weeks"].keys()),
        "largest_pay_type": largest_by_value(raw["pay_type"], pay_types),
        "combined_overscale_employee_count": combined,
        "partial_quarter_employee_count": partial,
    }
    return ordered_top_level(answer, template)


def scenario_factors(scenario, year_key, previous=None):
    current = scenario.get(year_key, {})
    previous = previous or {"mws": 1.0, "overscale": 1.0, "seniority": 1.0, "title_multiplier": 1.0}
    return {
        "mws": previous["mws"] * (1.0 + float(current.get("mws_growth", 0.0))),
        "overscale": previous["overscale"] * (1.0 + float(current.get("overscale_growth", 0.0))),
        "seniority": previous["seniority"] * (1.0 + float(current.get("seniority_growth", 0.0))),
        "title_multiplier": previous["title_multiplier"] * float(current.get("title_pct_multiplier", 1.0)),
    }


def largest_growth_pay_type(current, future, pay_types):
    def growth(pay_type):
        base = current["pay_type"].get(pay_type, 0.0)
        next_value = future["pay_type"].get(pay_type, 0.0)
        if base == 0.0:
            return float("inf") if next_value > 0.0 else float("-inf")
        return (next_value - base) / base

    return sorted(pay_types, key=lambda key: (-growth(key), pay_types.index(key)))[0]


def compensation_forecast(api, memo, template):
    rate_book = api.get("/api/compensation/rate-book")
    rows = compensation_rows(api, memo["ensemble_id"])
    scenarios = api.get("/api/compensation/scenarios")
    scenario = scenarios[memo["scenario_id"]]
    pay_types = list(rate_book["pay_types"])

    current = compensation_totals(rate_book, rows)
    year_plus_1_factors = scenario_factors(scenario, "year_plus_1")
    year_plus_2_factors = scenario_factors(scenario, "year_plus_2", previous=year_plus_1_factors)
    year_plus_1 = compensation_totals(rate_book, rows, year_plus_1_factors, years_add=1)
    year_plus_2 = compensation_totals(rate_book, rows, year_plus_2_factors, years_add=2)
    combined, partial = roster_counts(rate_book, rows)

    answer = {
        "ensemble_id": memo["ensemble_id"],
        "scenario_id": memo["scenario_id"],
        "annual_totals": {
            "current": annual_from_rounded_quarters(current, rate_book["quarter_weeks"].keys()),
            "year_plus_1": annual_from_rounded_quarters(year_plus_1, rate_book["quarter_weeks"].keys()),
            "year_plus_2": annual_from_rounded_quarters(year_plus_2, rate_book["quarter_weeks"].keys()),
        },
        "growth_rates": {
            "year_plus_1_vs_current": ratio(safe_div(year_plus_1["total"] - current["total"], current["total"])),
            "year_plus_2_vs_year_plus_1": ratio(safe_div(year_plus_2["total"] - year_plus_1["total"], year_plus_1["total"])),
        },
        "year_plus_2_quarter_totals": rounded_quarter_totals(year_plus_2, rate_book["quarter_weeks"].keys()),
        "year_plus_2_pay_type_totals": rounded_pay_type_totals(year_plus_2, pay_types),
        "largest_growth_pay_type": largest_growth_pay_type(current, year_plus_2, pay_types),
        "combined_overscale_employee_count": combined,
        "partial_quarter_employee_count": partial,
    }
    return ordered_top_level(answer, template)


def parse_time_to_minutes(value):
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def service_category(service_type):
    if service_type == "Performance":
        return "performance"
    if service_type == "Audit":
        return "audit"
    if service_type == "Rehearsal":
        return "rehearsal"
    if "Sound Check" in service_type:
        return "sound_check"
    return re.sub(r"[^a-z0-9]+", "_", service_type.lower()).strip("_")


def base_service_amount(rate_book, service):
    service_type = service["service_type"]
    rate = float(rate_book["service_rates"].get(service_type, 0.0))
    if service_type == "Rehearsal":
        return max(float(service.get("duration_hours", 0.0)), 3.0) * rate
    return rate


def musician_pay(rate_book, musician, schedule_by_id):
    categories = defaultdict(float)
    performance_base = 0.0
    for service_id in musician.get("assigned_service_ids", []):
        service = schedule_by_id[service_id]
        amount = base_service_amount(rate_book, service)
        category = service_category(service["service_type"])
        categories[category] += amount
        if category == "performance":
            performance_base += amount

    substitute_adjustment = 0.0
    if musician.get("substitute", False):
        substitute_adjustment = performance_base * 0.5
        categories["performance"] += substitute_adjustment
        categories["substitute_adjustment"] += substitute_adjustment

    service_pay_for_premiums = sum(
        amount
        for category, amount in categories.items()
        if category in {"performance", "audit", "rehearsal", "sound_check"}
    )

    premium_pct = 0.0
    premiums = rate_book["premium_pct"]
    if musician.get("principal", False) or musician.get("lead", False):
        premium_pct += float(premiums.get("principal_or_lead", 0.0))
    if musician.get("electronic", False):
        premium_pct += float(premiums.get("electronic", 0.0))
    if musician.get("quartet", False):
        premium_pct += float(premiums.get("quartet", 0.0))
    if musician.get("concertmaster", False):
        premium_pct += float(premiums.get("concertmaster", 0.0))
    premium = service_pay_for_premiums * premium_pct
    if premium:
        categories["premium"] += premium

    doubles = int(musician.get("doubles", 0) or 0)
    if doubles > 0:
        doubles_pct = float(premiums.get("first_double", 0.0))
        doubles_pct += max(0, doubles - 1) * float(premiums.get("additional_double", 0.0))
        categories["doubles"] += service_pay_for_premiums * doubles_pct

    if musician.get("vacation_eligible", False):
        vacation_base = service_pay_for_premiums + categories.get("premium", 0.0) + categories.get("doubles", 0.0)
        categories["vacation"] += vacation_base * float(premiums.get("vacation", 0.0))

    if not musician.get("substitute", False):
        guarantee_gap = float(rate_book.get("weekly_guarantee", 0.0)) - service_pay_for_premiums
        if guarantee_gap > 0.0:
            categories["guarantee_adjustment"] += guarantee_gap

    total = sum(categories.values())
    rounded_categories = {
        category: money(amount)
        for category, amount in sorted(categories.items())
        if abs(amount) > 1e-9
    }
    return total, rounded_categories, categories


def conflict_flags(rate_book, schedule):
    flags = set()
    earliest = parse_time_to_minutes(rate_book["conflict_thresholds"]["rehearsal_earliest_start"])
    latest = parse_time_to_minutes(rate_book["conflict_thresholds"]["rehearsal_latest_end"])
    for service in schedule:
        service_type = service["service_type"]
        duration = float(service.get("duration_hours", 0.0))
        limit = rate_book.get("service_time_limits", {}).get(service_type)
        if limit is not None and duration > float(limit) + 1e-9:
            flags.add("SERVICE_OVER_TIME_LIMIT")
        if "Sound Check" in service_type and limit is not None and abs(duration - float(limit)) > 1e-9:
            flags.add("SOUND_CHECK_DURATION_MISMATCH")
        if service_type == "Rehearsal":
            if parse_time_to_minutes(service["start_time"]) < earliest:
                flags.add("REHEARSAL_EARLY_START")
            if parse_time_to_minutes(service["end_time"]) > latest:
                flags.add("REHEARSAL_LATE_END")
    return sorted(flags)


def payroll_review(api, memo, template):
    rate_book = api.get("/api/payroll/rate-book")
    productions = api.get("/api/payroll/productions")
    production = next(row for row in productions if row["production_id"] == memo["production_id"])
    schedule_by_id = {row["service_id"]: row for row in production["schedule"]}

    service_counts = defaultdict(int)
    for service in production["schedule"]:
        service_counts[service["service_type"]] += 1

    category_totals_raw = defaultdict(float)
    per_musician = []
    top_id = None
    top_total = None
    for musician in sorted(production["roster"], key=lambda row: row["musician_id"]):
        total, rounded_categories, raw_categories = musician_pay(rate_book, musician, schedule_by_id)
        for category, amount in raw_categories.items():
            category_totals_raw[category] += amount
        per_musician.append(
            {
                "musician_id": musician["musician_id"],
                "name": musician["name"],
                "total": money(total),
                "categories": rounded_categories,
            }
        )
        if top_total is None or total > top_total or (total == top_total and musician["musician_id"] < top_id):
            top_total = total
            top_id = musician["musician_id"]

    category_totals = {
        category: money(amount)
        for category, amount in sorted(category_totals_raw.items())
        if abs(amount) > 1e-9
    }
    answer = {
        "production_id": memo["production_id"],
        "service_counts": {key: service_counts[key] for key in sorted(service_counts)},
        "category_totals": category_totals,
        "weekly_total": money(sum(category_totals_raw.values())),
        "conflict_flags": conflict_flags(rate_book, production["schedule"]),
        "per_musician": per_musician,
        "top_paid_musician_id": top_id,
    }
    return ordered_top_level(answer, template)


def dispatch(api, memo, template):
    if "target_branch_id" in memo:
        return branch_close(api, memo, template)
    if "target_region_id" in memo:
        return regional_report(api, memo, template)
    if "production_id" in memo:
        return payroll_review(api, memo, template)
    if "scenario_id" in memo:
        return compensation_forecast(api, memo, template)
    if "ensemble_id" in memo:
        return compensation_current(api, memo, template)
    raise SystemExit("Could not classify request_memo.json")


def main():
    parser = argparse.ArgumentParser(description="Compute a Crescent Finance Ops answer JSON object.")
    parser.add_argument("input_path", help="Task input directory, task root, or payloads directory")
    parser.add_argument("--base-url", help="Finance Ops API base URL override")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    payloads = find_payloads(args.input_path)
    memo = load_json(payloads / "request_memo.json")
    template = load_json(payloads / "answer_template.json")
    api = Api(resolve_base_url(payloads, args.base_url))
    answer = dispatch(api, memo, template)
    json.dump(answer, sys.stdout, indent=2 if args.pretty else None)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
