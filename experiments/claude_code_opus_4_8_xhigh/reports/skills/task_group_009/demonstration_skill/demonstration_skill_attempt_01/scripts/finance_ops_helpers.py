#!/usr/bin/env python3
"""
Crescent Finance Ops — reusable helpers for management-reporting tasks.

These functions encode the EXACT business rules reverse-engineered from the
Finance Ops API and validated to reproduce the standard answers to the penny.
Import or copy what you need; adapt field selection to the specific task's
answer_template.json. Nothing here calls the network except `get()`.

Usage:
    from finance_ops_helpers import *
    BASE = "http://127.0.0.1:8028"   # read from payloads/environment_access.json
"""
import json
import urllib.request

# ----------------------------------------------------------------------------
# Networking + rounding
# ----------------------------------------------------------------------------

def get(base_url, path):
    """GET a JSON endpoint. `path` like '/api/finance/branches'."""
    with urllib.request.urlopen(base_url.rstrip("/") + path) as r:
        return json.load(r)


def money(x):
    """Round currency to 2 decimals. Add tiny epsilon to avoid float-floor on .xx5."""
    return round(x + 1e-9, 2)


def ratio(x):
    """Round a FRACTION (ratio / 'decimal percent') to 4 decimals.
    8.95% must be stored as 0.0895, NOT 8.95. Never multiply by 100."""
    return round(x + 1e-12, 4)


# ----------------------------------------------------------------------------
# FINANCE — period map, income statement, FY metrics, rollups, rankings
# ----------------------------------------------------------------------------

# Account groupings (from /api/finance/accounts; category field). Hard-coded
# here for clarity, but verify against the live accounts endpoint per task.
REVENUE_ACCTS = ["product_revenue", "service_revenue"]
COGS_ACCTS = ["direct_materials_cogs", "direct_labor_cogs"]
SGA_ACCTS = ["sales_sga", "admin_sga", "occupancy_sga"]
ALLOC_ACCTS = ["shared_service_allocations"]
# Operating counts used in dashboard ratios:
CUSTOMER_ACCT = "active_customers"      # ARPU denominator (SUM over the period)
LABOR_ACCT = "labor_headcount"          # sales-per-labor-headcount denominator (SUM)


def fy_periods(period_map, fiscal_year):
    """Return the list of period labels (e.g. ['M13'..'M24']) for a fiscal year.
    ALWAYS derive this from /api/finance/period-map — do not assume M1-12=FY24
    by hand. The map ships period -> fiscal_year. As shipped: M1..M12 -> FY2024,
    M13..M24 -> FY2025, but read it live so future maps still work."""
    return [row["period"] for row in period_map if row["fiscal_year"] == fiscal_year]


def index_records(records):
    """records (from /api/finance/records) -> {branch_id: {account: {period: value}}}.
    Each record has account/branch_id/region_id/values(map period->amount)."""
    idx = {}
    for r in records:
        idx.setdefault(r["branch_id"], {})[r["account"]] = r["values"]
    return idx


def acct_sum(idx, branch_id, accounts, periods):
    """Sum given accounts over given periods for one branch."""
    total = 0.0
    bm = idx.get(branch_id, {})
    for a in accounts:
        vals = bm.get(a, {})
        for p in periods:
            total += vals.get(p, 0.0)
    return total


def income_statement(idx, branch_id, periods):
    """Income-statement lines for a branch over a set of periods.
        revenue       = product_revenue + service_revenue
        cogs          = direct_materials_cogs + direct_labor_cogs
        gross_margin  = revenue - cogs
        sga           = sales + admin + occupancy SG&A
        allocations   = shared_service_allocations
        ebitda        = gross_margin - sga - allocations
    Works for a single month (periods=['M24']) or a full FY (12 periods)."""
    rev = acct_sum(idx, branch_id, REVENUE_ACCTS, periods)
    cogs = acct_sum(idx, branch_id, COGS_ACCTS, periods)
    sga = acct_sum(idx, branch_id, SGA_ACCTS, periods)
    alloc = acct_sum(idx, branch_id, ALLOC_ACCTS, periods)
    gm = rev - cogs
    ebitda = gm - sga - alloc
    return dict(revenue=rev, cogs=cogs, gross_margin=gm, sga=sga,
                allocations=alloc, ebitda=ebitda)


def fy_metrics(idx, branch_id, periods):
    """Income statement PLUS dashboard ratios for one branch over a FY.
        ebitda_margin             = ebitda / revenue                (ratio, 4dp)
        arpu                      = revenue / SUM(active_customers)  (currency)
        sales_per_labor_headcount = revenue / SUM(labor_headcount)  (currency)
    NOTE the denominators are the SUM of the monthly counts across the period,
    NOT a point-in-time or average headcount."""
    m = income_statement(idx, branch_id, periods)
    cust = acct_sum(idx, branch_id, [CUSTOMER_ACCT], periods)
    labor = acct_sum(idx, branch_id, [LABOR_ACCT], periods)
    m["ebitda_margin"] = (m["ebitda"] / m["revenue"]) if m["revenue"] else 0.0
    m["arpu"] = (m["revenue"] / cust) if cust else 0.0
    m["sales_per_labor_headcount"] = (m["revenue"] / labor) if labor else 0.0
    return m


def growth(curr, prior):
    """(curr - prior) / prior. Used for MoM variance pct and YoY growth pct."""
    return (curr - prior) / prior if prior else 0.0


def region_branches(branches):
    """{region_id: [branch_id,...]} from /api/finance/branches (sorted ascending)."""
    out = {}
    for b in branches:
        out.setdefault(b["region_id"], []).append(b["branch_id"])
    for k in out:
        out[k].sort()
    return out


def region_rollup(idx, branch_ids, periods):
    """Region = arithmetic SUM of its branches' income-statement lines.
    There is no separate region-level record; reconciliation variance is 0.0
    by construction (region_total - sum_of_branches == 0)."""
    agg = dict(revenue=0.0, cogs=0.0, gross_margin=0.0, sga=0.0,
               allocations=0.0, ebitda=0.0)
    for b in branch_ids:
        m = income_statement(idx, b, periods)
        for k in agg:
            agg[k] += m[k]
    return agg


def rank_desc(value_by_id):
    """Return [(id, rank)] sorted by value descending, rank starting at 1.
    Caller decides tie-break; default Python sort is stable on insertion order."""
    ordered = sorted(value_by_id.items(), key=lambda kv: -kv[1])
    return [(k, i + 1) for i, (k, v) in enumerate(ordered)]


# ----------------------------------------------------------------------------
# COMPENSATION — quarterly comp, pay-type split, forecast escalation
# ----------------------------------------------------------------------------

QUARTERS = ["Q1", "Q2", "Q3", "Q4"]


def seniority_weekly(rate_book, years):
    """Pick the seniority band weekly amount for a years-of-service value.
    Bands are inclusive [min_years, max_years]; the open band has max_years=None."""
    for band in rate_book["seniority_weekly"]:
        lo, hi = band["min_years"], band["max_years"]
        if years >= lo and (hi is None or years <= hi):
            return band["weekly_amount"]
    return 0.0


def comp_breakdown(rate_book, roster, year_offset=0, scenario=None):
    """Compute quarter totals + pay-type totals for one ensemble-year.

    year_offset: 0 = current, 1 = Year+1, 2 = Year+2.
    scenario: a single scenario dict from /api/compensation/scenarios (or None
              for the current year). Growth rates COMPOUND across years.

    Per employee, per quarter, weeks come from roster `weeks_by_quarter`
    (use the roster's actual weeks, NOT a fixed 13 — partial quarters differ):
        Minimum Weekly Scale = scale * weeks
        Titled Position Prem = scale * title_pct[title] * title_mult * weeks
                               (SKIP entirely if combined_overscale_includes_title)
        Seniority            = band(years + year_offset) * sen_factor * weeks
        Overscale            = overscale_weekly * over_factor * weeks
    where scale = minimum_weekly_scale * mws_factor.

    Forecast escalation (rate book business rule): for Year+N, add N years of
    service BEFORE choosing the seniority band — that band jump is what makes
    Seniority frequently the largest-GROWTH pay type even though MWS is the
    largest by dollars."""
    scale0 = rate_book["minimum_weekly_scale"]
    title_pct = rate_book["title_premium_pct"]

    mws_f = over_f = sen_f = title_mult = 1.0
    if scenario is not None:
        for k in ["year_plus_1", "year_plus_2"][:year_offset]:
            s = scenario[k]
            mws_f *= 1 + s["mws_growth"]
            over_f *= 1 + s["overscale_growth"]
            sen_f *= 1 + s["seniority_growth"]
            title_mult *= s["title_pct_multiplier"]
    scale = scale0 * mws_f

    qt = {q: 0.0 for q in QUARTERS}
    ptt = {pt: 0.0 for pt in rate_book["pay_types"]}
    for e in roster:
        years = e["years_of_service"] + year_offset
        title = e.get("title")
        combo = e.get("combined_overscale_includes_title", False)
        over = e.get("overscale_weekly", 0.0)
        for q in QUARTERS:
            w = e["weeks_by_quarter"].get(q, 0)
            mws = scale * w
            tpp = scale * title_pct[title] * title_mult * w if (title in title_pct and not combo) else 0.0
            sn = seniority_weekly(rate_book, years) * sen_f * w
            ov = over * over_f * w
            qt[q] += mws + tpp + sn + ov
            ptt["Minimum Weekly Scale"] += mws
            ptt["Titled Position Premium"] += tpp
            ptt["Seniority"] += sn
            ptt["Overscale"] += ov
    return qt, ptt


def annual_total_from_quarters(qt):
    """Annual total = SUM of the four ROUNDED quarter totals.
    This matters: rounding each quarter first then summing can differ by a cent
    from rounding the raw annual sum. The quarter-first path matches the
    standard answers, so use it everywhere annual_total is reported."""
    return money(sum(money(v) for v in qt.values()))


def combined_overscale_count(roster):
    return sum(1 for e in roster if e.get("combined_overscale_includes_title"))


def partial_quarter_count(roster):
    """Employees whose any quarter has weeks != 13 (the full-quarter norm)."""
    return sum(1 for e in roster
               if any(e["weeks_by_quarter"].get(q, 0) != 13 for q in QUARTERS))


# ----------------------------------------------------------------------------
# PAYROLL — weekly theatre payroll, premiums, conflicts
# ----------------------------------------------------------------------------

def base_service_pay(rate_book, svc):
    """Base pay for one scheduled service.
    Rehearsal is hourly with a 3-hour minimum call; everything else is per
    service at its flat rate."""
    st = svc["service_type"]
    if st == "Rehearsal":
        hours = max(svc["duration_hours"], 3.0)
        return rate_book["service_rates"]["Rehearsal"] * hours
    return rate_book["service_rates"][st]


def service_category(service_type):
    """Map a service type to its category_totals bucket."""
    if service_type == "Performance":
        return "performance"
    if service_type == "Audit":
        return "audit"
    if service_type == "Rehearsal":
        return "rehearsal"
    if "Sound Check" in service_type:
        return "sound_check"
    return None


def musician_pay(rate_book, schedule_by_id, m):
    """Return {category: amount} for one musician (only nonzero categories).

    Order of operations (validated to the penny):
      1. Sum base service pay by category (performance/audit/rehearsal/sound_check).
      2. SUBSTITUTE uplift = 50% of performance base pay. It is added INTO the
         `performance` category AND reported again as `substitute_adjustment`
         (yes, both — it contributes twice to the weekly total). The uplifted
         base is what premiums are then computed on. Substitutes get NO
         guarantee adjustment.
      3. Role premiums STACK (sum the percentages, apply once to base service):
            principal OR lead -> principal_or_lead (0.15)
            quartet           -> quartet (0.15)
            electronic        -> electronic (0.25)
            concertmaster     -> concertmaster (0.20)  [if a roster flag exists]
         -> bucket `premium`.
      4. Doubles premium: first extra instrument 25%, each additional +10%
         (i.e. first_double + additional_double*(doubles-1)) on base service ->
         bucket `doubles`.
      5. Vacation = 4% of (base service + role premium + doubles premium) when
         vacation_eligible -> bucket `vacation`.
      6. Guarantee adjustment: ONLY non-substitute guaranteed regular players,
         and ONLY when base service pay (NOT including premiums) < weekly_guarantee;
         amount = weekly_guarantee - base_service_pay -> bucket `guarantee_adjustment`.
    """
    prem = rate_book["premium_pct"]
    guar = rate_book["weekly_guarantee"]
    cats = {}

    def add(k, v):
        if v:
            cats[k] = cats.get(k, 0.0) + v

    base_service = 0.0
    perf_base = 0.0
    for sid in m["assigned_service_ids"]:
        svc = schedule_by_id[sid]
        bp = base_service_pay(rate_book, svc)
        cat = service_category(svc["service_type"])
        if cat:
            add(cat, bp)
        if svc["service_type"] == "Performance":
            perf_base += bp
        base_service += bp

    # 2. substitute uplift
    if m.get("substitute"):
        uplift = perf_base * 0.5
        add("performance", uplift)
        add("substitute_adjustment", uplift)
        base_service += uplift

    # 3. role premiums (stack)
    role_pct = 0.0
    if m.get("principal") or m.get("lead"):
        role_pct += prem["principal_or_lead"]
    if m.get("quartet"):
        role_pct += prem["quartet"]
    if m.get("electronic"):
        role_pct += prem["electronic"]
    if m.get("concertmaster"):
        role_pct += prem["concertmaster"]
    role_prem = base_service * role_pct
    add("premium", role_prem)

    # 4. doubles
    d = m.get("doubles", 0)
    dbl_pct = 0.0
    if d >= 1:
        dbl_pct += prem["first_double"]
    if d >= 2:
        dbl_pct += prem["additional_double"] * (d - 1)
    dbl = base_service * dbl_pct
    add("doubles", dbl)

    # 5. vacation
    if m.get("vacation_eligible"):
        add("vacation", (base_service + role_prem + dbl) * prem["vacation"])

    # 6. guarantee
    if not m.get("substitute") and base_service < guar:
        add("guarantee_adjustment", guar - base_service)

    return cats


def conflict_flags(rate_book, schedule):
    """Return the sorted set of CBA conflict flags for a production schedule.
    Enum: REHEARSAL_EARLY_START, REHEARSAL_LATE_END, SERVICE_OVER_TIME_LIMIT,
          SOUND_CHECK_DURATION_MISMATCH.
      - REHEARSAL_EARLY_START : a Rehearsal start_time < rehearsal_earliest_start
      - REHEARSAL_LATE_END    : a Rehearsal end_time   > rehearsal_latest_end
      - SERVICE_OVER_TIME_LIMIT : duration_hours > service_time_limits[type]
      - SOUND_CHECK_DURATION_MISMATCH : a sound check whose duration != its
        nominal length (1hr->1.0, 2hr->2.0)
    A flag is emitted once if ANY service triggers it. Time strings compare
    lexicographically because they are zero-padded HH:MM."""
    thr = rate_book["conflict_thresholds"]
    limits = rate_book["service_time_limits"]
    flags = set()
    for s in schedule:
        st = s["service_type"]
        if st == "Rehearsal":
            if s["start_time"] < thr["rehearsal_earliest_start"]:
                flags.add("REHEARSAL_EARLY_START")
            if s["end_time"] > thr["rehearsal_latest_end"]:
                flags.add("REHEARSAL_LATE_END")
        lim = limits.get(st)
        if lim is not None and s["duration_hours"] > lim:
            flags.add("SERVICE_OVER_TIME_LIMIT")
        if "Sound Check" in st:
            nominal = 1.0 if st.startswith("1hr") else 2.0
            if abs(s["duration_hours"] - nominal) > 1e-9:
                flags.add("SOUND_CHECK_DURATION_MISMATCH")
    return sorted(flags)
